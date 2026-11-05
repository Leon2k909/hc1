from pathlib import Path
from collections import Counter
import sys,json,hashlib,shutil,time
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent;OUT=ROOT/'output/riverside/discarded-tyres-v1';STAGE=OUT/'install-stage'
sys.path.insert(0,str(ROOT/'Tools'))
import map_kit as K,riverside_parts as P,riverside_map as R,riverdale_splice as S
import tyres,layout
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def put(rel,text):
 p=STAGE/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text,encoding='utf-8',newline='')
inputs=['Tools/riverside_parts.py','Assets/scenes/maps/riverside/riverside.scene']
for name in ('pad','dressing'):
 inputs += [f'Assets/models/maps/riverside/riverside_{name}.{ext}' for ext in ('obj','mtl','vmdl')]
inputs += [p.relative_to(ROOT).as_posix() for p in (ROOT/'Assets/models/maps/riverside').glob('*hulls*.obj')]
baseline='before-'+str(time.time_ns());guards={r:sha(ROOT/r) for r in inputs}
for rel in inputs:
 p=OUT/baseline/rel;p.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/rel,p)
reports=[]
for name in ('pad','dressing'):
 old=K.Model();new=K.Model();specs=[p for group,p in layout.placements() if group==name]
 for p in specs:P.tire(old,p,(0,0,1),r=12.5,w=8);tyres.tire(new,p,(0,0,1),r=12.5,w=8)
 R.configure(old);R.configure(new)
 K.write_obj(OUT/(name+'-removed.obj'),old,'riverside_'+name);removed=Counter(S.read_obj(OUT/(name+'-removed.obj'))[1])
 K.write_obj(OUT/(name+'-added.obj'),new,'riverside_'+name);added=S.read_obj(OUT/(name+'-added.obj'))[1]
 obj=f'Assets/models/maps/riverside/riverside_{name}.obj';header,original=S.read_obj(ROOT/obj)
 assert not removed-Counter(original),'Original tyres differ: '+name
 result=list((Counter(original)-removed).elements())+added
 p=STAGE/obj;p.parent.mkdir(parents=True,exist_ok=True);S.write_obj(p,header,result)
 doc=obj[:-3]+'vmdl';text=(ROOT/doc).read_bytes().decode();eol='\r\n' if '\r\n' in text else '\n';anchor=next(l for l in text.splitlines() if 'from = ' in l)
 remaps=eol.join(f'\t\t\t\t\t\t\t{{ from = "{k}.vmat" to = "{v}" }},' for k,v in new.material_overrides.items())
 put(doc,text.replace(anchor,remaps+eol+anchor,1))
 mtl=obj[:-3]+'mtl';put(mtl,(ROOT/mtl).read_bytes().decode()+''.join(f'\nnewmtl {k}\nKd 1 1 1\nd 1\n' for k in new.material_overrides))
 reports.append(dict(asset=name,tyres=len(specs),removed=sum(removed.values()),added=len(added),preserved=len(original)-sum(removed.values())))
tool='Tools/riverside_parts.py';text=(ROOT/tool).read_text();needle='    a = unit( axis )\n    p = v( *c )\n'
assert text.count(needle)==1
replacement='''    a = unit( axis )
    if abs( a[2] ) > 0.99:
        from riverside_discarded_tyres import tire as draw_loose_tyre
        draw_loose_tyre( m, c, a, r, w, paint_name )
        return
    p = v( *c )
'''
put(tool,text.replace(needle,replacement,1));put('Tools/riverside_discarded_tyres.py',(HERE/'tyres.py').read_text())
plan=dict(baseline=baseline,guards=guards,files={p.relative_to(STAGE).as_posix():sha(p) for p in STAGE.rglob('*') if p.is_file()},models=reports)
(OUT/'install-plan.json').write_text(json.dumps(plan,indent=2));print(json.dumps(reports,indent=2))
script=(ROOT/'Sources/Riverside/searchlight-v1/install.cs.txt').read_text().replace('searchlight-v1','discarded-tyres-v1').replace('riverside_searchlight.py','riverside_discarded_tyres.py')
start=script.index('var allowed=');end=script.index('\nforeach',start)
script=script[:start]+'var allowed=new[]{'+','.join(json.dumps(p) for p in plan['files'])+'};'+script[end:]
script=script.replace('Searchlights=1','LooseTyres='+str(sum(r['tyres'] for r in reports)))
(HERE/'install.cs.txt').write_text(script)
