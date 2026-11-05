from pathlib import Path
import importlib.util,inspect,json,re,shutil,sys,tempfile
import numpy as np
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent;sys.path.insert(0,str(ROOT/'Tools'))
import map_kit as K,belltower_map as B,belltower_detail as D,belltower_dish_lamps as Lamps,belltower_remove_doorway_posts as Patch
from belltower_move_square_lamps import geometry,sha
spec=importlib.util.spec_from_file_location('chair_install',ROOT/'Sources/Belltower/bistro-chair-v2/stage_install.py');C=importlib.util.module_from_spec(spec);spec.loader.exec_module(C)
OUT=Path(tempfile.gettempdir())/'belltower-dish-lamp-v2';STAGE=OUT/'install-stage';Patch.STAGE=STAGE
STAGE.mkdir(parents=True,exist_ok=False)
(STAGE/'legacy-dish-lamp.py.txt').write_text(inspect.getsource(D.dish_lamp))
review=json.loads((OUT/'manifest.json').read_text());assert all(sha(ROOT/p)==h for p,h in review['files'].items())
west=K.Model();placements=[]
for e,n0,n1,z in B.CABLES:
    p=(e,(n0+n1)/2,z-12);D.dish_lamp(west,p);placements += [('west',p),('east',(-p[0],p[1],p[2]))]
wanted=geometry(west)+geometry(west.mirrored(B.EAST_PAINTS));assert sum(wanted.values())==3560
documents={p:(ROOT/p).read_text() for p in C.DOCUMENTS};refs={r for t in documents.values() for r in re.findall(r'filename\s*=\s*"([^"]+\.obj)"',t)}
targets={f'Assets/models/maps/belltower/belltower_{s}.obj' for s in ('east','west')}
targets.update('Assets/'+r for r in refs if re.search(r'_(iron_black|lamp_bulb|lamp_reflector)\.obj$',r))
files={}
for p in sorted(targets):
    row,found=Patch.render(ROOT/p,wanted)
    if row:assert row['triangles_after']>0;files[p]=row
assert all(files[f'Assets/models/maps/belltower/belltower_{s}.obj']['removed_triangles']==1780 for s in ('east','west'))
protected={p:sha(ROOT/p) for p in C.DOCUMENTS}
protected.update({'Assets/'+r:sha(ROOT/'Assets'/r) for r in refs if 'Assets/'+r not in files})
protected.update({p:h for p,h in review['files'].items() if re.search(r'/(wall_lantern\.vmdl|lantern_lod[0-2]\.(obj|mtl))$',p)})
protected.update({p.relative_to(ROOT).as_posix():sha(p) for p in (ROOT/'Assets/models/maps/belltower/wall-lantern-original').iterdir() if p.is_file()})
deleted={};folder=ROOT/'Assets/models/maps/belltower/dish-lamp-v2'
for name in ('west_baseline.vmdl','west_without_lantern.vmdl','base_iron_black.obj','base_lamp_bulb.obj','base_lamp_reflector.obj','materials.mtl'):
    for p in (folder/name,Path(str(folder/name)+'.meta'),Path(str(folder/name)+'_c')):
        if not p.exists():continue
        relative=p.relative_to(ROOT).as_posix();backup=STAGE/'deleted-backups'/relative;backup.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,backup);deleted[relative]={'before':sha(p),'backup':str(backup)}
(STAGE/'lamps.json').write_text(json.dumps(Lamps.group(B.ids,placements),indent=2))
m={'revision':'belltower-dish-lamp-v2-install','files':files,'protected':protected,'deleted':deleted,'compile_models':C.DOCUMENTS,'scene_before':sha(ROOT/'Assets/scenes/maps/Belltower/belltower.scene'),'group_sha256':sha(STAGE/'lamps.json'),'lamps':10,'old_triangles_removed':3560,'placements':placements}
(STAGE/'manifest.json').write_text(json.dumps(m,indent=2));print(json.dumps({'lamps':10,'targets':len(files),'old_triangles':3560,'retired_files':len(deleted)}))
