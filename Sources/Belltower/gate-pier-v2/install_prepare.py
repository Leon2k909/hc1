from pathlib import Path
import importlib.util,inspect,json,re,shutil,sys,tempfile
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent;sys.path.insert(0,str(ROOT/'Tools'))
import map_kit as K,belltower_map as B,belltower_gate_piers as P,belltower_remove_doorway_posts as Patch
from belltower_move_square_lamps import geometry,sha
spec=importlib.util.spec_from_file_location('chairs_install',ROOT/'Sources/Belltower/bistro-chair-v2/stage_install.py');C=importlib.util.module_from_spec(spec);spec.loader.exec_module(C)
OUT=Path(tempfile.gettempdir())/'belltower-gate-pier-v2';STAGE=OUT/'install-stage';Patch.STAGE=STAGE;STAGE.mkdir(parents=True,exist_ok=False)
review=json.loads((OUT/'manifest.json').read_text());assert all(sha(ROOT/p)==h for p,h in review['files'].items());(STAGE/'legacy-pier.py.txt').write_text(inspect.getsource(B.pier))
old=K.Model();placements=[]
for e in (-459,-361):
    for n in (-405,-895):B.pier(old,(e,n),0,64);placements.extend([('west',(e,n,0)),('east',(-e,n,0))])
wanted=geometry(old)+geometry(old.mirrored(B.EAST_PAINTS));assert sum(wanted.values())==928
docs=C.DOCUMENTS;refs={r for p in docs for r in re.findall(r'filename\s*=\s*"([^"]+\.obj)"',(ROOT/p).read_text())}
targets={f'Assets/models/maps/belltower/belltower_{s}.obj' for s in ('west','east')}|{'Assets/'+r for r in refs if re.search(r'_(ashlar|ashlar_grey)\.obj$',r)};files={}
for p in sorted(targets):
    row,found=Patch.render(ROOT/p,wanted)
    if row:assert row['triangles_after']>0;files[p]=row
assert all(files[f'Assets/models/maps/belltower/belltower_{s}.obj']['removed_triangles']==464 for s in ('west','east'))
protected={p:sha(ROOT/p) for p in docs};protected.update({'Assets/'+r:sha(ROOT/'Assets'/r) for r in refs if 'Assets/'+r not in files});protected.update({p:h for p,h in review['files'].items() if re.search(r'/(gate_pier\.vmdl|lantern_lod[0-2]\.(obj|mtl))$',p)})
deleted={};public=ROOT/'Assets/models/maps/belltower/gate-pier-v2'
for p in public.iterdir():
    if not (p.name.startswith('base_') or p.name.startswith('west_baseline') or p.name.startswith('west_without_lantern') or p.name=='materials.mtl'):continue
    rel=p.relative_to(ROOT).as_posix();backup=STAGE/'deleted-backups'/rel;backup.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,backup);deleted[rel]={'before':sha(p),'backup':str(backup)}
(STAGE/'piers.json').write_text(json.dumps(P.group(B.ids,placements),indent=2))
m={'revision':'belltower-gate-pier-v2-install','files':files,'protected':protected,'deleted':deleted,'compile_models':docs,'scene_before':sha(ROOT/'Assets/scenes/maps/Belltower/belltower.scene'),'group_sha256':sha(STAGE/'piers.json'),'piers':8,'old_triangles_removed':928,'placements':placements};(STAGE/'manifest.json').write_text(json.dumps(m,indent=2))
for name in ('install.cs.txt','delete-old.cs.txt','finish_install.py'):
    s=(ROOT/'Sources/Belltower/bistro-table-v2'/name).read_text().replace('bistro-table-v2','gate-pier-v2').replace('bistro_table.vmdl','gate_pier.vmdl').replace('Bistro tables','Churchyard gate piers').replace('tables','piers').replace('Tables','Piers').replace('table','pier').replace('Table','Pier').replace('!=7','!=8').replace('all 7','all 8').replace('Installed=7','Installed=8').replace('3038','928');(HERE/name).write_text(s)
print({'piers':8,'source_meshes':len(files),'old_triangles':928,'retired_files':len(deleted)})
