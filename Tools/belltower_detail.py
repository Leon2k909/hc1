"""Belltower's visible props and material choices. Gameplay collision remains in belltower_map.py.

Foliage uses the engine's oak/beech assets, with individual renderers for instancing and distance LOD.
Wood uses Poly Haven's CC0 brown_planks_03 (mounted by hc1.sbproj). The cobbles and flagstones are the project's scans
with dry roughness, and the walling stone, the parasols' canvas and the market's produce are drawn by
Tools/belltower_materials.py (materials/belltower/).

Round things (fruit, bars) carry a normal per point (Model.polygon's normals), so they shade smoothly instead of as
facets. A crate of produce is a low mound under a picture of the heaped fruit (belltower_materials.produce_pile), with a
few whole fruit loose on top, drawn with their kind's skin alone (produce_skin): the pile's picture carries each
fruit's roundness in its normals, which on a round fruit would count it twice.

The lamps are lit, as a town's are on a bright day: a lantern's panes, a dish lamp's bulb and the enamel inside its
shade are belltower_fronts' self-lit lamp pictures. Lanterns hang from wall brackets or stand on the street lamps' posts;
dish lamps hang from wires strung across the streets.
"""
import math
import numpy as np

from pathlib import Path

import belltower_materials as Materials
import belltower_finishes as Finishes
import belltower_fronts as Fronts

OAK = "models/sbox_props/trees/oak/tree_oak_small_a.vmdl"
OAK_BIG = "models/sbox_props/trees/oak/tree_oak_medium_a.vmdl"
BUSH = "models/sbox_props/shrubs/beech/beech_bush_small.vmdl"


OWN = Materials.RESOURCE_DIR

# Paint: the material it's drawn with, where that isn't building_textures' own.
MATERIALS = {
    "planks": "materials/wood/brown_planks_03.vmat",
    "planks_dark": "materials/wood/brown_planks_03.vmat",
    "setts": f"{OWN}/street_cobbles.vmat",
    "rubble": f"{OWN}/rubble.vmat",
    "ashlar": f"{OWN}/ashlar.vmat",
    "ashlar_grey": f"{OWN}/ashlar_grey.vmat",
    "flagstones": f"{OWN}/flagstones.vmat",
    "roof_tiles": "materials/stone/red_roof_tile.vmat",
    "parasol_red": f"{OWN}/parasol_red.vmat",
    "parasol_cream": f"{OWN}/parasol_cream.vmat",
    "parasol_blue": f"{OWN}/parasol_blue.vmat",
    **{f"produce_{kind}": f"{OWN}/produce_{kind}.vmat" for kind in Materials.PRODUCE},
    "produce_skin": f"{OWN}/produce_skin.vmat",
}
# The houses' lime render (belltower_finishes.PLASTERS). "whitewash" stays building_textures' flat whitewash for the
# rooms inside; an outside wall in whitewash is "render_white".
PLASTERS = {paint: f"{OWN}/{Finishes.plaster_paint(paint)}.vmat" for paint in Finishes.PLASTERS if paint != "whitewash"}
PLASTERS["render_white"] = f"{OWN}/plaster_whitewash.vmat"
MATERIALS.update(PLASTERS)

# The fronts' pictures (belltower_fronts): each drawn once across its own polygon (map_kit's decal paints).
FRONT_DECALS = (
    [f"louvre_{c}" for c in Fronts.LOUVRE_PAINTS] + [f"louvre_pair_{c}" for c in Fronts.LOUVRE_PAINTS]
    + [f"window_{k}" for k in "abcd"] + [f"shopfront_{k}" for k in "abc"] + [f"door_{k}" for k in "abcdefg"]
    + [f"sign_{k}" for k in range(len(Fronts.SIGNS))] + [f"letters_{k}" for k in range(len(Fronts.SIGNS))]
    + [f"geranium_{k}" for k in Fronts.GERANIUMS] + ["trailing", "ivy_climb", "ivy_hang", "bougainvillea"]
    + [f"chalkboard_{k}" for k in Fronts.CHALKBOARDS] + [f"plaque_{k}" for k in range(len(Fronts.PLAQUES))]
    + [f"banner_{k}" for k in Fronts.BANNERS] + [f"ghost_{k}" for k in range(len(Fronts.GHOSTS))]
    + ["lantern_glass", "lamp_bulb", "lamp_reflector"] + [f"insegna_{k}" for k in range(len(Fronts.INSEGNE))])
# Repeating along their run, with UVs given where they're built: railing bays, awning canvas and its valance.
FRONT_TILED = ["railing"] + [f"awning_{k}" for k in Fronts.AWNINGS] + [f"valance_{k}" for k in Fronts.AWNINGS]
MATERIALS.update({paint: f"{OWN}/{paint}.vmat" for paint in FRONT_DECALS + FRONT_TILED})
# World units a texture tile covers: the stone's own tiles (belltower_materials' RUBBLE_TILE, ASHLAR_TILE), the scans'
# real sizes. Parasols and produce are given their UVs, so theirs only stand in.
TILES = {"planks": 48, "planks_dark": 48, "setts": 64, "rubble": Materials.RUBBLE_TILE, "ashlar": Materials.ASHLAR_TILE,
         "ashlar_grey": Materials.ASHLAR_TILE, "flagstones": 96, "parasol_red": Materials.PARASOL_TILE,
         "parasol_cream": Materials.PARASOL_TILE, "parasol_blue": Materials.PARASOL_TILE,
         **{f"produce_{kind}": Materials.produce_tile(kind) for kind in Materials.PRODUCE}, "produce_skin": 12.0}
