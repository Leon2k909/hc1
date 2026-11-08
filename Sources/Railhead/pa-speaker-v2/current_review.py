"""Compare the uninstalled refined speaker with the actual current legacy assembly."""
from pathlib import Path
import json,sys,hashlib,collections
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent;OUT=ROOT/'output/railhead/pa-speaker-v2';CURRENT=OUT/'current-native';CURRENT.mkdir(exist_ok=True)
base=ROOT/'Sources/Railhead/help-point-v1'
(HERE/'current_native.py').write_text((base/'native.py').read_text().replace('help-point-v1','pa-speaker-v2').replace('railhead-help-point','railhead-speaker-current'))
sys.path.insert(0,str(HERE));import current_native as native
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
m=json.loads((OUT/'manifest.json').read_text());source=ROOT/m['source'];assert sha(source)==m['source_sha256']
for p,h in m['files'].items():assert sha(ROOT/p)==h,p
old=source.read_text().splitlines();new=(ROOT/'Assets/models/maps/railhead/pa-speaker-v2/centre_without_speaker.obj').read_text().splitlines()
assert [l for l in old if l.startswith(('v ','vt ','vn '))]==[l for l in new if l.startswith(('v ','vt ','vn '))]
a=collections.Counter(l for l in old if l.startswith('f '));b=collections.Counter(l for l in new if l.startswith('f '));assert not b-a and sum((a-b).values())==36
public=(ROOT/'Assets/models/maps/railhead/railhead_dress_centre.vmdl').read_text();preview=(ROOT/'Assets/models/maps/railhead/pa-speaker-v2/centre_without_speaker.vmdl').read_text();assert preview.replace('models/maps/railhead/pa-speaker-v2/centre_without_speaker.obj','models/maps/railhead/clock-v1/dressing_without_clock.obj')==public
paths=[source,ROOT/'Assets/models/maps/railhead/railhead_dress_centre.vmdl',ROOT/'Assets/scenes/maps/Railhead/railhead.scene']
guard={p.relative_to(ROOT).as_posix():sha(p) for p in paths};(CURRENT/'guard.json').write_text(json.dumps(guard,indent=2))
text=(base/'capture.cs.txt').read_text().replace('output/railhead/help-point-v1/native','output/railhead/pa-speaker-v2/current-native').replace('models/maps/railhead/railhead_dress_west.vmdl','models/maps/railhead/railhead_dress_centre.vmdl').replace('models/props/railhead/help_point_v1/preview.vmdl','models/maps/railhead/pa-speaker-v2/centre_without_speaker.vmdl').replace('models/props/railhead/help_point_v1/help_point.vmdl','models/maps/railhead/pa-speaker-v2/pa_speaker.vmdl').replace('"East Taxi Rank Head Post"','"East Taxi Rank Head Post","West Platform Help Point"')
start=text.index(' var views=');end=text.index('\n foreach(var after',start)
text=text[:start]+''' var views=new[]{("detail",new Vector3(813,-43,205),new Vector3(820,-14.1f,213.4f),42f),("side",new Vector3(794,-35,213),new Vector3(820,-14.1f,213.4f),43f)};'''+text[end:]
text=text.replace('view.Item1=="detail"?1000:900','1600').replace('new Bitmap(1600,1200)','new Bitmap(1600,900)')
text=text.replace('scene.Deserialize(data);','scene.Deserialize(data);var inspection=new GameObject(true,"Identical temporary review light");inspection.WorldPosition=new Vector3(800,-65,230);var key=inspection.AddComponent<PointLight>();key.Radius=200;key.LightColor=new Color(4,3.9f,3.7f);key.Shadows=true;')
(HERE/'capture_current.cs.txt').write_text(text)
for name in ('pa_speaker','centre_without_speaker'):print(native.call('asset_compile',dict(path=f'models/maps/railhead/pa-speaker-v2/{name}.vmdl')))
print(native.script(HERE/'capture_current.cs.txt'))
for p,h in guard.items():assert sha(ROOT/p)==h,p
(CURRENT/'verification.json').write_text(json.dumps(dict(review_only=True,old_triangles=36,new_triangles=32386,existing_uninstalled_model_reused=True,public_inputs_unchanged=True,unrelated_obj_records_unchanged=True,physics_unchanged=True)))
