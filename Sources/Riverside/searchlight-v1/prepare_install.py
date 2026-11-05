"""Splice only the old lamp body and mount; retain the original lens, beam and tower."""
from pathlib import Path
from collections import Counter
import json,sys,hashlib,shutil,time
import numpy as np
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent
OUT=ROOT/'output/riverside/searchlight-v1';STAGE=OUT/'install-stage';STAGE.mkdir(exist_ok=True)
sys.path.insert(0,str(ROOT/'Tools'))
import map_kit as K,riverdale_parts as P,riverside_map as R,riverdale_splice as S
import searchlight,layout
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def put(rel,text):
 p=STAGE/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text,encoding='utf-8',newline='');return p
asset='Assets/models/maps/riverside/riverside_dressing.obj';doc='Assets/models/maps/riverside/riverside_dressing.vmdl';mtl='Assets/models/maps/riverside/riverside_dressing.mtl';tool='Tools/riverside_parts.py'
protected=[ROOT/rel for rel in (asset,doc,mtl,tool,'Tools/riverside_pole_transformer.py','Assets/scenes/maps/riverside/riverside.scene')]
protected += list((ROOT/'Assets/models/maps/riverside').glob('*hulls*.obj'))
protected += list((ROOT/'Assets/models/maps/riverside').glob('*beam*'))
protected += [ROOT/'Assets/materials/riverside/rs_lamp_search.vmat',ROOT/'Assets/materials/riverside/rs_beam.vmat']
protected=[p for p in protected if p.is_file()]
guards={p.relative_to(ROOT).as_posix():sha(p) for p in protected}
baseline='before-'+str(time.time_ns())
for rel in (asset,doc,mtl,tool):
 p=OUT/baseline/rel;p.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/rel,p)
sl,head,axis=layout.placement();old=K.Model();new=K.Model()
layout.original(old,sl,head,axis,lens=False);searchlight.searchlight(new,sl,head,axis)
R.configure(old);R.configure(new)
K.write_obj(OUT/'removed.obj',old,'riverside_dressing');removed=Counter(S.read_obj(OUT/'removed.obj')[1])
K.write_obj(OUT/'added.obj',new,'riverside_dressing');added=S.read_obj(OUT/'added.obj')[1]
header,original=S.read_obj(ROOT/asset);before=Counter(original)
assert sum(removed.values())==72
assert not removed-before,'Original lamp has changed; inspect before replacing'
result=list((before-removed).elements())+added
target=STAGE/asset;target.parent.mkdir(parents=True,exist_ok=True);S.write_obj(target,header,result)
assert before-removed==Counter(result)-Counter(added)
assert not new.boxes and not new.hulls
lens=Counter(f for f in original if f[0]=='rs_lamp_search')
assert lens and lens==Counter(f for f in result if f[0]=='rs_lamp_search')
text=(ROOT/doc).read_bytes().decode('utf-8');original_doc=text;eol='\r\n' if '\r\n' in text else '\n'
anchor=next(line for line in text.splitlines() if 'from = ' in line)
remaps=eol.join(f'\t\t\t\t\t\t\t{{ from = "{key}.vmat" to = "{value}" }},' for key,value in searchlight.MATS.items())
text=text.replace(anchor,remaps+eol+anchor,1)
marker='_class = "PhysicsShapeList"';assert text[text.index(marker):]==original_doc[original_doc.index(marker):]
put(doc,text);put(mtl,(ROOT/mtl).read_bytes().decode('utf-8')+''.join(f'\nnewmtl {key}\nKd 1 1 1\nd 1\n' for key in searchlight.MATS))
text=(ROOT/tool).read_text()
needle='''    cylinder( m, sl, 2.5, sl[2] - 10, sl[2], "rs_steel", 8 )
    head = sl + UP * 6
    a = unit( v( *aim ) - head ) if aim is not None else f
    a_side, a_up = RP.perp( a )
    rod( m, sl + UP * 2, head, 1.5, "rs_steel", 6 )
    rod( m, head - a * 8, head + a * 10, 9, "rs_dark", 12, caps=True )'''
replacement='''    head = sl + UP * 6
    a = unit( v( *aim ) - head ) if aim is not None else f
    from riverside_searchlight import searchlight as draw_searchlight
    draw_searchlight( m, sl, head, a )
    a_side, a_up = RP.perp( a )'''
assert text.count(needle)==1
put(tool,text.replace(needle,replacement,1));put('Tools/riverside_searchlight.py',(HERE/'searchlight.py').read_text())
for p in (STAGE/'Tools').glob('*.py'):compile(p.read_text(),str(p),'exec')
plan=dict(baseline=baseline,guards=guards,files={p.relative_to(STAGE).as_posix():sha(p) for p in STAGE.rglob('*') if p.is_file()},
 head=head.tolist(),axis=axis.tolist(),lens_centre=(head+axis*10.2).tolist(),lens_radius=8,
 original_triangles=len(original),removed_triangles=sum(removed.values()),added_triangles=len(added),
 final_triangles=len(result),preserved_faces=len(original)-sum(removed.values()),
 original_lens_faces_retained=sum(lens.values()),scene_unchanged=True,physics_unchanged=True,beam_unchanged=True)
(OUT/'install-plan.json').write_text(json.dumps(plan,indent=2));print(json.dumps({k:v for k,v in plan.items() if k not in ('guards','files')},indent=2))
script=(ROOT/'Sources/Riverside/pole-transformer-v1/install.cs.txt').read_text()
script=script.replace('pole-transformer-v1','searchlight-v1').replace('riverside_pole_transformer.py','riverside_searchlight.py').replace('.transformer-writing','.searchlight-writing').replace('Transformers=3','Searchlights=1')
(HERE/'install.cs.txt').write_text(script)
