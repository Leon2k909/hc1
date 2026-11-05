from pathlib import Path
import json,hashlib
HERE=Path(__file__).parent;REVIEW=HERE.parents[2];ROOT=Path('C:/sbox-projects/hc1/forked-shooter-main');OUT=REVIEW/'output/riverside/neon-sign-v1';folder=REVIEW/'Assets/materials/riverside/neon-sign-v1'
for name in ('tube.vmat','tube_glow.vmat','tube_color.png'):
    p=folder/name;assert p.resolve().parent==folder.resolve()
    if p.exists():p.unlink()
p=OUT/'manifest.json';m=json.loads(p.read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
m['files']={f.relative_to(REVIEW).as_posix():sha(f) for d in (REVIEW/'Assets/models/maps/riverside/neon-sign-v1',folder) for f in d.iterdir() if f.is_file()}
m['external_files']={x:sha(ROOT/x) for x in ('Assets/materials/riverside/rs_lit.vmat','Assets/materials/riverside/rs_lit_color.png','Assets/materials/riverside/rs_lit_illum.png')}
p.write_text(json.dumps(m,indent=2),encoding='utf-8')
build=HERE/'build.py';s=build.read_text(encoding='utf-8');s=s.replace("source_vmdl_sha256=sha(public),files=", "source_vmdl_sha256=sha(public),external_files={p:sha(ROOT/p) for p in ('Assets/materials/riverside/rs_lit.vmat','Assets/materials/riverside/rs_lit_color.png','Assets/materials/riverside/rs_lit_illum.png')},files=");build.write_text(s,encoding='utf-8')
print('Final manifest contains',len(m['files']),'private source files.')
