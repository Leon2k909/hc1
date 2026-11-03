"""Riverdale's first aid cabinet v2: build, bake and export. Uses the capture flag's mesh toolkit.

blender -b --factory-startup -t 4 --python first_aid.py -- <work dir> <project root> <build|bake|export> ...

A wall-hung steel first aid cabinet in place of a painted block with a picture on it: a folded enamel case on four mounting tabs, a hinged door with a seal in its gap, a piano hinge, pressed louvres,
a riveted sign plate, and below it a lock, a quarter-turn handle, a small rating plate, a red tamper seal and an inspection tag. It covers the old 14 x 17 x 5 box. Inches. +X is out of the wall, the door's
front faces it, Y runs to the right as you face it, Z is up, and the origin is on the wall at the case's foot. It goes at z 54 in the hall.
"""
import hashlib
import json
import math
import os
import sys

sys.dont_write_bytecode = True
import bmesh
import bpy
import numpy as np
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1 :]
WORK, ROOT = argv[0], argv[1]
STAGES = argv[2:]
os.makedirs(WORK, exist_ok=True)
sys.path.insert(0, os.path.join(ROOT, "Sources", "Gameplay", "capture-flag-v2"))
import build as kit  # noqa: E402

from build import Part, add, tube  # noqa: E402

ENAMEL, ZINC, BRASS, RUBBER, PLATE = kit.PAINT, kit.ZINC, kit.BRASS, kit.RUBBER, kit.PLATE
RATING, SEAL, TAG = 9, 12, 13
FOLDER = "models/maps/riverdale/first_aid_v2"
OUT = os.path.join(ROOT, "Assets", "models", "maps", "riverdale", "first_aid_v2")
BLEND = os.path.join(WORK, "first_aid_build.blend")
NAME = "first_aid"
W, H = 2048, 2048
POS_RANGE = 64.0  # The position bake spans this many inches.
HY, Z0, Z1, BODY, DOOR = 7.06, -0.05, 17.05, 4.3, 5.12
SIGN_Y0, SIGN_Y1, SIGN_Z0, SIGN_Z1, SIGN_T = -6.45, 6.45, 3.95, 16.6, 0.05
LOCK_Y, LOCK_Z = 4.2, 1.95
RATING_Y0, RATING_Y1, RATING_Z0, RATING_Z1 = -6.1, -2.3, 1.35, 2.55
rng = np.random.default_rng(1928)
edge_lines = []
NO_EDGE = ("hinge", "string", "seal", "cylinder", "rose")


def piece(finish, lod, bevel=0.0, segs=1, angle=35.0, name=""):
    return add(Part(finish, lod, bevel=bevel, segs=segs, angle=angle, name=name))


def on_door(y, z, x=DOOR):
    """Local x along +Y, local y up, local z out of the door."""
    return kit.frame((x, y, z), (1, 0, 0), (0, 1, 0))


def rounded(hw, hh, r, per=5):
    outline = []
    for cx, cy, a0 in ((hw - r, -hh + r, -90), (hw - r, hh - r, 0), (-hw + r, hh - r, 90), (-hw + r, -hh + r, 180)):
        for k in range(per + 1):
            a = math.radians(a0 + 90.0 * k / per)
            outline.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return outline


def rivet(y, z, x, size=0.2, lod=0):
    profile = [(size, 0.0), (size, size * 0.1), (size * 0.72, size * 0.34), (0, size * 0.42)]
    kit.lathe(piece(ZINC, lod, name="rivet"), profile, 10, kit.frame((x, y, z), (1, 0, 0)))


def case():
    kit.box(piece(ENAMEL, 3, bevel=0.05, angle=40, name="case"), (0.0, -HY, Z0), (BODY, HY, Z1))
    kit.box(piece(ENAMEL, 3, bevel=0.15, segs=2, angle=40, name="door"), (4.37, -7.03, -0.02), (DOOR, 7.03, 17.02))
    kit.box(piece(RUBBER, 2, name="door seal"), (4.26, -6.96, 0.05), (4.4, 6.96, 16.95))
    # The mounting tabs, flat on the wall, each with its anchor.
    for y in (-4.6, 4.6):
        for lo, hi, z in ((Z1 - 0.05, Z1 + 1.15, Z1 + 0.62), (Z0 - 1.15, Z0 + 0.05, Z0 - 0.62)):
            kit.box(piece(ENAMEL, 2, bevel=0.03, angle=40, name="tab"), (0.0, y - 1.05, lo), (0.11, y + 1.05, hi))
            kit.hex_bolt((0.11, y, z), (1, 0, 0), size=0.38, lod=0, finish=ZINC)


