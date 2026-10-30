"""Matched actual-OBJ chair renders, without launching the game editor."""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
s=(ROOT/'Sources/Collider/equipment-case-trial-v1/render.py').read_text()
s=s.replace("OUT=ROOT/'output/asset-improvement-20261029/equipment-case'","OUT=ROOT/'output/asset-improvement-20261029/chair'")
s=s.replace("RESOURCE='models/props/collider/equipment-case-trial-v1'","RESOURCE='models/props/collider/chair-trial-v1'")
s=s.replace('output/collider-case-accepted-20261029/retired-before-resources','output/collider-chair-accepted-20261029/retired-before-resources')
s=s.replace('scene.cycles.samples=48','scene.cycles.samples=32')
s=s.replace("views=[('main',(3.5,-4.6,3.3),(0,0,.85)),('detail',(2.25,-3.5,1.85),(.35,-.55,.95))]",
    "views=[('main',(1.7,-2.5,1.55),(0,0,.65))]")
s=s.replace("data.lens=54. if view=='main' else 67.","data.lens=43.")
(Path(__file__).parent/'render.py').write_text(s)
print('Prepared matched full-chair renders.')
