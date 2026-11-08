"""Build the Veridant reclining lion variant from the existing lion sculpt."""
from pathlib import Path
import numpy as np
from belltower_fountain_ornaments import Carving

root = Path(__file__).resolve().parents[1]
folder = root / 'Assets/models/props/shared/veridant_fountain_sculpture_v4'
folder.mkdir(parents=True, exist_ok=True)

# x is across the animal, depth runs from the haunches toward the paws.
body = Carving((-11, -4, 54), (11, 32, 83), .22)
# Submerged casting base, tucked behind the paws.
body.ellipsoid((0, 11.8, 57.3), (7.35, 14.9, 1.6), .44)
body.ellipsoid((0, 9.9, 64.25), (5.45, 9.4, 4.65), .85)
body.ellipsoid((0, 4.1, 63.55), (6.2, 5.05, 5.35), .8)
body.ellipsoid((0, 14.55, 66.25), (5.25, 4.9, 7.05), 1.05)
body.ellipsoid((0, 15.1, 71.2), (4.25, 4.3, 6.15), 1.2)
for sign in (-1, 1):
    body.ellipsoid((sign * 4.35, 4.65, 63.15), (2.85, 4.45, 4.75), .72, tilt=sign * .22)
    body.ellipsoid((sign * 4.75, 7.55, 60.5), (2.35, 3.35, 2.05), .52)
    body.ellipsoid((sign * 4.1, 15.2, 64.85), (2.9, 3.75, 4.5), .62, tilt=sign * -.21)
    body.ellipsoid((sign * 4.9, 17.25, 61.75), (1.92, 2.6, 2.55), .47)
    body.stroke([(sign * 4.5, 15.1, 64.8), (sign * 5.25, 18.25, 60.4),
                 (sign * 4.65, 22.5, 59.7), (sign * 4.45, 25.8, 59.72)], 2.3, 1.35, .88, .48)
    body.ellipsoid((sign * 4.45, 25.25, 59.8), (2.1, 2.65, 1.32), .32)
    for toe in range(4):
        x = sign * 4.45 + (toe - 1.5) * .88
        depth = 27.05 - abs(toe - 1.5) * .29
        body.ellipsoid((x, depth, 59.63), (.59, 1.12, .84), .17)
        if toe < 3:
            body.stroke([(x + .44, 28.25, 60.34), (x + .44, 27.72, 60.52),
                         (x + .44, 27.05, 60.76), (x + .44, 26.35, 60.83)],
                        .24, .13, 1, .09, subtract=True)
    # Staggered locks sweep from the back of the head over the shoulder.
    for lock in range(6):
        x = sign * (2.15 + lock * .58)
        body.stroke([(x, 16.25 - lock * .76, 76.9 - lock * .53),
                     (x + sign * 2.65, 15.8 - lock * .79, 73.1 - lock * .34),
                     (x + sign * 1.65, 13.65 - lock * .65, 68.4 - lock * .28),
                     (x + sign * .82, 15.05 - lock * .76, 65.45 - lock * .21)],
                    1.16, .19, 1.12, .27)
    # The silhouette needs separate swept locks from the side and rear as well.
    for lock in range(5):
        body.stroke([(sign * (2.25 + lock * .53), 10.2 + lock * .54, 77.9 - lock * .52),
                     (sign * (4.95 + lock * .38), 9.1 + lock * .73, 75.7 - lock * .6),
                     (sign * (6.8 - lock * .12), 9.0 + lock * .66, 71.65 - lock * .42),
                     (sign * (4.9 + lock * .34), 10.7 + lock * .72, 68.15 - lock * .54)],
                    1.05, .30, 1.06, .29)
body.stroke([(-.5, 1.8, 62), (-8.6, 1.5, 58.9), (-9, 13, 58.85),
             (-4.2, 17.2, 59.5)], 1.1, .61, .9, .34)
