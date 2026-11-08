"""Fit Rigsters' CC-BY Barye sculpture, preserving its authored UV and normal map."""
from pathlib import Path
import sys
import numpy as np
from PIL import Image
import trimesh
import veridant_fountain_reference_top as mount

ROOT=Path(__file__).resolve().parents[1]
architectural = '--architectural-pier' in sys.argv
single = '--single-lion' in sys.argv
variant = 'single_lion' if single else 'architectural' if architectural else 'open_mouth'
DEST=ROOT/'Assets/models/props/shared'/f'veridant_fountain_barye_{variant}'
DEST.mkdir(parents=True,exist_ok=True)
mount.FOLDER=DEST
mount.PIER=[(48.3,8.7,10.2),(48.7,9.1,10.5),(49.5,9.1,10.5),
 (50,8.7,10.1),(51,8.3,9.8),(53,7.7,9.4),(55,7.1,9.0),
 (58,6.4,8.5),(61,5.8,8.1),(64,5.35,7.8),(67,5.0,7.6),
 (70,4.8,7.5),(73,4.75,7.5),(76,4.8,7.6),(78,5.0,7.8),
 (78.4,6.1,8.7),(78.8,6.1,8.7),(79.2,6.7,9.2),
 (79.6,7.2,9.6),(80.1,7.6,9.9),(80.7,7.6,9.9),(81.2,7.2,9.6),(81.5,6.8,9.3)]
mount.PIER_HEIGHTS,mount.PIER_WIDTHS,mount.PIER_DEPTHS=np.array(mount.PIER).T
scene=trimesh.load_scene(ROOT/'Sources/Veridant/cairo-lion/barye-lion.glb')
mesh=scene.geometry['lion_texture_lion_texture_0'].copy()
material=mesh.visual.material
tex=ROOT/'Assets/materials/veridant'
if not architectural and not single:
    material.baseColorTexture.save(tex/'barye_lion_color.png')
    material.normalTexture.save(tex/'barye_lion_normal.png')
    packed=np.array(material.metallicRoughnessTexture)
    Image.fromarray(packed[:,:,1]).save(tex/'barye_lion_rough.png')
uv=mesh.visual.uv.copy();p=mesh.vertices.copy()
mesh.vertices=np.column_stack((3+(13.42-p[:,1])*1.25,(p[:,0]+2.32)*1.25,49.4+(p[:,2]+.073)*1.25))
# Recess the front of the muzzle while keeping the scan's continuous UV surface.
vertices=mesh.vertices.copy()
radial,lateral,height=vertices.T
opening=((lateral-3.2)/1.65)**2+((height-70.65)/1.02)**2
recess=np.clip(1-opening,0,1)**1.4
vertices[:,0]-=2.8*recess*np.clip((radial-27.5)/1.5,0,1)
mesh.vertices=vertices
# Transformation from source XYZ to (-Y,X,Z) preserves winding.
if single:
    mesh.vertices = (mesh.vertices - [17, 0, 49.4]) * 1.65 + [0, 0, 50.6]
assets = [(f'barye_lion_{sign}', 'barye_bronze', mesh, uv, sign)
          for sign in ((1,) if single else (-1, 1))]
# The scan already has a complete bronze base; avoid a second oversized slab.
if single:
    plinth = mount.moulding([
        (46.5, 25.8, 15.6), (47.8, 25.8, 15.6), (48.6, 24.8, 14.6),
        (49.1, 24.3, 14.1), (49.6, 24.6, 14.4), (50.2, 24.6, 14.4),
        (50.6, 24.1, 13.9),
    ], exponent=2.8, sides=128)
    assets.extend((f'plinth_{i}', mount.STONE, part, coords, 1)
                  for i, (part, coords) in enumerate(plinth))
elif architectural:
    from veridant_fountain_architectural_pier import build
    assets.extend(build())
else:
    assets.extend((f'stone_core_{i}',mount.STONE,m,uv,1) for i,(m,uv) in enumerate(mount.moulding(mount.PIER,exponent=mount.PIER_EXPONENT)))
    for side in (-1,1):
        assets.extend((f'acanthus_{side}_{i}',mount.STONE,m,uv,1) for i,(m,uv) in enumerate(mount.acanthus(side)))
mount.write_obj(assets)
(DEST/'crown.mtl').write_text('newmtl barye_bronze\nnewmtl reference_bronze\nnewmtl carved_limestone\n')
t=(ROOT/'Assets/models/props/shared/veridant_fountain_reference_top/crown.vmdl').read_text().replace('veridant_fountain_reference_top/crown.obj',DEST.name+'/crown.obj')
t=t.replace('{ from = "reference_bronze.vmat"','{ from = "barye_bronze.vmat" to = "materials/veridant/fountain_barye_bronze.vmat" },\n{ from = "reference_bronze.vmat"')
(DEST/'crown.vmdl').write_text(t)
print('Triangles',sum(len(m.faces) for _,_,m,_,_ in assets),'Lion bounds',mesh.bounds.tolist())