def hinge():
    """A piano hinge down the door's left edge, painted with the case."""
    count, z0, z1 = 15, 0.7, 16.3
    pitch = (z1 - z0) / count
    y = -7.19
    for k in range(count):
        z = z0 + k * pitch
        kit.lathe(piece(ENAMEL, 1, bevel=0.0, name="hinge"), [(0, 0.0), (0.165, 0.0), (0.165, pitch - 0.025), (0, pitch - 0.025)], 8, kit.frame((4.45, y, z)))
    kit.box(piece(ENAMEL, 2, bevel=0.015, angle=40, name="hinge leaf"), (3.95, -7.12, z0), (4.32, -7.04, z1))
    for z in (z0, z1):
        kit.lathe(piece(ZINC, 0, name="hinge"), [(0, 0.0), (0.09, 0.0), (0.09, 0.06), (0, 0.06)], 6, kit.frame((4.45, y, z - (0.06 if z == z1 else 0.03))))


def louvres():
    for sign in (-1, 1):
        for k in range(3):
            z = 13.0 + k * 0.95
            y0, y1 = sorted((sign * HY, sign * (HY + 0.085)))
            kit.box(piece(ENAMEL, 1, bevel=0.03, angle=40, name="louvre"), (0.9, y0, z), (3.4, y1, z + 0.42))


def sign():
    m = on_door(0.0, (SIGN_Z0 + SIGN_Z1) / 2)
    kit.prism(piece(PLATE, 3, bevel=0.012, angle=40, name="sign"), rounded((SIGN_Y1 - SIGN_Y0) / 2, (SIGN_Z1 - SIGN_Z0) / 2, 0.34), 0.0, SIGN_T, m)
    for y in (SIGN_Y0 + 0.42, SIGN_Y1 - 0.42):
        for z in (SIGN_Z0 + 0.42, SIGN_Z1 - 0.42):
            rivet(y, z, DOOR + SIGN_T)


def rating_plate():
    m = on_door((RATING_Y0 + RATING_Y1) / 2, (RATING_Z0 + RATING_Z1) / 2)
    kit.prism(piece(RATING, 1, bevel=0.01, angle=40, name="rating plate"), rounded((RATING_Y1 - RATING_Y0) / 2, (RATING_Z1 - RATING_Z0) / 2, 0.08), 0.0, 0.035, m)
    for y in (RATING_Y0 + 0.18, RATING_Y1 - 0.18):
        rivet(y, (RATING_Z0 + RATING_Z1) / 2, DOOR + 0.035, size=0.09)


def lock():
    """A pressed rose, a brass key cylinder and a black quarter-turn handle lying across it to the left."""
    rose = kit.frame((DOOR, LOCK_Y, LOCK_Z), (1, 0, 0))
    kit.lathe(piece(ZINC, 1, name="rose"), [(0.6, 0.0), (0.6, 0.04), (0.52, 0.08), (0, 0.08)], 18, rose)
    kit.lathe(piece(BRASS, 1, name="cylinder"), [(0.27, 0.1), (0.27, 0.2), (0.21, 0.24), (0, 0.24)], 14, kit.frame((DOOR, LOCK_Y + 1.25, LOCK_Z), (1, 0, 0)))
    kit.box(piece(RUBBER, 0, name="key slot"), (DOOR + 0.235, LOCK_Y + 1.25 - 0.035, LOCK_Z - 0.13), (DOOR + 0.25, LOCK_Y + 1.25 + 0.035, LOCK_Z + 0.13))
    kit.lathe(piece(ZINC, 0, name="rose"), [(0.34, 0.0), (0.34, 0.04), (0.28, 0.08), (0, 0.08)], 12, kit.frame((DOOR, LOCK_Y + 1.25, LOCK_Z), (1, 0, 0)))
    kit.lathe(piece(RUBBER, 1, name="cylinder"), [(0.36, 0.08), (0.36, 0.42), (0.3, 0.48), (0, 0.48)], 14, kit.frame((DOOR, LOCK_Y, LOCK_Z), (1, 0, 0)))
    grip = piece(RUBBER, 1, bevel=0.07, segs=2, angle=40, name="handle")
    kit.box(grip, (DOOR + 0.42, LOCK_Y - 2.35, LOCK_Z - 0.26), (DOOR + 0.9, LOCK_Y + 0.14, LOCK_Z + 0.26))
    kit.box(piece(RUBBER, 1, bevel=0.04, angle=40, name="handle neck"), (DOOR + 0.3, LOCK_Y - 0.2, LOCK_Z - 0.2), (DOOR + 0.48, LOCK_Y + 0.2, LOCK_Z + 0.2))


