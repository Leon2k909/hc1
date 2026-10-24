"""Verify the installed circular dials, unaffected mesh bytes and native views."""
import hashlib
import json
from pathlib import Path
import numpy as np
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
STAGE=ROOT/'output/belltower/clock-v1/stage'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    manifest=json.loads((STAGE/'manifest.json').read_text())
    target=ROOT/manifest['path'];original=STAGE/'before'/manifest['path']
    assert sha(original)==manifest['before'] and sha(target)==manifest['after']
    assert sha(target.with_suffix('.vmdl'))==manifest['vmdl_sha256']
    assert sha(target.with_suffix('.mtl'))==manifest['mtl_sha256']
    for group in ('source_sha256','texture_sha256'):
        for relative,expected in manifest[group].items():assert sha(ROOT/relative)==expected,relative
    before=original.read_bytes().splitlines(keepends=True)
    after=target.read_bytes().splitlines(keepends=True)
    first=lambda lines:next(i for i,line in enumerate(lines) if line.startswith(b'usemtl '))
    a,b=first(before),first(after);drop=set(manifest['removed_face_lines'])
    assert len(drop)==48 and all(before[i].startswith(b'f ') for i in drop)
    kept=[line for i,line in enumerate(before[a:],a) if i not in drop]
    assert before[:a]==after[:a] and after[b:b+len(kept)]==kept
    tail=after[b+len(kept):]
    assert sum(line.startswith(b'f ') for line in tail)==8056
    old_v=sum(line.startswith(b'v ') for line in before)
    vertices=[tuple(map(float,line.split()[1:])) for line in after[a:b] if line.startswith(b'v ')]
    assert len(vertices)>0
    used=set();paint=None
    for line in tail:
        if line.startswith(b'usemtl '):paint=line[7:].strip().decode()
        elif line.startswith(b'f ') and paint=='clock':
            used.update(int(t.split(b'/')[0])-old_v-1 for t in line.split()[1:])
    points=np.array([vertices[i] for i in used])
    # OBJ axes are (world y, world z, world x). Check all four exported faces
    # against their actual tower planes and the circular 37.1-inch enamel edge.
    checks=[]
    for axis,plane,horizontal,centre in ((2,712.5,0,0),(2,937.5,0,0),
                                         (0,112.5,2,825),(0,-112.5,2,825)):
        group=points[np.abs(points[:,axis]-plane)<.001]
        assert len(group)==96
        radii=np.hypot(group[:,horizontal]-centre,group[:,1]-690)
        assert np.max(np.abs(radii-37.1))<.002
        checks.append({'plane_axis':axis,'plane':plane,'vertices':len(group),'radius':37.1})
    assert len(used)==384
    compiled=Path(str(target.with_suffix('.vmdl'))+'_c')
    assert compiled.stat().st_mtime>=target.stat().st_mtime
    comparison={}
    common=('Position','Angles','FieldOfView','FovAxis','Width','Height','RequestedExposure',
            'ViewportSettledMilliseconds','SourceSceneSha256','HelperSha256')
    for view in ('front','angle'):
        paths=[ROOT/f'output/belltower/quality/clock-v1-{suffix}/{view}' for suffix in ('before','after')]
        data=[json.loads(p.with_name(p.name+'-camera.json').read_text()) for p in paths]
        assert all(data[0]['Capture'][key]==data[1]['Capture'][key] for key in common)
        assert all(all(d['Restoration'].values()) for d in data)
        images=[np.asarray(Image.open(p.with_suffix('.png')).convert('RGB'),dtype=np.int16) for p in paths]
        drift=float(np.abs(images[0][30:150,20:180]-images[1][30:150,20:180]).mean())
        assert drift<.1,(view,drift)
        comparison[view]={'matched_inputs':True,'restoration_verified':True,'unchanged_stone_mean_rgb8':drift}
    assert sha(ROOT/'Assets/scenes/maps/Belltower/belltower.scene')==manifest['scene_sha256']
    report={'revision':'round-clock-v1','clock_faces':checks,'other_obj_lines_byte_identical':True,
            'model_resource_and_physics_byte_identical':True,'original_texture_bytes_unchanged':True,
            'new_materials':0,'new_game_objects':0,'new_colliders':0,'native_comparisons':comparison,
            'scene_unchanged':True,'compiled_new_mesh':True,'native_play_test_performed':False}
    (STAGE.parent/'verification.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf8')
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
