from pathlib import Path
import importlib.util,inspect,json,re,shutil,sys,tempfile
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent;sys.path.insert(0,str(ROOT/'Tools'))
import map_kit as K,belltower_map as B,belltower_sack_piles as P,belltower_remove_doorway_posts as Patch
from belltower_move_square_lamps import geometry,sha
def module(name,path):
    s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
C=module('chair_install',ROOT/'Sources/Belltower/bistro-chair-v2/stage_install.py');Build=module('sack_build',HERE/'build.py')
OUT=Path(tempfile.gettempdir())/'belltower-sack-pile-v2';STAGE=OUT/'install-stage';Patch.STAGE=STAGE
STAGE.mkdir(parents=True,exist_ok=False);(STAGE/'legacy-sacks.py.txt').write_text(inspect.getsource(B.sacks))
review=json.loads((OUT/'manifest.json').read_text());assert all(sha(ROOT/p)==h for p,h in review['files'].items())
# A true reflected mesh keeps the eastern pile's original handedness.
folder=STAGE/'Assets/models/maps/belltower/sack-pile-v2';folder.mkdir(parents=True)
for i in range(3):K.write_obj(folder/f'mirrored_lod{i}.obj',Build.build(i).mirrored(),f'mirrored_lod{i}')
doc=(ROOT/'Assets/models/maps/belltower/sack-pile-v2/sack_pile.vmdl').read_text().replace('lantern_lod','mirrored_lod')
(folder/'sack_pile_mirrored.vmdl').write_text(doc)
imports={p.relative_to(STAGE).as_posix():sha(p) for p in folder.iterdir() if p.is_file()}
west=K.Model();B.sacks(west,(-1215,730),0,7);wanted=geometry(west)+geometry(west.mirrored(B.EAST_PAINTS));assert sum(wanted.values())==168
documents={p:(ROOT/p).read_text() for p in C.DOCUMENTS};refs={r for t in documents.values() for r in re.findall(r'filename\s*=\s*"([^"]+\.obj)"',t)}
targets={f'Assets/models/maps/belltower/belltower_{s}.obj' for s in ('east','west')};targets.update('Assets/'+r for r in refs if r.endswith('_canvas_plain.obj'))
files={}
for p in sorted(targets):
    row,found=Patch.render(ROOT/p,wanted)
    if row:assert row['triangles_after']>0;files[p]=row
assert all(files[f'Assets/models/maps/belltower/belltower_{s}.obj']['removed_triangles']==84 for s in ('east','west'))
protected={p:sha(ROOT/p) for p in C.DOCUMENTS};protected.update({'Assets/'+r:sha(ROOT/'Assets'/r) for r in refs if 'Assets/'+r not in files})
protected.update({p:h for p,h in review['files'].items() if re.search(r'/(sack_pile\.vmdl|lantern_lod[0-2]\.(obj|mtl))$',p)})
protected.update(imports)
deleted={};public=ROOT/'Assets/models/maps/belltower/sack-pile-v2'
for name in ('west_baseline.vmdl','west_without_lantern.vmdl','base_canvas_plain.obj','materials.mtl'):
    for p in (public/name,Path(str(public/name)+'.meta'),Path(str(public/name)+'_c')):
        if not p.exists():continue
        rel=p.relative_to(ROOT).as_posix();backup=STAGE/'deleted-backups'/rel;backup.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,backup);deleted[rel]={'before':sha(p),'backup':str(backup)}
placements=[('west',(-1215,730,0)),('east',(1215,730,0))];(STAGE/'piles.json').write_text(json.dumps(P.group(B.ids,placements),indent=2))
m={'revision':'belltower-sack-pile-v2-install','files':files,'protected':protected,'imports':imports,'deleted':deleted,'compile_models':C.DOCUMENTS,'scene_before':sha(ROOT/'Assets/scenes/maps/Belltower/belltower.scene'),'group_sha256':sha(STAGE/'piles.json'),'piles':2,'old_triangles_removed':168,'placements':placements}
(STAGE/'manifest.json').write_text(json.dumps(m,indent=2));print({'piles':2,'sacks':14,'targets':len(files),'old_triangles':168,'retired_files':len(deleted)})
