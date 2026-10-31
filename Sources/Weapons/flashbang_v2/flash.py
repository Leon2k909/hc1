"""Flashbang v2: build, bake and export. Uses the capture flag's mesh toolkit and the frag grenade's fuze.

blender -b --factory-startup -t 4 --python flash.py -- <work dir> <project root> <build|bake|export> ...

A generic fictional stun grenade, the size and shape of the old one, on the same origin and axes: a steel tube with three
rows of six real ports between two hex caps turned from bar, a canister inside it, the lever down the -X side and the pull
ring off +Y. It keeps the old model's three body groups in the same order (grenade, spoon, pin), so the prefabs' mask of 11
still shows all three. Held in first person, so the close LOD is generous for its size. Inches, engine axes.
Exports to <work dir>/export, and install.ps1 copies that into Assets.
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

from build import Part, add, frame, lathe, ring_path, spline, tube  # noqa: E402

PAINT, OXIDE, ZINC = kit.PAINT, kit.OXIDE, kit.ZINC
LEVER, CANISTER = 11, 12
GROUPS = ("grenade", "spoon", "pin")
MESH = {"grenade": "grenade", "spoon": "grenade_spoon", "pin": "grenade_pin"}
LODS = {"grenade": 3, "spoon": 3, "pin": 2}
FOLDER = "weapons/throwable/flashbang/flashbang_v2"
OUT = os.path.join(WORK, "export")
BLEND = os.path.join(WORK, "flash_build.blend")
NAME = "flashbang"
RES = 2048
POS_RANGE = 16.0  # The position bake spans this many inches.

R, ZC = 0.679, 2.25  # The tube, as the old one's, and its middle.
BORE = 0.60
ROWS = (1.40, 2.25, 3.10)  # The port rows' heights, as the old one's.
PORT = 0.27
COLUMNS = 6
TUBE_LOW, TUBE_HIGH = 0.80, 3.72
APOTHEM = 0.75  # Across the hex caps' flats, which face +X and -X. Their corners are turned back to the old one's 0.855.
TURNED = 0.855
DZ = 1.952  # From the frag grenade's fuze up to this one's.
HINGE = (0.54, 3.345 + DZ)
PIN_X, PIN_Z = -0.40, 3.08 + DZ
edge_lines = []


def piece(group, finish, lod, bevel=0.0, segs=1, angle=35.0, name=""):
    part = add(Part(finish, lod, bevel=bevel, segs=segs, angle=angle, name=name))
    part.group = group
    return part


def extrude_xz(part, outline, y0, y1):
    """An outline in the XZ plane, extruded along Y. Winding is settled for every part in harden_all."""
    bm = part.bm
    a = [bm.verts.new((x, y0, z)) for x, z in outline]
    b = [bm.verts.new((x, y1, z)) for x, z in outline]
    n = len(outline)
    for k in range(n):
        bm.faces.new((a[k], a[(k + 1) % n], b[(k + 1) % n], b[k]))
    bm.faces.new(a)
    bm.faces.new(b)


def hex_radius(a):
    """How far the hex bar reaches at an angle: its flats face +X and -X."""
    sector = (math.degrees(a) + 30.0) % 60.0 - 30.0
    return APOTHEM / math.cos(math.radians(sector))


def turned_hex(part, profile, sides=36):
    """Rings of (radius, z) cut from hex bar: a ring reaching past the bar takes the bar's shape, which is what leaves the
    arcs on a turned hex's faces. 36 sides put a vertex on every corner."""
    bm = part.bm
    rings = []
    for r, z in profile:
        if r < 1e-5:
            rings.append([bm.verts.new((0, 0, z))])
            continue
        ring = []
        for k in range(sides):
            a = 2 * math.pi * k / sides
            reach = min(r, hex_radius(a))
            ring.append(bm.verts.new((reach * math.cos(a), reach * math.sin(a), z)))
        rings.append(ring)
    for a, b in zip(rings, rings[1:]):
        if len(a) == 1:
            for k in range(sides):
                bm.faces.new((a[0], b[(k + 1) % sides], b[k]))
        elif len(b) == 1:
            for k in range(sides):
                bm.faces.new((a[k], a[(k + 1) % sides], b[0]))
        else:
            for k in range(sides):
                bm.faces.new((a[k], a[(k + 1) % sides], b[(k + 1) % sides], b[k]))
    if len(rings[0]) > 1:
        bm.faces.new(list(reversed(rings[0])))
    if len(rings[-1]) > 1:
        bm.faces.new(list(rings[-1]))


