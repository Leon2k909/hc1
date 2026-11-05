from pathlib import Path
import json
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
plan=json.loads((HERE/'review/install-plan.json').read_text())
s=(ROOT/'Sources/Orion/yard-lamp-v1/install.cs.txt').read_text()
s=s.replace('output/orion/yard-lamp-v1','Sources/ReefHall/bronze-planter-v1/review')
a=s.index('var allowed=');b=s.index('\nforeach',a)
s=s[:a]+'var allowed=new[]{'+','.join(json.dumps(p) for p in plan['files'])+'};'+s[b:]
s=s.replace('Tools/orion_yard_lamp.py','Tools/reefhall_bronze_planter.py').replace('YardLamps=1','Planters=2').replace('.searchlight-writing','.planter-writing')
(HERE/'install.cs.txt').write_text(s)