def seal():
    """A red pull-tight seal from an eye on the door, round the handle's neck, with its tail hanging."""
    eye_y, eye_z = LOCK_Y - 1.2, LOCK_Z - 0.95
    kit.lathe(piece(ZINC, 0, name="rose"), [(0.17, 0.0), (0.17, 0.05), (0.08, 0.07), (0, 0.07)], 8, kit.frame((DOOR, eye_y, eye_z), (1, 0, 0)))
    x = DOOR + 0.2
    path = kit.spline([(DOOR + 0.1, eye_y, eye_z + 0.02), (x + 0.14, eye_y + 0.32, eye_z + 0.42), (x + 0.3, LOCK_Y - 0.62, LOCK_Z - 0.26), (x + 0.42, LOCK_Y - 0.34, LOCK_Z + 0.02), (x + 0.28, LOCK_Y - 0.62, LOCK_Z - 0.3), (x + 0.1, eye_y + 0.06, eye_z - 0.2)], 3)
    tube(piece(SEAL, 0, name="seal"), path, 0.042, 5, flatten=0.5)
    head = piece(SEAL, 0, bevel=0.015, angle=40, name="seal head")
    kit.box(head, (x + 0.02, eye_y - 0.16, eye_z - 0.5), (x + 0.11, eye_y + 0.16, eye_z - 0.18))
    kit.box(piece(SEAL, 0, bevel=0.01, angle=40, name="seal tail"), (x + 0.03, eye_y - 0.09, eye_z - 1.32), (x + 0.075, eye_y + 0.09, eye_z - 0.5))


def inspection_tag():
    """A yellow card on a string from the handle's end, hanging against the door."""
    y, z = LOCK_Y - 2.16, LOCK_Z - 0.16
    x = DOOR + 0.13
    top = (x + 0.01, y - 0.2, z - 1.15)
    tube(piece(RUBBER, 0, name="string"), kit.spline([(DOOR + 0.62, y, z + 0.02), (DOOR + 0.42, y - 0.08, z - 0.32), (x + 0.1, y - 0.16, z - 0.8), top], 3), 0.022, 4)
    m = kit.frame(top, (1.0, -0.02, 0.09), (0.04, 0.985, -0.17))
    outline = [(-0.46, 0.08), (-0.46, -2.05), (0.46, -2.05), (0.46, 0.08), (0.28, 0.24), (-0.28, 0.24)]
    kit.prism(piece(TAG, 0, name="tag"), outline, -0.012, 0.012, m)


def geometry():
    case()
    hinge()
    louvres()
    sign()
    rating_plate()
    lock()
    seal()
    inspection_tag()


def harden_all():
    seen = set()
    for p in kit.parts:
        bm = p.bm
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        bm.normal_update()
        if p.finish in (ENAMEL, PLATE, RATING) and p.name not in NO_EDGE:
            for e in bm.edges:
                if len(e.link_faces) == 2 and e.calc_face_angle_signed(0.0) > math.radians(24):
                    a, b = e.verts[0].co, e.verts[1].co
                    count = max(1, int((b - a).length / 0.05))
                    for k in range(count + 1):
                        edge_lines.append(tuple(a.lerp(b, k / count)))
        kit.harden(p)
        p.done = p.bm
        # A part is looked up by this at four digits when the LODs are cut, so no two can share one.
        while True:
            p.rand = float(kit.rng.uniform(0, 1))
            if round(p.rand, 4) not in seen:
                seen.add(round(p.rand, 4))
                break


def share(finish, normal, centre):
    """How much texture an island gets, against the sign's face at 1."""
    if finish == PLATE:
        return 1.0 if normal.x > 0.5 else 0.3
    if finish in (RATING, TAG):
        return 1.3 if normal.x > 0.5 else 0.2
    if finish == ENAMEL:
        if normal.x < -0.7:
            return 0.04
        if normal.x > 0.7 and centre.x > 4.5:
            return 1.0
        return 0.6
    if finish == RUBBER:
        return 0.5
    return 0.7


