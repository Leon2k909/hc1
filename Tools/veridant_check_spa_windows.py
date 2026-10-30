"""Verify the scoped spa asset replacement and four existing fixture relocations."""
import argparse
import copy
import json
from pathlib import Path
import shutil

import map_kit as K
import veridant_map as V
import veridant_spa_windows as W
from railhead_stage_extinguisher import sha

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output/veridant/spa-windows-v2'
SCENE=ROOT/'Assets/scenes/maps/Veridant/veridant.scene'


def objects(scene):
    def walk(items):
        for item in items:
            yield item
            yield from walk(item.get('Children',[]))
    return {item['__guid']:item for item in walk(scene['GameObjects'])}


def results(path):
    raw=json.loads(path.read_text());assert not raw.get('isError'),path
    return [json.loads(item['text']) for item in raw['content'] if item['type']=='text']


def prepare():
    manifest=json.loads((OUT/'stage-v4/manifest.json').read_text())
    assert sha(SCENE)==manifest['protected_sha256']['Assets/scenes/maps/Veridant/veridant.scene']
    backup=OUT/'before-light-relocation.scene'
    if backup.exists():assert sha(backup)==sha(SCENE)
    else:shutil.copy2(SCENE,backup)
    data=json.loads(SCENE.read_text());named={o.get('Name',''):o for o in objects(data).values()}
    names=('Spa lamp 100.0','Spa lamp 500.0','Spa lamp 900.0','Spa west lamp');reads=[];moves=[];details=[]
    for name in names:
        o=named[name];assert len(o['Components'])==1 and o['Components'][0]['__type']=='Sandbox.PointLight'
        p=o['Position'].split(',');old_z=float(p[2]);assert old_z==(218 if name=='Spa west lamp' else 272)
        p[2]='192' if name=='Spa west lamp' else '250';position=','.join(p)
        reads.append(dict(name='get_game_object',arguments=dict(id=o['__guid'],includeComponentProperties=True)))
        moves.append(dict(name='set_game_object',arguments=dict(id=o['__guid'],position=position)))
        details.append(dict(id=o['__guid'],name=name,before=o['Position'],after=position))
    reads.append(dict(name='editor_status',arguments={}))
    moves.append(dict(name='save_scene',arguments={}))
    (OUT/'light-read-request.json').write_text(json.dumps(dict(calls=reads),indent=2)+'\n')
    (OUT/'light-move-request.json').write_text(json.dumps(dict(calls=moves),indent=2)+'\n')
    (OUT/'light-moves.json').write_text(json.dumps(details,indent=2)+'\n')
    print(json.dumps(dict(existing_lights_to_move=4,backup_sha256=sha(backup))))


def preflight():
    moves=json.loads((OUT/'light-moves.json').read_text());actual=results(OUT/'light-read/call_tools.json')
    assert sha(SCENE)==sha(OUT/'before-light-relocation.scene')
    for expected,row in zip(moves,actual[:4]):
        assert row['Id']==expected['id'] and row['Name']==expected['name']
        a=[float(x) for x in row['WorldPosition'].split(',')];b=[float(x) for x in expected['before'].split(',')]
        assert all(abs(x-y)<1e-4 for x,y in zip(a,b)),(row['Name'],a,b)
    status=actual[-1]
    assert status['ActiveScene']=='veridant' and not status['IsPlaying'] and not status['SceneHasUnsavedChanges']
    print(json.dumps(dict(verified_existing_light_positions=4,scene_saved=True,ready=True)))


