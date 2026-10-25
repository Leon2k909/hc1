"""Belltower's carved limestone bell fountain; authored geometry, in plan inches.

The basin retains the original 114-inch radius and 30-inch cover height. Small
carvings and water are visual only; the masonry carries simple stone collision.
"""
import math
from io import BytesIO

import numpy as np
from PIL import Image

import map_kit as K
import belltower_detail as D
import belltower_materials as M
import belltower_fountain_water as Water
import belltower_fountain_ornaments as Ornaments
import belltower_stone_wear as StoneWear
import belltower_bell as Bell

STONE = "fountain_limestone"
RELIEF = "fountain_relief"
BRONZE = "fountain_bronze"
WATER = "fountain_water"
JET = "fountain_jet"


def materials(centre=(0., 130.)):
    """Seamless cut stone, aged bronze and rippled water, without masonry joints."""
    folder = K.ASSETS / "materials/belltower"
    folder.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(731)
    size = 512

    def noise(grid):
        a = rng.integers(0, 256, (grid, grid), dtype=np.uint8)
        return np.asarray(Image.fromarray(a).resize((size, size), Image.Resampling.BICUBIC), float) / 255 - .5

    broad, grain, pores = noise(12), noise(80), noise(size)
    height = broad * .25 + grain * .08 + pores * .035
    stone = np.clip(np.array((181, 173, 151)) + (broad * 30 + grain * 16 + pores * 12)[..., None], 0, 255)
    bronze = np.clip(np.array((139, 103, 55)) + broad[..., None] * 38 + grain[..., None] * 16, 0, 255)
    y, x = np.mgrid[:size, :size] * (2 * math.pi / size)
    waves = np.sin(x * 13 + np.sin(y * 7)) + .4 * np.cos(y * 19 + x * 5)
    water = np.clip(np.array((39, 91, 96)) + waves[..., None] * 5, 0, 255)

    def save(name, array):
        if array.ndim == 2:
            array = np.repeat(array[..., None], 3, axis=2)
        out = BytesIO()
        Image.fromarray(np.clip(array, 0, 255).astype(np.uint8)).save(out, format="PNG")
        path = folder / name
        data = out.getvalue()
        if not path.exists() or path.read_bytes() != data:
            path.write_bytes(data)

    for name, colour, h, rough, metal in (
        (STONE, stone, height, 205 + grain * 30, 0),
        (BRONZE, bronze, height * .3, 135 + grain * 35, .8),
        (WATER, water, waves * .05, np.full((size, size), 35), 0),
        (JET, np.clip(np.array((167, 203, 205)) + waves[..., None] * 16, 0, 255), waves * .025, np.full((size, size), 45), 0),
    ):
        save(f"{name}_color.png", colour)
        save(f"{name}_normal.png", (M.gl_normal(h, size / 48) * .5 + .5) * 255)
        save(f"{name}_rough.png", rough)
        text = M.vmat(f"{M.RESOURCE_DIR}/{name}_color.png", f"{M.RESOURCE_DIR}/{name}_normal.png",
                      f"{M.RESOURCE_DIR}/{name}_rough.png", "materials/default/default_ao.tga")
        text = text.replace('g_flMetalness "0.00"', f'g_flMetalness "{metal:.2f}"')
        if name in (WATER, JET):
            text = Water.material_definitions(centre)[name]
        K.write_text(folder / f"{name}.vmat", text)
    text = (folder / f"{STONE}.vmat").read_text().replace(
        'g_vColorTint "[1.0 1.0 1.0 1.0]"', 'g_vColorTint "[0.72 0.70 0.67 1.0]"')
    K.write_text(folder / f"{RELIEF}.vmat", text)
    Bell.materials()


