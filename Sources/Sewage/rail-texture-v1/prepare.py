"""Stage generated enamel for the upgraded platform rail material only."""
from pathlib import Path
import hashlib,json,sys,shutil
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent
OUT=ROOT/'output/sewage/rail-texture-v1';STAGE=OUT/'stage';BASE=OUT/'baseline'
assert not (OUT/'plan.json').exists(),'Already staged'
STAGE.mkdir(parents=True);BASE.mkdir()
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
public=ROOT/'Assets/models/maps/sewage/sewage_catwalks.vmdl'
doc=public.read_text();old='materials/sewage/yellow.vmat';new='materials/sewage/rail-texture-v1/enamel.vmat'
anchor='{ from = "ww_platform_rail.vmat" to = "'+old+'" }'
assert doc.count(anchor)==1
edited=doc.replace(anchor,anchor.replace(old,new))
assert edited.replace(new,old)==doc
dest=STAGE/'Assets/models/maps/sewage/sewage_catwalks.vmdl';dest.parent.mkdir(parents=True);dest.write_text(edited)
(BASE/public.name).write_bytes(public.read_bytes())
preview=STAGE/'Assets/models/maps/sewage/rail-texture-v1';preview.mkdir()
for suffix in ('.obj','.mtl'):
 source=public.with_suffix(suffix)
 (preview/('before'+suffix)).write_bytes(source.read_bytes().replace(b'sewage_catwalks.mtl',b'before.mtl') if suffix=='.obj' else source.read_bytes())
(preview/'before.vmdl').write_text(doc.replace('models/maps/sewage/sewage_catwalks.obj','models/maps/sewage/rail-texture-v1/before.obj'))
mat=STAGE/'Assets/materials/sewage/rail-texture-v1';mat.mkdir(parents=True)
shutil.copyfile(Path(sys.argv[1]),mat/'enamel_color.png')
(mat/'enamel.vmat').write_text('''// AI-generated albedo, physically scaled fine chips in yellow enamel.
"Layer0"
{
    shader "shaders/complex.shader"
    F_SPECULAR "1"
    g_flMetalness ".08"
    g_flRoughness ".67"
    TextureColor "materials/sewage/rail-texture-v1/enamel_color.png"
    TextureNormal "materials/default/default_normal.tga"
    TextureAmbientOcclusion "materials/default/default_ao.tga"
    g_vTexCoordScale "[3.25 3.25]"
    g_vColorTint "[1 1 1 1]"
    g_flModelTintAmount "1"
}
''')
files={p.relative_to(STAGE).as_posix():sha(p) for p in STAGE.rglob('*') if p.is_file()}
plan=dict(files=files,public_before_sha=sha(public),public_after_sha=sha(dest),
 obj_hash=sha(public.with_suffix('.obj')),mtl_hash=sha(public.with_suffix('.mtl')),hull_hash=sha(public.with_name('sewage_catwalks_hulls_metal.obj')),
 geometry_unchanged=True,collision_unchanged=True,only_material_slot='ww_platform_rail')
(OUT/'plan.json').write_text(json.dumps(plan,indent=2))
for name in ('native.py','capture.cs.txt'):
 (HERE/name).write_text((HERE.parent/'platform-rails-v1'/name).read_text().replace('sewage/platform-rails-v1','sewage/rail-texture-v1'))
source=ROOT/'Tools/sewage_platform_rails.py';text=source.read_text();assert text.count(old)==1
(HERE/'platform-rails-before.py').write_bytes(source.read_bytes());source.write_text(text.replace(old,new))
print(json.dumps(plan,indent=2))
