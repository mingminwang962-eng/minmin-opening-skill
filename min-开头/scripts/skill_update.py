"""Check and install an approved min-开头 release from its download site."""

import argparse
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import sys
import tempfile
import time
from urllib.parse import quote
from urllib.request import HTTPRedirectHandler, build_opener
import zipfile

BASE = "https://tools.minmin11538.cn/opening/"
ARCHIVE_ROOT = "minmin-opening-skill"
SKILL = "min-开头"
SKILL_ENTRY = f"{SKILL}/SKILL.md"
CHECK_INTERVAL = 24 * 60 * 60
MAX_PACKAGE_BYTES = 64 * 1024 * 1024
MAX_EXPANDED_BYTES = 128 * 1024 * 1024
VERSION = re.compile(r"(0|[1-9][0-9]{0,5})\.(0|[1-9][0-9]{0,5})\.(0|[1-9][0-9]{0,5})")


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def fetch(url, limit, timeout):
    with build_opener(NoRedirect()).open(url, timeout=timeout) as response:
        body = response.read(limit + 1)
    if len(body) > limit:
        raise ValueError("下载大小超过预期")
    return body


def version_key(version):
    match = VERSION.fullmatch(version) if isinstance(version, str) else None
    if not match:
        raise ValueError("版本号格式无效")
    return tuple(map(int, match.groups()))


def read_release():
    release = json.loads(fetch(BASE + "release.json", 32 * 1024, 5))
    if not isinstance(release, dict):
        raise ValueError("版本清单格式无效")
    version = release.get("version")
    version_key(version)
    expected_url = BASE + "downloads/" + quote(f"{ARCHIVE_ROOT}-v{version}.zip")
    if release.get("download_url") != expected_url:
        raise ValueError("下载地址与官方版本路径不一致")
    if release.get("archive_root") != ARCHIVE_ROOT or release.get("skill_entry") != SKILL_ENTRY:
        raise ValueError("安装包入口不匹配")
    if release.get("release_status") == "local_preview":
        raise ValueError("此版本为本地预览")
    size = release.get("bytes")
    digest = release.get("sha256")
    if type(size) is not int or not 1 <= size <= MAX_PACKAGE_BYTES:
        raise ValueError("安装包大小无效")
    if not isinstance(digest, str) or not re.fullmatch("[a-f0-9]{64}", digest):
        raise ValueError("SHA-256 格式无效")
    notice = release.get("notice")
    release["notice"] = " ".join(notice.split())[:120] if isinstance(notice, str) else ""
    return release


def check(skill_dir, state_file):
    try:
        current = (skill_dir / "VERSION").read_text(encoding="utf-8").strip()
        current_key = version_key(current)
        now = int(time.time())
        try:
            record = json.loads(state_file.read_text(encoding="utf-8"))
            if (record["version"] == current and type(record["at"]) is int
                    and 0 <= now - record["at"] < CHECK_INTERVAL):
                return None
        except (OSError, ValueError, KeyError, TypeError):
            pass
        state_file.parent.mkdir(parents=True, exist_ok=True)
        state_file.write_text(json.dumps({"at": now, "version": current}), encoding="utf-8")
        release = read_release()
        return release if version_key(release["version"]) > current_key else None
    except (OSError, ValueError):
        return None