def pack(mesh, pad_px=5):
    """The toolkit's real-scale shelf packing, with a share of the atlas for each island, which is kept in the facts' third channel."""
    bm = bmesh.new()
    bm.from_mesh(mesh)
    layer = bm.loops.layers.uv.active
    facts = bm.loops.layers.float_color["facts"]
    bm.faces.ensure_lookup_table()
    seen = set()
    islands = []
    for seed in bm.faces:
        if seed.index in seen:
            continue
        seen.add(seed.index)
        stack, faces = [seed], []
        while stack:
            f = stack.pop()
            faces.append(f)
            for l in f.loops:
                a, b = l[layer].uv, l.link_loop_next[layer].uv
                for other in l.link_loops:
                    g = other.face
                    if g.index in seen:
                        continue
                    c, d = other[layer].uv, other.link_loop_next[layer].uv
                    if ((a - d).length < 1e-5 and (b - c).length < 1e-5) or ((a - c).length < 1e-5 and (b - d).length < 1e-5):
                        seen.add(g.index)
                        stack.append(g)
        islands.append(faces)

    rects = []
    for n, faces in enumerate(islands):
        area3 = sum(f.calc_area() for f in faces)
        pts = np.array([tuple(l[layer].uv) for f in faces for l in f.loops])
        tris = np.array([[tuple(l[layer].uv) for l in f.loops] for f in faces])
        areauv = 0.5 * np.abs((tris[:, 1, 0] - tris[:, 0, 0]) * (tris[:, 2, 1] - tris[:, 0, 1]) - (tris[:, 2, 0] - tris[:, 0, 0]) * (tris[:, 1, 1] - tris[:, 0, 1])).sum()
        weighted = Vector((0, 0, 0))
        middle = Vector((0, 0, 0))
        for f in faces:
            weighted += f.normal * f.calc_area()
            middle += f.calc_center_median() * f.calc_area()
        weight = share(int(round(faces[0].loops[0][facts][0] * 16)), weighted.normalized(), middle / max(area3, 1e-9))
        scale = math.sqrt(area3 / max(areauv, 1e-12)) * weight
        centre = pts.mean(0)
        inches = (pts - centre) * scale
        best = None
        for deg in np.linspace(0, 90, 19):
            r = math.radians(deg)
            rot = np.array(((math.cos(r), -math.sin(r)), (math.sin(r), math.cos(r))))
            q = inches @ rot.T
            w, h = np.ptp(q, axis=0)
            if best is None or w * h < best[0]:
                best = (w * h, rot, w, h)
        _, rot, w, h = best
        q = inches @ rot.T
        if h > w:
            rot = np.array(((0.0, 1.0), (-1.0, 0.0))) @ rot
            q = inches @ rot.T
            w, h = h, w
        rects.append((w, h, n, centre, scale, rot, q.min(0), weight))

    def attempt(px_per_in):
        pad = pad_px / px_per_in
        limit_x, limit_y = W / px_per_in, H / px_per_in
        x = y = pad
        row = 0.0
        places = {}
        for w, h, n, *_ in sorted(rects, key=lambda r: (-round(r[1], 1), -r[0])):
            if x + w + pad > limit_x:
                x = pad
                y += row + pad
                row = 0.0
            if y + h + pad > limit_y:
                return None
            places[n] = (x, y)
            x += w + pad
            row = max(row, h)
        return places

    lo, hi = 2.0, 400.0
    places = None
    for _ in range(30):
        mid = (lo + hi) / 2
        got = attempt(mid)
        if got:
            places, lo = got, mid
        else:
            hi = mid
    density = lo
    for w, h, n, centre, scale, rot, low, weight in rects:
        px, py = places[n]
        for f in islands[n]:
            for l in f.loops:
                q = (np.array(tuple(l[layer].uv)) - centre) * scale @ rot.T - low
                l[layer].uv = ((q[0] + px) * density / W, (q[1] + py) * density / H)
                l[facts][2] = weight
    bm.to_mesh(mesh)
    bm.free()
    print("islands", len(rects), "density px/in %.1f" % density, flush=True)
    return density


