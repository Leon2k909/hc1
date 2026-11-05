"""Remove the seven approved legacy tables without changing other geometry."""
from pathlib import Path
from collections import Counter
import importlib.util,inspect,json,re,shutil,sys,tempfile
import numpy as np
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'Tools'))
import map_kit as K
import belltower_map as B
import belltower_detail as D
import belltower_cafe_spacing as Spacing
import belltower_bistro_tables as Tables
import belltower_remove_doorway_posts as Patch
from belltower_move_square_lamps import geometry,sha
spec=importlib.util.spec_from_file_location('chair_install',ROOT/'Sources/Belltower/bistro-chair-v2/stage_install.py')
Chairs=importlib.util.module_from_spec(spec);spec.loader.exec_module(Chairs)
OUT=Path(tempfile.gettempdir())/'belltower-bistro-table-v2';STAGE=OUT/'install-stage';Patch.STAGE=STAGE

def placements_and_geometry():
    west=K.Model();east=K.Model();placements=[]
    for k,centre in enumerate(Spacing.OLD_WEST):
        old=K.Model();D.bistro_table(old,centre)
        for paint,rows in old.polygons.items():west.polygons[paint].extend(rows)
        placements.append(('west',(*centre,0.)))
        shift=Spacing.delta(k)
        if shift is None:continue
        mirrored=old.mirrored(B.EAST_PAINTS)
        for paint,rows in mirrored.polygons.items():east.polygons[paint].extend(([p+shift for p in points],normal) for points,normal in rows)
        placements.append(('east',tuple(np.array((-centre[0],centre[1],0.))+shift)))
    return placements,west,east

def main():
    STAGE.mkdir(parents=True,exist_ok=False)
    (STAGE/'legacy-table.py.txt').write_text(inspect.getsource(D.bistro_table))
    review=json.loads((OUT/'manifest.json').read_text())
    for path,checksum in review['files'].items():assert sha(ROOT/path)==checksum,path
    placements,west,east=placements_and_geometry();assert len(placements)==7
    wanted=geometry(west)+geometry(east);assert sum(wanted.values())==3038
    documents={p:(ROOT/p).read_text() for p in Chairs.DOCUMENTS}
    references={ref for text in documents.values() for ref in re.findall(r'filename\s*=\s*"([^"]+\.obj)"',text)}
    candidates={f'Assets/models/maps/belltower/belltower_{side}.obj' for side in ('west','east')}
    candidates.update('Assets/'+r for r in references if re.search(r'_(iron_green|iron_black)\.obj$',r))
    files={}
    for relative in sorted(candidates):
        row,found=Patch.render(ROOT/relative,wanted)
        if not row:continue
        assert all(v<=wanted[k] for k,v in found.items()) and row['triangles_after']>0
        files[relative]=row
    assert files['Assets/models/maps/belltower/belltower_west.obj']['removed_triangles']==1736
    assert files['Assets/models/maps/belltower/belltower_east.obj']['removed_triangles']==1302
    protected={p:sha(ROOT/p) for p in Chairs.DOCUMENTS}
    protected.update({'Assets/'+r:sha(ROOT/'Assets'/r) for r in references if 'Assets/'+r not in files})
    protected.update({p:h for p,h in review['files'].items() if re.search(r'/(bistro_table\.vmdl|table_lod[0-2]\.(obj|mtl))$',p)})
    deleted={};folder=ROOT/'Assets/models/maps/belltower/bistro-table-v2'
    for name in ('west_baseline.vmdl','west_without_table.vmdl','base_green.obj','base_black.obj','materials.mtl'):
        p=folder/name
        for q in (p,Path(str(p)+'.meta'),Path(str(p)+'_c')):
            if not q.exists():continue
            relative=q.relative_to(ROOT).as_posix();backup=STAGE/'deleted-backups'/relative
            backup.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(q,backup)
            deleted[relative]={'before':sha(q),'backup':str(backup)}
    (STAGE/'tables.json').write_text(json.dumps(Tables.group(B.ids,placements),indent=2))
    report={'revision':'belltower-bistro-table-v2-install','files':files,'protected':protected,'deleted':deleted,'compile_models':Chairs.DOCUMENTS,'scene_before':sha(ROOT/'Assets/scenes/maps/Belltower/belltower.scene'),'group_sha256':sha(STAGE/'tables.json'),'tables':7,'old_triangles_removed':3038,'placements':placements}
    (STAGE/'manifest.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'tables':7,'west':4,'east':3,'targets':len(files),'old_triangles_removed':3038,'retired_review_files':len(deleted),'other_geometry_and_physics_preserved':True}))

if __name__=='__main__':main()