def unpack_skill(package, stage, version):
    skill_root = PurePosixPath(ARCHIVE_ROOT, SKILL)
    with zipfile.ZipFile(io.BytesIO(package)) as archive:
        members = archive.infolist()
        if sum(member.file_size for member in members) > MAX_EXPANDED_BYTES:
            raise ValueError("解压大小超出上限")
        seen = set()
        for member in members:
            name = member.orig_filename
            parts = name.rstrip("/").split("/")
            mode = stat.S_IFMT(member.external_attr >> 16)
            key = name.rstrip("/").casefold()
            if (parts[0] != ARCHIVE_ROOT or any(part in {"", ".", ".."} for part in parts)
                    or any(char in name for char in '\\:\x00')
                    or any(part.endswith((" ", ".")) for part in parts)
                    or mode not in (0, stat.S_IFREG, stat.S_IFDIR) or key in seen):
                raise ValueError("ZIP 含不安全或重复的路径")
            seen.add(key)
            path = PurePosixPath(*parts)
            if skill_root not in path.parents or member.is_dir():
                continue
            output = stage / SKILL / path.relative_to(skill_root)
            output.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(member) as source, output.open("xb") as destination:
                shutil.copyfileobj(source, destination)
        if archive.read(f"{ARCHIVE_ROOT}/VERSION").decode("utf-8").strip() != version:
            raise ValueError("ZIP 版本与版本清单不一致")
    skill_dir = stage / SKILL
    if (skill_dir / "VERSION").read_text(encoding="utf-8").strip() != version:
        raise ValueError("Skill 版本与版本清单不一致")
    if (not re.search(rf"^name: {re.escape(SKILL)}\s*$",
                      (skill_dir / "SKILL.md").read_text(encoding="utf-8"), re.M)
            or not (skill_dir / "scripts/skill_update.py").is_file()):
        raise ValueError("安装包缺少 Skill 入口或更新器")
    return skill_dir


def apply(skill_dir, expected_version):
    if skill_dir.name != SKILL or skill_dir.is_symlink():
        raise ValueError("目标必须是已确认的 Skill 安装目录")
    lock = skill_dir.parent / f".{SKILL}-update.lock"
    try:
        lock.mkdir()
    except FileExistsError as error:
        raise ValueError("已有更新正在进行，或上次更新尚未恢复") from error
    stage = None
    backup = None
    try:
        current = version_key((skill_dir / "VERSION").read_text(encoding="utf-8").strip())
        release = read_release()
        if release["version"] != expected_version:
            raise ValueError("线上版本已变更，请重新确认要更新的版本")
        if version_key(expected_version) <= current:
            raise ValueError("本机已是当前或更高版本")
        package = fetch(release["download_url"], release["bytes"], 25)
        if len(package) != release["bytes"] or hashlib.sha256(package).hexdigest() != release["sha256"]:
            raise ValueError("安装包字节数或 SHA-256 校验失败")
        stage = Path(tempfile.mkdtemp(prefix=f".{SKILL}-update-", dir=skill_dir.parent))
        replacement = unpack_skill(package, stage, expected_version)
        # Keep a profile explicitly maintained inside an older installation.
        # The preferred external user profile never enters this release directory.
        profile = Path("references/创作者背书档案.md")
        if (skill_dir / profile).is_file():
            shutil.copy2(skill_dir / profile, replacement / profile)
        backup = stage / "previous"
        skill_dir.rename(backup)
        try:
            replacement.rename(skill_dir)
        except BaseException:
            backup.rename(skill_dir)
            raise
        return backup
    finally:
        if stage is not None and (backup is None or not backup.exists()):
            shutil.rmtree(stage, ignore_errors=True)
        lock.rmdir()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    sub.add_parser("check")
    install = sub.add_parser("apply")
    install.add_argument("--installed-dir", required=True, type=Path)
    install.add_argument("--version", required=True)
    args = parser.parse_args()
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        skill_dir = Path(__file__).resolve().parents[1]
        if args.action == "check":
            key = hashlib.sha256(str(skill_dir).encode()).hexdigest()[:16]
            state = Path.home() / ".cache" / "minmin-skills" / "opening-update" / f"{key}.json"
            release = check(skill_dir, state)
            if release:
                print(json.dumps({"version": release["version"], "notice": release["notice"]}, ensure_ascii=False))
        else:
            if args.installed_dir.is_symlink() or args.installed_dir.resolve() != skill_dir:
                raise ValueError("请使用已确认的安装目录中的更新器")
            backup = apply(skill_dir, args.version)
            print(json.dumps({"version": args.version, "backup": str(backup)}, ensure_ascii=False))
        return 0
    except (OSError, KeyError, ValueError, zipfile.BadZipFile, RuntimeError) as error:
        sys.stderr.reconfigure(encoding="utf-8")
        print(f"min-开头更新失败：{error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
