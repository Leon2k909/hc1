"""Precisely retire all old menu geometry, including shared preview imports."""
from pathlib import Path
from collections import Counter
import json,re,sys,tempfile,shutil,inspect
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'Tools'))
import map_kit as K
import belltower_map as B
import belltower_detail as D
import belltower_menu_boards as Boards
import belltower_remove_doorway_posts as Patch
from belltower_move_square_lamps import geometry,sha
OUT=Path(tempfile.gettempdir())/'belltower-menu-board-v2'
STAGE=OUT/'install-stage'
Patch.STAGE=STAGE
WEST=[((-628.,-218.),0.,'chalkboard_a'),((-1000.,1124.),90.,'chalkboard_b'),((-972.,-84.),90.,'chalkboard_a')]
DOCUMENTS=['Assets/models/maps/belltower/belltower_west.vmdl','Assets/models/maps/belltower/belltower_east.vmdl',
 'Assets/models/maps/belltower/wheelbarrow-v2/trial_west.vmdl','Assets/models/maps/belltower/wheelbarrow-v2/trial_east.vmdl',
 'Assets/models/maps/belltower/ivy-realism-v3/preview_west.vmdl','Assets/models/maps/belltower/ivy-realism-v3/preview_east.vmdl',
 'Assets/models/compare_old/headstone-preview/belltower_west_nostones.vmdl']

def remove_import(text,reference):
    marker=text.index('filename = "'+reference+'"')
    start=text.rfind('\n\t\t\t\t\t{',0,marker)+1
    end=text.index('\n\t\t\t\t\t},',marker)+len('\n\t\t\t\t\t},')
    assert text[start:end].count('_class = "RenderMeshFile"')==1
    return text[:start]+text[end:]

def main():
    STAGE.mkdir(parents=True,exist_ok=False)
    (STAGE/'legacy-generator.py.txt').write_text(inspect.getsource(D.sandwich_board))
    legacy=K.Model()
    for c,yaw,picture in WEST:D.sandwich_board(legacy,c,yaw,picture)
    wanted=geometry(legacy)+geometry(legacy.mirrored())
    assert sum(wanted.values())==264
    files={};deleted={};protected={};placements=[];references=set()
    for region,sign in [('west',1),('east',-1)]:
        placements.extend((region,(c[0]*sign,c[1],0.),yaw*sign,picture) for c,yaw,picture in WEST)
    # Old private comparison wrappers are obsolete. Keep their PNG evidence.
    obsolete=[]
    for folder,names in [
      ('menu-board-v2',['west_without_menu_board.vmdl','base_chalkboard_a.obj','base_iron_black.obj','base_planks_dark.obj','materials.mtl']),
      ('terracotta-pot-v2',['west_without_one_pot.vmdl','clay_without_one_pot.obj','materials.mtl'])]:
        for name in names:
            p=ROOT/'Assets/models/maps/belltower'/folder/name
            obsolete.extend(q for q in [p,Path(str(p)+'.meta'),Path(str(p)+'_c')] if q.exists())
    documents={p:(ROOT/p).read_text() for p in DOCUMENTS}
    for text in documents.values():references.update(re.findall(r'filename\s*=\s*"([^"]+\.obj)"',text))
    candidates={f'Assets/models/maps/belltower/belltower_{s}.obj' for s in ('west','east')}
    candidates.update('Assets/'+ref for ref in references if re.search(r'_(planks_dark|iron_black|chalkboard_[ab])\.obj$',ref))
    removed=set()
    for relative in sorted(candidates):
        p=ROOT/relative
        row,found=Patch.render(p,wanted)
        if not row:continue
        assert all(v<=wanted[k] for k,v in found.items())
        files[relative]=row
        if row['triangles_after']==0:
            removed.add(relative.removeprefix('Assets/'))
            obsolete.extend(q for q in [p,Path(str(p)+'.meta'),Path(str(p)+'_c')] if q.exists())
            files.pop(relative)
    for side in ('west','east'):
        r=files[f'Assets/models/maps/belltower/belltower_{side}.obj']
        assert r['removed_triangles']==132
    assert len(removed)==4,removed
    for relative,text in documents.items():
        new=text
        for ref in removed:
            if 'filename = "'+ref+'"' in new:new=remove_import(new,ref)
        assert new!=text,relative
        files[relative]=Patch.record(ROOT/relative,new.encode(),{'retired_menu_imports_removed':2,'all_other_modeldoc_bytes_exact':True})
    for p in dict.fromkeys(obsolete):
        relative=p.relative_to(ROOT).as_posix();backup=STAGE/'deleted-backups'/relative
        backup.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,backup)
        deleted[relative]={'before':sha(p),'backup':str(backup)}
    for ref in references:
        relative='Assets/'+ref
        if relative not in files and relative not in deleted:protected[relative]=sha(ROOT/relative)
    # The bakery uses the same new geometry with its own unchanged menu picture.
    p=STAGE/'Assets/models/maps/belltower/menu-board-v2/menu_board_b.vmdl';p.parent.mkdir(parents=True,exist_ok=True)
    text=(ROOT/'Assets/models/maps/belltower/menu-board-v2/menu_board.vmdl').read_text().replace('to = "materials/belltower/chalkboard_a.vmat"','to = "materials/belltower/chalkboard_b.vmat"')
    p.write_text(text)
    relative=p.relative_to(STAGE).as_posix();assert not (ROOT/relative).exists()
    new_files={relative:{'source':str(p),'after':sha(p)}}
    group=Boards.group(B.ids,placements);assert len(group['Children'])==6
    (STAGE/'boards.json').write_text(json.dumps(group,indent=2))
    report={'revision':'belltower-menu-board-v2-install','files':files,'new_files':new_files,'deleted':deleted,'protected':protected,'scene_before':sha(ROOT/'Assets/scenes/maps/Belltower/belltower.scene'),'group_sha256':sha(STAGE/'boards.json'),'boards':6,'old_triangles_removed':264,'retired_imports':sorted(removed)}
    (STAGE/'manifest.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'boards':6,'targets':len(files),'new_models':1,'deleted_files':len(deleted),'old_triangles_removed':264,'other_geometry_and_physics_preserved':True}))

if __name__=='__main__':main()
