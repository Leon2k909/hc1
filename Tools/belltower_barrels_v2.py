"""Scoped repair of the two barrel pairs outside the clock building.

Only the four identified barrels change. All other barrel calls keep their old
geometry and placement. Positions are plan inches; baked physics moves with them.
"""
import argparse
import json
import math
from pathlib import Path
import numpy as np

import map_kit as K
import belltower_furniture as F

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'output/belltower/barrels-v2'
SOURCE = ROOT/'Sources/Belltower/barrels/placement-v2.json'
MATERIALS = {F.WOOD: 'materials/belltower/furniture_wood.vmat',
             F.DARK: 'materials/belltower/furniture_wood_dark.vmat',
             F.IRON: 'materials/buildings/iron_black.vmat',
             'barrel_rust': 'materials/stillhouse/sh_rust.vmat',
             'garden_endgrain': 'materials/gunsmith_range/bench_oak_endgrain.vmat'}


def read_hulls(path):
    vertices = [None]; vertex_lines = []; faces = []
    for number, line in enumerate(path.read_bytes().splitlines(keepends=True)):
        if line.startswith(b'v '):
            vertices.append(np.asarray(list(map(float, line.split()[1:])))); vertex_lines.append(number)
        elif line.startswith(b'f '): faces.append([int(v) for v in line.split()[1:]])
    parent = list(range(len(vertices)))
    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]; a = parent[a]
        return a
    for face in faces:
        for other in face[1:]: parent[find(other)] = find(face[0])
    groups = {}
    for i in range(1, len(vertices)): groups.setdefault(find(i), []).append(i)
    result = []
    for indices in groups.values():
        p = np.asarray([vertices[i] for i in indices])
        result.append({'indices': indices, 'lines': [vertex_lines[i-1] for i in indices], 'obj': p,
                       'centre': (-float(p[:, 0].mean()), float(p[:, 2].mean())),
                       'z0': float(p[:, 1].min()), 'height': float(np.ptp(p[:, 1]))})
    return result


def placements():
    return json.loads(SOURCE.read_text())['barrels'] if SOURCE.exists() else []


def resolve(centre, z, r, h):
    if abs(z) > .001 or abs(r-13) > .001 or abs(h-36) > .001:
        return None
    for row in placements():
        if np.linalg.norm(np.asarray(centre)-row['old']) < .003:
            return row
    return None


def radius(t, r):
    return r*(.84+.16*math.sin(math.pi*t)**.72)


