"""Remove baked olives where standalone replacement trees are installed."""
from pathlib import Path
from itertools import combinations
import map_kit as K
import veridant_parts as P

folder = Path(__file__).resolve().parents[1] / 'Assets/models/maps/veridant/garden_cedri'
terrace = K.Model()
P.olive(terrace, (560, 720, 214), 120, seed=87)
P.olive(terrace, (-660, 330, 148), 90, seed=30)
P.olive(terrace, (-660, 560, 148), 85, seed=31)
def face_keys(model):
    for paint, polygons in model.polygons.items():
        for points, _ in polygons:
            keys = [tuple(map(float, K.obj_vector(K.to_world(point)).split())) for point in points]
            for triangle in combinations(keys, 3):
                yield paint, tuple(sorted(triangle))

terrace_faces = set(face_keys(terrace))
lawn_plants = K.Model()
P.shrubs(lawn_plants, (-620, 300), (-560, 520), 128, seed=42, kind='rosemary', h=22)
lawn_plant_faces = set(face_keys(lawn_plants))
vertices, output = [], []
material = ''
removed = 0
removed_lawn_plants = 0
for line in (folder / 'garden_foliage.obj').read_text().splitlines():
    if line.startswith('v '):
        vertices.append(tuple(map(float, line.split()[1:])))
    elif line.startswith('usemtl '):
        material = line.split()[1]
    elif material in {'vr_bark', 'vr_foliage'} and line.startswith('f '):
        points = [vertices[int(token.split('/')[0])-1] for token in line.split()[1:]]
        if (material, tuple(sorted(points))) in lawn_plant_faces:
            removed_lawn_plants += 1
            continue
        if ((material, tuple(sorted(points))) in terrace_faces or
            any(all(abs(y-1100)<95 and abs(x-centre)<95 and 23<z<195 for y,z,x in points)
                for centre in (-150, 250))):
            removed += 1
            continue
    output.append(line)
expected = 700 + sum(len(points)-2 for group in terrace.polygons.values() for points, _ in group)
if removed != expected:
    raise RuntimeError(f'Expected {expected} olive faces, found {removed}')
if removed_lawn_plants != 112:
    raise RuntimeError(f'Expected 112 lawn plant faces, found {removed_lawn_plants}')
name = 'garden_foliage_paved_garden_olives'
(folder / f'{name}.obj').write_text('\n'.join(output) + '\n')
(folder / f'{name}.vmdl').write_text((folder / 'garden_foliage.vmdl').read_text().replace('garden_cedri/garden_foliage.obj', f'garden_cedri/{name}.obj'))
print(f'Removed {removed} baked olive faces')
