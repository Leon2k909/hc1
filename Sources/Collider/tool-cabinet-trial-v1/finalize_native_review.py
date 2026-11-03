"""Seal the temporary native comparison without installing either preview object."""
from pathlib import Path
import hashlib,json
from PIL import Image

ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent
OUT=ROOT/'output/asset-improvement-20261030/tool-cabinet';NATIVE=OUT/'native-review-20261031'
if (HERE/'installed.json').exists():
    raise SystemExit('Cabinet is installed; use finalize_install.py to verify the installed sources.')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
rel=lambda p:p.relative_to(ROOT).as_posix()
def write(path,data):path.write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8')

archive=NATIVE/'candidate-before-native-import-fix.json'
if not archive.exists():archive.write_bytes((HERE/'candidate.json').read_bytes())
baseline=json.loads(archive.read_text());candidate=json.loads((HERE/'candidate.json').read_text())
render=json.loads((OUT/'render-report.json').read_text())
refinement=json.loads((OUT/'collision-refinement/change.json').read_text())
fixes={};new_textures={}
for phase in ('paint-test','remaining'):
    pack=json.loads((NATIVE/f'texture-import-{phase}.json').read_text())
    for item in pack['Changes']:
        material=ROOT/'Assets'/item['Material'];backup=NATIVE/'texture-import-fix'/phase/(material.stem+'-before.vmat')
        assert sha(backup)==item['OriginalSHA256'] and sha(material)==item['UpdatedSHA256'],material
        fixes[rel(material)]={'before':item['OriginalSHA256'],'after':item['UpdatedSHA256'],'backup':rel(backup),'textures':item['Textures']}
        for texture in item['Textures']:
            path=ROOT/'Assets'/texture['Target'];assert sha(path)==texture['SHA256']
            with Image.open(path) as im:assert im.size==(2048,2048)
            new_textures[rel(path)]=sha(path)

expected_pump={f'Assets/materials/collider/pump-skid-trial-v1/{name}.vmat' for name in ('ps_frame','ps_guard','ps_sheet','ps_tray')}
changed=set()
for name,h in baseline['protectedSourceSHA256'].items():
    if sha(ROOT/name)!=h:
        assert name in expected_pump and fixes[name]['before']==h and sha(ROOT/name)==fixes[name]['after'],name
        changed.add(name)
assert changed==expected_pump
for name,h in render['proposalSourceSHA256'].items():
    change=refinement['changedFiles'].get(name) or fixes.get(name)
    if change:
        assert h in (change['before'],change['after']) and sha(ROOT/name)==change['after'],name
    else:assert sha(ROOT/name)==h,name

receipt={'date':'2026-10-31','reason':'Native normal/RMA mip generation failed for 2046x1364 atlases.',
    'method':'Native Bitmap.Resize to 2048x2048; normalized UV layout and raw source maps retained.',
    'geometryAndPhysicsUnchanged':True,'changes':fixes,'newTextureSHA256':new_textures,
    'previousProtectedSourceSnapshot':rel(archive),'originalProtectedSourcesUnchanged':len(baseline['protectedSourceSHA256'])-len(changed),
    'protectedPumpMaterialsCorrected':sorted(changed)}
write(HERE/'native-import-fix.json',receipt)
write(ROOT/'Sources/Collider/pump-skid-trial-v1/native-import-fix.json',
      {**receipt,'changes':{k:v for k,v in fixes.items() if k in expected_pump},
       'newTextureSHA256':{k:v for k,v in new_textures.items() if '/pump-skid-trial-v1/' in k}})

# Supersede only the four explicitly archived pump imports, and protect their new dependencies.
candidate['protectedSourceSHA256']=dict(baseline['protectedSourceSHA256'])
for name in changed:candidate['protectedSourceSHA256'][name]=fixes[name]['after']
candidate['protectedSourceSHA256'].update({k:v for k,v in new_textures.items() if '/pump-skid-trial-v1/' in k})
candidate['nativeTextureImportFix']=rel(HERE/'native-import-fix.json')
for path in (HERE/'candidate.json',OUT/'manifest.json'):write(path,candidate)

capture=json.loads((NATIVE/'capture-report.json').read_text())
collision=json.loads((NATIVE/'collision-report.json').read_text())
cleanup=json.loads((NATIVE/'after-editor-state.json').read_text())
assert capture['NativeEngineCapture'] and capture['RuntimeScene'] and capture['SceneName']=='collider'
assert capture['OriginalOnLeft'] and not capture['ModelsInstalledInMap']
assert collision['NativePhysics'] and collision['Passed'] and collision['Count']==26
assert cleanup['ComparisonObjectsRemaining']==[] and cleanup['ColliderComparisonDocumentClosed']
assert cleanup['PreviousRuntimeMapRestored'] and cleanup['Playing']
assert {s['Name'] for s in cleanup['Sessions']}=={'ares','spillway'}
assert all(not s['HasUnsavedChanges'] for s in cleanup['Sessions'])
compiled={}
for path in sorted(NATIVE.glob('*-asset_compile.txt')):
    try:entry=json.loads(path.read_text())
    except (ValueError,UnicodeError):continue
    if isinstance(entry,dict) and 'Path' in entry:compiled[entry['Path']]=entry
assert all(compiled[name.removeprefix('Assets/')]['Success'] for name in fixes)
images=[]
for view in capture['Captures']:
    assert view['EnablePostProcessing'] and view['MinimumExposure']==1 and abs(view['MaximumExposure']-2.3)<.001
    for suffix,size in (('.png',(1920,1080)),('-native.png',(3840,2160))):
        path=NATIVE/(view['Name']+suffix)
        with Image.open(path) as im:assert im.size==size
        images.append({'path':rel(path),'sha256':sha(path),'dimensions':list(size)})

review=json.loads((HERE/'review.json').read_text())
write(NATIVE/'offline-review-before-native-check.json',review) if not (NATIVE/'offline-review-before-native-check.json').exists() else None
review.update(status='native-preview-ready-awaiting-user-approval',userApproved=False,installedInMap=False,originalRetained=True,
    editorUsed=True,engineCompilation='success',nativeCollisionAndAppearance='native comparison inspected; 26 runtime physics checks passed',
    geometryAndCollisionVerification=json.loads((OUT/'verification.json').read_text()),
    protectedSourceSHA256=candidate['protectedSourceSHA256'],nativeTextureImportFix=receipt,
    proposalSourceSHA256={rel(p):sha(p) for folder in (ROOT/'Assets/models/props/collider/tool-cabinet-trial-v1',ROOT/'Assets/materials/collider/tool-cabinet-trial-v1')
                          for p in folder.iterdir() if p.suffix in ('.obj','.mtl','.vmdl','.vmat','.png')},
    nativeCapture=capture,nativeCollision=collision,nativeCleanup=cleanup,nativeImages=images,
    nativeEngineScreenshot=True,comparisonImage=rel(NATIVE/'side-by-side-front.png'),comparisonSHA256=sha(NATIVE/'side-by-side-front.png'),
    wholeObjectShown=True,originalColliderSceneUnchanged=True)
for path in (HERE/'review.json',OUT/'review.json',NATIVE/'review.json'):write(path,review)
print(json.dumps({'nativePreviewReady':True,'installed':False,'originalRetained':True,'nativePhysicsChecks':26,
                  'originalProtectedSourcesUnchanged':receipt['originalProtectedSourcesUnchanged'],
                  'pumpMaterialImportsCorrected':len(changed),'protectedSourcesNow':len(candidate['protectedSourceSHA256']),
                  'mapAndPlayStateRestored':True,'temporaryObjectsRemaining':0}))
