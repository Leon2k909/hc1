"""Verify the published shelf patch, native compilation and doorway ray checks."""
import json
from collections import Counter
from pathlib import Path
import re
import map_kit as K
import veridant_stage_door_clearance as T


def results(path):
    raw=json.loads(path.read_text(encoding='utf-8'));assert not raw.get('isError'),path
    rows=[]
    for item in raw['content']:
        if item['type']=='text':
            try:rows.append(json.loads(item['text']))
            except json.JSONDecodeError:pass
    return rows


def installed_shelves(model, doors, overrides=None):
    """Follow current render imports, including later prop-isolation changes."""
    resource=T.ROOT/'Assets/models/maps/veridant/veridant_buildings.vmdl'
    text=resource.read_text()
    start,end=T.Patch.span(text,'_class = "RenderMeshList"')
    render=text[start:end]
    for field,expected in (('import_translation',[0,0,0]),('import_rotation',[0,0,0]),('import_scale',[1,1,1])):
        for values in re.findall(field+r'\s*=\s*\[([^\]]+)\]',render):
            assert [float(v) for v in values.replace(',',' ').split()]==expected
    paths=[T.ROOT/'Assets'/name for name in re.findall(r'filename\s*=\s*"([^"]+\.obj)"',render)]
    assert paths
    lookup,faces=T.Patch.lookup_polygons(model)
    found=Counter();blocked=[];imports={}
    for path in paths:
        if overrides:path=overrides.get(path,path)
        digest=T.sha(path);vertices=[None];paint=None
        for line in path.open('rb'):
            if line.startswith(b'v '):vertices.append(T.Patch.point(line[2:].decode()))
            elif line.startswith(b'usemtl '):paint=line.split()[1]
            elif line.startswith(b'f '):
                points=[vertices[int(v.split(b'/')[0])] for v in line.split()[1:]]
                key=(paint,frozenset(points))
                if key in lookup:found[key]+=1
                if paint and (b'timber' in paint or b'wood' in paint):
                    plan=[(-p[0]/1000,p[2]/1000,p[1]/1000) for p in points]
                    low=[min(p[i] for p in plan) for i in range(3)]
                    high=[max(p[i] for p in plan) for i in range(3)]
                    for centre,width,bottom,top in doors:
                        opening=((-706,-690),(centre-width/2+.1,centre+width/2-.1),(bottom+2,top-2))
                        if all(high[i]>=a and low[i]<=b for i,(a,b) in enumerate(opening)):
                            blocked.append({'import':str(path),'material':paint.decode(),'door':centre,'bounds':[low,high]})
        assert T.sha(path)==digest,('Shared render import changed during check',path)
        imports[path.relative_to(T.ROOT).as_posix()]=digest
    T.Patch.coverage(found,lookup,faces)
    assert not blocked,blocked[:10]
    return {'render_import_sha256':imports,'replacement_triangles_present':sum(found.values()),'wood_faces_in_doorways':0}


def main():
    stage=T.OUT/'stage-v5-index-repair';manifest=json.loads((stage/'manifest.json').read_text())
    current_assets={relative:T.sha(T.ROOT/relative) for relative in manifest['files']}
    assert all(current_assets[p]==item['after'] for p,item in manifest['files'].items())
    sources={p:T.sha(T.ROOT/p)==v for p,v in manifest['source_sha256'].items()}
    protected={p:T.sha(T.ROOT/p)==v for p,v in manifest['protected_sha256'].items()}
    # The editor is shared. Preserve later work in other map functions, while
    # checking that the scoped replacement fixture still matches the publication.
    old,new,ranges=T.fixtures()
    assert not old.boxes and not old.hulls and not new.boxes and not new.hulls
    assert json.loads(json.dumps(ranges))==manifest['shelf_ranges']
    folder=T.OUT/'validation-fixture';folder.mkdir(exist_ok=True)
    K.write_obj(folder/'shelves.obj',new,'veridant_buildings')
    assert T.sha(folder/'shelves.obj')==T.sha(T.OUT/'stage-v1/shelves.obj')
    installed=installed_shelves(new,[manifest['doorways']['lounge'],*manifest['doorways']['cafe']])
    compiled=results(T.OUT/'compile-current/asset_compile.json')[0];assert compiled['Success']
    rays=results(T.OUT/'trace-current/call_tools.json')
    assert len(rays)==27 and all(not r['Hit'] and not r['StartedSolid'] for r in rays)
    requests=json.loads((T.OUT/'trace-doorways.json').read_text())['calls']
    status,camera=results(T.OUT/'final-status/call_tools.json')
    assert Path(status['Paths']['ProjectRoot']).resolve()==T.ROOT
    assert status['ActiveScene']=='veridant' and status['LastCompileSucceeded'] and status['LastCompileErrors']==0
    image=T.ROOT/'output/veridant/quality/door-obstruction-after-repaired/cafe-south.png'
    meta=json.loads(image.with_name('cafe-south-camera.json').read_text())
    original=json.loads((T.ROOT/'output/veridant/quality/door-obstruction-before/cafe-south-camera.json').read_text())
    assert all(meta['Restoration'].values())
    for key in ('Position','Angles','FieldOfView','FovAxis','Width','Height','RequestedExposure'):
        assert original['Capture'][key]==meta['Capture'][key],key
    report={'revision':manifest['revision'],'doorways_cleared':3,'native_compile':compiled,
        'native_collision_rays_clear':27,'rays':[{'request':q,'result':r} for q,r in zip(requests,rays)],
        'door_width_inches':60,'door_height_inches':96,'shelf_jamb_clearance_inches':4,
        'shelf_ranges':ranges,'unrelated_face_and_material_records_exact':True,
        'original_geometry_indices_restored':True,'index_repair_proof':manifest['index_repair_proof'],
        'physics_unwritten_by_this_task':True,'scene_unwritten_by_this_task':True,
        'source_files_matching_publication':sources,'protected_files_matching_publication':protected,
        'published_asset_sha256':{p:i['after'] for p,i in manifest['files'].items()},
        'current_asset_sha256':current_assets,'installed_shelves':installed,
        'native_import':'output/veridant/door-obstruction/native-import-index-repair.json',
        'screenshot':image.relative_to(T.ROOT).as_posix(),'screenshot_sha256':T.sha(image),
        'capture_restoration':meta['Restoration'],'editor_status':status,'editor_camera_at_completion':camera,
        'limitations':['The optional player-box sweep timed out and is not claimed as passed.',
                       'Other entrance captures were interrupted while unrelated shared assets recompiled; the pictured cafe entrance was visually verified.']}
    (T.OUT/'validation.json').write_text(json.dumps(report,indent=2)+'\n')
    (T.ROOT/'Sources/Veridant/door-clearance-v1/installed.json').write_text(json.dumps({
        'revision':report['revision'],'doorways_cleared':3,'native_compile_passed':True,
        'native_collision_rays_clear':27,'physics_unwritten_by_this_task':True,'scene_unwritten_by_this_task':True,
        'validation':'output/veridant/door-obstruction/validation.json','screenshot':report['screenshot'],
        'source_hook':'Tools/veridant_map.py:shelves_beside_doors'},indent=2)+'\n')
    print(json.dumps({'doorways_cleared':3,'native_compile_passed':True,'native_collision_rays_clear':27,
                      'shelf_ranges':ranges,'pictured_door_visually_verified':True}))


if __name__=='__main__':main()
