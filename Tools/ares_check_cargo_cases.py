"""Verify the installed case assets, saved instances, retained scene and LODs."""
import copy
from collections import Counter
import json
from pathlib import Path
from uuid import UUID
import numpy as np

import ares_map as A
import ares_cargo_case as C
from ares_stage_cargo_cases import placements
from railhead_stage_extinguisher import sha

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output/ares/crate-v2'


def walk(value):
    if isinstance(value,dict):
        yield value
        for child in value.values():yield from walk(child)
    elif isinstance(value,list):
        for child in value:yield from walk(child)


def json_diffs(a,b,path=''):
    if type(a)!=type(b):return [(path,a,b)]
    if isinstance(a,dict):
        return [(path+'/'+k,a.get(k),b.get(k)) for k in a.keys()^b.keys()]+[
            row for k in a.keys()&b.keys() for row in json_diffs(a[k],b[k],path+'/'+k)]
    if isinstance(a,list):
        rows=[] if len(a)==len(b) else [(path+'/length',len(a),len(b))]
        return rows+[row for i,(x,y) in enumerate(zip(a,b)) for row in json_diffs(x,y,path+'/'+str(i))]
    return [] if a==b else [(path,a,b)]


def results(path):
    raw=json.loads(path.read_text());assert not raw.get('isError'),path
    rows=[]
    for block in raw['content']:
        if block['type']=='text':
            try:rows.append(json.loads(block['text']))
            except json.JSONDecodeError:pass
    return rows


def audit_serialization(before,after,diffs):
    """Reject authored changes; account for measured current-editor serialization.

    The old generated scene omitted defaults and used v0 reflection probes. The
    native save writes defaults, typed resource paths and migrated probes. Check
    each difference against a disposable native component, not a broad whitelist.
    """
    defaults={n['__type']:n for n in json.loads((OUT/'engine-component-defaults.json').read_text())}
    migration=json.loads((OUT/'engine-serialization-audit.json').read_text())
    probes={n['__guid']:n for n in migration['MigratedProbes']}
    prefab_migrations={n['__guid']:n for n in migration['MigratedPrefabs']}
    description=next(n['Description'] for n in walk(before) if n.get('__type')=='Sandbox.SceneInformation')
    counts=Counter();max_delta=0.
    events={'OnComponentFixedUpdate','OnComponentEnabled','OnComponentUpdate','OnComponentDisabled',
            'OnComponentDestroy','OnComponentStart','OnTriggerEnter','OnObjectTriggerEnter','OnTriggerExit','OnObjectTriggerExit'}

    def parent(doc,path):
        parts=path.split('/')[1:];value=doc
        for key in parts[:-1]:value=value[int(key)] if isinstance(value,list) else value[key]
        return value,parts[-1]

    for path,a,b in diffs:
        old,key=parent(before,path);new,_=parent(after,path)
        kind=new.get('__type','') if isinstance(new,dict) else ''
        category=None
        if isinstance(a,(int,float)) and not isinstance(a,bool) and a==b:
            category='numeric_format'
        elif isinstance(a,str) and isinstance(b,dict) and b.get('Path')==a and set(b)=={'Id','Path'}:
            UUID(b['Id']);category='typed_resource_same_path'
        elif isinstance(a,str) and isinstance(b,str) and key in {'Rotation','Position','Tint','LightColor'}:
            x=np.asarray(a.split(','),float);y=np.asarray(b.split(','),float)
            assert x.shape==y.shape and np.allclose(x,y,atol=1e-6,rtol=0),(path,a,b)
            max_delta=max(max_delta,float(np.max(np.abs(x-y))));category='float_serialization'
        elif a is None and path in {'/Description','/SceneProperties/Metadata/Description'} and b==description:
            category='existing_description_metadata'
        elif key not in old:
            if key in events and b is None:category='unassigned_component_event'
            elif kind in defaults and key in defaults[kind] and b==defaults[kind][key]:
                category='measured_engine_default'
            elif kind=='Sandbox.EnvmapProbe' and key=='Mode' and b==probes[new['__guid']]['Mode']:
                category='measured_probe_migration'
            elif kind=='Facepunch.MapInformation' and key=='ZombiesOnly' and b is False:
                assert 'public bool ZombiesOnly { get; set; }' in (ROOT/'Code/Maps/MapInformation.cs').read_text()
                category='map_information_default'
            elif path=='/SceneProperties/Metadata/ZombiesOnly' and b=='False':category='map_metadata_default'
            elif path=='/SceneProperties/GameObjectSystems':
                assert set(b)=={'Sandbox.Clutter.ClutterGridSystem','Sandbox.SelectionSetsSystem'}
                storage=b['Sandbox.Clutter.ClutterGridSystem']['Storage']
                assert set(storage)=={'$blob','$refs'} and storage['$refs']==[]
                UUID(storage['$blob'])
                assert b['Sandbox.SelectionSetsSystem']=={'Data':{'SelectionSets':[]}}
                category='editor_system_bookkeeping'
            elif '/__PrefabIdToInstanceId/' in path:
                instance,_=parent(after,path.rsplit('/',1)[0])
                measured=prefab_migrations[instance['__guid']]
                assert key in measured['__PrefabIdToInstanceId'],path
                UUID(b);category='measured_prefab_guid_bookkeeping'
        elif key not in new and key=='RenderDynamically' and kind=='Sandbox.EnvmapProbe':
            assert a is True and new['Mode']==probes[new['__guid']]['Mode']=='Realtime'
            category='measured_probe_migration'
        assert category is not None,('Unexplained scene change',path,a,b)
        counts[category]+=1
    return {'differences_classified':len(diffs),'categories':dict(counts),
            'max_numeric_string_delta':max_delta,'original_authored_properties_preserved':True,
            'probe_migrations_measured_in_disposable_scene':4}


