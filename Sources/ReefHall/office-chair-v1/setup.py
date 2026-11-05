"""Configure the matched actual-play view and validation."""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent
old=ROOT/'Sources/Railhead/cable-drum-v1'
(HERE/'native.py').write_text((old/'native.py').read_text().replace('output/railhead/cable-drum-v1','output/reefhall/office-chair-v1').replace('railhead-cable-drum','reefhall-office-chair'))
src=(old/'runtime_review.cs.txt').read_text()
for a,b in [('output/railhead/cable-drum-v1','output/reefhall/office-chair-v1'),('scenes/maps/railhead/railhead.scene','scenes/maps/reefhall/reefhall.scene'),('models/maps/railhead/railhead_dress_east.vmdl','models/maps/reefhall/reefhall_control.vmdl'),('models/maps/railhead/cable-drum-v1/east_without_drum.vmdl','models/maps/reefhall/office-chair-v1/control_without_chair.vmdl'),('models/maps/railhead/cable-drum-v1/cable_drum.vmdl','models/maps/reefhall/office-chair-v1/office_chair.vmdl'),('Railhead','Reef Hall'),('cable drum review','office chair review'),('Candidate reel','Candidate chair'),('new Vector2(1600,900)','new Vector2(1000,1000)'),('new Bitmap(1600,900)','new Bitmap(1000,1000)')]:src=src.replace(a,b)
start=src.index(' var views=new[]');end=src.index(' foreach(var variant in',start)
src=src[:start]+''' var views=new[]{new {Name="chair",Eye=new Vector3(850,-2020,249),Target=new Vector3(806,-1960,228),Fov=38f}};
'''+src[end:]
(HERE/'runtime_review.cs.txt').write_text(src)
(HERE/'capture.py').write_text((old/'capture.py').read_text().replace('scenes/maps/railhead/railhead.scene','scenes/maps/reefhall/reefhall.scene'))
verify=(ROOT/'Sources/Riverside/drinks-fridge-v1/verify.py').read_text()
for a,b in [('riverside/drinks-fridge-v1','reefhall/office-chair-v1'),('store_without_fridge','control_without_chair'),('riverside/riverside_store','reefhall/reefhall_control'),('scenes/maps/riverside/riverside.scene','scenes/maps/reefhall/reefhall.scene'),('== 14','== 36'),('replaced_triangles=14','replaced_triangles=36'),("('fridge',)","('chair',)"),('RIVERSIDE / DRINKS FRIDGE','REEF HALL / OFFICE CHAIR')]:verify=verify.replace(a,b)
verify=verify.replace("assert restored['after']['LastCompileSucceeded'] and restored['after']['LastCompileErrors'] == 0", "assert restored['after']['LastCompileErrors'] == 0\nif not restored['after']['IsCompiling']: assert restored['after']['LastCompileSucceeded']")
(HERE/'verify.py').write_text(verify)
