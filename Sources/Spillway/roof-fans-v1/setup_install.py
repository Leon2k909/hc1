from pathlib import Path
import json
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
plan=json.loads((HERE/'review/install-plan.json').read_text())
s=(ROOT/'Sources/ReefHall/bronze-planter-v1/install.cs.txt').read_text()
s=s.replace('Sources/ReefHall/bronze-planter-v1/review','Sources/Spillway/roof-fans-v1/review')
a=s.index('var allowed=');b=s.index('\nforeach',a)
s=s[:a]+'var allowed=new[]{'+','.join(json.dumps(p) for p in plan['files'])+'};'+s[b:]
s=s.replace('Tools/reefhall_bronze_planter.py','Tools/spillway_roof_fans.py').replace('Planters=2','RoofFans=7').replace('.planter-writing','.roof-fan-writing')
(HERE/'install.cs.txt').write_text(s)