def caps():
    low = piece("grenade", PAINT, 3, bevel=0.009, angle=42, name="low cap")
    turned_hex(low, [(0.0, 0.035), (0.44, 0.035), (0.465, 0.0), (0.735, 0.0), (0.79, 0.035), (TURNED, 0.07), (TURNED, 0.73), (0.79, 0.765), (0.735, 0.80), (0.60, 0.80)])
    high = piece("grenade", PAINT, 3, bevel=0.009, angle=42, name="high cap")
    turned_hex(high, [(0.60, 3.72), (0.735, 3.72), (0.79, 3.755), (TURNED, 3.79), (TURNED, 4.43), (0.79, 4.465), (0.735, 4.50), (0.545, 4.50), (0.515, 4.527), (0.30, 4.527)])


def ported_tube():
    """The tube as a shell: outside and inside surfaces, joined by a drilled, countersunk bore through every port."""
    part = piece("grenade", PAINT, 3, name="tube")
    bm = part.bm
    wide, tall = 6, 4  # A port cell's segments across and up: 2 * (6 + 4) round each port.
    around = COLUMNS * wide
    step = 2 * math.pi / around
    pitch = ROWS[1] - ROWS[0]
    low_edge, high_edge = ROWS[0] - pitch / 2, ROWS[-1] + pitch / 2
    outer, inner = {}, {}

    def grid(store, radius, a_index, z):
        key = (a_index % around, round(z, 5))
        vert = store.get(key)
        if vert is None:
            a = (a_index + 0.5 - wide / 2) * step
            vert = store[key] = bm.verts.new((radius * math.cos(a), radius * math.sin(a), z))
        return vert

    def on_cylinder(radius, az, s, t, z):
        """A point of a straight bore, s across and t up from its centre, where it meets a cylinder."""
        depth = math.sqrt(radius * radius - s * s)
        return Vector((depth * math.cos(az) - s * math.sin(az), depth * math.sin(az) + s * math.cos(az), z + t))

    count = 2 * (wide + tall)
    for column in range(COLUMNS):
        az = 2 * math.pi * column / COLUMNS
        first = column * wide
        for z in ROWS:
            rows = [z - pitch / 2 + pitch * k / tall for k in range(tall + 1)]
            # Round the cell anticlockwise from outside, starting at its lower left, with the angle each point takes on the port.
            walk = [(first + k, rows[0]) for k in range(wide)] + [(first + wide, rows[k]) for k in range(tall)]
            walk += [(first + wide - k, rows[-1]) for k in range(wide)] + [(first, rows[tall - k]) for k in range(tall)]
            start = -math.pi / 2 - (wide / 2) * (2 * math.pi / count)
            loops = []
            for layer, (radius, hole, sink) in enumerate(((R, PORT + 0.018, 0.0), (R, PORT, 0.018), (BORE, PORT, 0.0))):
                ring = []
                for k in range(count):
                    a = start + k * 2 * math.pi / count
                    s, t = hole * math.cos(a), hole * math.sin(a)
                    ring.append(bm.verts.new(on_cylinder(radius - sink, az, s, t, z)))
                loops.append(ring)
            face_out = [grid(outer, R, a, h) for a, h in walk]
            face_in = [grid(inner, BORE, a, h) for a, h in walk]
            for k in range(count):
                n = (k + 1) % count
                bm.faces.new((face_out[k], face_out[n], loops[0][n], loops[0][k]))
                bm.faces.new((loops[0][k], loops[0][n], loops[1][n], loops[1][k]))
                bm.faces.new((loops[1][k], loops[1][n], loops[2][n], loops[2][k]))
                bm.faces.new((loops[2][k], loops[2][n], face_in[n], face_in[k]))

    # Plain tube past the last rows, into the caps, and a closed end at each.
    for edge, end in ((low_edge, TUBE_LOW - 0.02), (high_edge, TUBE_HIGH + 0.02)):
        for k in range(around):
            a, b = grid(outer, R, k, edge), grid(outer, R, k + 1, edge)
            c, d = grid(outer, R, k + 1, end), grid(outer, R, k, end)
            e, f = grid(inner, BORE, k, edge), grid(inner, BORE, k + 1, edge)
            g, h = grid(inner, BORE, k + 1, end), grid(inner, BORE, k, end)
            bm.faces.new((a, b, c, d))
            bm.faces.new((e, h, g, f))
            bm.faces.new((d, c, g, h))


