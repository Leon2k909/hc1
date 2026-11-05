"""Stage all 21 chairs, retaining the blue cafe's accepted asymmetric layout."""
from pathlib import Path
from collections import Counter
import inspect,json,math,re,shutil,sys,tempfile
import numpy as np
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'Tools'))
import map_kit as K
import belltower_map as B
import belltower_detail as D
import belltower_cafe_spacing as Spacing
import belltower_bistro_chairs as Chairs
import belltower_remove_doorway_posts as Patch
from belltower_move_square_lamps import geometry,sha
OUT=Path(tempfile.gettempdir())/'belltower-bistro-chair-v2'
STAGE=OUT/'install-stage'
Patch.STAGE=STAGE
DOCUMENTS=['Assets/models/maps/belltower/belltower_west.vmdl','Assets/models/maps/belltower/belltower_east.vmdl',
 'Assets/models/maps/belltower/wheelbarrow-v2/trial_west.vmdl','Assets/models/maps/belltower/wheelbarrow-v2/trial_east.vmdl',
 'Assets/models/maps/belltower/ivy-realism-v3/preview_west.vmdl','Assets/models/maps/belltower/ivy-realism-v3/preview_east.vmdl',
 'Assets/models/compare_old/headstone-preview/belltower_west_nostones.vmdl']

def placements_and_geometry():
    west=K.Model();east=K.Model();placements=[]
    for k,centre in enumerate(Spacing.OLD_WEST):
        rng=np.random.default_rng(70+k);rng.uniform(0,math.pi/4)
        for angle in (.5,2.6,4.7):
            angle+=rng.uniform(-.25,.25)
            c=np.array((centre[0]+24*math.cos(angle),centre[1]+24*math.sin(angle),0.))
            yaw=math.degrees(angle)+180+rng.uniform(-12,12)
            old=K.Model();D.bistro_chair(old,c[:2],yaw)
            for paint,rows in old.polygons.items():west.polygons[paint].extend(rows)
            placements.append(('west',tuple(c),yaw))
            shift=Spacing.delta(k)
            if shift is None:continue
            mirror=old.mirrored(B.EAST_PAINTS)
            for paint,rows in mirror.polygons.items():east.polygons[paint].extend(([p+shift for p in points],normal) for points,normal in rows)
            e=c*np.array((-1.,1.,1.))+shift
            placements.append(('east',tuple(e),180.-yaw))
    return placements,west,east

def main():
    STAGE.mkdir(parents=True,exist_ok=False)
    (STAGE/'legacy-chair.py.txt').write_text(inspect.getsource(D.bistro_chair))
    placements,west,east=placements_and_geometry()
    assert len(placements)==21
    wanted=geometry(west)+geometry(east);assert sum(wanted.values())==8064
    documents={p:(ROOT/p).read_text() for p in DOCUMENTS}
    references=set(ref for text in documents.values() for ref in re.findall(r'filename\s*=\s*"([^"]+\.obj)"',text))
    candidates={f'Assets/models/maps/belltower/belltower_{s}.obj' for s in ('west','east')}
    candidates.update('Assets/'+r for r in references if re.search(r'_(iron_green|planks)\.obj$',r))
    files={}
    for relative in sorted(candidates):
        row,found=Patch.render(ROOT/relative,wanted)
        if not row:continue
        assert all(v<=wanted[k] for k,v in found.items()) and row['triangles_after']>0
        files[relative]=row
    assert files['Assets/models/maps/belltower/belltower_west.obj']['removed_triangles']==4608
    assert files['Assets/models/maps/belltower/belltower_east.obj']['removed_triangles']==3456
    protected={p:sha(ROOT/p) for p in DOCUMENTS}
    protected.update({'Assets/'+r:sha(ROOT/'Assets'/r) for r in references if 'Assets/'+r not in files})
    deleted={}
    folder=ROOT/'Assets/models/maps/belltower/bistro-chair-v2'
    for name in ('west_baseline.vmdl','west_without_chair.vmdl','base_green.obj','base_wood.obj','materials.mtl'):
        p=folder/name
        for q in (p,Path(str(p)+'.meta'),Path(str(p)+'_c')):
            if not q.exists():continue
            relative=q.relative_to(ROOT).as_posix();backup=STAGE/'deleted-backups'/relative
            backup.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(q,backup)
            deleted[relative]={'before':sha(q),'backup':str(backup)}
    group=Chairs.group(B.ids,placements);(STAGE/'chairs.json').write_text(json.dumps(group,indent=2))
    report={'revision':'belltower-bistro-chair-v2-install','files':files,'protected':protected,'deleted':deleted,'compile_models':DOCUMENTS,'scene_before':sha(ROOT/'Assets/scenes/maps/Belltower/belltower.scene'),'group_sha256':sha(STAGE/'chairs.json'),'chairs':21,'old_triangles_removed':8064,'placements':placements}
    (STAGE/'manifest.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'chairs':21,'west':12,'east':9,'targets':len(files),'old_triangles_removed':8064,'retired_review_files':len(deleted),'other_geometry_and_physics_preserved':True}))

if __name__=='__main__':main()