def build(model, centre, ring):
    materials(centre)
    for paint in (STONE, RELIEF, BRONZE, WATER, JET):
        model.material_overrides[paint] = f"{M.RESOURCE_DIR}/{paint}.vmat"
        model.tile_overrides[paint] = 48 if paint in (STONE, RELIEF, BRONZE) else 96
    e, n = centre
    up = np.array((0., 0., 1.))

    def box(half, z0, z1, paint=STONE, solid=True):
        StoneWear.fountain_block(model, centre, half, z0, z1, paint, "default" if solid else None)

    def face_frame(angle, radius):
        out = np.array((math.cos(angle), math.sin(angle), 0.))
        along = np.array((-out[1], out[0], 0.))
        origin = np.array((e, n, 0.)) + radius*out
        return lambda x, d, z: origin + along*x + out*d + up*z, along, out

    def trim(P, x0, x1, z0, z1, depth=1.1):
        model.beam(P(x0, depth, z0), P(x1, depth, z1), (1.3, 1.3), STONE)

    def fleur(P, z, scale):
        Ornaments.lily(model, P, z, scale)

    # Octagonal basin, stepped plinth, projecting coping and framed carved panels.
    paints = {"outside": STONE, "inside": STONE, "top": STONE}
    StoneWear.fountain_rings(model, centre, ring, "default")
    Water.pool(model, centre)
    model.cylinder(centre, 96, 3, 4, {"top": STONE}, sides=8, turn=math.pi/8)
    for k in range(8):
        P, _, _ = face_frame(k*math.pi/4 + math.pi/4, 114*math.cos(math.pi/8))
        for x in (-37, 37):
            trim(P, x, x, 6, 25)
        for z in (7, 24):
            trim(P, -37, 37, z, z)
        fleur(P, 13, .65)

    # Square monument with recessed-looking panels between projecting mouldings.
    for half, z0, z1 in ((35, 0, 24), (32, 24, 29), (27, 29, 62), (31, 62, 67),
                         (27, 67, 109), (30, 109, 113), (33, 113, 119), (31, 119, 123)):
        box(half, z0, z1)
    for k in range(4):
        P, along, out = face_frame(k*math.pi/2, 27)
        for x in (-23, 23):
            trim(P, x, x, 70, 106)
        for z in (71, 105):
            trim(P, -23, 23, z, z)
        fleur(P, 83, 1.25)
        Ornaments.lion(model, P)
        Water.spout(model, P, along, out, k)

    # Four moulded columns, fluted shafts and capitals around an open bell cage.
    for se in (-1, 1):
        for sn in (-1, 1):
            c = (e+se*24, n+sn*24)
            D.lathe(model, c, 123, [(8,0), (8,3), (6.5,4), (6.5,6), (5,8), (4.8,48),
                                  (6,50), (7,52), (7,56)], STONE, sides=16, caps=(True,True))
            model.cylinder(c, 5, 123, 179, STONE, sides=12, surface="default")
            for j in range(10):
                a = j*math.pi/5
                D.rod(model, (c[0]+4.7*math.cos(a), c[1]+4.7*math.sin(a), 132),
                      (c[0]+4.7*math.cos(a), c[1]+4.7*math.sin(a), 170), .55, STONE, sides=5)
            model.box((c[0]-8,c[1]-8,175), (c[0]+8,c[1]+8,179), STONE, "default")

    # Separate voussoirs form true open arches on each face, rather than flat cards.
    for k in range(4):
        P, _, out = face_frame(k*math.pi/2, 24)
        for j in range(11):
            a0, a1 = j*math.pi/11+.009, (j+1)*math.pi/11-.009
            profile = [(r*math.cos(a), 176+r*math.sin(a)) for r,a in
                       ((16,a0), (23,a0), (23,a1), (16,a1))]
            front = [P(x, 4, z) for x,z in profile]
            back = [P(x, -4, z) for x,z in profile]
            D.outward(model, STONE, front, out)
            D.outward(model, STONE, back, -out)
            for i in range(4):
                ii = (i+1)%4
                model.polygon(STONE, [front[i], back[i], back[ii], front[ii]])
            model.hull(front+back, "default")

    box(32, 199, 203)
    box(35, 203, 207)
    # Shallow hipped terracotta roof, with individually modelled ridge tiles.
    D.frustum(model, lambda x,y,z: np.array((e+x,n+y,z)), 37, 207, 3, 226, "roof_tiles")
    for k in range(4):
        P, _, _ = face_frame(math.pi/4+k*math.pi/2, 0)
        for t in np.linspace(.12, .94, 9):
            D.rod(model, P(0, 49*t-2, 226-19*t), P(0, 49*t+3, 224-19*t), 1.7, "roof_tiles", sides=8)
    D.ball(model, (e,n,227), 3.2, STONE)

    # A hollow bronze bell on its timber yoke, with crown loops and visible clapper.
    model.beam((e-22,n,190), (e+22,n,190), (5,6), "planks_dark")
    Bell.build(model, centre)