def build(model, centre, z=0., r=13., h=36., seed=0):
    rng = np.random.default_rng(seed+9137)
    c = np.asarray((*centre, z), float)
    yaw = rng.uniform(0, math.tau)
    count = 20
    levels = np.array((0., .025, .07, .16, .30, .48, .66, .82, .93, .975, 1.))
    body_variations = rng.uniform(-.055, .035, count)
    chip_indices = set(rng.choice(count, 4, replace=False).tolist())
    model.material_overrides.update(MATERIALS)
    model.tile_overrides.update({F.WOOD: F.TILE, F.DARK: F.TILE, F.IRON: 48, 'barrel_rust': 32, 'garden_endgrain': 18})

    def polar(a, depth, height):
        return c+np.array((depth*math.cos(a), depth*math.sin(a), height))

    # Each stave has its own small joint, thickness, grain strip and worn chime.
    for stave in range(count):
        left = yaw+stave*math.tau/count+.0018
        right = yaw+(stave+1)*math.tau/count-.0018
        angles = np.linspace(left, right, 4)
        u0, u1 = F.STRIPS[(stave+seed) % len(F.STRIPS)]
        shift = rng.uniform(0, 1)
        end_variation = rng.uniform(-.065, .015)
        points = {}
        normals = {}
        for inner in (False, True):
            for j, t in enumerate(levels):
                rr = radius(float(t), r)+body_variations[stave]-(.68 if inner else 0)
                slope = (radius(min(.9999, float(t)+.001), r)-radius(max(.0001, float(t)-.001), r)) / (.002*h)
                slope = float(np.clip(slope, -.65, .65))
                for k, a in enumerate(angles):
                    # Sparse tapered nicks at the upper rim, not random full-body dents.
                    chip = (.17 if k in (0, 3) else .06) if stave in chip_indices and t > .974 else 0
                    zz = t*h+end_variation*t**12-chip
                    points[inner, j, k] = polar(a, rr, zz)
                    normal = K.normalise((math.cos(a), math.sin(a), -slope))
                    normals[inner, j, k] = -normal if inner else normal
            for j in range(len(levels)-1):
                # Only the top inner wall can be seen beyond the recessed head.
                if inner and levels[j+1] < .93: continue
                for k in range(3):
                    ids = [(inner,j,k),(inner,j,k+1),(inner,j+1,k+1),(inner,j+1,k)]
                    uv = [(u0+(u1-u0)*a/3, levels[b]*h/F.TILE+shift) for _,b,a in ids]
                    F.face(model, F.DARK if inner else F.WOOD, [points[i] for i in ids],
                           sum(normals[i] for i in ids), uv, [normals[i] for i in ids])
        for k, sign in ((0, -1), (3, 1)):
            tangent = np.array((-math.sin(angles[k]), math.cos(angles[k]), 0))*sign
            for j in range(len(levels)-1):
                ids = [(False,j,k),(True,j,k),(True,j+1,k),(False,j+1,k)]
                F.face(model, F.DARK, [points[i] for i in ids], tangent)
        for j, sign in ((0, -1), (len(levels)-1, 1)):
            for k in range(3):
                F.face(model, 'garden_endgrain', [points[False,j,k], points[False,j,k+1], points[True,j,k+1], points[True,j,k]], (0,0,sign))

    # A real, recessed coopered head, with narrow board joints and eased ends.
    lid_r = r*.811
    grid = np.linspace(-lid_r, lid_r, 6)
    lid_z = h-1.05
    for board, (x0, x1) in enumerate(zip(grid, grid[1:])):
        x0 += .035; x1 -= .035
        outline = []
        for x in np.linspace(x0, x1, 8): outline.append((x, -math.sqrt(max(0., lid_r*lid_r-x*x))))
        for x in np.linspace(x1, x0, 8): outline.append((x, math.sqrt(max(0., lid_r*lid_r-x*x))))
        dz = rng.uniform(-.07, .045)
        u0, u1 = F.STRIPS[(board+seed+2) % len(F.STRIPS)]
        v0 = rng.uniform(0, 1)
        # Inset top edge gives each clipped circular board a shallow worn bevel.
        centre2 = np.asarray(outline).mean(axis=0)
        top = [centre2+(np.asarray(p)-centre2)*.993 for p in outline]
        def at(p, zz):
            return c+np.array((p[0]*math.cos(yaw)-p[1]*math.sin(yaw), p[0]*math.sin(yaw)+p[1]*math.cos(yaw), zz))
        uv = [(u0+(x-x0)/(x1-x0)*(u1-u0), y/F.TILE+v0) for x,y in top]
        F.face(model, F.WOOD, [at(p, lid_z+dz) for p in top], (0,0,1), uv)
        for i in range(len(outline)):
            j = (i+1) % len(outline)
            a, b = outline[i], outline[j]
            edge = np.asarray(b)-a
            if np.linalg.norm(edge) < 1e-7: continue
            expected = np.array((edge[1]*math.cos(yaw)+edge[0]*math.sin(yaw), edge[1]*math.sin(yaw)-edge[0]*math.cos(yaw), 0))
            F.face(model,F.DARK,[at(a,lid_z+dz-.12),at(b,lid_z+dz-.12),at(top[j],lid_z+dz),at(top[i],lid_z+dz)],expected)
    # A small bung, off-centre, reads as a working container rather than a table.
    bung = c+np.array((math.cos(yaw)*3, math.sin(yaw)*3, lid_z+.015))
    F.turned(model,bung,(0,0,1),(1,0,0),[(.58,-.06),(.62,.03),(.53,.10)],F.DARK,16,True,seed=seed+3)

    # Hoops hug the actual belly; bevels and slight hand-made height variation
    # catch light without making the iron look damaged or loose.
    for band, t in enumerate((.06,.22,.76,.91)):
        base_z = h*t
        def hoop_radius(zz, extra=0):
            return radius(float(np.clip(zz/h,0,1)),r)+.08+extra
        rr = hoop_radius(base_z+.78)
        phase = rng.uniform(0, math.tau)
        ring_profile = [(-.015,0),(.11,.055),(.15,.14),(.15,1.38),(.10,1.52),(-.015,1.58)]
        for (oa,za),(ob,zb) in zip(ring_profile,ring_profile[1:]):
            ra,rb=hoop_radius(base_z+za,oa),hoop_radius(base_z+zb,ob)
            for k in range(64):
                a,b = yaw+k*math.tau/64, yaw+(k+1)*math.tau/64
                wa,wb = .04*math.sin(a*3+phase), .04*math.sin(b*3+phase)
                p = [polar(a,hoop_radius(base_z+za+wa,oa),base_z+za+wa),polar(b,hoop_radius(base_z+za+wb,oa),base_z+za+wb),
                     polar(b,hoop_radius(base_z+zb+wb,ob),base_z+zb+wb),polar(a,hoop_radius(base_z+zb+wa,ob),base_z+zb+wa)]
                slope = K.normalise((zb-za, -(rb-ra)))
                na,nb = np.array((math.cos(a)*slope[0],math.sin(a)*slope[0],slope[1])),np.array((math.cos(b)*slope[0],math.sin(b)*slope[0],slope[1]))
                F.face(model,F.IRON,p,na+nb,normals=[na,nb,nb,na])
        # A small overlapping seam and rivets, facing a different way on each cask.
        angle = yaw+band*.23+.75
        normal = np.array((math.cos(angle),math.sin(angle),0))
        tangent = np.array((-normal[1],normal[0],0))
        F.bevel_box(model,polar(angle,rr+.20,base_z+.78),(tangent,normal,(0,0,1)),(.78,.13,1.46),F.IRON,.045)
        for zz in (.4,1.12): F.turned(model,polar(angle,rr+.28,base_z+zz),normal,tangent,[(.11,0),(.13,.035),(.10,.075)],F.IRON,8)
        # Restrained irregular oxide along two short stretches of each band.
        for patch in range(2):
            start = yaw+rng.uniform(0, math.tau)
            for k in range(5):
                a,b = start+k*.025,start+(k+1)*.025
                za = base_z+.10+rng.uniform(0,.10); zb = base_z+.35+rng.uniform(0,.20)
                F.face(model,'barrel_rust',[polar(a,hoop_radius(za,.153),za),polar(b,hoop_radius(za+.02,.153),za+.02),
                       polar(b,hoop_radius(zb,.153),zb),polar(a,hoop_radius(zb-.02,.153),zb-.02)],
                       (math.cos((a+b)/2),math.sin((a+b)/2),0))
    return model


