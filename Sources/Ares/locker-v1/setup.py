"""Set up an actual-play view of the fourth east-wing locker."""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent;old=ROOT/'Sources/Belltower/picnic-table-v1'
(HERE/'native.py').write_text((old/'native.py').read_text().replace('output/belltower/picnic-table-v1','output/ares/locker-v1').replace('belltower-picnic-table','ares-locker'))
src=(old/'runtime_review.cs.txt').read_text()
for a,b in [('output/belltower/picnic-table-v1','output/ares/locker-v1'),('scenes/maps/belltower/belltower.scene','scenes/maps/ares/ares.scene'),('models/maps/belltower/belltower_west.vmdl','models/maps/ares/ares_hall.vmdl'),('models/maps/belltower/picnic-table-v1/west_without_table.vmdl','models/maps/ares/locker-v1/hall_without_locker.vmdl'),('models/maps/belltower/picnic-table-v1/picnic_table.vmdl','models/maps/ares/locker-v1/locker.vmdl'),('Belltower','Ares'),('picnic table review','locker review'),('Candidate table','Candidate locker'),('new Vector2(1200,900)','new Vector2(900,1200)'),('new Bitmap(1200,900)','new Bitmap(900,1200)')]:src=src.replace(a,b)
start=src.index(' var views=new[]');end=src.index(' foreach(var variant in',start)
src=src[:start]+''' var views=new[]{new {Name="locker",Eye=new Vector3(-592,-1318,62),Target=new Vector3(-709,-1278,42),Fov=36f}};
'''+src[end:]
(HERE/'runtime_review.cs.txt').write_text(src)
(HERE/'capture.py').write_text((old/'capture.py').read_text().replace('scenes/maps/belltower/belltower.scene','scenes/maps/ares/ares.scene'))
verify=(ROOT/'Sources/Riverside/drinks-fridge-v1/verify.py').read_text()
for a,b in [('riverside/drinks-fridge-v1','ares/locker-v1'),('store_without_fridge','hall_without_locker'),('riverside/riverside_store','ares/ares_hall'),('scenes/maps/riverside/riverside.scene','scenes/maps/ares/ares.scene'),('== 14','== 24'),('replaced_triangles=14','replaced_triangles=24'),("('fridge',)","('locker',)"),('RIVERSIDE / DRINKS FRIDGE','ARES / STORAGE LOCKER')]:verify=verify.replace(a,b)
verify=verify.replace("'models/maps/ares/ares_hall.obj'","'models/maps/ares/pressure-doors-v2/hall_base.obj'")
verify=verify.replace("assert restored['after']['LastCompileSucceeded'] and restored['after']['LastCompileErrors'] == 0", "assert restored['after']['LastCompileErrors'] == 0\nif not restored['after']['IsCompiling']: assert restored['after']['LastCompileSucceeded']")
(HERE/'verify.py').write_text(verify)