def canister():
    """The charge's can behind the ports: what you see when you look through one."""
    can = piece("grenade", CANISTER, 1, name="canister")
    profile = [(0.0, 0.78), (0.42, 0.78)]
    for z in (ROWS[0] + 0.425, ROWS[1] + 0.425):
        profile += [(0.42, z - 0.025), (0.405, z), (0.42, z + 0.025)]
    profile += [(0.42, 3.74), (0.0, 3.74)]
    lathe(can, profile, 16)


def fuze_body():
    nut = piece("grenade", OXIDE, 2, bevel=0.008, angle=25, name="nut")
    lathe(nut, [(0.30, 2.565 + DZ), (0.475, 2.565 + DZ), (0.50, 2.59 + DZ), (0.50, 2.685 + DZ), (0.47, 2.712 + DZ), (0.34, 2.712 + DZ)], 12)
    ring = piece("grenade", OXIDE, 1, bevel=0.004, name="lock ring")
    lathe(ring, [(0.30, 2.71 + DZ), (0.40, 2.71 + DZ), (0.41, 2.72 + DZ), (0.41, 2.742 + DZ), (0.40, 2.752 + DZ), (0.30, 2.752 + DZ)], 40)
    neck = piece("grenade", OXIDE, 3, bevel=0.006, name="neck")
    lathe(neck, [(0.20, 2.75 + DZ), (0.345, 2.75 + DZ), (0.345, 2.79 + DZ), (0.30, 2.875 + DZ), (0.30, 2.95 + DZ), (0.20, 2.95 + DZ)], 28)

    head = piece("grenade", OXIDE, 3, bevel=0.016, segs=2, name="head")
    extrude_xz(head, [(x, z + DZ) for x, z in [(-0.34, 2.93), (0.26, 2.93), (0.40, 3.06), (0.40, 3.385), (-0.46, 3.385), (-0.50, 3.31), (-0.50, 3.10)]], -0.27, 0.27)
    hx, hz = HINGE
    outline = [(0.36, 3.20 + DZ), (0.47, 3.225 + DZ), (hx + 0.06, hz - 0.075), (hx + 0.085, hz), (hx + 0.06, hz + 0.06), (hx, hz + 0.08), (0.40, 3.405 + DZ), (0.36, 3.385 + DZ)]
    for y0, y1 in ((0.19, 0.272), (-0.272, -0.19)):
        extrude_xz(piece("grenade", OXIDE, 2, bevel=0.01, name="lug"), outline, y0, y1)
    # The hinge pin, peened over at both ends.
    pin = piece("grenade", ZINC, 1, name="hinge pin")
    profile = [(0, -0.312), (0.05, -0.312), (0.072, -0.298), (0.072, -0.272), (0.042, -0.272), (0.042, 0.272), (0.072, 0.272), (0.072, 0.298), (0.05, 0.312), (0, 0.312)]
    lathe(pin, profile, 14, frame((hx, 0, hz), (0, 1, 0)))
    # A pressed boss on each face of the head, where the pull pin passes through.
    for side in (-1, 1):
        lathe(piece("grenade", OXIDE, 1, bevel=0.004, name="boss"), [(0.05, 0.268), (0.085, 0.268), (0.085, 0.279), (0.05, 0.279)], 18, frame((PIN_X, 0, PIN_Z), (0, side, 0)))


