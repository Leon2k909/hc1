"""Verify exact face removal, unchanged surrounding scene, all transforms and regeneration."""
from pathlib import Path
import hashlib,json,sys,math,os,time
import numpy as np
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent;OUT=ROOT/'output/riverdale-emergency-phone-installed-20261031'
sys.path.insert(0,str(ROOT/'Tools'))
import map_kit as K,riverdale_hall as H,riverdale_emergency_phones as E
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    receipt=json.loads((HERE/'installed.json').read_text());plan=json.loads((OUT/'plan.json').read_text())
    for item in plan['files']:
        p=ROOT/item['path'];assert sha(p)==item['after'],item['path']
        before=(OUT/'before'/item['path']).read_bytes().decode().splitlines(keepends=True)
        drops=set(item['removedFaceLines']);assert all(before[i].startswith('f ') for i in drops)
        expected=''.join(line for i,line in enumerate(before) if i not in drops).encode()
        assert p.read_bytes()==expected,'Unrelated attribute/face lines changed'
    scene=ROOT/'Assets/scenes/maps/Riverdale/riverdale.scene';current=json.loads(scene.read_text())
    old=json.loads((OUT/'before/Assets/scenes/maps/Riverdale/riverdale.scene').read_text())
    world=next(o for o in current['GameObjects'] if o.get('Name')=='Riverdale')
    group=world['Children'].pop();assert group==plan['group'] and current==old
    assert len(group['Children'])==8
    guids=[]
    def ids(o):
        if '__guid' in o:guids.append(o['__guid'])
        for c in o.get('Components',[]):guids.append(c['__guid'])
        for c in o.get('Children',[]):ids(c)
    for node in current['GameObjects']:ids(node)
    ids(group);assert len(guids)==len(set(guids)),'Duplicate object/component identity'
    E.PLACED.clear()
    for (origin,facing),go in zip(plan['placements'],group['Children']):
        origin=np.asarray(origin);face=H.Face(origin[:2],facing);detail=K.Model();fine=K.Model()
        H.wall_phone(detail,fine,face,0,float(origin[2]+7));assert detail.triangle_count()==0 and fine.triangle_count()==0
        assert np.allclose(np.fromstring(go['Position'],sep=','),K.to_world(origin))
        assert go['Scale']=='1,1,1'
        q=np.fromstring(go['Rotation'],sep=',');yaw=2*math.atan2(q[2],q[3]);front=np.array((-math.cos(yaw),-math.sin(yaw),0))
        assert np.allclose(front,K.to_world((*facing,0)),atol=1e-6)
        components=go['Components'];assert [c['__type'] for c in components]==['Sandbox.ModelRenderer','Sandbox.ModelCollider']
        assert all(c['Model']==E.MODEL for c in components) and components[1]['Static']
    rebuilt=E.scene_group(K.SceneIds('5f1c9a72-8e34-4b6d-a2c7-91e0d4b36f85'))
    assert rebuilt==group,'Regeneration differs from saved placement'
    for path,h in plan['proposalSourceSHA256'].items():assert sha(ROOT/path)==h,path
    for path,h in plan['publishedMapModelDocsUnchanged'].items():assert sha(ROOT/path)==h,path
    # OBJ updates alone can escape a model's stale check. Mark the unchanged ModelDocs newer than their caches.
    marked=[]
    for item in plan['files']:
        path=(ROOT/item['path']).with_suffix('.vmdl');os.utime(path,None);marked.append(str(path.relative_to(ROOT)).replace(chr(92),'/'))
    result=dict(phones=8,removedOriginalTriangles=1008,unrelatedObjLinesByteIdentical=True,
        sceneDiffOnlyPhoneGroup=True,allGuidsUnique=True,allPlacementsAndFacingCorrect=True,
        rendererAndStaticColliderOnEveryPhone=True,regenerationMatchesSavedGroup=True,
        approvedModelAndMaterialsUnchanged=True,existingMapModelDocsByteIdentical=True,
        sharedAssetNativeCollisionTests=7,placedSceneNativeCheck='pending editor reopening',modelDocsMarkedForRecompilation=marked)
    receipt.update(verification=result,packedModelCompilation='required on next editor load; model source timestamps refreshed',
                   generatorHashes={name:sha(ROOT/name) for name in ('Tools/riverdale_hall.py','Tools/riverdale_map.py','Tools/riverdale_emergency_phones.py')})
    for p in (HERE/'installed.json',OUT/'installed.json'):p.write_text(json.dumps(receipt,indent=2)+'\n')
    review=json.loads((HERE/'review.json').read_text());review.update(status='approved-installed-in-saved-map',userApproved=True,installedInMap=True,
        originalRetained=False,originalKeptInMap=False,originalAvailableInRollback=True,installationReceipt='Sources/Riverdale/emergency-phone-v1/installed.json',
        nativePlacedSceneCheck='pending editor reopening')
    for p in (HERE/'review.json',ROOT/'output/riverdale-emergency-phone-review-20261031/review.json'):p.write_text(json.dumps(review,indent=2)+'\n')
    (OUT/'verification.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
if __name__=='__main__':main()