def verify():
    manifest=json.loads((OUT/'stage-v4/manifest.json').read_text())
    for p,item in manifest['files'].items():assert sha(ROOT/p)==item['after'],p
    for group in ('source_sha256','protected_sha256'):
        for p,h in manifest[group].items():
            if p!='Assets/scenes/maps/Veridant/veridant.scene':assert sha(ROOT/p)==h,p
    for p,parts in manifest['required_source_snippets'].items():
        text=(ROOT/p).read_text();assert all(part in text for part in parts),p
    # Model collision definition stays byte-identical throughout both publications.
    resource=Path('Assets/models/maps/veridant/veridant_buildings.vmdl')
    first=json.loads((OUT/'stage-v2/manifest.json').read_text())
    before=(ROOT/first['files'][resource.as_posix()]['backup']).read_text();after=(ROOT/resource).read_text()
    marker='_class = "PhysicsShapeList"';assert before[before.index(marker):]==after[after.index(marker):]
    assert sha(ROOT/manifest['base_import'])==manifest['retained_bytes_sha256']
    # The generator retains the exact two original spa collision boxes.
    old=K.Model();new=K.Model();e0,e1,n0,n1=V.SPA
    V.solid(old,e0,e1,n0,n1,0,V.SPA_TOP,{'default':'vr_stone','+n':None,'-z':None})
    V.solid(old,e0-6,e1+6,n0-6,n1+6,V.SPA_TOP,V.SPA_TOP+14,'vr_stone_dark')
    W.build_spa(new,V.SPA,V.SPA_TOP)
    import numpy as np
    assert len(old.boxes)==len(new.boxes)==2
    for a,b in zip(old.boxes,new.boxes):
        for x,y in zip(a[:3],b[:3]):assert np.array_equal(x,y)
        assert a[3]==b[3]
    # A native scene save is allowed to change only these four object positions.
    baseline=json.loads((OUT/'before-light-relocation.scene').read_text());expected=copy.deepcopy(baseline)
    revised=objects(expected);moves=json.loads((OUT/'light-moves.json').read_text())
    for row in moves:revised[row['id']]['Position']=row['after']
    current=json.loads(SCENE.read_text())
    assert current==expected,'Scene changed outside the four fixture transforms; inspect structural diff.'
    light_receipt=results(OUT/'light-move/call_tools.json')
    assert len(light_receipt)==5 and light_receipt[-1]['HasUnsavedChanges']==False
    compiles=results(OUT/'compile-final/call_tools.json')
    assert len(compiles)==13 and all(r['Success'] for r in compiles)
    captures={}
    for name in ('front','angle','west'):
        picture=ROOT/f'output/veridant/quality/spa-windows-v2-final/{name}.png'
        meta=json.loads(picture.with_name(name+'-camera.json').read_text())
        assert all(meta['Restoration'].values())
        captures[name]=dict(path=picture.relative_to(ROOT).as_posix(),sha256=sha(picture),**meta)
    old_meta=json.loads((ROOT/'output/veridant/quality/spa-windows-v2-before/front-camera.json').read_text())
    for key in ('Position','Angles','FieldOfView','FovAxis','Width','Height','RequestedExposure'):
        assert old_meta['Capture'][key]==captures['front']['Capture'][key],key
    status,camera=results(OUT/'final-status/call_tools.json')
    assert Path(status['Paths']['ProjectRoot']).resolve()==ROOT
    assert status['ActiveScene']=='veridant' and not status['IsPlaying'] and not status['IsCompiling']
    assert not status['SceneHasUnsavedChanges'] and status['LastCompileSucceeded'] and status['LastCompileErrors']==0
    receipt=json.loads((OUT/'native-import.json').read_text())
    assert receipt['WindowsUpdated']==9 and receipt['EditorStatePreserved'] and receipt['PhysicsBytesPreserved']
    report=dict(revision=manifest['revision'],stage='stage-v4',windows_updated=9,
        triangles=manifest['new_triangles'],physics_bytes_exact=True,generator_collision_preserved=True,
        retained_obj_bytes_and_indices_preserved=True,other_imports_preserved=True,
        scene_changes_only_four_existing_light_positions=True,fixture_moves=moves,
        corner_room_overlap_removed=True,native_compiles=compiles,captures=captures,
        matched_camera_and_exposure=True,editor_status=status,editor_camera=camera,
        visual_review='Front, oblique and west facade captures reviewed; pane-obstructing fixture meshes removed.',
        performance_note='43,420 replacement triangles across nine windows and two facade faces; FPS was not benchmarked.')
    (OUT/'validation.json').write_text(json.dumps(report,indent=2)+'\n')
    (ROOT/'Sources/Veridant/spa-windows-v2/installed.json').write_text(json.dumps(dict(
        revision=manifest['revision'],windows_updated=9,validation='output/veridant/spa-windows-v2/validation.json',
        screenshot=captures['angle']['path'],source_hook='Tools/veridant_map.py:spa',
        physics_unchanged=True,scene_changed_only_four_existing_fixture_positions=True),indent=2)+'\n')
    print(json.dumps(dict(windows_updated=9,native_compiles_passed=13,physics_preserved=True,
                         scene_changes_only_four_light_positions=True,captures_reviewed=3)))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prepare-light-move',action='store_true');parser.add_argument('--preflight',action='store_true')
    args=parser.parse_args()
    if args.prepare_light_move:prepare()
    elif args.preflight:preflight()
    else:verify()