def build_stage():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    geometry()
    harden_all()
    print("parts", len(kit.parts), flush=True)
    hw = kit.join_parts(kit.parts, "first_aid_lod0")
    hw.data.uv_layers.new(name="UVMap")
    bpy.context.view_layer.objects.active = hw
    hw.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=math.radians(52), margin_method="SCALED", rotate_method="AXIS_ALIGNED_Y", island_margin=0.0, area_weight=0.0, correct_aspect=True, scale_to_bounds=False)
    bpy.ops.object.mode_set(mode="OBJECT")
    hw.select_set(False)
    density = pack(hw.data, 5)
    hw.data.calc_loop_triangles()
    print("tris", len(hw.data.loop_triangles), "px/in %.1f" % density, flush=True)

    lookup = {round(p.rand, 4): p for p in kit.parts}

    def lod(number, keep, ratio):
        copy = hw.copy()
        copy.data = hw.data.copy()
        copy.name = copy.data.name = f"first_aid_lod{number}"
        bpy.context.scene.collection.objects.link(copy)
        bm = bmesh.new()
        bm.from_mesh(copy.data)
        facts = bm.loops.layers.float_color["facts"]
        drop = [f for f in bm.faces if lookup[round(f.loops[0][facts][1], 4)].lod < keep]
        bmesh.ops.delete(bm, geom=drop, context="FACES")
        bm.to_mesh(copy.data)
        bm.free()
        bpy.context.view_layer.objects.active = copy
        copy.select_set(True)
        mod = copy.modifiers.new("collapse", "DECIMATE")
        mod.decimate_type = "COLLAPSE"
        mod.ratio = ratio
        mod.use_collapse_triangulate = True
        mod.delimit = {"UV", "SEAM"}
        bpy.ops.object.modifier_apply(modifier=mod.name)
        copy.select_set(False)
        copy.data.calc_loop_triangles()
        print(copy.name, "tris", len(copy.data.loop_triangles), flush=True)

    lod(1, 1, 0.7)
    lod(2, 3, 0.8)
    np.save(os.path.join(WORK, "first_aid_edges.npy"), np.array(edge_lines, np.float32))
    with open(os.path.join(WORK, "first_aid.json"), "w") as h:
        json.dump(dict(density=density, range=POS_RANGE, hy=HY, z0=Z0, z1=Z1, door=DOOR, sign=(SIGN_Y0, SIGN_Y1, SIGN_Z0, SIGN_Z1, SIGN_T), lock=(LOCK_Y, LOCK_Z), rating=(RATING_Y0, RATING_Y1, RATING_Z0, RATING_Z1)), h)
    bpy.ops.wm.save_as_mainfile(filepath=BLEND)
    print("saved build", flush=True)


def uv_hash(ob):
    data = np.empty(len(ob.data.loops) * 2, np.float32)
    ob.data.uv_layers["UVMap"].data.foreach_get("uv", data)
    return hashlib.sha1(data.tobytes()).hexdigest()


