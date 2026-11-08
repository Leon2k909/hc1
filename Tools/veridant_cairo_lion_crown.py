"""Fit Daniel Pett's CC0 reclining lion scan with clean modeled limestone support."""
from pathlib import Path
import numpy as np
import trimesh
import veridant_fountain_reference_top as mount

ROOT=Path(__file__).resolve().parents[1]
DEST=ROOT/'Assets/models/props/shared/veridant_fountain_cairo_crown'
DEST.mkdir(parents=True,exist_ok=True)
mount.FOLDER=DEST
# A broad stone foot sweeps inward to the neck, below a separate moulded capital.
mount.PIER=[(48.3,8.7,10.2),(48.7,9.1,10.5),(49.5,9.1,10.5),
 (50,8.7,10.1),(51,8.3,9.8),(53,7.7,9.4),(55,7.1,9.0),
 (58,6.4,8.5),(61,5.8,8.1),(64,5.35,7.8),(67,5.0,7.6),
 (70,4.8,7.5),(73,4.75,7.5),(76,4.8,7.6),(78,5.0,7.8),
 (78.4,6.1,8.7),(78.8,6.1,8.7),(79.2,6.7,9.2),
 (79.6,7.2,9.6),(80.1,7.6,9.9),(80.7,7.6,9.9),(81.2,7.2,9.6),(81.5,6.8,9.3)]
mount.PIER_HEIGHTS,mount.PIER_WIDTHS,mount.PIER_DEPTHS=np.array(mount.PIER).T
scene=trimesh.load_scene(ROOT/'Sources/Veridant/cairo-lion/lion.glb')
assets=[]
for node in scene.graph.nodes_geometry:
    transform,key=scene.graph[node]
    mesh=scene.geometry[key].copy();mesh.apply_transform(transform)
    uv=mesh.visual.uv.copy()
    mask=np.all(mesh.vertices[mesh.faces,1]>-.40,axis=1)
    # Keep the complete carved animal, remove the scanned masonry plinth and floor.
    mesh.update_faces(mask)
    p=mesh.vertices.copy()
    mesh.vertices=np.column_stack((3.0+(p[:,2]+6.9)*6.15,
                                    (p[:,0]-.04)*6.4,
                                    49.4+(p[:,1]+.40)*9.7))
    for sign in (-1,1):assets.append((f'cairo_lion_{node}_{sign}',mount.BRONZE,mesh,uv,sign))
pads=mount.moulding([(47.9,16.5,8.6),(48.5,16.9,8.9),(49.15,16.9,8.9),
                     (49.5,16.5,8.5)],centre=17.0,exponent=4)
for sign in (-1,1):
    assets.extend((f'cast_pad_{sign}_{i}',mount.BRONZE,m,uv,sign) for i,(m,uv) in enumerate(pads))
assets.extend((f'stone_core_{i}',mount.STONE,m,uv,1) for i,(m,uv) in enumerate(mount.moulding(mount.PIER,exponent=mount.PIER_EXPONENT)))
for side in (-1,1):
    assets.extend((f'acanthus_{side}_{i}',mount.STONE,m,uv,1) for i,(m,uv) in enumerate(mount.acanthus(side)))
mount.write_obj(assets)
(DEST/'crown.mtl').write_text('newmtl reference_bronze\nKd 0.15 0.13 0.10\nnewmtl carved_limestone\nKd 0.5 0.47 0.4\n')
template=(ROOT/'Assets/models/props/shared/veridant_fountain_reference_top/crown.vmdl').read_text()
template=template.replace('veridant_fountain_reference_top/crown.obj','veridant_fountain_cairo_crown/crown.obj')
(DEST/'crown.vmdl').write_text(template)
print('Crown triangles',sum(len(m.faces) for _,_,m,_,_ in assets))
print('Lion bounds', [a[2].bounds.tolist() for a in assets[:6]])