body.ellipsoid((-4.4, 16.95, 59.45), (.78, 1.25, .65), .28, tilt=-.25)
# Sculpt the skull, mane and jaw into the body field. The mouth stays on the
# established fountain jet anchor at (0, 21.7, 70.5).
body.ellipsoid((0, 14.4, 74.85), (4.7, 5.1, 5.85), .93)
body.ellipsoid((0, 17.7, 74.85), (3.3, 3.7, 4.15), .64)
body.ellipsoid((0, 20.25, 72.6), (2.15, 2.6, 1.67), .43)
body.ellipsoid((0, 22.25, 73.08), (1.26, .93, .71), .31)
body.ellipsoid((0, 19.95, 69.45), (1.95, 2.45, 1.08), .36)
for sign in (-1, 1):
    body.ellipsoid((sign * 2.06, 19.78, 72.13), (1.25, 2.0, 1.42), .42)
    body.ellipsoid((sign * 2.45, 16.6, 77.65), (1.17, 1.22, 1.32), .27, tilt=sign * .28)
    body.ellipsoid((sign * 2.62, 17.47, 77.96), (.62, .58, .76), .14, subtract=True)
    body.ellipsoid((sign * 1.68, 20.08, 74.38), (.83, .82, .52), .13, subtract=True)
    body.ellipsoid((sign * 1.71, 19.77, 74.36), (.48, .43, .34), .12)
    body.stroke([(sign * .95, 20.4, 74.73), (sign * 1.5, 20.22, 75.15),
                 (sign * 2.31, 19.78, 75.12), (sign * 2.79, 19.0, 74.71)],
                .43, .18, 1, .19)
    body.ellipsoid((sign * .61, 22.94, 72.83), (.32, .45, .22), .08, subtract=True)
    for lock in range(4):
        body.stroke([(sign * (.65 + lock * .72), 16.7 - lock * .67, 79.72 - lock * .39),
                     (sign * (2.8 + lock * .44), 13.3, 81.1 - lock * .38),
                     (sign * (4.25 + lock * .42), 11.6, 76.5 - lock * .47),
                     (sign * (4.45 + lock * .32), 10.4, 72.15 - lock * .42)],
                    .85, .22, 1.05, .27)
    for lock in range(6):
        depth = 12.1 + lock * .88
        body.stroke([(sign * 2.8, depth - 1.1, 78.8 - lock * .26),
                     (sign * 5.65, depth - 1.5, 77.0 - lock * .33),
                     (sign * 6.05, depth - .1, 71.9 - lock * .31),
                     (sign * 4.6, depth + .1, 67.6 - lock * .18)],
                    .76, .24, 1.2, .24)
body.ellipsoid((0, 21.65, 70.62), (1.53, 2.42, .71), .17, subtract=True)
body_mesh = body.mesh()

with (folder / 'sculpture.obj').open('w', encoding='utf-8') as obj:
    obj.write('mtllib sculpture.mtl\no reclining_lions\nusemtl lion_bronze\n')
    offset = 1
    for sign in (1, -1):
        forward = np.array((.6, -.8, 0)) * sign
        side = np.array((-.8, -.6, 0)) * sign
        basis = np.column_stack((side, forward, (0, 0, 1)))
        for vertices, faces, normals in (body_mesh,):
            for x, y, z in vertices @ basis.T:
                obj.write(f'v {y:.5f} {z:.5f} {x:.5f}\n')
            for x, y, z in vertices:
                obj.write(f'vt {(x + y * .31) / 32 + .5:.5f} {z / 32 + .25:.5f}\n')
            for x, y, z in normals @ basis.T:
                obj.write(f'vn {y:.5f} {z:.5f} {x:.5f}\n')
            for face in faces:
                obj.write('f ' + ' '.join(f'{i}/{i}/{i}' for i in face + offset) + '\n')
            offset += len(vertices)

(folder / 'sculpture.mtl').write_text('newmtl lion_bronze\nKd 0.4 0.28 0.16\n', encoding='utf-8')
old = root / 'Assets/models/props/shared/veridant_fountain_lions/lions_patina.vmdl'
model = old.read_text(encoding='utf-8-sig')
model = model.replace('veridant_fountain_lions/lions.obj', f'{folder.name}/sculpture.obj')
model = model.replace('fountain_lion_patina.vmat', 'fountain_weathered_bronze.vmat')
(folder / 'sculpture.vmdl').write_text(model.replace('paired_lion_masks', 'reclining_lions'), encoding='utf-8')