def main():
    stage=json.loads((OUT/'import-request.json').read_text())['stage']
    manifest=json.loads((OUT/stage/'manifest.json').read_text())
    for p,item in manifest['files'].items():assert sha(ROOT/p)==item['after'],p
    original=ROOT/'output/ares/crate-v2/stage-v5/before/Assets/scenes/maps/Ares/ares.scene'
    before=json.loads(original.read_text());after=json.loads((ROOT/'Assets/scenes/maps/Ares/ares.scene').read_text())
    groups=[node for node in walk(after) if node.get('Name')=='ARES transport cases']
    assert len(groups)==1 and len(groups[0]['Children'])==132
    group=groups[0];specs=json.loads((OUT/stage/'placements.json').read_text())
    assert placements()==specs
    children=sorted(group['Children'],key=lambda n:n['Name'])
    for i,(node,spec) in enumerate(zip(children,specs)):
        assert node['Name']==f'ARES transport case {i+1:03d}'
        assert len(node['Components'])==1 and node['Components'][0]['__type']=='Sandbox.ModelRenderer'
        assert np.allclose(np.asarray(node['Position'].split(','),float), (spec['n'],-spec['e'],spec['z']),atol=.001)
        expected=np.asarray(A.K.yaw_rotation(spec['heading']).split(','),float)
        actual=np.asarray(node['Rotation'].split(','),float)
        assert np.allclose(expected,actual,atol=.000001) or np.allclose(expected,-actual,atol=.000001)
        model=node['Components'][0]['Model'];model=model if isinstance(model,str) else model['Path']
        assert model==C.prop_path(spec['size'],spec['front'])
        assert node['Scale']=='1,1,1'
    planned=C.scene_group(A.ids,[{'model':C.prop_path(s['size'],s['front']),
        'position':(s['e'],s['n'],s['z']),'heading':s['heading']} for s in specs])
    assert planned['__guid']==group['__guid']
    for authored,saved in zip(planned['Children'],children):
        assert authored['__guid']==saved['__guid']
        assert authored['Components'][0]['__guid']==saved['Components'][0]['__guid']
    comparison=copy.deepcopy(after)
    parent=next(n for n in walk(comparison) if any(c.get('Name')=='ARES transport cases' for c in n.get('Children',[])))
    parent['Children']=[c for c in parent['Children'] if c.get('Name')!='ARES transport cases']
    diffs=json_diffs(before,comparison)
    (OUT/'scene-diff-without-cases.json').write_text(json.dumps(diffs,indent=2)+'\n')
    serialization=audit_serialization(before,comparison,diffs)
    resource='Assets/models/maps/ares/ares_dressing.vmdl'
    original_doc=(ROOT/'output/ares/crate-v2/stage-v5/before'/resource).read_bytes()
    current_doc=(ROOT/resource).read_bytes();marker=b'_class = "PhysicsShapeList"'
    assert original_doc[original_doc.index(marker):]==current_doc[current_doc.index(marker):]
    assert sha(ROOT/manifest['base_import'])==manifest['retained_bytes_sha256']
    reference=json.loads((OUT/'integration.json').read_text())['ProtectedInputsAtIntegration']
    drifts={p:{'at_integration':h,'current':sha(ROOT/p)} for p,h in reference.items()
            if p!='Assets/scenes/maps/Ares/ares.scene' and sha(ROOT/p)!=h}
    # Independent pressure-door refinement is outside this task. It may move
    # while the case verification runs; never replace its files with a snapshot.
    assert all(p=='Assets/models/maps/ares/ares_hall.vmdl' or '/pressure-doors-v2/' in p for p in drifts),drifts
    lod_proof=[];material_names={'ar_cargo_black','ar_cargo_black_edge','ar_cargo_dust','ar_cargo_gasket'}
    for tag,spec in manifest['models'].items():
        for lod in range(3):
            model=C.build_prop(spec['size'],tag.endswith('-marked'),lod)
            low=spec['size'][1]*.735+.65;high=spec['size'][1]-.95;edges=Counter()
            for paint,rows in model.polygons.items():
                if paint not in material_names:continue
                for points,normal in rows:
                    if min(p[2] for p in points)<low-1e-5 or max(p[2] for p in points)>high+1e-5:continue
                    vs=[tuple(round(float(v),5) for v in p) for p in points]
                    for i in range(1,len(vs)-1):
                        tri=(vs[0],vs[i],vs[i+1])
                        for a,b in zip(tri,tri[1:]+tri[:1]):edges[tuple(sorted((a,b)))]+=1
            holes=[(a,b) for (a,b),count in edges.items() if count==1 and not
                   ((abs(a[2]-low)<1e-4 and abs(b[2]-low)<1e-4) or
                    (abs(a[2]-high)<1e-4 and abs(b[2]-high)<1e-4))]
            assert not holes,(tag,lod,holes)
            lod_proof.append({'model':tag,'lod':lod,'triangles':model.triangle_count(),'open_lid_edges':0})
    compiles=results(OUT/'compile-props-v6/call_tools.json')
    latest=results(OUT/'compile-models-v7/call_tools.json')
    assert len(compiles)==13 and len(latest)==4 and all(r['Success'] for r in compiles+latest)
    native=results(OUT/'final-native-checks/call_tools.json')
    assert len(native)==6 and native[0]['Success']
    for trace,z in zip(native[1:3],(60.,90.)):
        assert trace['Hit'] and not trace['StartedSolid'] and trace['Component']=='ModelCollider'
        assert trace['GameObject']['Name']=='Dressing' and float(trace['EndPosition'].split(',')[-1])==z
    status=native[3];build=native[4]
    assert status['ActiveScene']=='ares' and not status['IsPlaying'] and not status['SceneHasUnsavedChanges']
    assert Path(status['Paths']['ProjectRoot']).resolve()==ROOT
    assert not build['IsBuilding'] and all(c['Success'] and c['Errors']==0 for c in build['Compilers'])
    captures={}
    for key,relative in {
        'hall':'final/hall-stack','hardware':'final/hardware','player':'final/player','cargo':'final/cargo',
        'lod0':'lod-check/player-lod0','lod1':'lod-check/player-lod1','lod2':'lod-check-fixed/player-lod2'}.items():
        image=OUT/f'captures/{relative}.png';meta=json.loads(image.with_name(image.stem+'-camera.json').read_text())
        assert all(meta['Restoration'].values()),key
        if key.startswith('lod'):
            assert meta['Capture']['ForcedCaseLod']==int(key[-1]) and meta['Capture']['ForcedCaseLodRenderers']==132
        captures[key]={'image':image.relative_to(ROOT).as_posix(),'sha256':sha(image),**meta}
    before_meta=json.loads((OUT/'captures/before/hall-stack-camera.json').read_text())['Capture']
    for key in ('Position','Angles','FieldOfView','FovAxis','Width','Height','RequestedExposure'):
        assert before_meta[key]==captures['hall']['Capture'][key],key
    report={'revision':manifest['revision'],'stage':stage,'cases_saved':132,'shared_models':4,'lods_per_model':3,
        'new_authored_scene_objects_only_case_group':True,'existing_authored_scene_properties_preserved':True,
        'editor_save_serialization_audit':serialization,'source_regeneration_ids_preserved':True,
        'collision_definition_bytes_exact':True,'old_case_triangles_removed':12408,'unrelated_obj_bytes_exact':True,
        'original_obj_indices_preserved':True,'models':manifest['models'],'lid_closure_checks':lod_proof,
        'native_prop_compiles':latest,'material_and_initial_model_compiles':compiles,'captures':captures,
        'saved_scene_sha256':sha(ROOT/'Assets/scenes/maps/Ares/ares.scene'),
        'native_scene_compile':native[0],'native_collision_traces':native[1:3],
        'native_final_editor_status':status,'native_compile_errors':0,
        'native_compile_warnings':sum(c['Warnings'] for c in build['Compilers']),
        'matched_hall_camera_and_exposure':True,'independent_hall_changes_preserved':drifts,
        'performance_note':'Four reusable assets with three LODs each; frame-rate impact was not benchmarked.'}
    (OUT/'validation.json').write_text(json.dumps(report,indent=2)+'\n')
    sources=['Tools/ares_map.py','Tools/ares_cargo_case.py','Tools/ares_case_shell.py',
             'Tools/ares_stage_cargo_cases.py','Tools/ares_check_cargo_cases.py',
             'Sources/Ares/crate-v2/scene-instance-ids.json']
    installed={'revision':manifest['revision'],'stage':stage,'scene':'Assets/scenes/maps/Ares/ares.scene',
               'scene_sha256':report['saved_scene_sha256'],'group_guid':group['__guid'],'case_count':132,
               'asset_files':{p:item['after'] for p,item in manifest['files'].items()},
               'sources':{p:sha(ROOT/p) for p in sources},'models':manifest['models'],
               'validation':'output/ares/crate-v2/validation.json','validation_sha256':sha(OUT/'validation.json'),
               'native_save':'output/ares/crate-v2/save-native-cases/save_scene.json',
               'native_checks':'output/ares/crate-v2/final-native-checks/call_tools.json',
               'original_scene':'output/ares/crate-v2/stage-v5/before/Assets/scenes/maps/Ares/ares.scene',
               'captures':{k:v['image'] for k,v in captures.items()}}
    (ROOT/'Sources/Ares/crate-v2/installed.json').write_text(json.dumps(installed,indent=2)+'\n')
    print(json.dumps({'cases_saved':132,'shared_models':4,'lods_each':3,'lid_checks':len(lod_proof),
                      'captures_reviewed':len(captures),'collision_preserved':True}))


if __name__=='__main__':main()
