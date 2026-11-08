from pathlib import Path
import json,hashlib
ROOT=Path('C:/sbox-projects/hc1/forked-shooter-main');OUT=ROOT/'output/cerroblanco/west-gallery-vase-v1'
source=ROOT/'Assets/models/maps/cerroblanco/quality-v1/cerroblanco_dressing_v2.obj'
plan=json.loads((OUT/'checks.json').read_text());assert hashlib.sha256(source.read_bytes()).hexdigest()==plan['source_sha256']
folder=OUT/'installed';folder.mkdir(exist_ok=True)
(folder/'before.obj').write_bytes(source.read_bytes())
patched=(OUT/'stage/models/maps/cerroblanco/west-gallery-vase-v1/dressing.obj').read_text().replace('mtllib dressing.mtl','mtllib cerroblanco_dressing_v2.mtl');(folder/'after.obj').write_text(patched)
text=(ROOT/'Sources/CerroBlanco/west-gallery-vase-v1/build.py').read_text();body=text[text.index('def build():'):text.index('\ndef keys(')]
module='''"""Approved turned display vase; rolled mouth and continuous hollow wall."""\nimport math\nimport numpy as np\nfrom scipy.interpolate import PchipInterpolator\nimport map_kit as K\nimport riverdale_parts as P\n\n'''+body+'''
def build_into(model,e,n,z):
    local=build()
    for mat,rows in local.polygons.items():
        for i,(points,normal) in enumerate(rows):rows[i]=([p+np.array((e,n,z)) for p in points],normal)
    model.extend(local)
'''
(ROOT/'Tools/cerroblanco_display_vase.py').write_text(module)
plan.update({'installed_sha256':hashlib.sha256((folder/'after.obj').read_bytes()).hexdigest(),'public_obj':str(source),'model_sha256':hashlib.sha256(source.with_suffix('.vmdl').read_bytes()).hexdigest()});(folder/'plan.json').write_text(json.dumps(plan,indent=2));print(plan)