TILES["setts"] = Finishes.COBBLE_TILE
TILES.update({paint: Finishes.PLASTER_TILE for paint in PLASTERS})
# Decals are drawn once across their polygon whatever the tile; the rest are given their UVs.
TILES.update({paint: 64.0 for paint in FRONT_DECALS})
TILES.update({paint: 48.0 for paint in FRONT_TILED})


def configure(model, render=True):
    """ render: the render paints in lime plaster, its picture standing on z 0 (map_kit's anchored paints). The vista's
    farms keep building_textures' flat renders: they stand far below z 0, where the plaster's damp would float. """
    model.grain_paints.update(("planks", "planks_dark"))
    materials = MATERIALS if render else {p: m for p, m in MATERIALS.items() if p not in PLASTERS or p == "render_white"}
    model.material_overrides.update(materials)
    model.tile_overrides.update({p: t for p, t in TILES.items() if p in materials or p not in MATERIALS})
    model.anchored_paints = set(PLASTERS) if render else set()
    model.decal_paints = set(FRONT_DECALS)


def material_colour_file(paint, assets):
    """ The colour map a paint is drawn with, if it's one of Belltower's own (for the previews' flat colours). """
    path = MATERIALS.get(paint, "")
    if path.startswith(OWN + "/"):
        return assets / OWN / (Path(path).stem + "_color.png")
    return None


def instance(model, path, position, yaw, scale, name="Foliage"):
    model.props.append(dict(path=path, position=tuple(position), yaw=float(yaw), scale=tuple(scale), name=name))


def shrub(model, centre, radius, squash=0.8, seed=0):
    # Source bounds ~144 x 137 x 75; plant its roots in the bed, not on the crown's centre.
    rng = np.random.default_rng(seed)
    sx = radius * 2 / 144
    sz = radius * 2 * squash / 75
    p = np.asarray(centre, float) - (0, 0, radius * squash - 19.2 * sz)
    instance(model, BUSH, p, rng.uniform(0, 360), (sx, sx, sz), "Beech shrub")


def tree(model, centre, z, height, spread, seed, coarse=False):
    rng = np.random.default_rng(seed)
    large = height > 220
    width, top = (610, 703.73) if large else (304, 391.94)
    # Keep the existing crown's envelope, with some asymmetry from the authored branching.
    sx = spread * 2.8 / width
    sz = (height * .62 + spread * 1.27) / top
    instance(model, OAK_BIG if large else OAK, (*centre, z), rng.uniform(0, 360), (sx, sx, sz), "Oak tree")


def barrel(model, centre, z, r, h):
    # Coopered staves taper at either end; bands follow the belly instead of a ten-sided straight tube.
    c = np.asarray(centre, float)
    sides = 48
    levels = [(0, .84), (.035, .88), (.15, .94), (.38, 1), (.62, 1), (.85, .94), (.965, .88), (1, .84)]
    def point(k, zz, rr):
        a = 2 * math.pi * k / sides
        return (* (c + rr * np.array((math.cos(a), math.sin(a)))), z + zz)
    for (za, ra), (zb, rb) in zip(levels, levels[1:]):
        for k in range(sides):
            u0, u1 = k/sides*2*math.pi*r/48, (k+1)/sides*2*math.pi*r/48
            model.polygon("planks_dark", [point(k, za*h, ra*r), point(k+1, za*h, ra*r),
                                            point(k+1, zb*h, rb*r), point(k, zb*h, rb*r)],
                          uv=[(u0,za*h/48),(u1,za*h/48),(u1,zb*h/48),(u0,zb*h/48)])
    # Recessed wooden lid and a visible rim.
    model.cylinder(centre, r*.815, z+h-1.2, z+h-.6, {"top": "planks"}, sides=48)
    for zz, rr in ((.06, .9), (.22, .975), (.76, .975), (.91, .9)):
        band_ring(model, c, z + h*zz, r*rr, 1.6, .35, sides)


def band_ring(model, centre, z, radius, height, lip, sides):
    rings = [(z, radius), (z+.2, radius+lip), (z+height-.2, radius+lip), (z+height, radius)]
    for (za, ra), (zb, rb) in zip(rings, rings[1:]):
        for k in range(sides):
            a, b = 2*math.pi*k/sides, 2*math.pi*(k+1)/sides
            model.polygon("iron_black", [(centre[0]+ra*math.cos(a), centre[1]+ra*math.sin(a), za),
                (centre[0]+ra*math.cos(b), centre[1]+ra*math.sin(b), za),
                (centre[0]+rb*math.cos(b), centre[1]+rb*math.sin(b), zb),
                (centre[0]+rb*math.cos(a), centre[1]+rb*math.sin(a), zb)])


def wheel(model, p, side, axle):
    centre = p.at((-6, side*38, 24))
    # Open spokes and a 48-segment iron tyre. No broad plank-textured disk.
    def at(k, radius, offset):
        a = 2*math.pi*k/48
        return centre + p.x*(math.cos(a)*radius) + p.z*(math.sin(a)*radius) + p.y*offset
    def face(paint, points, outward):
        n = np.cross(points[1]-points[0], points[2]-points[0])
        model.polygon(paint, points if np.dot(n, outward) > 0 else points[::-1])
    for k in range(48):
        radial = at(k+.5, 1, 0) - centre
        for offset in (-2.5, 2.5):
            points = [at(k,20,offset), at(k+1,20,offset), at(k+1,24,offset), at(k,24,offset)]
            face("planks_dark", points, p.y*offset)
        face("iron_black", [at(k,24,-2.5), at(k+1,24,-2.5), at(k+1,24,2.5), at(k,24,2.5)], radial)
        face("planks_dark", [at(k,20,2.5), at(k+1,20,2.5), at(k+1,20,-2.5), at(k,20,-2.5)], -radial)
    for k in range(10):
        a = 2*math.pi*k/10
        end = centre + (p.x*math.cos(a) + p.z*math.sin(a))*21
        model.beam(centre, end, (2.2, 2.8), "planks_dark", up=p.y)
    axle(model, centre, p.y, 4.5, 9, {"side": "planks_dark", "end": "iron_black"}, sides=24)


