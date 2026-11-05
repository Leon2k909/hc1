"""Retire only the old lamp faces/material aliases from retained Riverside comparisons."""
from pathlib import Path
import hashlib,json,re,sys
ROOT=Path(sys.argv[1]).resolve()
OUT=ROOT/'output/asset-improvement-20261030/riverside-porch-light/installed/legacy-cleanup'
OUT.mkdir(parents=True,exist_ok=True)
changes=[]
for folder in (ROOT/'Assets/models/maps/riverside',ROOT/'Assets/models/props/riverside'):
    for path in folder.rglob('*'):
        if path.suffix not in ('.obj','.mtl','.vmdl'):continue
        original=path.read_bytes()
        if b'rs_porch_light' not in original:continue
        text=original.decode();removed=0
        if path.suffix=='.obj':
            material=None;kept=[]
            for line in text.splitlines(keepends=True):
                if line.startswith('usemtl '):material=line.split()[1]
                if material=='rs_porch_light' and line.startswith('f '):removed+=1
                elif line.strip()=='usemtl rs_porch_light':continue
                else:kept.append(line)
            after=''.join(kept)
        elif path.suffix=='.mtl':
            after=re.sub(r'(?ms)^newmtl rs_porch_light\r?\n.*?(?=^newmtl |\Z)','',text)
        else:
            after=re.sub(r'\{\s*from\s*=\s*"rs_porch_light\.vmat"\s+to\s*=\s*"materials/riverside/rs_porch_light\.vmat"\s*\},?[ \t]*(?:\r?\n)?','',text)
            if '_class = "PhysicsShapeList"' in text:assert after[after.index('_class = "PhysicsShapeList"'):]==text[text.index('_class = "PhysicsShapeList"'):]
        data=after.encode()
        if data==original:continue
        relative=path.relative_to(ROOT)
        stage=OUT/'stage'/relative;stage.parent.mkdir(parents=True,exist_ok=True);stage.write_bytes(data)
        backup=OUT/'before'/relative;backup.parent.mkdir(parents=True,exist_ok=True)
        if backup.exists() and backup.read_bytes()!=original:backup=backup.with_name(backup.name+'.'+hashlib.sha256(original).hexdigest()[:12])
        backup.write_bytes(original)
        changes.append(dict(path=str(relative).replace('\\','/'),before_sha256=hashlib.sha256(original).hexdigest(),after_sha256=hashlib.sha256(data).hexdigest(),removed_faces=removed))
(OUT/'plan.json').write_text(json.dumps(changes,indent=2))
print(dict(files=len(changes),old_comparison_faces_removed=sum(r['removed_faces'] for r in changes),models=[r['path'] for r in changes if r['path'].endswith('.vmdl')]))
