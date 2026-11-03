"""Bind inspected native phone comparisons to their exact model/material sources."""
from pathlib import Path
import hashlib,json,importlib.util,psutil
from PIL import Image
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2];OUT=ROOT/'output/riverdale-emergency-phone-review-20261031'
if (HERE/'installed.json').exists():
    raise SystemExit('Phone is installed; use verify_install.py. Historical preview does not supersede installation.')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
candidate=json.loads((HERE/'candidate.json').read_text());native=json.loads((OUT/'native-review.json').read_text())
assert native['NativeEngineRendering'] and native['OriginalLeft'] and native['SharedLightingAndCamera']
assert native['RuntimeScenePreserved'] and native['PlayStatePreserved'] and not native['InstalledInMap']
assert len(native['NativePhysicsChecks'])==7 and all(c['Passed'] for c in native['NativePhysicsChecks'])
source=ROOT/'Sources/Collider/tool-cabinet-trial-v1/native_cli.py'
spec=importlib.util.spec_from_file_location('phone_transport',source);transport=importlib.util.module_from_spec(spec);spec.loader.exec_module(transport)
transport.OUT=OUT/'native'
compiled=[]
for name in ('before','after','review_wall'):
    asset=transport.call('asset_info',{'path':candidate['resource']+'/'+name+'.vmdl'})
    assert asset['IsCompiledAndUpToDate'] and not asset['IsCompileFailed'],asset
    compiled.append(asset)
state=transport.call('editor_status',{});assert state['Paths']['ProjectRoot'].lower()==str(ROOT).lower()
assert state['IsPlaying'] and not state['IsPaused'] and not state['IsCompiling'] and state['LastCompileSucceeded']
images=[]
for view in ('front','angle'):
    for suffix,size in (('.png',(1920,1080)),('-native.png',(3840,2160))):
        path=OUT/('comparison-'+view+suffix)
        with Image.open(path) as im:assert im.size==size
        images.append(dict(path=path.relative_to(ROOT).as_posix(),sha256=sha(path),size=list(size)))
sources={p.relative_to(ROOT).as_posix():sha(p) for directory in (ROOT/'Assets'/candidate['resource'],ROOT/'Assets'/candidate['materials'])
         for p in directory.iterdir() if p.is_file() and p.suffix in ('.obj','.mtl','.vmdl','.vmat','.png')}
publish=json.loads((OUT/'publish.json').read_text())
for item in publish['files']:assert sha(ROOT/'Assets'/item['path'])==item['sha256'],item['path']
changed={p:dict(before=h,after=sha(ROOT/p)) for p,h in candidate['protectedSourceSHA256'].items() if sha(ROOT/p)!=h}
receipt={**candidate,'status':'native-preview-ready-awaiting-user-approval','nativeChecks':'passed','nativeEngineComparison':native,
         'compiledAssets':compiled,'images':images,'proposalSourceSHA256':sources,'finalEditorState':state,
         'originalKeptInMap':True,'publishedMapFilesWrittenByThisTask':[],
         'concurrentPublishedSourceChangesDetected':changed,'triangleCount':candidate['proposedTriangles'],
         'wholeObjectsVisuallyInspected':True,'lighting':'Shared native directional/sky light with Riverdale wall materials; isolated review scene',
         'productionLODAndFrameTimeBenchmark':'not performed; proposal is not installed'}
for path in (HERE/'review.json',OUT/'review.json'):path.write_text(json.dumps(receipt,indent=2)+'\n')
(OUT/'final-editor-state.json').write_text(json.dumps(state,indent=2)+'\n')
print(json.dumps(dict(status=receipt['status'],nativeCollisionChecks=7,originalKept=True,compiledAssets=len(compiled),
                     concurrentSourceChanges=len(changed),remainingCLIProcesses=[p.pid for p in psutil.process_iter(['name']) if (p.info['name'] or '').lower()=='sbox-cli.exe'])))