def crate(model, p, size, paint):
    h = size/2
    # Boards have actual seams and thickness; battens cast shadows across them.
    rows = max(4, round(size/6))
    for row in range(rows):
        za, zb = row*size/rows+.12, (row+1)*size/rows-.12
        for side in (-1, 1):
            y = side*(h-.65)
            p.box(model, (-h, y-.65, za), (h, y+.65, zb), paint)
            x = side*(h-.65)
            p.box(model, (x-.65, -h+1.3, za), (x+.65, h-1.3, zb), paint)
    for k in range(rows):
        x0, x1 = -h+k*size/rows+.12, -h+(k+1)*size/rows-.12
        p.box(model, (x0,-h,size-1.3), (x1,h,size), paint)
    for s in (-1,1):
        for y in (-h-.6,h+.6):
            p.box(model, (s*h*.7-1.8,y-.6,0), (s*h*.7+1.8,y+.6,size), "planks_dark")


# ---------------------------------------------------------------------------------------------------------------------
# The café: bistro tables and chairs, and gored parasols

def local(origin, yaw):
    """ A frame at origin turned yaw degrees: ( at( ( x, y, z ) ), x axis, y axis ). """
    a = math.radians(yaw)
    x = np.array((math.cos(a), math.sin(a), 0.0))
    y = np.array((-math.sin(a), math.cos(a), 0.0))
    o = np.asarray(origin, float)
    return (lambda q: o + x*q[0] + y*q[1] + np.array((0.0, 0.0, q[2]))), x, y


def outward(model, paint, points, towards, uv=None, normals=None):
    """ A polygon wound to face towards (its UVs and normals following the points). """
    pts = [np.asarray(q, float) for q in points]
    n = np.zeros(3)
    for k in range(1, len(pts) - 1):
        n += np.cross(pts[k] - pts[0], pts[k+1] - pts[0])
    if np.linalg.norm(n) < 1e-9:
        return
    if np.dot(n, towards) < 0:
        order = [0] + list(range(len(pts) - 1, 0, -1))
        pts = [pts[i] for i in order]
        uv = None if uv is None else [uv[i] for i in order]
        normals = None if normals is None else [normals[i] for i in order]
    model.polygon(paint, pts, uv=uv, normals=normals)


def rod(model, a, b, r, paint, sides=8):
    """ A round bar from a to b, shaded smooth (a chair's leg, a parasol's pole). """
    a, b = np.asarray(a, float), np.asarray(b, float)
    axis = b - a
    length = np.linalg.norm(axis)
    axis /= length
    u = np.cross(axis, (0, 0, 1.0)) if abs(axis[2]) < 0.9 else np.cross(axis, (1.0, 0, 0))
    u /= np.linalg.norm(u)
    v = np.cross(axis, u)
    rim = [math.cos(2*math.pi*k/sides)*u + math.sin(2*math.pi*k/sides)*v for k in range(sides)]
    for k in range(sides):
        d0, d1 = rim[k], rim[(k+1) % sides]
        outward(model, paint, [a + r*d0, a + r*d1, b + r*d1, b + r*d0], d0 + d1, normals=[d0, d1, d1, d0])
    outward(model, paint, [b + r*d for d in rim], axis)


def bistro_table(model, centre, z=0.0, top="iron_green", frame="iron_black"):
    """ A round café table, 27 across and 29 high: a four-footed cast base, a column and a painted steel top with a
    rolled edge. Its collision is left to the caller. Returns the top's height. """
    c = np.array((centre[0], centre[1], z), float)
    for k in range(4):
        a = math.pi/4 + k*math.pi/2
        d = np.array((math.cos(a), math.sin(a), 0.0))
        model.beam(c + d*1.2 + (0, 0, 9), c + d*11 + (0, 0, 0.8), (1.6, 1.1), frame)
        model.cylinder(tuple(c[:2] + d[:2]*11), 1.4, z, z + 0.8, {"side": frame, "top": frame}, sides=8)
    model.cylinder(tuple(c[:2]), 2.4, z + 6, z + 10, {"side": frame, "top": frame}, sides=12)
    rod(model, c + (0, 0, 6), c + (0, 0, 27.4), 1.2, frame, sides=10)
    for k in range(4):
        a = k*math.pi/2
        d = np.array((math.cos(a), math.sin(a), 0.0))
        model.beam(c + (0, 0, 26.6), c + d*9 + (0, 0, 27.4), (0.8, 0.8), frame)
    model.cylinder(tuple(c[:2]), 13.5, z + 27.4, z + 29, {"side": top, "top": top, "bottom": top}, sides=32)
    model.cylinder(tuple(c[:2]), 13.8, z + 28.3, z + 29.2, {"side": top}, sides=32)
    return z + 29


