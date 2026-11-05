"""Derive the native review harness; write scripts only, never live assets."""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent
template=ROOT/'Sources/Ares/locker-v1'
native=(template/'native.py').read_text().replace('output/ares/locker-v1','output/railhead/brick-pallet-v1').replace('ares-locker','railhead-pallet')
(HERE/'native.py').write_text(native)
capture=(template/'capture.py').read_text().replace('scenes/maps/ares/ares.scene','scenes/maps/railhead/railhead.scene')
(HERE/'capture.py').write_text(capture)
runtime=(template/'runtime_review.cs.txt').read_text()
for old,new in [('scenes/maps/ares/ares.scene','scenes/maps/railhead/railhead.scene'),('output/ares/locker-v1','output/railhead/brick-pallet-v1'),('models/maps/ares/ares_hall.vmdl','models/maps/railhead/railhead_dress_east.vmdl'),('models/maps/ares/locker-v1/locker.vmdl','models/maps/railhead/brick-pallet-v1/brick_pallet.vmdl'),('models/maps/ares/locker-v1/hall_without_locker.vmdl','models/maps/railhead/brick-pallet-v1/east_without_pallet.vmdl'),('900,1200','1200,900'),('Name="locker",Eye=new Vector3(-592,-1318,62),Target=new Vector3(-709,-1278,42),Fov=36f','Name="pallet",Eye=new Vector3(-1650,-1995,74),Target=new Vector3(-1580,-1884,21),Fov=44f'),('Ares','Railhead'),('locker','brick pallet')]:
 runtime=runtime.replace(old,new)
(HERE/'runtime_review.cs.txt').write_text(runtime)
verify=(ROOT/'Sources/Railhead/road-barrier-v1/verify.py').read_text()
for old,new in [('road-barrier-v1','brick-pallet-v1'),('east_without_barrier','east_without_pallet'),('models/maps/railhead/extinguisher-v2/east-base.obj','models/maps/railhead/cable-drum-v1/east_without_drum.obj'),(" == manifest['original_triangles'] == 120"," == manifest['original_triangles']"),("('barrier',)","('pallet',)"),('ROADWORKS BARRIER','BRICK PALLET'),('replaced_triangles=120',"replaced_triangles=manifest['original_triangles']")]:
 verify=verify.replace(old,new)
(HERE/'verify.py').write_text(verify)
print('Native review scripts ready')
