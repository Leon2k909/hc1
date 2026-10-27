"""Verify published display assets, scoped lighting and native review evidence."""
import json
from pathlib import Path
import re
from railhead_stage_extinguisher import sha
from belltower_safe_imports import span
from veridant_stage_backbar import units

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output/veridant/backbar-v2'


def results(path):
    raw=json.loads(path.read_text());assert not raw.get('isError'),path
    return [json.loads(x['text']) for x in raw['content'] if x['type']=='text']


def flatten(scene):
    queue=list(scene['GameObjects']);out={}
    while queue:
        node=queue.pop();out[node['__guid']]=node;queue.extend(node.get('Children',[]))
    return out


def normalize(value):
    # Engine saves can refresh asset IDs while retaining the same resource path.
    if isinstance(value,dict):
        if 'Path' in value and 'Id' in value:return {'Path':value['Path']}
        return {k:normalize(v) for k,v in value.items()}
    if isinstance(value,list):return [normalize(v) for v in value]
    return value


def main():
    manifest=json.loads((OUT/'stage-v7/manifest.json').read_text())
    for p,item in manifest['files'].items():assert sha(ROOT/p)==item['after'],p
    for p,h in manifest['source_sha256'].items():assert sha(ROOT/p)==h,p
    for p,parts in manifest['required_source_snippets'].items():
        assert all(part in (ROOT/p).read_text() for part in parts),p
    scene_path='Assets/scenes/maps/Veridant/veridant.scene'
    first=json.loads((OUT/'stage-v1/manifest.json').read_text())
    unrelated_changes=[p for p,h in manifest['unrelated_import_snapshot_sha256'].items() if sha(ROOT/p)!=h]
    for p,h in manifest['protected_sha256'].items():
        if p!=scene_path:assert sha(ROOT/p)==h,p
    expected=[{k:x[k] for k in ('lo','hi','z0','face')} for x in manifest['sections']]
    assert units()==expected
    document='Assets/models/maps/veridant/veridant_buildings.vmdl'
    old=(ROOT/manifest['files'][document]['backup']).read_text();new=(ROOT/document).read_text()
    for marker in ('_class = "RenderMeshList"','_class = "PhysicsShapeList"'):
        a,b=span(old,marker);c,d=span(new,marker);assert old[a:b]==new[c:d],marker
    before=json.loads((OUT/'before-lighting.scene.json').read_text())
    after=json.loads((ROOT/scene_path).read_text())
    shared=json.loads((ROOT/'Sources/Veridant/backbar-v2/shared-scene-review.json').read_text())
    reviewed={(x['id'],x['field']):x for x in shared['existing_object_fields']}
    old_nodes,new_nodes=flatten(before),flatten(after)
    receipt=json.loads((OUT/'lighting-native.json').read_text())
    own_ids={receipt['Group']}|{x['Id'] for x in receipt['CreatedLights']}
    assert len(own_ids)==23 and own_ids.issubset(set(new_nodes)-set(old_nodes))
    external_ids=set(new_nodes)-set(old_nodes)-own_ids
    explicit_ids=set(old_nodes)|{c['__guid'] for n in old_nodes.values() for c in n.get('Components',[])}
    assert set(old_nodes).issubset(new_nodes)
    refreshes=0;changes=[];retired_prefab_aliases=[]
    for key,a in old_nodes.items():
        b=new_nodes[key]
        for field in a.keys()|b.keys():
            if field=='Children':
                assert [x['__guid'] for x in a.get(field,[])]==[x['__guid'] for x in b.get(field,[]) if x['__guid'] in old_nodes]
            elif field=='__PrefabIdToInstanceId':
                for k,v in a[field].items():
                    if k in b[field]:assert b[field][k]==v
                    else:
                        assert v not in explicit_ids
                        retired_prefab_aliases.append((key,k,v))
            elif field=='Components':
                assert [x['__guid'] for x in a[field]]==[x['__guid'] for x in b[field]]
                for ca,cb in zip(a[field],b[field]):
                    if ca!=cb and normalize(ca)==normalize(cb):refreshes+=1
                    for prop in ca.keys()|cb.keys():
                        if normalize(ca.get(prop))==normalize(cb.get(prop)):continue
                        assert a.get('Name') in ('Probe Cafe','Probe Lounge Down')
                        assert prop in ('Mode','BakedTexture')
                        changes.append((a['Name'],prop))
            elif a.get(field)!=b.get(field):
                review=reviewed.get((key,field));assert review,(a.get('Name'),field)
                assert a[field]==review['before'] and b[field]==review['after']
    assert len(changes)==4
    for k in before.keys()|after.keys():
        if k=='GameObjects':continue
        if k=='__references':assert before[k]==shared['references_before'] and after[k]==shared['references_after']
        else:assert before.get(k)==after.get(k),k
    group=new_nodes[receipt['Group']]
    assert len(group['Children'])==22
    for node in group['Children']:
        assert len(node['Components'])==1
        c=node['Components'][0];assert c['__type']=='Sandbox.PointLight' and c['Shadows'] is False and c['Radius']==34
    cache=json.loads((ROOT/'Sources/Veridant/backbar-v2/lighting-installed.json').read_text())
    for name,path in cache['probe_textures'].items():
        node=next(n for n in new_nodes.values() if n.get('Name')==name);p=node['Components'][0]
        assert p['Mode']=='Baked' and p['BakedTexture']['Path']==path
        assert (ROOT/'Assets'/str(path+'_c')).exists()
    assets=results(OUT/'asset-info-final/call_tools.json')
    assert len(assets)==17 and all(a['IsCompiledAndUpToDate'] and not a['IsCompileFailed'] for a in assets)
    rays=results(OUT/'door-rays/call_tools.json')
    assert len(rays)==27 and all(not x['Hit'] and not x['StartedSolid'] for x in rays)
    status,camera=results(OUT/'final-status/call_tools.json')
    assert Path(status['Paths']['ProjectRoot']).resolve()==ROOT
    assert status['ActiveScene']=='veridant' and not status['IsPlaying'] and not status['SceneHasUnsavedChanges']
    assert not status['IsCompiling'] and status['LastCompileSucceeded'] and status['LastCompileErrors']==0
    captures={}
    for view in ('cafe','niche','bottles','angle'):
        image=ROOT/f'output/veridant/quality/backbar-v2-final-clean/{view}.png'
        meta=json.loads(image.with_name(view+'-camera.json').read_text())
        assert all(meta['Restoration'].values()) and meta['Capture']['SourceSceneSha256']==sha(ROOT/scene_path)
        captures[view]={'path':image.relative_to(ROOT).as_posix(),'sha256':sha(image),**meta}
    baseline=json.loads((ROOT/'output/veridant/quality/backbar-v2-before/cafe-camera.json').read_text())
    for k in ('Position','Angles','FieldOfView','FovAxis','Width','Height','RequestedExposure'):
        assert baseline['Capture'][k]==captures['cafe']['Capture'][k],k
    families=sorted({x for s in manifest['sections'] for x in s['families']});assert families==list(range(8))
    report={'revision':manifest['revision'],'stage':'stage-v7','sections':manifest['sections'],
            'bottles':manifest['bottles'],'glasses':manifest['glasses'],'bottle_families':8,
            'triangles':manifest['triangles'],'shelf_lights':22,'baked_room_probes':2,
            'native_assets_compiled_and_current':17,'clear_doorway_rays':27,
            'all_previous_object_ids_preserved':True,'existing_resource_id_refreshes':refreshes,
            'unrelated_render_imports_and_physics_preserved_on_publication':True,'lighting_scene_changes_scoped':True,
            'external_import_updates_since_staging':unrelated_changes,
            'preserved_external_scene_additions':[{'id':k,'name':new_nodes[k].get('Name')} for k in external_ids],
            'reviewed_shared_scene_fields_preserved':shared['existing_object_fields'],
            'engine_retired_nonserialized_prefab_aliases':retired_prefab_aliases,
            'editor_status':status,'editor_camera':camera,'captures':captures,
            'performance_note':'Geometry and bounded unshadowed light count recorded; FPS not benchmarked.'}
    (OUT/'validation.json').write_text(json.dumps(report,indent=2)+'\n')
    installed={k:v for k,v in report.items() if k not in ('captures','editor_status','editor_camera')}
    installed.update({'validation':'output/veridant/backbar-v2/validation.json',
                      'hero':captures['cafe']['path'],'detail':captures['niche']['path']})
    (ROOT/'Sources/Veridant/backbar-v2/installed.json').write_text(json.dumps(installed,indent=2)+'\n')
    print(json.dumps({k:report[k] for k in ('sections','bottles','glasses','bottle_families','triangles',
                                          'shelf_lights','baked_room_probes','clear_doorway_rays')}))


if __name__=='__main__':main()