def lever():
    """A strip of sheet steel from a curl round the hinge, over the head, and straight down past the top cap, clear of its flat."""
    hx, hz = HINGE
    r = 0.105
    # x, z, half width, flange depth, bead height
    stations = [(hx + r * math.cos(math.radians(a)), hz + r * math.sin(math.radians(a)), 0.17, 0.004, 0.0) for a in (-115, -65, -20, 25, 70)]
    stations += [
        (0.41, hz + 0.117, 0.17, 0.004, 0.0),
        (0.31, 3.466 + DZ, 0.30, 0.004, 0.0),
        (0.10, 3.474 + DZ, 0.32, 0.004, 0.0),
        (-0.40, 3.485 + DZ, 0.32, 0.006, 0.0),
        (-0.54, 3.447 + DZ, 0.32, 0.012, 0.0),
        (-0.64, 3.335 + DZ, 0.33, 0.03, 0.004),
        (-0.76, 5.05, 0.345, 0.05, 0.012),
        (-0.90, 4.70, 0.345, 0.06, 0.016),
        (-0.985, 4.32, 0.27, 0.06, 0.016),
        (-1.02, 3.90, 0.24, 0.06, 0.016),
        (-1.06, 2.20, 0.24, 0.055, 0.016),
        (-1.08, 1.88, 0.235, 0.045, 0.012),
        (-1.13, 1.745, 0.225, 0.03, 0.006),
        (-1.21, 1.69, 0.20, 0.012, 0.0),
    ]
    per = 1
    points = spline([(s[0], 0, s[1]) for s in stations], per)
    table = []
    for i in range(len(stations) - 1):
        a, b = np.array(stations[i][2:]), np.array(stations[i + 1][2:])
        for k in range(per):
            table.append(a + (b - a) * k / per)
    table.append(np.array(stations[-1][2:]))
    t = 0.036
    strip = piece("spoon", LEVER, 3, bevel=0.0045, angle=30, name="strip")
    bm = strip.bm
    rings = []
    n = len(points)
    for i in range(n):
        d = points[min(i + 1, n - 1)] - points[max(i - 1, 0)]
        d.normalize()
        out = Vector((d.z, 0, -d.x))  # Away from the body, all the way along.
        w, f, b = table[i]
        f = max(f, 0.004)
        bw = min(0.10, w * 0.55)
        section = [
            (-w, -t / 2 - f),
            (-w, t / 2 - 0.01),
            (-w + 0.012, t / 2),
            (-bw - 0.05, t / 2),
            (-bw, t / 2 + b),
            (bw, t / 2 + b),
            (bw + 0.05, t / 2),
            (w - 0.012, t / 2),
            (w, t / 2 - 0.01),
            (w, -t / 2 - f),
            (w - t, -t / 2 - f),
            (w - t, -t / 2),
            (bw + 0.05, -t / 2),
            (bw, -t / 2 + b),
            (-bw, -t / 2 + b),
            (-bw - 0.05, -t / 2),
            (-w + t, -t / 2),
            (-w + t, -t / 2 - f),
        ]
        rings.append([bm.verts.new(points[i] + Vector((0, y, 0)) + out * o) for y, o in section])
    m = len(rings[0])
    for a, b in zip(rings, rings[1:]):
        for k in range(m):
            bm.faces.new((a[k], a[(k + 1) % m], b[(k + 1) % m], b[k]))
    bm.faces.new(rings[0])
    bm.faces.new(rings[-1])

    # Two ears off the strip, down the head's faces, carrying the pull pin.
    ear = [(x, z + DZ) for x, z in [(-0.565, 3.42), (0.20, 3.46), (0.14, 3.26), (-0.12, 3.02), (-0.28, 2.93), (-0.47, 2.93), (-0.565, 3.02)]]
    for y0, y1 in ((0.282, 0.318), (-0.318, -0.282)):
        extrude_xz(piece("spoon", LEVER, 3, bevel=0.0045, angle=30, name="ear"), ear, y0, y1)
    for side in (-1, 1):
        lathe(piece("spoon", LEVER, 1, bevel=0.004, name="eyelet"), [(0.04, 0.316), (0.082, 0.316), (0.09, 0.325), (0.09, 0.33), (0.075, 0.338), (0.04, 0.338)], 18, frame((PIN_X, 0, PIN_Z), (0, side, 0)))


