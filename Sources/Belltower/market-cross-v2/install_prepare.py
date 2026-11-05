from pathlib import Path
import importlib.util,inspect,json,re,shutil,sys,tempfile
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent;sys.path.insert(0,str(ROOT/'Tools'))
import map_kit as K,belltower_map as B,belltower_remove_doorway_posts as Patch
from belltower_move_square_lamps import geometry,sha
OUT=Path(tempfile.gettempdir())/'belltower-market-cross-v2';STAGE=OUT/'install-stage';Patch.STAGE=STAGE;STAGE.mkdir(parents=True,exist_ok=False)
review=json.loads((OUT/'manifest.json').read_text());assert all(sha(ROOT/p)==h for p,h in review['files'].items())
(STAGE/'legacy-cross.py.txt').write_text(inspect.getsource(B.market_cross))
old=K.Model();old.cylinder(B.MARKET_CROSS,13,36,200,{'side':'ashlar'},sides=8,turn=3.141592653589793/8)
e,n=B.MARKET_CROSS;old.beam((e,n,212),(e,n,266),(8,8),'ashlar');old.beam((e-20,n,244),(e+20,n,244),(8,8),'ashlar');wanted=geometry(old)
docs=['Assets/models/maps/belltower/belltower_centre.vmdl'];refs={r for p in docs for r in re.findall(r'filename\s*=\s*"([^"]+\.obj)"',(ROOT/p).read_text())}
targets={'Assets/models/maps/belltower/belltower_centre.obj'}|{'Assets/'+r for r in refs if r.endswith('_ashlar.obj')};files={}
for p in sorted(targets):
    row,found=Patch.render(ROOT/p,wanted)
    if row:assert row['triangles_after']>0;files[p]=row
assert files['Assets/models/maps/belltower/belltower_centre.obj']['removed_triangles']==40
protected={p:sha(ROOT/p) for p in docs};protected.update({'Assets/'+r:sha(ROOT/'Assets'/r) for r in refs if 'Assets/'+r not in files});protected.update({p:h for p,h in review['files'].items() if re.search(r'/(market_cross\.vmdl|lantern_lod[0-2]\.(obj|mtl))$',p)})
deleted={};public=ROOT/'Assets/models/maps/belltower/market-cross-v2'
for p in public.iterdir():
    if not (p.name.startswith('base_') or p.name.startswith('west_baseline') or p.name.startswith('west_without_lantern') or p.name=='materials.mtl'):continue
    rel=p.relative_to(ROOT).as_posix();backup=STAGE/'deleted-backups'/rel;backup.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,backup);deleted[rel]={'before':sha(p),'backup':str(backup)}
key='market_cross';child=K.game_object(B.ids,'Market cross',key,K.to_world((0,1275,0)),components=[K.component(B.ids,'Sandbox.ModelRenderer',key+'/renderer',Model='models/maps/belltower/market-cross-v2/market_cross.vmdl',RenderType='On',Tint='1,1,1,1')])
group=K.game_object(B.ids,'Market cross model',key+'/group',children=[child]);(STAGE/'crosses.json').write_text(json.dumps(group,indent=2))
m={'revision':'belltower-market-cross-v2-install','files':files,'protected':protected,'deleted':deleted,'compile_models':docs,'scene_before':sha(ROOT/'Assets/scenes/maps/Belltower/belltower.scene'),'group_sha256':sha(STAGE/'crosses.json'),'crosses':1,'old_triangles_removed':40};(STAGE/'manifest.json').write_text(json.dumps(m,indent=2))
for name in ('install.cs.txt','delete-old.cs.txt','finish_install.py'):
    s=(ROOT/'Sources/Belltower/bistro-table-v2'/name).read_text().replace('bistro-table-v2','market-cross-v2').replace('bistro_table.vmdl','market_cross.vmdl').replace('Bistro tables','Market cross model').replace('tables','crosses').replace('Tables','Crosses').replace('table','cross').replace('Table','Cross')
    s=s.replace('!=7','!=1').replace('all 7','all 1').replace('Installed=7','Installed=1').replace('3038','40');(HERE/name).write_text(s)
print({'source_meshes':len(files),'old_triangles':40,'retired_files':len(deleted)})
