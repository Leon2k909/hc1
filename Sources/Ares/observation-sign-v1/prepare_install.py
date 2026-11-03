from pathlib import Path
import hashlib,json,re
ROOT=Path(__file__).resolve().parents[3]
HERE=Path(__file__).parent
OUT=ROOT/'output/ares/observation-sign-v1'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
manifest=json.loads((OUT/'manifest.json').read_text())
assert sha(ROOT/manifest['source'])==manifest['source_sha256'],'Installed dressing changed; rebase the extraction first'
for p,h in manifest['files'].items():assert sha(ROOT/p)==h,p
public=ROOT/'Assets/models/maps/ares/ares_dressing.vmdl'
old=public.read_bytes();text=old.decode('utf-8')
assert 'observation-sign-v1' not in text,'Already installed: inspect before retrying'
backup=OUT/'install-before';backup.mkdir(exist_ok=True)
(backup/'ares_dressing.vmdl').write_bytes(old)
paths=list((ROOT/'Assets/models/maps/ares').rglob('*'))+list((ROOT/'Assets/materials/ares').rglob('*'))+[ROOT/'Assets/scenes/maps/Ares/ares.scene']
guard={str(p.relative_to(ROOT)).replace('\\','/'):sha(p) for p in paths if p.is_file() and p.suffix!='.meta' and not p.name.endswith('_c')}
(OUT/'install-source-guard.json').write_text(json.dumps(guard,indent=2))
candidate=(ROOT/'Assets/models/maps/ares/observation-sign-v1/observation_sign.vmdl').read_text()
node=re.search(r'\t{5}\{\n\t{6}_class = "RenderMeshFile".*?\n\t{5}\},',candidate,re.S).group()
remaps=re.findall(r'\{ from = "[^\n]+?\}',candidate)
oldnode=re.search(r'\t{5}\{\n\t{6}_class = "RenderMeshFile".*?\n\t{5}\},',text,re.S).group()
newnode=oldnode.replace('models/maps/ares/crate-v2/dressing-base.obj','models/maps/ares/observation-sign-v1/dressing_without_sign.obj')
text=text.replace(oldnode,newnode+'\n'+node)
marker='\t\t\t\t\t\t\t{ from = "ar_bezel.vmat"'
assert marker in text
text=text.replace(marker,'\n'.join('\t'*7+r+',' for r in remaps)+'\n'+marker,1)
assert old.decode()[old.decode().index('_class = "PhysicsShapeList"'):]==text[text.index('_class = "PhysicsShapeList"'):]
target=OUT/'install-stage.vmdl';target.write_text(text)
(OUT/'install-plan.json').write_text(json.dumps(dict(before_sha256=hashlib.sha256(old).hexdigest(),after_sha256=sha(target),target='Assets/models/maps/ares/ares_dressing.vmdl'),indent=2))
# Retain the approved geometry in future map generation using a dedicated helper.
build=(HERE/'build.py').read_text();start=build.index('m=K.Model()');end=build.index('tris=K.write_model',start)
body=build[start:end]
helper='''"""Approved Ares observation sign geometry. Plan inches; native import is renderer-only."""
import numpy as np
import map_kit as K
import boxyard_map as BY
MAT='materials/ares/observation-sign-v1'
def model():
'''+''.join('    '+l+'\n' for l in body.splitlines()).replace('A.rod(', 'BY.rod(')+'''    return m

def append_to(target):
    source=model()
    for paint,faces in source.polygons.items():
        alias='ar_os_'+paint
        target.material_overrides[alias]=source.material_overrides[paint]
        target.tile_overrides[alias]=source.tile_overrides[paint]
        for i,(points,normal) in enumerate(faces):
            target.polygon(alias,points,normal,uv=source.polygon_uvs.get((paint,i)),normals=source.polygon_normals.get((paint,i)))
'''
(ROOT/'Tools/ares_observation_sign.py').write_text(helper)
generator=ROOT/'Tools/ares_map.py';g=generator.read_text()
assert 'from ares_observation_sign import' not in g
g=g.replace('if paint.startswith( "ar_in_" ) and paint in model.material_overrides:','if paint.startswith( "ar_os_" ) and paint in model.material_overrides:\n            continue\n        if paint.startswith( "ar_in_" ) and paint in model.material_overrides:',1)
block='''    lit_sign( m, "observation", ( 0.0, 600.0, 420.0 ), ( 0, -1 ), 192.0, 48.0 )
    for e in ( -80.0, 80.0 ):
        rod( m, ( e, 598.0, 444.0 ), ( e, 598.0, HALL_TOP ), 0.6, "ar_gunmetal", sides=4 )'''
assert block in g
g=g.replace(block,'    from ares_observation_sign import append_to as append_observation_sign\n    append_observation_sign( m )',1)
(backup/'ares_map.py').write_bytes(generator.read_bytes());generator.write_text(g)
print(json.dumps(dict(target=str(public),before=hashlib.sha256(old).hexdigest(),after=sha(target),render_imports_added=1,physics_unchanged=True)))
