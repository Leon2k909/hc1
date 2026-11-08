"""Export the paired Veridant fountain masks from the installed Belltower sculpt."""
from pathlib import Path
import numpy as np

root = Path(__file__).resolve().parents[1]
source = root / 'Sources/Belltower/props/fountain-ornaments-v2/lion-d6d3738f2be0.npz'
folder = root / 'Assets/models/props/shared/veridant_fountain_lions'
folder.mkdir(parents=True, exist_ok=True)

with np.load(source, allow_pickle=False) as data:
    vertices, normals, faces = (data[key] for key in ('vertices', 'normals', 'faces'))

with (folder / 'lions.obj').open('w', encoding='utf-8') as obj:
    obj.write('mtllib lions.mtl\no paired_lion_masks\nusemtl lion_bronze\n')
    for index, sign in enumerate((1, -1)):
        forward = np.array((0.6, -0.8, 0)) * sign
        side = np.array((-0.8, -0.6, 0)) * sign
        basis = np.column_stack((side, forward, (0, 0, 1)))
        points = vertices * 0.68 @ basis.T + forward * 1.15 + (0, 0, 68)
        for x, y, z in points:
            obj.write(f'v {y:.5f} {z:.5f} {x:.5f}\n')
        for x, _, z in vertices:
            obj.write(f'vt {x / 30 + .5:.5f} {z / 34 + .5:.5f}\n')
        for x, y, z in normals @ basis.T:
            obj.write(f'vn {y:.5f} {z:.5f} {x:.5f}\n')
        for face in faces:
            ids = face + index * len(vertices) + 1
            obj.write('f ' + ' '.join(f'{i}/{i}/{i}' for i in ids) + '\n')

(folder / 'lions.mtl').write_text('newmtl lion_bronze\nKd 0.4 0.28 0.16\n', encoding='utf-8')
template = root / 'Assets/models/props/shared/fountain_bowl_v1/fountain_bowl.vmdl'
model = template.read_text(encoding='utf-8')
model = model.replace('vr_stone.vmat', 'lion_bronze.vmat').replace('materials/veridant/', 'materials/belltower/')
model = model.replace('fountain_bowl_v1/fountain_bowl.obj', 'veridant_fountain_lions/lions.obj')
(folder / 'lions.vmdl').write_text(model.replace('name = "fountain_bowl"', 'name = "paired_lion_masks"'), encoding='utf-8')