def bistro_chair(model, centre, yaw, z=0.0, frame="iron_green", slats="planks"):
    """ A café chair facing yaw: a steel frame with splayed round legs, a seat of five wooden slats at 18 and a
    two-slat back raked a little. No collision. """
    at, x, y = local((centre[0], centre[1], z), yaw)
    h = 7.5
    for sx in (-1, 1):
        for sy in (-1, 1):
            rod(model, at((sx*(h + 1.2), sy*(h + 1.2), 0)), at((sx*h, sy*h, 17)), 0.45, frame, sides=6)
    for sy in (-1, 1):
        # The back legs carry on up as the back's uprights, raked back.
        rod(model, at((-h, sy*h, 17)), at((-h - 2.4, sy*(h - 0.6), 33)), 0.45, frame, sides=6)
    for a0, a1 in (((h, -h), (h, h)), ((-h, -h), (-h, h)), ((-h, -h), (h, -h)), ((-h, h), (h, h))):
        model.beam(at((*a0, 17)), at((*a1, 17)), (0.9, 0.9), frame)
        model.beam(at((a0[0]*1.1, a0[1]*1.1, 6)), at((a1[0]*1.1, a1[1]*1.1, 6)), (0.5, 0.5), frame)
    width = 2*h / 5
    for k in range(5):
        y0 = -h + k*width + 0.2
        # Front to back, rounded down over the front edge.
        corners = lambda xa, xb, za, zb: (at((xa, y0, za)), at((xb, y0 + width - 0.4, zb)))
        lo, hi = corners(-h - 0.4, h - 1.0, 17.45, 18.2)
        model.oriented_box((lo + hi)/2, (x, y, (0, 0, 1)), (2*h - 0.6, width - 0.4, 0.75), slats)
        nose = at((h - 0.4, y0 + (width - 0.4)/2, 17.5))
        model.oriented_box(nose, (x, y, (0, 0, 1)), (1.4, width - 0.4, 1.2), slats)
    for zb in (24.0, 30.0):
        t = (zb - 17)/16
        xb = -h - 2.4*t - 0.4
        for s0, s1 in ((-1, -0.35), (-0.35, 0.35), (0.35, 1)):
            # Curved round the sitter's back: three straight pieces.
            bow = lambda s: 1.2*(1 - s*s)
            a = at((xb + bow(s0), s0*(h - 0.6*t), zb))
            b = at((xb + bow(s1), s1*(h - 0.6*t), zb))
            model.beam(a, b, (0.6, 3.6), slats, up=(-x*0.25 + np.array((0, 0, 1.0))))


def parasol(model, centre, z_rim, z_top, radius, colours=("parasol_red", "parasol_cream"), gores=8, turn=0.0,
            pole_from=None, rib="planks_dark", pole="planks_dark"):
    """ A café parasol: gores of canvas stretched over ribs, each gore one colour (alternating colours), sagging a
    little between the ribs, a scalloped valance, the ribs and stretchers underneath and a pole up to a finial. The
    canvas is drawn both sides. pole_from: where the pole starts (a table's top); None stands it on the ground. No
    collision. """
    c = np.asarray(centre, float)
    z0 = c[2] if len(c) > 2 else 0.0
    c = c[:2]
    rise = z_top - z_rim
    tile = Materials.PARASOL_TILE
    crown = 2.5
    steps = (0.0, 0.3, 0.62, 1.0)
    sag = radius*0.035

    def radial(a):
        return np.array((math.cos(a), math.sin(a), 0.0))

    def on_rib(a, t):
        r = crown + (radius - crown)*t
        return np.array((*(c + r*radial(a)[:2]), z_top - rise*t**1.25))

    def on_mid(a0, a1, t):
        # Half way between two ribs, pulled in to the chord and down by the canvas's sag, most at the edge.
        p = (on_rib(a0, t) + on_rib(a1, t))/2
        return p - np.array((0, 0, sag*t**1.2))

    up = np.array((0, 0, 1.0))
    for g in range(gores):
        a0 = turn + 2*math.pi*g/gores
        a1 = turn + 2*math.pi*(g + 1)/gores
        paint = colours[g % len(colours)]
        width = 2*math.pi*radius/gores
        for t0, t1 in zip(steps, steps[1:]):
            for side, a in ((-1, a0), (1, a1)):
                quad = [on_mid(a0, a1, t0), on_rib(a, t0), on_rib(a, t1), on_mid(a0, a1, t1)]
                # UVs across the gore from its middle and down it, at the canvas's own scale.
                uv = []
                for k, q in enumerate(quad):
                    t = (t0, t0, t1, t1)[k]
                    across = side*(k in (1, 2))*width*(crown + (radius - crown)*t)/radius/2
                    uv.append((across/tile, -(t*math.hypot(radius, rise))/tile))
                out = up + 0.3*radial((a0 + a1)/2)
                outward(model, paint, quad, out, uv=uv)
                outward(model, paint, quad, -out, uv=uv)
        # The valance: a flap hanging from the edge, scalloped along its hem.
        rim0, rim_mid, rim1 = on_rib(a0, 1.0), on_mid(a0, a1, 1.0), on_rib(a1, 1.0)
        hem = []
        for k in range(5):
            s = k/4
            p = rim0 + (rim_mid - rim0)*2*s if s <= 0.5 else rim_mid + (rim1 - rim_mid)*(2*s - 1)
            hem.append((p, p - np.array((0, 0, 5.0 + 1.6*math.sin(math.pi*s)))))
        for k in range(4):
            quad = [hem[k][0], hem[k+1][0], hem[k+1][1], hem[k][1]]
            mid = (a0 + a1)/2
            uv = [(((k + (i in (1, 2)))/4)*width/tile, (-5.0 if i in (2, 3) else 0.0)/tile) for i in range(4)]
            outward(model, paint, quad, radial(mid), uv=uv)
            outward(model, paint, quad, -radial(mid), uv=uv)
        # The rib under the canvas, and its stretcher from the runner.
        model.beam(on_rib(a0, 0.02) - (0, 0, 0.6), on_rib(a0, 1.0) - (0, 0, 0.5), (0.7, 0.7), rib)
        runner = np.array((*c, z_top - 20))
        model.beam(runner + radial(a0)*1.3, on_rib(a0, 0.5) - (0, 0, 0.7), (0.5, 0.5), rib)
    # The crown's cap, the finial and the pole with its runner.
    cap = [np.array((*(c + 3.2*radial(turn + 2*math.pi*k/12)[:2]), z_top + 0.6)) for k in range(12)]
    outward(model, colours[0], cap, up)
    for k in range(12):
        q = [cap[k], cap[(k + 1) % 12], cap[(k + 1) % 12] - (0, 0, 1.2), cap[k] - (0, 0, 1.2)]
        outward(model, colours[0], q, radial(turn + 2*math.pi*(k + 0.5)/12))
    rod(model, (*c, z_top + 0.6), (*c, z_top + 4.5), 0.7, pole, sides=8)
    rod(model, (*c, z_top + 4.5), (*c, z_top + 6.0), 1.1, pole, sides=8)
    base = z0 if pole_from is None else pole_from
    rod(model, (*c, base), (*c, z_top), 1.0, pole, sides=10)
    rod(model, (*c, z_top - 22), (*c, z_top - 18), 1.8, pole, sides=10)