def pull_pin():
    # The ring leans away from the head, as a ring hanging off a pin does. Its top passes through the pin's eye.
    c = Vector((PIN_X, 0.73, 4.61))
    u = Vector((1, 0, 0))
    v = Vector((0, -0.28, 0.96)).normalized()
    radius = 0.44
    m = frame(c, u.cross(v), u)
    tube(piece("pin", ZINC, 2, name="ring"), ring_path(radius, 40, m), 0.036, 8, closed=True)
    # A crimped sleeve where the wire's two ends meet.
    low = c - v * radius
    lathe(piece("pin", ZINC, 0, name="sleeve"), [(0, -0.085), (0.03, -0.085), (0.052, -0.066), (0.052, 0.066), (0.03, 0.085), (0, 0.085)], 12, frame(low, u))
    # One wire doubled over, through the head and both ears, its two legs spread at the far side.
    x = PIN_X
    a, b = PIN_Z - 0.021, PIN_Z + 0.021
    points = [(x, -0.60, 2.79 + DZ), (x, -0.50, 2.94 + DZ), (x, -0.40, a - 0.01), (x, -0.30, a), (x, 0.10, a), (x, 0.50, a), (x, 0.60, a - 0.05), (x, 0.665, PIN_Z), (x, 0.60, b + 0.05), (x, 0.50, b), (x, 0.10, b), (x, -0.30, b), (x, -0.40, b + 0.01), (x, -0.50, 3.22 + DZ), (x, -0.585, 3.35 + DZ)]
    path = spline(points, 3)
    tube(piece("pin", ZINC, 1, name="pull pin"), path, [0.012] + [0.0195] * (len(path) - 2) + [0.012], 6)


def geometry():
    caps()
    ported_tube()
    canister()
    fuze_body()
    lever()
    pull_pin()


def harden_all():
    """Settle each part's winding, note its convex edges for the wear, then bevel it."""
    for p in kit.parts:
        bm = p.bm
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        bm.normal_update()
        if p.finish in (PAINT, LEVER, OXIDE):
            for e in bm.edges:
                if len(e.link_faces) == 2 and e.calc_face_angle_signed(0.0) > math.radians(24):
                    a, b = e.verts[0].co, e.verts[1].co
                    count = max(1, int((b - a).length / 0.012))
                    for k in range(count + 1):
                        edge_lines.append(tuple(a.lerp(b, k / count)))
        kit.harden(p)
        p.done = p.bm
        p.rand = float(kit.rng.uniform(0, 1))


