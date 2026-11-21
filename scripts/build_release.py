from pathlib import Path
import json,zipfile,hashlib
root=Path(__file__).resolve().parents[1]
version=(root/'VERSION').read_text().strip()
site=root/'website';downloads=site/'downloads';downloads.mkdir(exist_ok=True)
archive=downloads/f'minmin-opening-skill-v{version}.zip'
paths=[p for p in root.rglob('*') if p.is_file() and '.git' not in p.parts and '__pycache__' not in p.parts and not p.is_relative_to(downloads)]
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
 for p in sorted(paths):
  if p==site/'release.json':continue
  info=zipfile.ZipInfo('minmin-opening-skill/'+p.relative_to(root).as_posix(),(2026,11,21,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=0o100644<<16;z.writestr(info,p.read_bytes())
b=archive.read_bytes();digest=hashlib.sha256(b).hexdigest()
release={'version':version,'notice':'补齐联系敏敏、复制后的安装指引及包内联系资源；写作规则保持不变。','download_url':f'https://tools.minmin11538.cn/opening/downloads/{archive.name}','bytes':len(b),'sha256':digest,'archive_root':'minmin-opening-skill','skill_entry':'开头skill/SKILL.md','release_status':'published','released_at':'2026-11-21','instructions_url':'https://tools.minmin11538.cn/opening/install.md'}
(site/'release.json').write_text(json.dumps(release,ensure_ascii=False,indent=2)+'\n')
(downloads/'SHA256SUMS').write_text(f'{digest}  {archive.name}\n')
print(json.dumps(release,ensure_ascii=False))
