from pathlib import Path
from collections import Counter
import json,sys,hashlib,shutil,time
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent;OUT=ROOT/'output/sewage/salvage-drums-v1';STAGE=OUT/'install-stage'
sys.path.insert(0,str(ROOT/'Tools'))
import map_kit as K,sewage_map as R,riverdale_splice as S
import drums
R.PAINTS.update(steel=96,rust=96)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def put(rel,text):
 p=STAGE/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text,encoding='utf-8',newline='')
base='Assets/models/maps/sewage/sewage_details';tool='Tools/sewage_map.py'
inputs=[tool,*[base+'.'+ext for ext in ('obj','mtl','vmdl')],'Assets/scenes/maps/sewage/sewage.scene','Sources/Sewage/salvage-drums-v1/source-drum-lod0.obj']
inputs += [p.relative_to(ROOT).as_posix() for p in (ROOT/'Assets/models/maps/sewage').glob('*hulls*.obj')]
guards={rel:sha(ROOT/rel) for rel in inputs};baseline='before-'+str(time.time_ns())
for rel in inputs:
 p=OUT/baseline/rel;p.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/rel,p)
old=R.model();new=K.Model()
for centre in drums.PLACEMENTS:drums.original(old,*centre);drums.emit(new,centre)
K.write_obj(OUT/'removed.obj',old,'sewage_details');removed=Counter(S.read_obj(OUT/'removed.obj')[1])
K.write_obj(OUT/'added.obj',new,'sewage_details');added=S.read_obj(OUT/'added.obj')[1]
header,original=S.read_obj(ROOT/(base+'.obj'));assert not removed-Counter(original),'Original drums differ'
result=list((Counter(original)-removed).elements())+added
p=STAGE/(base+'.obj');p.parent.mkdir(parents=True,exist_ok=True);S.write_obj(p,header,result)
text=(ROOT/(base+'.vmdl')).read_bytes().decode();eol='\r\n' if '\r\n' in text else '\n';anchor=next(l for l in text.splitlines() if 'from = ' in l)
remaps=eol.join(f'\t\t\t\t\t\t\t{{ from = "{key}.vmat" to = "{path}" }},' for key,path in drums.MATS.items())
put(base+'.vmdl',text.replace(anchor,remaps+eol+anchor,1));put(base+'.mtl',(ROOT/(base+'.mtl')).read_bytes().decode()+''.join(f'\nnewmtl {k}\nKd 1 1 1\nd 1\n' for k in drums.MATS))
text=(ROOT/tool).read_text();start=text.index('        detail.cylinder((e,n),20,z,z+54,');end=text.index('    # The cabinets',start)
text=text[:start]+'''        from sewage_salvage_drums import emit as draw_salvage_drum
        draw_salvage_drum(detail,(e,n,z))
'''+text[end:]
put(tool,text);put('Tools/sewage_salvage_drums.py',(HERE/'drums.py').read_text())
plan=dict(baseline=baseline,guards=guards,files={p.relative_to(STAGE).as_posix():sha(p) for p in STAGE.rglob('*') if p.is_file()},
 drums=6,removed_triangles=sum(removed.values()),added_triangles=len(added),preserved_faces=len(original)-sum(removed.values()))
(OUT/'install-plan.json').write_text(json.dumps(plan,indent=2));print(json.dumps({k:v for k,v in plan.items() if k not in ('guards','files')},indent=2))
script=(ROOT/'Sources/Sewage/crane-blocks-v1/install.cs.txt').read_text().replace('crane-blocks-v1','salvage-drums-v1').replace('sewage_crane_blocks.py','sewage_salvage_drums.py').replace('CraneBlocks=2','SalvageDrums=6')
start=script.index('var allowed=');end=script.index('\nforeach',start)
script=script[:start]+'var allowed=new[]{'+','.join(json.dumps(p) for p in plan['files'])+'};'+script[end:]
(HERE/'install.cs.txt').write_text(script)