def bake_stage():
    bpy.ops.wm.open_mainfile(filepath=BLEND)
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.render.threads_mode = "FIXED"
    scene.render.threads = 4
    scene.cycles.use_denoising = False
    scene.cycles.use_adaptive_sampling = False
    scene.cycles.max_bounces = 2
    hw = bpy.data.objects["first_aid_lod0"]
    for ob in scene.objects:
        ob.hide_render = ob is not hw
    world = bpy.data.worlds.new("bake")
    scene.world = world
    world.light_settings.distance = 3.0
    with open(os.path.join(WORK, "first_aid_baked_uv_hash.txt"), "w") as h:
        h.write(uv_hash(hw))

    def source(kind):
        def setup(nt, emit):
            if kind == "facts":
                attr = nt.nodes.new("ShaderNodeVertexColor")
                attr.layer_name = "facts"
                nt.links.new(attr.outputs[0], emit.inputs[0])
                return
            geo = nt.nodes.new("ShaderNodeNewGeometry")
            mapped = nt.nodes.new("ShaderNodeVectorMath")
            mapped.operation = "MULTIPLY_ADD"
            scale = 1 / POS_RANGE if kind == "pos" else 0.5
            mapped.inputs[1].default_value = (scale, scale, scale)
            mapped.inputs[2].default_value = (0.5, 0.5, 0.5)
            nt.links.new(geo.outputs["Position" if kind == "pos" else "Normal"], mapped.inputs[0])
            nt.links.new(mapped.outputs[0], emit.inputs[0])

        return setup

    def bake_one(w, h, kind, setup, samples, out):
        img = bpy.data.images.new(out, w, h, alpha=True, float_buffer=True)
        img.colorspace_settings.name = "Non-Color"
        mat = bpy.data.materials.new(out)
        mat.use_nodes = True
        nt = mat.node_tree
        if setup:
            nt.nodes.clear()
            o = nt.nodes.new("ShaderNodeOutputMaterial")
            e = nt.nodes.new("ShaderNodeEmission")
            nt.links.new(e.outputs[0], o.inputs[0])
            setup(nt, e)
        tex = nt.nodes.new("ShaderNodeTexImage")
        tex.image = img
        nt.nodes.active = tex
        tex.select = True
        hw.data.materials.clear()
        hw.data.materials.append(mat)
        scene.cycles.samples = samples
        bpy.ops.object.select_all(action="DESELECT")
        bpy.context.view_layer.objects.active = hw
        hw.select_set(True)
        bpy.ops.object.bake(type=kind, margin=0, use_clear=True, target="IMAGE_TEXTURES")
        data = np.empty(w * h * 4, np.float32)
        img.pixels.foreach_get(data)
        np.save(os.path.join(WORK, out + ".npy"), data.reshape(h, w, 4))
        print("baked", out, flush=True)

    bake_one(W, H, "EMIT", source("pos"), 1, "bake_fa_pos")
    bake_one(W, H, "EMIT", source("nor"), 1, "bake_fa_nor")
    bake_one(W, H, "EMIT", source("facts"), 1, "bake_fa_facts")
    bake_one(W // 2, H // 2, "AO", None, 48, "bake_fa_ao")


def export_stage():
    bpy.ops.wm.open_mainfile(filepath=BLEND)
    os.makedirs(OUT, exist_ok=True)
    if uv_hash(bpy.data.objects["first_aid_lod0"]) != open(os.path.join(WORK, "first_aid_baked_uv_hash.txt")).read().strip():
        raise SystemExit("The build's UVs are not the ones the textures were baked on.")
    counts = {}
    for number in (0, 1, 2):
        ob = bpy.data.objects[f"first_aid_lod{number}"]
        mesh = ob.data
        mesh.polygons.foreach_set("use_smooth", np.ones(len(mesh.polygons), bool))
        mesh.set_sharp_from_angle(angle=math.radians(62))
        mod = ob.modifiers.new("wn", "WEIGHTED_NORMAL")
        mod.mode = "FACE_AREA"
        mod.weight = 100
        mod.keep_sharp = True
        mod.thresh = 0.01
        dg = bpy.context.evaluated_depsgraph_get()
        e = ob.evaluated_get(dg)
        em = e.to_mesh()
        em.calc_loop_triangles()
        n_loops, n_tris = len(em.loops), len(em.loop_triangles)
        loops = np.empty(n_tris * 3, np.int32)
        em.loop_triangles.foreach_get("loops", loops)
        verts = np.empty(n_loops, np.int32)
        em.loops.foreach_get("vertex_index", verts)
        co = np.empty(len(em.vertices) * 3)
        em.vertices.foreach_get("co", co)
        uv = np.empty(n_loops * 2)
        em.uv_layers["UVMap"].data.foreach_get("uv", uv)
        nn = np.empty(n_loops * 3)
        em.corner_normals.foreach_get("vector", nn)
        p = co.reshape(-1, 3)[verts[loops]][:, [1, 2, 0]]
        t = uv.reshape(-1, 2)[loops]
        n = nn.reshape(-1, 3)[loops][:, [1, 2, 0]]
        e.to_mesh_clear()
        tables = ({}, {}, {})
        lines = ([], [], [])
        faces = []
        for k in range(n_tris):
            tri = []
            for c in range(3):
                i = k * 3 + c
                idx = []
                for table, store, prefix, vec, digits in zip(tables, lines, ("v ", "vt ", "vn "), (p[i], t[i], n[i]), (5, 6, 5)):
                    key = tuple(np.round(vec, digits))
                    got = table.get(key)
                    if got is None:
                        got = len(table) + 1
                        table[key] = got
                        store.append(prefix + " ".join(f"{x:.{digits}f}" for x in key) + "\n")
                    idx.append(got)
                tri.append("%d/%d/%d" % tuple(idx))
            faces.append("f " + " ".join(tri) + "\n")
        with open(os.path.join(OUT, f"{NAME}_lod{number}.obj"), "w", newline="\n") as h:
            h.write(f"# Generated by Sources/Riverdale/first-aid-v2/first_aid.py\nmtllib {NAME}.mtl\n")
            for block in lines:
                h.writelines(block)
            h.write(f"usemtl {NAME}\n")
            h.writelines(faces)
        counts[number] = n_tris
        print("lod", number, "tris", n_tris, flush=True)
    with open(os.path.join(OUT, f"{NAME}.mtl"), "w", newline="\n") as h:
        h.write(f"newmtl {NAME}\nKd 1 1 1\nd 1\n")
    meshes = ",\n".join(
        f'\t\t\t\t\t{{ _class = "RenderMeshFile" name = "lod{l}" filename = "{FOLDER}/{NAME}_lod{l}.obj" '
        'import_translation = [ 0.0, 0.0, 0.0 ] import_rotation = [ 0.0, 0.0, 0.0 ] import_scale = 1.0 '
        'align_origin_x_type = "None" align_origin_y_type = "None" align_origin_z_type = "None" parent_bone = "" '
        "import_filter = { exclude_by_default = false exception_list = [ ] } }" for l in counts
    )
    groups = ",\n".join(f'\t\t\t\t\t{{ _class = "LODGroup" switch_threshold = {t:.1f} meshes = [ "lod{l}" ] }}' for l, t in zip(counts, (0.0, 12.0, 40.0)))
    doc = f"""<!-- kv3 encoding:text:version{{e21c7f3c-8a33-41c5-9977-a76d3a32aa0d}} format:modeldoc29:version{{3cec427c-1b0e-4d48-a90a-0436f33a6041}} -->
// Generated by Sources/Riverdale/first-aid-v2/first_aid.py
{{
	rootNode =
	{{
		_class = "RootNode"
		children =
		[
			{{
				_class = "MaterialGroupList"
				children =
				[
					{{
						_class = "DefaultMaterialGroup"
						remaps =
						[
							{{ from = "{NAME}.vmat" to = "{FOLDER}/scanned/{NAME}_scanned.vmat" }}
						]
						use_global_default = false
						global_default_material = ""
					}},
				]
			}},
			{{
				_class = "RenderMeshList"
				children =
				[
{meshes}
				]
			}},
			{{
				_class = "LODGroupList"
				children =
				[
{groups}
				]
			}},
		]
		model_archetype = ""
		primary_associated_entity = ""
		anim_graph_name = ""
		base_model_name = ""
	}}
}}
"""
    with open(os.path.join(OUT, f"{NAME}.vmdl"), "w", newline="\n") as h:
        h.write(doc)
    # The model draws the scan-based finish (paint_scanned.ps1). This code-painted material is kept beside it: the user liked both.
    vmat = f"""// Generated by Sources/Riverdale/first-aid-v2/first_aid.py

Layer0
{{
	shader "shaders/complex.shader"

	//---- PBR ----
	F_METALNESS_TEXTURE 1
	F_SPECULAR 1

	//---- Ambient Occlusion ----
	g_flAmbientOcclusionDirectDiffuse "0.300"
	g_flAmbientOcclusionDirectSpecular "0.500"
	TextureAmbientOcclusion "{FOLDER}/{NAME}_ao.png"

	//---- Color ----
	g_flModelTintAmount "1.000"
	g_vColorTint "[1.000000 1.000000 1.000000 0.000000]"
	TextureColor "{FOLDER}/{NAME}_color.png"

	//---- Fog ----
	g_bFogEnabled "1"

	//---- Metalness ----
	TextureMetalness "{FOLDER}/{NAME}_metal.png"

	//---- Normal ----
	TextureNormal "{FOLDER}/{NAME}_normal.png"

	//---- Roughness ----
	g_flRoughnessScaleFactor "1.000"
	TextureRoughness "{FOLDER}/{NAME}_rough.png"
}}
"""
    with open(os.path.join(OUT, f"{NAME}.vmat"), "w", newline="\n") as h:
        h.write(vmat)
    print("exported", counts, flush=True)


if "build" in STAGES:
    build_stage()
if "bake" in STAGES:
    bake_stage()
if "export" in STAGES:
    export_stage()
print("first aid stages done", flush=True)