# ---------------------------------------------------------------------------------------------------------------------
# The market's produce

PRODUCE = list(Materials.PRODUCE)


def fruit(model, centre, kind, rng, below=2.3):
    """ One whole fruit lying on the heap: a squashed ball down to below radians from its top (the rest is in the
    heap), 12 around, shaded smooth, mapped from above onto its kind's square of produce_skin. """
    radius, squash, aspect = Materials.PRODUCE[kind]
    r = radius*rng.uniform(0.95, 1.05)
    around, rings = 12, 5
    c = np.asarray(centre, float)
    spin = rng.uniform(0, 2*math.pi)
    uc, vc, hu, hv = Materials.skin_window(kind)
    bumps = 1.0 + 0.03*rng.standard_normal((rings + 1, around))

    def point(i, j):
        polar = below*i/rings
        a = 2*math.pi*j/around
        k = bumps[i, j % around] if i else 1.0
        lx, ly, lz = math.sin(polar)*math.cos(a), math.sin(polar)*math.sin(a), math.cos(polar)
        # Long ways along the fruit's own x, turned by spin.
        x0, y0 = lx*aspect, ly
        px, py = x0*math.cos(spin) - y0*math.sin(spin), x0*math.sin(spin) + y0*math.cos(spin)
        pos = c + r*k*np.array((px, py, lz*squash))
        nx0, ny0 = lx/aspect, ly
        normal = np.array((nx0*math.cos(spin) - ny0*math.sin(spin), nx0*math.sin(spin) + ny0*math.cos(spin), lz/squash))
        # Planar from above; past the equator the skin folds back over itself.
        s_ = math.sin(polar)
        return pos, normal/np.linalg.norm(normal), (uc + hu*s_*math.cos(a), vc + hv*s_*math.sin(a))

    top = point(0, 0)
    for j in range(around):
        p1, p2 = point(1, j), point(1, j + 1)
        outward(model, "produce_skin", [top[0], p1[0], p2[0]], top[1] + p1[1] + p2[1], uv=[top[2], p1[2], p2[2]],
                normals=[top[1], p1[1], p2[1]])
    for i in range(1, rings):
        for j in range(around):
            q = [point(i, j), point(i + 1, j), point(i + 1, j + 1), point(i, j + 1)]
            outward(model, "produce_skin", [p for p, _, _ in q], sum(n for _, n, _ in q), uv=[t for _, _, t in q],
                    normals=[n for _, n, _ in q])


