from pathlib import Path
import json,hashlib
ROOT=Path('C:/sbox-projects/hc1/forked-shooter-main');OUT=ROOT/'output/cerroblanco/courtyard-bin-v1'
source=ROOT/'Assets/models/maps/cerroblanco/quality-v1/cerroblanco_dressing_v2.obj'
plan=json.loads((OUT/'geometry-checks.json').read_text());assert hashlib.sha256(source.read_bytes()).hexdigest()==plan['source_sha256']
folder=OUT/'installed';folder.mkdir(exist_ok=True)
(folder/'before.obj').write_bytes(source.read_bytes())
patched=(OUT/'stage/models/maps/cerroblanco/courtyard-bin-v1/dressing.obj').read_text().replace('mtllib dressing.mtl','mtllib cerroblanco_dressing_v2.mtl')
(folder/'after.obj').write_text(patched)
# Promote the approved pure model function into the map's normal Tools module.
text=Path(__file__).with_name('build.py').read_text();body=text[text.index('def build():'):text.index('\ndef keys(')]
module='''"""Approved Cerro Blanco hooded bin; rolled rim and connected hood sockets."""\nimport math\nimport numpy as np\nimport map_kit as K\nimport riverdale_parts as P\nSTEEL='cb_steel';DARK='cb_black'\n\n'''+body+'''
def build_into(model,e,n):
    local=build()
    for mat,rows in local.polygons.items():
        for i,(points,normal) in enumerate(rows):
            rows[i]=([p+np.array((e,n,0)) for p in points],normal)
    model.extend(local)
'''
(ROOT/'Tools/cerroblanco_hooded_bin.py').write_text(module)
plan.update({'installed_sha256':hashlib.sha256((folder/'after.obj').read_bytes()).hexdigest(),'public_obj':str(source),'model_sha256':hashlib.sha256(source.with_suffix('.vmdl').read_bytes()).hexdigest()})
(folder/'plan.json').write_text(json.dumps(plan,indent=2));print(plan)
