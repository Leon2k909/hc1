"""Reuse the native actual-play harness with a beer-garden view."""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent;old=ROOT/'Sources/ReefHall/office-chair-v1'
(HERE/'native.py').write_text((old/'native.py').read_text().replace('output/reefhall/office-chair-v1','output/belltower/picnic-table-v1').replace('reefhall-office-chair','belltower-picnic-table'))
src=(old/'runtime_review.cs.txt').read_text()
for a,b in [('output/reefhall/office-chair-v1','output/belltower/picnic-table-v1'),('scenes/maps/reefhall/reefhall.scene','scenes/maps/belltower/belltower.scene'),('models/maps/reefhall/reefhall_control.vmdl','models/maps/belltower/belltower_west.vmdl'),('models/maps/reefhall/office-chair-v1/control_without_chair.vmdl','models/maps/belltower/picnic-table-v1/west_without_table.vmdl'),('models/maps/reefhall/office-chair-v1/office_chair.vmdl','models/maps/belltower/picnic-table-v1/picnic_table.vmdl'),('Reef Hall','Belltower'),('office chair review','picnic table review'),('Candidate chair','Candidate table'),('new Vector2(1000,1000)','new Vector2(1200,900)'),('new Bitmap(1000,1000)','new Bitmap(1200,900)')]:src=src.replace(a,b)
src=src.replace('if(!Game.IsPlaying||Game.ActiveScene!=runtimeScene)throw new InvalidOperationException("Play session changed while waiting for the player");', '''if(!Game.IsPlaying||Game.ActiveScene?.Source?.ResourcePath!="scenes/maps/belltower/belltower.scene")
   throw new InvalidOperationException("Unexpected play scene during startup: "+Game.ActiveScene?.Source?.ResourcePath);
  // Startup may replace the scene object with another runtime copy of the same map.
  runtimeScene=Game.ActiveScene;''')
start=src.index(' var views=new[]');end=src.index(' foreach(var variant in',start)
src=src[:start]+''' var views=new[]{new {Name="table",Eye=new Vector3(-700,690,70),Target=new Vector3(-600,800,16),Fov=50f}};
'''+src[end:]
(HERE/'runtime_review.cs.txt').write_text(src)
(HERE/'capture.py').write_text((old/'capture.py').read_text().replace('scenes/maps/reefhall/reefhall.scene','scenes/maps/belltower/belltower.scene'))
