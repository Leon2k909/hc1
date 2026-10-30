"""Reuse the already reviewed actual-mesh renderer with a cabinet camera."""
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
source=(ROOT/'Sources/Collider/equipment-case-trial-v1/render.py').read_text()
source=source.replace("OUT=ROOT/'output/asset-improvement-20261029/equipment-case'",
    "OUT=ROOT/'output/asset-improvement-20261029/west-cabinet'")
source=source.replace("RESOURCE='models/props/collider/equipment-case-trial-v1'",
    "RESOURCE='models/props/collider/west-cabinet-trial-v1'")
source=source.replace('output/collider-case-accepted-20261029/retired-before-resources',
    'output/collider-cabinet-accepted-20261029/retired-before-resources')
source=source.replace('scene.cycles.samples=48','scene.cycles.samples=32')
source=source.replace('scene.render.resolution_x=1400;scene.render.resolution_y=1050',
    'scene.render.resolution_x=1000;scene.render.resolution_y=1300')
source=source.replace("views=[('main',(3.5,-4.6,3.3),(0,0,.85)),('detail',(2.25,-3.5,1.85),(.35,-.55,.95))]",
    "views=[('main',(3.1,-4.7,3.2),(0,0,1.72))]")
source=source.replace("data.lens=54. if view=='main' else 67.","data.lens=48.")
source=source.replace("Vector((0,0,.85))","Vector((0,0,1.7))")
(Path(__file__).parent/'render.py').write_text(source)
print('Prepared two matched portrait renders of the actual cabinet meshes.')
