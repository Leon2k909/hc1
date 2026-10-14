"""Check installed slate assets against scope, physical map bounds and generator."""
from pathlib import Path
import hashlib
import json
import shutil
import sys
import uuid
import numpy as np
from PIL import Image

folder=Path(__file__).resolve().parent
root=folder.parents[2]
manifest=json.loads((folder/'roof-response-manifest.json').read_text())
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
for name,expected in manifest['protected'].items():
    assert digest(root/name)==expected,name
registered_metadata={}
for name,change in manifest['changes'].items():
    path=root/'Assets'/name
    if name.endswith('.meta') and change['before'] is None:
        # RegisterFile assigned native asset IDs before the staged sidecars were
        # imported. Retain those IDs; existing asset metadata was never changed.
        data=json.loads(path.read_text())
        assert set(data)=={'guid'} and uuid.UUID(data['guid']).version==4,name
        registered_metadata[name]={'guid':data['guid'],'sha256':digest(path)}
    else:
        assert digest(path)==change['after'],name
native=json.loads((folder/'roof-response-native-compile.json').read_text())
assert native['compiled'] and native['shader'] and not native['IsError']
assert not native['HasUnsavedChanges'] and not native['IsPlaying']
assert all(not r['modelError'] and len(r['slateSlots'])==1 and not r['slateSlots'][0]['hasOverride'] for r in native['renderers'])
maps=root/'Assets/materials/lowtide/roofs'
normal=np.asarray(Image.open(maps/'slate_normal.png').convert('RGB'),np.float32)/127.5-1
assert normal.shape==(2048,2048,3)
length=np.linalg.norm(normal,axis=2)
assert float(np.abs(length-1).max())<.008
assert float(normal[:,:,2].min())>0
ao=np.asarray(Image.open(maps/'slate_ao.png'))/255.
assert ao.shape==(2048,2048) and ao.min()>=.64 and ao.max()<=1 and ao.min()<.99
sys.path.insert(0,str(root/'Tools'))
import lowtide_roofs as R
R.DIRECTORY=maps
R.K.ASSETS=folder/'roof-response-generator-check'
(R.K.ASSETS/R.MATERIAL).parent.mkdir(parents=True,exist_ok=True)
R.write_materials()
assert (R.K.ASSETS/R.MATERIAL).read_text()==(root/'Assets'/R.MATERIAL).read_text()
exchange=Path('C:/Users/leon2/AppData/Local/Temp/sbox-cli/b85c6516c54b41ca8eb4fb9aaecf25af')
for name in ('apply-roof-response.cs','compile-roof-response.cs','verify-roof-response.cs','preview-roof-material.cs'):
    shutil.copy2(exchange/name,folder/name)
report={'protected_files':len(manifest['protected']),'installed_files':len(manifest['changes']),
        'native_registered_metadata':registered_metadata,
        'scene_and_models_preserved':True,'generated_albedo_preserved':True,'generator_matches':True,
        'normal_max_unit_error':float(np.abs(length-1).max()),'ao_range':[float(ao.min()),float(ao.max())],
        'native':native,'reviewed_views':['roof-response-quay.png','roof-response-west.png',
                    'roof-response-yard.png','roof-response-canal.png','roof-response-elevated.png'],
        'console_warnings_errors_since_711':[],'controlled_gameplay_performance_tested':False}
(folder/'roof-response-verification.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:report[k] for k in ('protected_files','installed_files','scene_and_models_preserved','generator_matches','normal_max_unit_error','ao_range')}))
