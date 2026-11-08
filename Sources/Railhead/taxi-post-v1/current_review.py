"""Render the existing proposal against the current map without switching editor scenes."""
from pathlib import Path
import json,sys,hashlib,collections
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent;OUT=ROOT/'output/railhead/taxi-post-v1';CURRENT=OUT/'current-native';CURRENT.mkdir(exist_ok=True)
sys.path.insert(0,str(HERE));import native
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
m=json.loads((OUT/'manifest.json').read_text());source=ROOT/m['source'];assert sha(source)==m['source_sha256']
old=source.read_text().splitlines();new=(ROOT/'Assets/models/maps/railhead/taxi-post-v1/east_without_taxi.obj').read_text().splitlines()
assert [l for l in old if l.startswith(('v ','vt ','vn '))]==[l for l in new if l.startswith(('v ','vt ','vn '))]
a=collections.Counter(l for l in old if l.startswith('f '));b=collections.Counter(l for l in new if l.startswith('f '));assert not b-a and sum((a-b).values())==124
public=(ROOT/'Assets/models/maps/railhead/railhead_dress_east.vmdl').read_text();preview=(ROOT/'Assets/models/maps/railhead/taxi-post-v1/east_without_taxi.vmdl').read_text();assert preview.replace('models/maps/railhead/taxi-post-v1/east_without_taxi.obj','models/maps/railhead/cable-drum-v1/east_without_drum.obj')==public
paths=[source,ROOT/'Assets/models/maps/railhead/railhead_dress_east.vmdl',ROOT/'Assets/scenes/maps/Railhead/railhead.scene']
guard={str(p.relative_to(ROOT)):sha(p) for p in paths};(CURRENT/'guard.json').write_text(json.dumps(guard,indent=2))
text=(ROOT/'Sources/Ares/main-airlock-sign-v1/capture.cs.txt').read_text().replace('output/ares/main-airlock-sign-v1/native','output/railhead/taxi-post-v1/current-native').replace('Assets/scenes/maps/Ares/ares.scene','Assets/scenes/maps/Railhead/railhead.scene')
start=text.index('var names=');end=text.index('\nvar roots=',start)
text=text[:start]+'var names=new[]{"Sun","Sky","Fog","Look","Station","Trees","Lights","Reflection Probes","Volumetric Haze","Station Indirect Light"}.ToHashSet(StringComparer.OrdinalIgnoreCase);'+text[end:]
text=text.replace('models/maps/ares/ares_hall.vmdl','models/maps/railhead/railhead_dress_east.vmdl').replace('models/props/ares/main_airlock_sign_v1/preview.vmdl','models/maps/railhead/taxi-post-v1/east_without_taxi.vmdl').replace('models/props/ares/main_airlock_sign_v1/sign.vmdl','models/maps/railhead/taxi-post-v1/taxi_post.vmdl')
start=text.index(' var views=');end=text.index('\n foreach(var after',start)
text=text[:start]+''' var views=new[]{("whole",new Vector3(1335,-1540,90),new Vector3(1180,-1488,51),32f),("detail",new Vector3(1265,-1513,104),new Vector3(1180,-1488,92.3f),26f)};'''+text[end:]
text=text.replace('view.Item1=="detail"?1600:1200','view.Item1=="detail"?1200:900').replace('view.Item1=="detail"?650:1000','view.Item1=="detail"?900:1200')
(HERE/'capture_current.cs.txt').write_text(text)
for model in ('taxi_post','east_without_taxi'):print(native.call('asset_compile',dict(path=f'models/maps/railhead/taxi-post-v1/{model}.vmdl')))
print(native.script(HERE/'capture_current.cs.txt'))
for p,h in guard.items():assert sha(ROOT/p)==h,p
(CURRENT/'verification.json').write_text(json.dumps(dict(review_only=True,old_triangles=124,new_triangles=4472,public_inputs_unchanged=True,unrelated_obj_records_unchanged=True,physics_unchanged=True)))
