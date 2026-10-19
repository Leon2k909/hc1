from pathlib import Path
import hashlib
import json
import shutil
import sys
import numpy as np
from PIL import Image

root=Path(__file__).resolve().parents[3]
out=root/'output/spillway/waterfall-pass'
source=root/'Sources/Spillway'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
geometry=json.loads((out/'geometry.json').read_text())
assert all(sha(root/p)==v for p,v in geometry['protected'].items())
models=root/'Assets/models/maps/spillway'
stage=out/'stage/models/maps/spillway'
for name in ('spillway_falls.obj','spillway_falls.mtl','spillway_mountains.obj','spillway_river.obj'):
    assert sha(models/name)==sha(stage/name),name
for name in ('spillway_falls.vmdl','spillway_mountains.vmdl','spillway_river.vmdl'):
    assert sha(models/name)==sha(out/'before-assets/models/maps/spillway'/name),name
shader='shaders/hc1_spillway_falls_v5.shader'
assert sha(root/'Assets'/shader)==sha(source/shader)
texture='materials/spillway/waterfall-turbulence-v1.png'
assert sha(root/'Assets'/texture)==sha(source/'waterfalls/waterfall-turbulence-v1.png')
bitmap=Image.open(root/'Assets'/texture)
assert bitmap.size[0]>=1024 and bitmap.size[1]>=1024
for name in ('sw_fall_v4','sw_foam_v4','sw_mist_v4'):
    material=(root/'Assets/materials/spillway'/f'{name}.vmat').read_text()
    assert shader in material and texture in material
before=(out/'before-assets/models/maps/spillway/spillway_mountains.obj').read_text().splitlines()
after=(models/'spillway_mountains.obj').read_text().splitlines()
assert len(before)==len(after)
assert all(a==b for a,b in zip(before,after) if not a.startswith(('v ','vn ')))
changed=sum(a!=b for a,b in zip(before,after) if a.startswith('v '))
assert changed==geometry['basin']['lowered_vertices']
for name in ('spillway_falls.obj','spillway_mountains.obj','spillway_river.obj'):
    vectors=[list(map(float,l.split()[1:4])) for l in (models/name).read_text().splitlines() if l.startswith(('v ','vn '))]
    assert np.isfinite(vectors).all(),name
capture=json.loads((out/'final/report.json').read_text())
motion=json.loads((out/'motion/motion-validation.json').read_text())
checks=('GamePreserved','DirtyPreserved','AuthoredObjectsPreserved','TemporaryCameraRemoved','CamerasRestored')
assert all(capture[k] for k in checks)
assert motion['Passed'] and motion['Frames']==16
materials=json.loads((out/'import.json').read_text())
imported=json.loads((out/'geometry-import.json').read_text())
assert materials['ShaderCompiled'] and all(m['Success'] for m in materials['Materials'])
assert all(m['Success'] for m in imported['Models'])
counts={p.stem:sum(l.startswith('f ') for l in p.read_text().splitlines()) for p in models.glob('*.obj') if 'hulls' not in p.stem}
old_count=sum(l.startswith('f ') for l in (out/'before-assets/models/maps/spillway/spillway_falls.obj').read_text().splitlines())
result={
    'date':'2026-10-18','status':'saved_and_native_verified',
    'imagegen':'built-in image_gen.imagegen', 'prompts':'Sources/Spillway/waterfalls/generation.json',
    'shader_compile_success':True,'materials_compile_success':True,'models_compile_success':True,
    'source_matches_live':True,'scene_and_seven_collision_hulls_unchanged':True,'modeldocs_unchanged':True,
    'terrain_uvs_faces_materials_unchanged':True,'terrain_vertices_lowered':changed,
    'waterfall_triangles_before':old_count,'waterfall_triangles_after':counts['spillway_falls'],
    'map_visual_triangles':sum(counts.values()),'texture_size':bitmap.size,
    'captured_views':[c['Name'] for c in capture['Captures']],
    'capture_state_checks':{k:capture[k] for k in checks},
    'motion':motion,'fps_benchmarked':False,
}
(out/'verification.json').write_text(json.dumps(result,indent=2)+'\n')
(source/'validation/waterfalls-2026-10-18.json').write_text(json.dumps(result,indent=2)+'\n')
exchange=Path(r'C:\Users\leon2\AppData\Local\Temp\sbox-cli\8d4e06413ab24941af45cba23c5fe323')
for before,after in (('import-waterfalls.cs','import-materials.cs.txt'),('import-waterfall-geometry.cs','import-geometry.cs.txt'),('capture-waterfalls.cs','capture-waterfalls.cs.txt'),('capture-waterfall-motion.cs','capture-motion.cs.txt')):
    if (exchange/before).exists():
        shutil.copy2(exchange/before,source/'waterfalls'/after)
    else:
        assert (source/'waterfalls'/after).exists()
print(json.dumps({k:v for k,v in result.items() if k!='motion'},indent=2))
if '--cleanup-exchange' in sys.argv:
    expected=Path(r'C:\Users\leon2\AppData\Local\Temp\sbox-cli\8d4e06413ab24941af45cba23c5fe323')
    assert exchange.resolve()==expected and exchange.parent.name=='sbox-cli'
    if exchange.exists(): shutil.rmtree(exchange)
