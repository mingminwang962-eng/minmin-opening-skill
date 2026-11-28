# -*- coding: utf-8 -*-
from pathlib import Path
import json,zipfile,hashlib
root=Path(__file__).resolve().parents[1];c=json.loads((root/'release-config.json').read_text());version=(root/'VERSION').read_text().strip();assert version==c['version']
site=root/'website';out=site/'downloads';out.mkdir(exist_ok=True);archive=out/(c['archive']+'-v'+version+'.zip')
paths=[p for p in root.rglob('*') if p.is_file() and '.git' not in p.parts and '__pycache__' not in p.parts and not p.is_relative_to(out) and p!=site/'release.json']
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
 for p in sorted(paths):
  info=zipfile.ZipInfo(c['archive']+'/'+p.relative_to(root).as_posix(),(2026,11,28,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=0o100644<<16;z.writestr(info,p.read_bytes())
b=archive.read_bytes();digest=hashlib.sha256(b).hexdigest();skills=[{'name':c['skill'],'path':c['skill'],'version':version}]
if c['id']=='opening-skill':skills.append({'name':'min-开头身份梳理','path':'min-开头身份梳理','version':'1.3.1','optional_use':True})
r={'version':version,'notice':c['notice'],'download_url':'https://tools.minmin11538.cn/'+c['slug']+'/downloads/'+archive.name,'bytes':len(b),'sha256':digest,'archive_root':c['archive'],'skill_entry':c['skill']+'/SKILL.md','skills':skills,'release_status':'published','released_at':'2026-11-28','release_number':c['release_number'],'instructions_url':'https://tools.minmin11538.cn/'+c['slug']+'/install.md'}
(site/'release.json').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n');(out/'SHA256SUMS').write_text(digest+'  '+archive.name+'\n');print(json.dumps(r,ensure_ascii=False))
