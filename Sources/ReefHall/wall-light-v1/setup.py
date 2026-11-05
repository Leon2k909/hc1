from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent;template=ROOT/'Sources/ReefHall/circulation-pump-v1'
(HERE/'native.py').write_text((template/'native.py').read_text().replace('circulation-pump-v1','wall-light-v1').replace('reefhall-pump','reefhall-wall-light'))
(HERE/'capture.py').write_text((template/'capture.py').read_text())
runtime=(template/'runtime_review.cs.txt').read_text().replace('circulation-pump-v1','wall-light-v1').replace('circulation_pump.vmdl','wall_light.vmdl').replace('filter_without_pump','filter_without_light').replace('circulation pump','wall light').replace('1200,900','900,1200')
a=runtime.index(' var views=');b=runtime.index(' foreach(var variant',a)
runtime=runtime[:a]+''' var views=new[]{new {Name="light",Eye=new Vector3(1136,-778,131),Target=new Vector3(1101.5f,-760,118),Fov=26f}};
'''+runtime[b:]
(HERE/'runtime_review.cs.txt').write_text(runtime)
verify=(template/'verify.py').read_text()
for old,new in [('circulation-pump-v1','wall-light-v1'),('filter_without_pump','filter_without_light'),("('pump','connections')","('light',)"),('REEFHALL / CIRCULATION PUMP','REEFHALL / WALL LIGHT')]:verify=verify.replace(old,new)
(HERE/'verify.py').write_text(verify)
review=(template/'review.py').read_text().replace('circulation-pump-v1','wall-light-v1').replace("('circulation_pump','filter_without_pump')","('wall_light','filter_without_light')");(HERE/'review.py').write_text(review)
print('Review harness ready')