def scan():
    hulls = read_hulls(ROOT/'Assets/models/maps/belltower/belltower_west_hulls_wood.obj')
    chosen = [r for r in hulls if len(r['indices']) == 20 and abs(r['height']-36)<.001
              and np.linalg.norm(np.asarray(r['centre'])-(-260,1160))<29]
    assert len(chosen) == 2, chosen
    chosen.sort(key=lambda p: np.linalg.norm(np.asarray(p['centre'])-(-260,1160)))
    rows = []
    for i,(row,new) in enumerate(zip(chosen,[(-419,1120),(-389,1119)])):
        rows.append({'old':list(row['centre']),'new':list(new),'z':row['z0'],'radius':13,'height':36,'seed':i+71})
    result = {'revision':'clock-building-barrels-v2','barrels':rows,
              'mirrored_east_pair':True,'reason':'Clear both ground-floor doors; store casks beneath adjacent windows.',
              'door_interval_e':[-288,-232],'closest_barrel_edge_e':-376,
              'minimum_lateral_door_clearance_inches':88,'back_wall_clearance_inches':3}
    SOURCE.parent.mkdir(parents=True,exist_ok=True)
    assert not SOURCE.exists()
    SOURCE.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result))


if __name__ == '__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--scan',action='store_true');args=parser.parse_args()
    if args.scan: scan()
