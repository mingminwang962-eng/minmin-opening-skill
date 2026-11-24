import hashlib
import importlib.util
import io
from pathlib import Path
import tempfile
import unittest
from unittest import mock
import zipfile

SCRIPT = Path(__file__).resolve().parents[1] / "min-开头/scripts/skill_update.py"
ROOT = "minmin-opening-skill"
ENTRY = ROOT + "/min-开头"


class SkillUpdateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.skill = self.root / "skills/min-开头"
        self.skill.mkdir(parents=True)
        (self.skill / "VERSION").write_text("0.9.7")
        (self.skill / "old.txt").write_text("old")
        self.state = self.root / "state/check.json"
        self.notes = self.root / "user-notes.txt"
        self.notes.write_text("keep")
        spec = importlib.util.spec_from_file_location("skill_update", SCRIPT)
        self.update = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.update)

    def package(self, version="0.9.8", extra=None):
        out = io.BytesIO()
        with zipfile.ZipFile(out, "w") as archive:
            archive.writestr(ROOT + "/VERSION", version)
            archive.writestr(ENTRY + "/VERSION", version)
            archive.writestr(ENTRY + "/SKILL.md", "---\nname: min-开头\n---\n")
            archive.writestr(ENTRY + "/scripts/skill_update.py", SCRIPT.read_bytes())
            archive.writestr(ENTRY + "/references/readme.md", "new")
            if extra:
                archive.writestr(*extra)
        return out.getvalue()

    def release(self, package, version="0.9.8"):
        return {
            "version": version,
            "archive_root": ROOT,
            "skill_entry": "min-开头/SKILL.md",
            "download_url": self.update.BASE + "downloads/" + self.update.quote(f"{ROOT}-v{version}.zip"),
            "sha256": hashlib.sha256(package).hexdigest(),
            "bytes": len(package),
            "notice": "新增更新检查",
        }

    def test_check_only_notifies_for_newer_release_and_is_throttled(self):
        release = self.release(self.package())
        with mock.patch.object(self.update, "read_release", return_value=release) as remote:
            self.assertEqual(self.update.check(self.skill, self.state), release)
            self.assertIsNone(self.update.check(self.skill, self.state))
        remote.assert_called_once_with()
        self.assertEqual((self.skill / "VERSION").read_text(), "0.9.7")

    def test_old_or_same_release_is_silent(self):
        with mock.patch.object(self.update, "read_release", return_value=self.release(self.package(), "0.9.7")):
            self.assertIsNone(self.update.check(self.skill, self.state))

    def test_network_failure_does_not_block_task(self):
        with mock.patch.object(self.update, "read_release", side_effect=OSError("offline")):
            self.assertIsNone(self.update.check(self.skill, self.state))
        self.assertEqual((self.skill / "VERSION").read_text(), "0.9.7")

    def test_confirmed_release_installs_only_skill_and_keeps_backup(self):
        package = self.package()
        with mock.patch.object(self.update, "read_release", return_value=self.release(package)), \
             mock.patch.object(self.update, "fetch", return_value=package):
            backup = self.update.apply(self.skill, "0.9.8")
        self.assertEqual((self.skill / "VERSION").read_text(), "0.9.8")
        self.assertTrue((self.skill / "references/readme.md").is_file())
        self.assertEqual((backup / "old.txt").read_text(), "old")
        self.assertEqual(self.notes.read_text(), "keep")

    def test_bad_hash_leaves_install_in_place(self):
        package = self.package()
        with mock.patch.object(self.update, "read_release", return_value=self.release(package)), \
             mock.patch.object(self.update, "fetch", return_value=b"!" + package[1:]):
            with self.assertRaisesRegex(ValueError, "SHA-256"):
                self.update.apply(self.skill, "0.9.8")
        self.assertEqual((self.skill / "VERSION").read_text(), "0.9.7")

    def test_unsafe_archive_is_rejected(self):
        package = self.package(extra=(ENTRY + "/../escape.txt", "bad"))
        with mock.patch.object(self.update, "read_release", return_value=self.release(package)), \
             mock.patch.object(self.update, "fetch", return_value=package):
            with self.assertRaisesRegex(ValueError, "路径"):
                self.update.apply(self.skill, "0.9.8")
        self.assertEqual((self.skill / "VERSION").read_text(), "0.9.7")

    def test_changed_release_requires_new_confirmation(self):
        package = self.package("0.9.9")
        with mock.patch.object(self.update, "read_release", return_value=self.release(package, "0.9.9")), \
             mock.patch.object(self.update, "fetch") as fetch:
            with self.assertRaisesRegex(ValueError, "确认"):
                self.update.apply(self.skill, "0.9.8")
        fetch.assert_not_called()

    def test_failed_replacement_restores_old_version(self):
        package = self.package()
        rename = Path.rename
        def fail_second(source, destination):
            if source.parent.name.startswith(".min-开头-update-") and source.name == self.skill.name:
                raise OSError("replace failed")
            return rename(source, destination)
        with mock.patch.object(self.update, "read_release", return_value=self.release(package)), \
             mock.patch.object(self.update, "fetch", return_value=package), \
             mock.patch.object(Path, "rename", fail_second):
            with self.assertRaisesRegex(OSError, "replace failed"):
                self.update.apply(self.skill, "0.9.8")
        self.assertEqual((self.skill / "old.txt").read_text(), "old")

    def test_manifest_cannot_send_download_to_github(self):
        package = self.package()
        release = self.release(package)
        release["download_url"] = "https://github.com/example/package.zip"
        with mock.patch.object(self.update, "fetch", return_value=self.update.json.dumps(release).encode()):
            with self.assertRaisesRegex(ValueError, "下载地址"):
                self.update.read_release()


    def test_local_preview_is_not_installable(self):
        release = self.release(self.package())
        release["release_status"] = "local_preview"
        with mock.patch.object(self.update, "fetch", return_value=self.update.json.dumps(release).encode()):
            with self.assertRaisesRegex(ValueError, "本地预览"):
                self.update.read_release()

    def test_user_profile_inside_old_installation_is_preserved(self):
        profile = self.skill / "references/创作者背书档案.md"
        profile.parent.mkdir()
        profile.write_text("this user's verified facts")
        package = self.package(extra=(ENTRY + "/references/创作者背书档案.md", "factory empty"))
        with mock.patch.object(self.update, "read_release", return_value=self.release(package)), mock.patch.object(self.update, "fetch", return_value=package):
            backup = self.update.apply(self.skill, "0.9.8")
        self.assertEqual(profile.read_text(), "this user's verified facts")
        self.assertEqual((backup / "references/创作者背书档案.md").read_text(), "this user's verified facts")

    def test_symlink_installed_directory_is_rejected(self):
        link = self.root / "alias" / "min-开头"
        link.parent.mkdir()
        link.symlink_to(self.skill, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, "安装目录"):
            self.update.apply(link, "0.9.8")


if __name__ == "__main__":
    unittest.main()
