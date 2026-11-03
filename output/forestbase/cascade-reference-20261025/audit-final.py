from pathlib import Path
import json,hashlib,py_compile
import numpy as np
from PIL import Image
r=Path('C:/Users/mimi-/Documents/S&box Projects/hc1');out=Path(__file__).parent
native=json.loads((out/'native-final.json').read_text());assets=json.loads((out/'native-assets.json').read_text(encoding='utf-8-sig'))
state=json.loads((out/'editor-final.json').read_text(encoding='utf-8-sig'))
assert native['ModelErrors']==0 and all(not m['MaterialError'] and not m['ShaderError'] for m in native['Materials'])
assert all(m['IsCompiledAndUpToDate'] and not m['IsCompileFailed'] for m in assets)
assert not state['SceneHasUnsavedChanges'] and not state['IsPlaying'] and state['LastCompileErrors']==0
for ext in ('.obj','.mtl','.vmdl'):
    assert (r/'Assets/models/maps/forestbase'/('vista'+ext)).read_bytes()==(out/('vista.before'+ext)).read_bytes()
initial=json.loads((r/'output/forestbase/river-foam-fix-20261025/integration.json').read_text())
allowed={'Assets/shaders/forestbase_waterfall.shader','Assets/shaders/forestbase_basin.shader'}
for path,value in initial['protectedSourceHashes'].items():
    if path.replace('\\','/') not in allowed:assert hashlib.sha256((r/path).read_bytes()).hexdigest()==value,path
for name in ('forestbase_water.py','forestbase_cascade.py'):py_compile.compile(str(r/'Tools'/name),doraise=True)
a=np.asarray(Image.open(out/'final-front.png').convert('RGB'),float)
b=np.asarray(Image.open(out/'final-front-motion.png').convert('RGB'),float)
motion=float(np.mean(abs(a[220:940,690:900]-b[220:940,690:900])))
assert motion>.2,'The two native frames do not show a measurable waterfall change'
files=[r/'Assets/shaders'/name for name in ('forestbase_current.shader','forestbase_waterfall.shader','forestbase_basin.shader','forestbase_mist.shader')]
files.extend(r/'Assets/materials/forestbase'/(n+'.vmat') for n in ('waterfall_current','waterfall_0','waterfall_1','waterfall_2','waterfall_3','waterfall_impact','waterfall_spray','plunge_basin'))
report={'editorUsed':True,'projectRoot':state['Paths']['ProjectRoot'],'engineCompileVerified':True,'compiledWaterMaterials':len(assets),
        'nativeMaterialAndShaderErrors':0,'sceneModels':native['Models'],'modelErrors':0,'sceneClean':True,'playStatePreserved':'stopped',
        'vistaSourceAndCollisionUnchanged':True,'otherProtectedSourcesUnchanged':True,'newTextures':0,'newSceneObjects':0,
        'waterfallPixelMeanDifference':motion,'animationLimit':'Native frames show change; no fluid simulation or match performance claim.',
        'referenceLimit':'Water appearance adapted; original cliff geometry and forest retained.',
        'sourceHashes':{str(p.relative_to(r)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files},
        'captures':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in out.glob('final-*.png')}}
(out/'integration.json').write_text(json.dumps(report,indent=2));print(json.dumps({k:v for k,v in report.items() if k not in ('sourceHashes','captures')},indent=2))