def produce_crate(model, centre, yaw, kind, rng, z=0.0, width=26.0, depth=20.0, wall=5.5, paint="planks",
                  post="planks_dark", loose=None):
    """ A shallow open crate of loose boards, heaped with one kind of produce: a mound a little over the rim under the
    heap's picture (its own normals give the fruit their shape), and loose whole fruit on top. No collision (it stands
    on the stall's counter). """
    at, x, y = local((centre[0], centre[1], z), yaw)
    axes = (x, y, np.array((0, 0, 1.0)))
    w, d = width/2, depth/2

    def board(lo, hi, p=paint):
        lo, hi = np.asarray(lo, float), np.asarray(hi, float)
        model.oriented_box(at((lo + hi)/2), axes, hi - lo, p)

    board((-w, -d, 0), (w, d, 0.6))
    for za, zb in ((0.6, 2.9), (3.3, wall)):
        for sy in (-1, 1):
            board((-w, sy*d - 0.3, za), (w, sy*d + 0.3, zb))
        for sx in (-1, 1):
            board((sx*w - 0.3, -d + 0.3, za), (sx*w + 0.3, d - 0.3, zb))
    for sx in (-1, 1):
        for sy in (-1, 1):
            board((sx*(w - 0.7) - 0.7, sy*(d - 0.7) - 0.7, 0.6), (sx*(w - 0.7) + 0.7, sy*(d - 0.7) + 0.7, wall + 0.3), post)

    radius, squash, _ = Materials.PRODUCE[kind]
    tile = Materials.produce_tile(kind)
    paint_heap = f"produce_{kind}"
    rim = wall - 0.6
    peak = min(2.2, 0.9*radius)
    iw, idepth = w - 0.3, d - 0.3

    def heap(lx, ly):
        """ The mound's height and its normal's slope over the crate's floor. """
        fx, fy = 1 - (lx/iw)**2, 1 - (ly/idepth)**2
        return rim + peak*fx*fy, np.array((-peak*(-2*lx/iw**2)*fy, -peak*fx*(-2*ly/idepth**2), 1.0))

    off = rng.uniform(0, 1, 2)
    nx, ny = 8, 6
    # Heaped by hand, not smoothed: each inner point a little up or down.
    lumps = rng.uniform(-0.35, 0.35, (ny + 1, nx + 1))*min(1.0, radius/1.6)
    lumps[[0, -1], :] = lumps[:, [0, -1]] = 0.0
    gx, gy = np.linspace(-iw, iw, nx + 1), np.linspace(-idepth, idepth, ny + 1)
    heights = np.array([[heap(lx, ly)[0] for lx in gx] for ly in gy]) + lumps
    # Its normals from the heights' slopes, so the lumps shade too.
    slope_y, slope_x = np.gradient(heights, gy, gx)
    for j in range(ny):
        for i in range(nx):
            pts, normals, uvs = [], [], []
            for jj, ii in ((j, i), (j, i + 1), (j + 1, i + 1), (j + 1, i)):
                lx, ly = gx[ii], gy[jj]
                pts.append(at((lx, ly, heights[jj, ii])))
                n = -x*slope_x[jj, ii] - y*slope_y[jj, ii] + np.array((0, 0, 1.0))
                normals.append(n/np.linalg.norm(n))
                uvs.append((off[0] + lx/tile, off[1] + ly/tile))
            outward(model, paint_heap, pts, (0, 0, 1.0), uv=uvs, normals=normals)
    # A handful loose on top, a few more of the small ones, none touching.
    placed = []
    for _ in range(40):
        if len(placed) >= (loose if loose is not None else min(6, round(14/radius))):
            break
        lx, ly = rng.uniform(-0.62, 0.62)*iw, rng.uniform(-0.62, 0.62)*idepth
        if any(math.hypot(lx - ox, ly - oy) < 2.4*radius for ox, oy in placed):
            continue
        placed.append((lx, ly))
        # On the lumped mound: its corners' heights, blended across the quad it's in.
        fi, fj = (lx + iw)/(2*iw)*nx, (ly + idepth)/(2*idepth)*ny
        i0, j0 = min(int(fi), nx - 1), min(int(fj), ny - 1)
        ti, tj = fi - i0, fj - j0
        q = heights[j0:j0 + 2, i0:i0 + 2]
        hz = (q[0, 0]*(1 - ti) + q[0, 1]*ti)*(1 - tj) + (q[1, 0]*(1 - ti) + q[1, 1]*ti)*tj
        fruit(model, at((lx, ly, hz + radius*squash*0.35)), kind, rng)


# ---------------------------------------------------------------------------------------------------------------------
# Lamps: lanterns on brackets and posts, dish lamps on wires, and the cafés' A-frame boards

LANTERN_HANG = 20.35    # a hanging lantern's ring top over its tray's underside, at scale 1


def ball(model, centre, r, paint, rings=5, segments=10):
    """ A sphere shaded smooth (a finial, a bulb). """
    c = np.asarray(centre, float)

    def d(i, k):
        t, a = math.pi*i/rings, 2*math.pi*k/segments
        return np.array((math.sin(t)*math.cos(a), math.sin(t)*math.sin(a), math.cos(t)))
    for i in range(rings):
        for k in range(segments):
            ds = [d(i, k), d(i, k + 1), d(i + 1, k + 1), d(i + 1, k)]
            if i == 0:
                ds = [ds[0], ds[2], ds[3]]
            elif i == rings - 1:
                ds = ds[:3]
            outward(model, paint, [c + r*q for q in ds], sum(ds), normals=ds)


def hoop(model, centre, u, v, radius, r, paint, segments=10):
    """ A ring of round bar in the plane of u and v (a lantern's ring, a bracket's scroll). """
    c, u, v = np.asarray(centre, float), np.asarray(u, float), np.asarray(v, float)
    pts = [c + radius*(math.cos(2*math.pi*k/segments)*u + math.sin(2*math.pi*k/segments)*v) for k in range(segments)]
    for k in range(segments):
        rod(model, pts[k], pts[(k + 1) % segments], r, paint, sides=5)


def frustum(model, P, h0, z0, h1, z1, paint, caps=(True, True)):
    """ A square frustum in a frame P( x, y, z ): half-width h0 at z0 to h1 at z1, its ends drawn where caps says. """
    corners = ((1, 1), (-1, 1), (-1, -1), (1, -1))
    c0 = [P(sx*h0, sy*h0, z0) for sx, sy in corners]
    c1 = [P(sx*h1, sy*h1, z1) for sx, sy in corners]
    m0, m1 = P(0, 0, z0), P(0, 0, z1)
    for k in range(4):
        q = [c0[k], c0[(k + 1) % 4], c1[(k + 1) % 4], c1[k]]
        outward(model, paint, q, sum(q)/4 - (m0 + m1)/2)
    if caps[0]:
        outward(model, paint, c0, m0 - m1)
    if caps[1]:
        outward(model, paint, c1, m1 - m0)


