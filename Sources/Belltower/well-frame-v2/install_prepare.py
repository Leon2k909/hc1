from pathlib import Path
import importlib.util,inspect,json,re,shutil,sys,tempfile
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent;sys.path.insert(0,str(ROOT/'Tools'))
import map_kit as K,belltower_map as B,belltower_remove_doorway_posts as Patch
from belltower_move_square_lamps import geometry,sha
OUT=Path(tempfile.gettempdir())/'belltower-well-frame-v2';STAGE=OUT/'install-stage';Patch.STAGE=STAGE;STAGE.mkdir(parents=True,exist_ok=True);assert not (STAGE/'manifest.json').exists()
review=json.loads((OUT/'manifest.json').read_text());assert all(sha(ROOT/p)==h for p,h in review['files'].items())
(STAGE/'legacy-cross.py.txt').write_text(inspect.getsource(B.garden_well))
old=K.Model();e,n=B.GARDEN_WELL;z=B.GARDEN_Z
for se in (-1,1):old.box((e+se*38-4,n-4,z+34),(e+se*38+4,n+4,z+116),'planks_dark')
old.beam((e-44,n,z+106),(e+44,n,z+106),(6,6),'planks_dark')
B.axle(old,(e,n,z+96),(1,0,0),6,50,{'side':'planks','end':'planks_dark'});wanted=geometry(old)
docs=['Assets/models/maps/belltower/belltower_centre.vmdl'];refs={r for p in docs for r in re.findall(r'filename\s*=\s*"([^"]+\.obj)"',(ROOT/p).read_text())}
targets={'Assets/models/maps/belltower/belltower_centre.obj'}|{'Assets/'+r for r in refs if re.search(r'_(planks|planks_dark)\.obj$',r)};files={}
for p in sorted(targets):
    row,found=Patch.render(ROOT/p,wanted)
    if row:assert row['triangles_after']>0;files[p]=row
assert files['Assets/models/maps/belltower/belltower_centre.obj']['removed_triangles']==72
protected={p:sha(ROOT/p) for p in docs};protected.update({'Assets/'+r:sha(ROOT/'Assets'/r) for r in refs if 'Assets/'+r not in files});protected.update({p:h for p,h in review['files'].items() if re.search(r'/(well_frame\.vmdl|lantern_lod[0-2]\.(obj|mtl))$',p)})
deleted={};public=ROOT/'Assets/models/maps/belltower/well-frame-v2'
for p in public.iterdir():
    if not (p.name.startswith('base_') or p.name.startswith('west_baseline') or p.name.startswith('west_without_lantern') or p.name=='materials.mtl'):continue
    rel=p.relative_to(ROOT).as_posix();backup=STAGE/'deleted-backups'/rel;backup.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,backup);deleted[rel]={'before':sha(p),'backup':str(backup)}
key='well_frame';child=K.game_object(B.ids,'Garden well frame',key,K.to_world((0,-1225,-48)),components=[K.component(B.ids,'Sandbox.ModelRenderer',key+'/renderer',Model='models/maps/belltower/well-frame-v2/well_frame.vmdl',RenderType='On',Tint='1,1,1,1')])
group=K.game_object(B.ids,'Garden well frame',key+'/group',children=[child]);(STAGE/'crosses.json').write_text(json.dumps(group,indent=2))
m={'revision':'belltower-well-frame-v2-install','files':files,'protected':protected,'deleted':deleted,'compile_models':docs,'scene_before':sha(ROOT/'Assets/scenes/maps/Belltower/belltower.scene'),'group_sha256':sha(STAGE/'crosses.json'),'crosses':1,'old_triangles_removed':72};(STAGE/'manifest.json').write_text(json.dumps(m,indent=2))
for name in ('install.cs.txt','delete-old.cs.txt','finish_install.py'):
    s=(ROOT/'Sources/Belltower/bistro-table-v2'/name).read_text().replace('bistro-table-v2','well-frame-v2').replace('bistro_table.vmdl','well_frame.vmdl').replace('Bistro tables','Garden well frame').replace('tables','crosses').replace('Tables','Crosses').replace('table','cross').replace('Table','Cross')
    s=s.replace('!=7','!=1').replace('all 7','all 1').replace('Installed=7','Installed=1').replace('3038','72');(HERE/name).write_text(s)
print({'source_meshes':len(files),'old_triangles':40,'retired_files':len(deleted)})
