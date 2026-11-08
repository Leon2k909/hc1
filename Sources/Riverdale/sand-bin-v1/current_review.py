"""Refresh the existing uninstalled proposal against the current Riverdale map."""
from pathlib import Path
import json,sys,hashlib,collections
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent;OUT=ROOT/'output/riverdale/sand-bin-v1';CURRENT=OUT/'current-native';CURRENT.mkdir(exist_ok=True)
base=ROOT/'Sources/Railhead/help-point-v1'
(HERE/'current_native.py').write_text((base/'native.py').read_text().replace('railhead/help-point-v1','riverdale/sand-bin-v1').replace('railhead-help-point','riverdale-sand-bin-current'))
sys.path.insert(0,str(HERE));import current_native as native
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
m=json.loads((OUT/'manifest.json').read_text());source=ROOT/m['source'];assert sha(source)==m['source_sha256']
for p,h in m['files'].items():assert sha(ROOT/p)==h,p
old=source.read_text().splitlines();new=(ROOT/'Assets/models/maps/riverdale/sand-bin-v1/yard_without_bin.obj').read_text().splitlines()
assert [l for l in old if l.startswith(('v ','vt ','vn '))]==[l for l in new if l.startswith(('v ','vt ','vn '))]
a=collections.Counter(l for l in old if l.startswith('f '));b=collections.Counter(l for l in new if l.startswith('f '));assert not b-a and sum((a-b).values())==38
public=(ROOT/'Assets/models/maps/riverdale/riverdale_yard_props.vmdl').read_text();preview=(ROOT/'Assets/models/maps/riverdale/sand-bin-v1/yard_without_bin.vmdl').read_text();assert preview.replace('models/maps/riverdale/sand-bin-v1/yard_without_bin.obj','models/maps/riverdale/riverdale_yard_props.obj')==public
paths=[source,ROOT/'Assets/models/maps/riverdale/riverdale_yard_props.vmdl',ROOT/'Assets/scenes/maps/Riverdale/riverdale.scene']
guard={p.relative_to(ROOT).as_posix():sha(p) for p in paths};(CURRENT/'guard.json').write_text(json.dumps(guard,indent=2))
text=(base/'capture.cs.txt').read_text().replace('output/railhead/help-point-v1/native','output/riverdale/sand-bin-v1/current-native').replace('Assets/scenes/maps/Railhead/railhead.scene','Assets/scenes/maps/Riverdale/riverdale.scene')
start=text.index('var names=');end=text.index('\nvar roots=',start)
text=text[:start]+'var names=new[]{"Sun","Sky","Fog","Look","Riverdale","Lights","Reflection Probes","Volumetric Fog","Indirect Light","Pipe Solids","Yard Prop Solids"}.ToHashSet(StringComparer.OrdinalIgnoreCase);'+text[end:]
text=text.replace('models/maps/railhead/railhead_dress_west.vmdl','models/maps/riverdale/riverdale_yard_props.vmdl').replace('models/props/railhead/help_point_v1/preview.vmdl','models/maps/riverdale/sand-bin-v1/yard_without_bin.vmdl').replace('models/props/railhead/help_point_v1/help_point.vmdl','models/maps/riverdale/sand-bin-v1/sand_bin.vmdl')
start=text.index(' var views=');end=text.index('\n foreach(var after',start)
text=text[:start]+''' var views=new[]{("whole",new Vector3(318,1295,45),new Vector3(258,1250,14),38f),("detail",new Vector3(305,1213,43),new Vector3(258,1250,19),38f)};'''+text[end:]
text=text.replace('new Bitmap(view.Item1=="detail"?1000:900,1200)','new Bitmap(1200,900)')
(HERE/'capture_current.cs.txt').write_text(text)
for name in ('sand_bin','yard_without_bin'):print(native.call('asset_compile',dict(path=f'models/maps/riverdale/sand-bin-v1/{name}.vmdl')))
print(native.script(HERE/'capture_current.cs.txt'))
for p,h in guard.items():assert sha(ROOT/p)==h,p
(CURRENT/'verification.json').write_text(json.dumps(dict(review_only=True,old_triangles=38,new_triangles=2126,existing_uninstalled_model_reused=True,public_inputs_unchanged=True,unrelated_obj_records_unchanged=True,physics_unchanged=True)))