def lantern(model, origin, yaw=0.0, scale=1.0, hanging=True, iron="iron_black", glass="lantern_glass"):
    """ A lantern: four tapered panes of lit glass (belltower_fronts' lantern_glass) between iron corner posts, on a
    tray over an inverted pyramid, under a band, an eaved hipped cap and a chimney. 10.6 wide at its eave and 24 tall
    hanging, at scale 1. origin: the tray's underside. hanging: a ring on top to hang it by (LANTERN_HANG over origin)
    and a drop finial under it; else a ball finial on top, to stand on a post. No collision. Returns its top. """
    at, _, _ = local(origin, yaw)
    s = scale

    def P(x, y, z):
        return at((x*s, y*s, z*s))
    frustum(model, P, 1.4, -1.4, 4.2, 0.0, iron, caps=(True, False))
    frustum(model, P, 4.6, 0.0, 4.6, 1.0, iron)
    b, t, z0, z1 = 3.4, 4.25, 1.0, 11.0
    for k in range(4):
        a = k*math.pi/2
        d, r = np.array((math.cos(a), math.sin(a))), np.array((-math.sin(a), math.cos(a)))
        pts = [P(*(d*b - r*b), z0), P(*(d*b + r*b), z0), P(*(d*t + r*t), z1), P(*(d*t - r*t), z1)]
        outward(model, glass, pts, P(*d, 0) - P(0, 0, 0), uv=[(0, 0), (1, 0), (1, 1), (0, 1)])
        c = np.array((math.cos(a + math.pi/4), math.sin(a + math.pi/4)))*math.sqrt(2)
        model.beam(P(*(c*b), z0), P(*(c*t), z1), (0.7*s, 0.7*s), iron)
    frustum(model, P, 4.45, 11.0, 4.45, 12.0, iron)
    frustum(model, P, 5.3, 12.0, 5.3, 12.45, iron)
    frustum(model, P, 5.0, 12.45, 1.3, 15.4, iron, caps=(False, True))
    frustum(model, P, 1.1, 15.4, 1.1, 16.6, iron, caps=(False, False))
    frustum(model, P, 1.7, 16.6, 1.7, 17.0, iron)
    if hanging:
        rod(model, P(0, 0, -1.4), P(0, 0, -2.6), 0.32*s, iron, sides=6)
        ball(model, P(0, 0, -3.2), 0.75*s, iron)
        rod(model, P(0, 0, 17.0), P(0, 0, 18.1), 0.3*s, iron, sides=6)
        hoop(model, P(0, 0, 19.1), P(1, 0, 0) - P(0, 0, 0), np.array((0, 0, 1.0))*s, 1.0, 0.25*s, iron)
        return P(0, 0, LANTERN_HANG)
    ball(model, P(0, 0, 17.9), 0.9*s, iron)
    rod(model, P(0, 0, 18.8), P(0, 0, 20.0), 0.25*s, iron, sides=6)
    return P(0, 0, 20.0)


def hanging_lantern(model, hook, yaw=0.0, scale=1.0, **kw):
    """ A lantern hanging by its ring from hook. """
    return lantern(model, np.asarray(hook, float) - (0, 0, LANTERN_HANG*scale), yaw, scale, True, **kw)


def dish_lamp(model, hook, scale=1.0, shade="iron_black", inside="lamp_reflector", bulb="lamp_bulb", sides=16):
    """ A street lamp hung from its wire: an enamelled dish shade on a drop rod, white and lit inside, a bare bulb under
    its socket. 18 across, hook: where it hangs. No collision. Returns the bulb's centre. """
    h, s = np.asarray(hook, float), scale
    rod(model, h, h - (0, 0, 5.2*s), 0.3*s, shade, sides=6)
    # The shade's profile ( r, z under the hook ), flaring out to a rolled rim.
    profile = [(2.2, -5.0), (4.6, -6.4), (7.0, -8.0), (8.6, -9.2), (9.0, -9.7)]
    rim = []
    for r, z in profile:
        rim.append([np.array((math.cos(2*math.pi*k/sides), math.sin(2*math.pi*k/sides), 0.0)) for k in range(sides)])
    normals = []
    for i, (r, z) in enumerate(profile):
        (ra, za), (rb, zb) = profile[max(i - 1, 0)], profile[min(i + 1, len(profile) - 1)]
        n = np.array((-(zb - za), rb - ra))
        normals.append(n/np.linalg.norm(n))
    for i in range(len(profile) - 1):
        (r0, z0), (r1, z1) = profile[i], profile[i + 1]
        for k in range(sides):
            a, b = rim[i][k], rim[i][(k + 1) % sides]
            q = [h + (a*r0 + (0, 0, z0))*s, h + (b*r0 + (0, 0, z0))*s, h + (b*r1 + (0, 0, z1))*s, h + (a*r1 + (0, 0, z1))*s]
            n0, n1 = normals[i], normals[i + 1]
            ns = [a*n0[0] + (0, 0, n0[1]), b*n0[0] + (0, 0, n0[1]), b*n1[0] + (0, 0, n1[1]), a*n1[0] + (0, 0, n1[1])]
            outward(model, shade, q, sum(ns), normals=ns)
            outward(model, inside, q, -sum(ns), normals=[-n for n in ns])
    top = [h + (rim[0][k]*profile[0][0] + (0, 0, profile[0][1]))*s for k in range(sides)]
    outward(model, shade, top, (0, 0, 1.0))
    rod(model, h + (0, 0, -5.0*s), h + (0, 0, -7.2*s), 1.1*s, shade, sides=8)
    centre = h + (0, 0, -8.5*s)
    ball(model, centre, 1.5*s, bulb, rings=4, segments=8)
    return centre