def build_stage():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    geometry()
    harden_all()
    print("parts", len(kit.parts), flush=True)
    hw = kit.join_parts(kit.parts, "all_lod0")
    hw.data.uv_layers.new(name="UVMap")
    bpy.context.view_layer.objects.active = hw
    hw.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=math.radians(52), margin_method="SCALED", rotate_method="AXIS_ALIGNED_Y", island_margin=0.0, area_weight=0.0, correct_aspect=True, scale_to_bounds=False)
    bpy.ops.object.mode_set(mode="OBJECT")
    hw.select_set(False)
    # The packer stops at 200 px/in, which would waste this small model's atlas, so it lays out a half-size atlas: same UVs, twice the cap.
    kit.pack_real_scale(hw.data, RES // 2, 2.5)
    mesh = hw.data
    uv = np.empty(len(mesh.loops) * 2)
    mesh.uv_layers["UVMap"].data.foreach_get("uv", uv)
    uv = uv.reshape(-1, 2)
    co = np.empty(len(mesh.vertices) * 3)
    mesh.vertices.foreach_get("co", co)
    co = co.reshape(-1, 3)
    mesh.calc_loop_triangles()
    area3 = uva = 0.0
    for tri in mesh.loop_triangles:
        a, b, c = co[list(tri.vertices)]
        area3 += 0.5 * np.linalg.norm(np.cross(b - a, c - a))
        p, q, r = uv[list(tri.loops)]
        uva += 0.5 * abs((q[0] - p[0]) * (r[1] - p[1]) - (r[0] - p[0]) * (q[1] - p[1]))
    density = RES * math.sqrt(uva / area3)
    print("tris", len(mesh.loop_triangles), "fill %.2f" % uva, "px/in %.1f" % density, flush=True)

    lookup = {round(p.rand, 4): p for p in kit.parts}

    def split(group, lod, keep, ratio):
        name = f"{MESH[group]}_lod{lod}"
        copy = hw.copy()
        copy.data = hw.data.copy()
        copy.name = copy.data.name = name
        bpy.context.scene.collection.objects.link(copy)
        bm = bmesh.new()
        bm.from_mesh(copy.data)
        facts = bm.loops.layers.float_color["facts"]
        drop = []
        for f in bm.faces:
            part = lookup[round(f.loops[0][facts][1], 4)]
            if part.group != group or part.lod < keep:
                drop.append(f)
        bmesh.ops.delete(bm, geom=drop, context="FACES")
        bm.to_mesh(copy.data)
        bm.free()
        if ratio < 1.0:
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
        print(name, "tris", len(copy.data.loop_triangles), flush=True)

    for group in GROUPS:
        split(group, 0, 0, 1.0)
        split(group, 1, 1, 0.5)
        if LODS[group] > 2:
            split(group, 2, 2, 0.16)
    np.save(os.path.join(WORK, "gr_edges.npy"), np.array(edge_lines, np.float32))
    with open(os.path.join(WORK, "flash.json"), "w") as h:
        json.dump(dict(density=density, res=RES, range=POS_RANGE, zc=ZC, radius=R), h)
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
    hw = bpy.data.objects["all_lod0"]
    for ob in scene.objects:
        ob.hide_render = ob is not hw
    world = bpy.data.worlds.new("bake")
    scene.world = world
    world.light_settings.distance = 1.2
    with open(os.path.join(WORK, "baked_uv_hash.txt"), "w") as h:
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

    def bake_one(size, kind, setup, samples, out):
        img = bpy.data.images.new(out, size, size, alpha=True, float_buffer=True)
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
        data = np.empty(size * size * 4, np.float32)
        img.pixels.foreach_get(data)
        np.save(os.path.join(WORK, out + ".npy"), data.reshape(size, size, 4))
        print("baked", out, flush=True)

    bake_one(RES, "EMIT", source("pos"), 1, "bake_gr_pos")
    bake_one(RES, "EMIT", source("nor"), 1, "bake_gr_nor")
    bake_one(RES, "EMIT", source("facts"), 1, "bake_gr_facts")
    bake_one(1024, "AO", None, 48, "bake_gr_ao")


def export_stage():
    bpy.ops.wm.open_mainfile(filepath=BLEND)
    os.makedirs(OUT, exist_ok=True)
    if uv_hash(bpy.data.objects["all_lod0"]) != open(os.path.join(WORK, "baked_uv_hash.txt")).read().strip():
        raise SystemExit("The build's UVs are not the ones the textures were baked on.")
    counts = {}
    for group in GROUPS:
        for lod in range(LODS[group]):
            ob = bpy.data.objects[f"{MESH[group]}_lod{lod}"]
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
                    for table, store, prefix, vec, digits in zip(tables, lines, ("v ", "vt ", "vn "), (p[i], t[i], n[i]), (6, 6, 5)):
                        key = tuple(np.round(vec, digits))
                        got = table.get(key)
                        if got is None:
                            got = len(table) + 1
                            table[key] = got
                            store.append(prefix + " ".join(f"{x:.{digits}f}" for x in key) + "\n")
                        idx.append(got)
                    tri.append("%d/%d/%d" % tuple(idx))
                faces.append("f " + " ".join(tri) + "\n")
            with open(os.path.join(OUT, f"{NAME}_{group}_lod{lod}.obj"), "w", newline="\n") as h:
                h.write(f"# Generated by Sources/Weapons/flashbang_v2/flash.py\nmtllib {NAME}.mtl\n")
                for block in lines:
                    h.writelines(block)
                h.write(f"usemtl {NAME}\n")
                h.writelines(faces)
            counts[f"{group}_lod{lod}"] = n_tris
            print("lod", group, lod, "tris", n_tris, flush=True)
    with open(os.path.join(OUT, f"{NAME}.mtl"), "w", newline="\n") as h:
        h.write(f"newmtl {NAME}\nKd 1 1 1\nd 1\n")
    all_meshes = [(group, lod) for group in GROUPS for lod in range(LODS[group])]
    meshes = ",\n".join(
        f'\t\t\t\t\t{{ _class = "RenderMeshFile" name = "{MESH[g]}_lod{l}" filename = "{FOLDER}/{NAME}_{g}_lod{l}.obj" '
        'import_translation = [ 0.0, 0.0, 0.0 ] import_rotation = [ 0.0, 0.0, 0.0 ] import_scale = 1.0 '
        'align_origin_x_type = "None" align_origin_y_type = "None" align_origin_z_type = "None" parent_bone = "" '
        "import_filter = { exclude_by_default = false exception_list = [ ] } }" for g, l in all_meshes
    )
    # 0, 4 and 8 are the old model's own switch distances.
    groups = ",\n".join(
        f'\t\t\t\t\t{{ _class = "LODGroup" switch_threshold = {t:.1f} meshes = [ ' + ", ".join(f'"{MESH[g]}_lod{l}"' for g in GROUPS if l < LODS[g]) + " ] }"
        for l, t in zip((0, 1, 2), (0.0, 4.0, 8.0))
    )

    def choice(name, group):
        items = ", ".join(f'"{MESH[group]}_lod{l}"' for l in range(LODS[group]))
        return f'{{ _class = "BodyGroupChoice" name = "{name}" meshes = [ {items} ] }}'

    bodies = ",\n".join(
        f'\t\t\t\t\t{{ _class = "BodyGroup" name = "{g}" children = [ {choice(g, g)}' + (f', {{ _class = "BodyGroupChoice" name = "none" meshes = [ ] }}' if g != "grenade" else "") + " ] hidden_in_tools = false }"
        for g in GROUPS
    )
    doc = f"""<!-- kv3 encoding:text:version{{e21c7f3c-8a33-41c5-9977-a76d3a32aa0d}} format:modeldoc29:version{{3cec427c-1b0e-4d48-a90a-0436f33a6041}} -->
// Generated by Sources/Weapons/flashbang_v2/flash.py
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
							{{ from = "{NAME}.vmat" to = "{FOLDER}/{NAME}.vmat" }}
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
				_class = "BodyGroupList"
				children =
				[
{bodies}
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
    vmat = f"""// Generated by Sources/Weapons/flashbang_v2/flash.py

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
print("flash stages done", flush=True)
