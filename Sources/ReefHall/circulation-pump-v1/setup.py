"""Derive the matched actual-play inspection harness."""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent;template=ROOT/'Sources/Railhead/brick-pallet-v1'
native=(template/'native.py').read_text().replace('output/railhead/brick-pallet-v1','output/reefhall/circulation-pump-v1').replace('railhead-pallet','reefhall-pump');(HERE/'native.py').write_text(native)
capture=(template/'capture.py').read_text().replace('scenes/maps/railhead/railhead.scene','scenes/maps/reefhall/reefhall.scene');(HERE/'capture.py').write_text(capture)
runtime=(template/'runtime_review.cs.txt').read_text()
for old,new in [('scenes/maps/railhead/railhead.scene','scenes/maps/reefhall/reefhall.scene'),('output/railhead/brick-pallet-v1','output/reefhall/circulation-pump-v1'),('models/maps/railhead/railhead_dress_east.vmdl','models/maps/reefhall/reefhall_filter.vmdl'),('models/maps/railhead/brick-pallet-v1/brick_pallet.vmdl','models/maps/reefhall/circulation-pump-v1/circulation_pump.vmdl'),('models/maps/railhead/brick-pallet-v1/east_without_pallet.vmdl','models/maps/reefhall/circulation-pump-v1/filter_without_pump.vmdl'),('Name="pallet",Eye=new Vector3(-1650,-1995,74),Target=new Vector3(-1580,-1884,21),Fov=44f','Name="pump",Eye=new Vector3(1480,480,80),Target=new Vector3(1610,380,30),Fov=44f'),('Railhead','ReefHall'),('brick pallet','circulation pump')]:runtime=runtime.replace(old,new)
runtime=runtime.replace('Fov=44f}};', 'Fov=44f},new {Name="connections",Eye=new Vector3(1465,250,84),Target=new Vector3(1610,380,30),Fov=44f}};')
(HERE/'runtime_review.cs.txt').write_text(runtime)
verify=(template/'verify.py').read_text()
for old,new in [('brick-pallet-v1','circulation-pump-v1'),('east_without_pallet','filter_without_pump'),('models/maps/railhead/cable-drum-v1/east_without_drum.obj','models/maps/reefhall/reefhall_filter.obj'),('railhead_dress_east.vmdl','reefhall_filter.vmdl'),('maps/railhead/','maps/reefhall/'),('output/railhead/','output/reefhall/'),("('pallet',)","('pump',)"),('RAILHEAD / BRICK PALLET','REEFHALL / CIRCULATION PUMP'),('scenes/maps/railhead/railhead.scene','scenes/maps/reefhall/reefhall.scene')]:verify=verify.replace(old,new)
verify=verify.replace('scenes/maps/reefhall/railhead.scene','scenes/maps/reefhall/reefhall.scene')
verify=verify.replace("('pump',)","('pump','connections')")
(HERE/'verify.py').write_text(verify)
review=(template/'review.py').read_text().replace("('brick_pallet','east_without_pallet')","('circulation_pump','filter_without_pump')").replace('models/maps/railhead/brick-pallet-v1','models/maps/reefhall/circulation-pump-v1');(HERE/'review.py').write_text(review)
print('Review scripts ready')