def wire(model, a, b, sag, paint="iron_black", thick=0.45, segments=10):
    """ A wire from a to b sagging sag at its middle, as thin bars. """
    a, b = np.asarray(a, float), np.asarray(b, float)
    pts = [a + (b - a)*t - np.array((0, 0, 4*sag*t*(1 - t))) for t in np.linspace(0, 1, segments + 1)]
    for p, q in zip(pts, pts[1:]):
        model.beam(p, q, (thick, thick), paint)


def sandwich_board(model, centre, yaw, picture, z=0.0, frame="planks_dark"):
    """ An A-frame chalkboard on the pavement: two 24 x 36 boards hinged at the top and 16 apart at the foot, each
    showing picture (belltower_fronts' chalkboard_<k>, its own frame drawn in) on its outer face, the front one
    facing yaw. No collision. """
    at, x, _ = local((centre[0], centre[1], z), yaw)
    foot, top, height = 8.0, 0.9, 35.0
    for side in (-1, 1):
        p0, p1 = at((side*foot, 0, 0)), at((side*top, 0, height))
        model.beam(p0, p1, (24.0, 1.2), frame)
        along = (p1 - p0)/np.linalg.norm(p1 - p0)
        out = side*x*height/math.hypot(height, foot - top) + np.array((0, 0, (foot - top)/math.hypot(height, foot - top)))
        out = out/np.linalg.norm(out)
        y = np.cross(out, along)
        f = 0.7
        pts = [p0 + out*f - y*12, p0 + out*f + y*12, p1 + out*f + y*12, p1 + out*f - y*12]
        outward(model, picture, pts, out)
    rod(model, at((0, -12.5, height + 0.4)), at((0, 12.5, height + 0.4)), 0.5, "iron_black", sides=6)


def lathe(model, centre, z, profile, paint, sides=12, caps=(False, False), turn=0.0):
    """ A turned shape about a vertical axis through centre: profile [ ( r, height over z ) ] from the bottom up (no
    radius of 0), shaded smooth round and faceted along it. caps: close its bottom and top. """
    c = np.array((centre[0], centre[1], z), float)
    rim = [np.array((math.cos(turn + 2*math.pi*k/sides), math.sin(turn + 2*math.pi*k/sides), 0.0)) for k in range(sides)]

    def p(d, r, h):
        return c + d*r + (0, 0, h)
    for (r0, h0), (r1, h1) in zip(profile, profile[1:]):
        n = np.array((h1 - h0, -(r1 - r0)), dtype=float)
        if np.linalg.norm(n) < 1e-9:
            continue
        n /= np.linalg.norm(n)
        for k in range(sides):
            a, b = rim[k], rim[(k + 1) % sides]
            na, nb = a*n[0] + (0, 0, n[1]), b*n[0] + (0, 0, n[1])
            outward(model, paint, [p(a, r0, h0), p(b, r0, h0), p(b, r1, h1), p(a, r1, h1)], na + nb,
                    normals=[na, nb, nb, na])
    for cap, (r, h), up in ((caps[0], profile[0], -1.0), (caps[1], profile[-1], 1.0)):
        if cap:
            outward(model, paint, [p(d, r, h) for d in rim], (0, 0, up))


def street_lamp(model, centre, z=0.0, iron="iron_black"):
    """ A cast-iron street lamp 147 tall: an octagonal plinth and a moulded base, a tapering column with two collars, a
    capital with four brackets curving up under a lantern (scale 1.5) standing on it. Drawn only: belltower_map gives it
    a plain base and shaft to collide with. """
    e, n = centre
    lathe(model, centre, z, [(7.6, 0.0), (7.6, 3.0), (6.9, 3.8)], iron, sides=8, caps=(False, True), turn=math.pi/8)
    lathe(model, centre, z, [(6.6, 3.8), (6.6, 5.6), (5.7, 7.0), (5.0, 9.4), (5.0, 12.8), (5.9, 13.8), (5.9, 15.2),
                             (4.7, 16.4), (4.1, 18.8), (3.5, 21.4), (3.5, 22.8), (2.7, 23.8), (2.3, 104.0)], iron)
    for h in (34.0, 66.0):
        lathe(model, centre, z, [(2.6, h), (3.3, h + 0.6), (3.3, h + 2.0), (2.6, h + 2.6)], iron)
    lathe(model, centre, z, [(2.3, 104.0), (3.3, 104.8), (3.3, 106.2), (2.5, 107.0), (2.5, 109.0), (3.1, 110.6),
                             (4.2, 113.2), (4.4, 114.4), (3.6, 115.0)], iron, caps=(False, True))
    base = np.array((e, n, z), float)
    for k in range(4):
        a = k*math.pi/2
        d = np.array((math.cos(a), math.sin(a), 0.0))
        p0, p1, p2 = base + d*2.4 + (0, 0, 100.0), base + d*5.6 + (0, 0, 108.0), base + d*6.4 + (0, 0, 116.4)
        rod(model, p0, p1, 0.45, iron, sides=6)
        rod(model, p1, p2, 0.45, iron, sides=6)
        ball(model, p1, 0.75, iron, rings=3, segments=6)
    lantern(model, (e, n, z + 117.0), 0.0, 1.5, False, iron=iron)
