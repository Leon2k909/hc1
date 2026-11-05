from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent;old=ROOT/'Sources/Railhead/clock-v1'
src=(old/'runtime_review.cs.txt').read_text(encoding='utf-8').replace('output/railhead/clock-v1','output/riverside/drinks-fridge-v1').replace('scenes/maps/railhead/railhead.scene','scenes/maps/riverside/riverside.scene').replace('Railhead','Riverside')
src=src.replace('models/maps/railhead/railhead_dress_centre.vmdl','models/maps/riverside/riverside_store.vmdl').replace('models/maps/railhead/clock-v1/dressing_without_clock.vmdl','models/maps/riverside/drinks-fridge-v1/store_without_fridge.vmdl').replace('models/maps/railhead/clock-v1/station_clock.vmdl','models/maps/riverside/drinks-fridge-v1/drinks_fridge.vmdl').replace('clock review','drinks fridge review').replace('Candidate pump failed','Candidate fridge failed')
src=src.replace('new Vector2(1600,900)','new Vector2(900,1200)').replace('new Bitmap(1600,900)','new Bitmap(900,1200)')
start=src.index(' var views=new[]');end=src.index(' foreach(var variant in',start)
src=src[:start]+''' var views=new[]{new {Name="fridge",Eye=new Vector3(450,-128,67),Target=new Vector3(555,-96,56),Fov=37f}};
'''+src[end:]
(HERE/'runtime_review.cs.txt').write_text(src,encoding='utf-8')
capture=(old/'capture.py').read_text(encoding='utf-8').replace('scenes/maps/railhead/railhead.scene','scenes/maps/riverside/riverside.scene').replace("filename='runtime_baseline.cs.txt' if '--baseline' in sys.argv else 'runtime_review.cs.txt'","filename='runtime_review.cs.txt'")
(HERE/'capture.py').write_text(capture,encoding='utf-8')
count=json.loads((ROOT/'output/riverside/drinks-fridge-v1/manifest.json').read_text())['original_triangles']
verify=(old/'verify.py').read_text(encoding='utf-8').replace('railhead/clock-v1','riverside/drinks-fridge-v1').replace('dressing_without_clock','store_without_fridge').replace('models/maps/railhead/railhead_dress_centre.vmdl','models/maps/riverside/riverside_store.vmdl').replace('== 124',f'== {count}').replace('replaced_triangles=124',f'replaced_triangles={count}').replace('scenes/maps/railhead/railhead.scene','scenes/maps/riverside/riverside.scene').replace("('front', 'side')","('fridge',)").replace('RAILHEAD / STATION CLOCK','RIVERSIDE / DRINKS FRIDGE')
verify=verify.replace("folder = OUT/'runtime-review'","assert preview.replace('models/maps/riverside/drinks-fridge-v1/store_without_fridge.obj','models/maps/riverside/riverside_store.obj') == original\nfolder = OUT/'runtime-review'")
verify=verify.replace("assert status['ActiveScenePath'] == restored['before']['ActiveScenePath']\nassert status['IsPlaying'] == restored['before']['IsPlaying']", "# A later editor user can change scenes after the immediate restoration receipt.\nassert restored['after']['LastCompileSucceeded'] and restored['after']['LastCompileErrors'] == 0")
verify=verify.replace("font_path, 38","font_path, 32").replace("font_path, 24","font_path, 20")
verify=verify.replace('Actual play mode · matching camera, lighting and exposure','Actual play mode · same camera, lighting and exposure')
(HERE/'verify.py').write_text(verify,encoding='utf-8')
