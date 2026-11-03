"""Writes canvas.py from Orion's tarp.py: python make_canvas_py.py. Each change must match exactly once, or nothing is written.

The cloth pipeline is the tarp pile's (Sources/Orion/tarp_pile_v2); what differs for Spillway's canvas cover is the load, the sheet,
the tucking walls, straps in place of ropes and sandbags, and the names.
"""
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
src = open(os.path.join(ROOT, "Sources", "Orion", "tarp_pile_v2", "tarp.py"), encoding="utf-8").read()


def swap(old, new, count=1):
    global src
    found = src.count(old)
    if found != count:
        raise SystemExit(f"expected {count} of {old[:70]!r}, found {found}")
    src = src.replace(old, new)


doc_end = src.index('"""', 3) + 3
src = '''"""Spillway's canvas cover v2: simulate the sheet, build its meshes, bake its facts and write its files. Made from Orion's tarp.py
(make_canvas_py.py writes this file), with the capture flag's mesh toolkit.

blender -b --factory-startup -t 4 --python canvas.py -- <work dir> <project root> <sim|clay|build|bake|export> ...

`spillway_map.equipment_cover` is a box of sagging cards on the B2 loading deck, which draws as a mustard crate. This is what it stands
for: an ochre cotton canvas thrown over a generator set on its skid, held down by two ratchet straps where the old strap boxes were. Its
folds come from Blender's cloth solver, run at real scale on the load's own shape. The load fills the old cover's collision box, which
stays: the model has no physics.
Inches, engine axes: on the deck under its middle. Its X is the map's n and its Y the map's -e, so it's placed with no turn.
"""''' + src[doc_end:]

swap("TARP, ROPE, BAG = 9, 10, 11", "TARP, STRAP, BUCKLE = 9, 10, 11")
swap('MODEL = "models/props/orion/tarp_pile_v2"', 'MODEL = "models/maps/spillway/canvas_cover_v2"')
swap('MATS = "materials/orion/tarp_pile_v2"', 'MATS = "materials/spillway/canvas_cover_v2"')
swap('BLEND = os.path.join(WORK, "tarp_build.blend")', 'BLEND = os.path.join(WORK, "canvas_build.blend")')
swap("SHEET_X, SHEET_Y = 196.0, 218.0  # A real tarp's cut size, inches: enough to reach the ground all round the load with some to spare.",
     "SHEET_X, SHEET_Y = 288.0, 300.0  # A 24 x 25 ft cover, inches: down to the deck all round the load with a little to spare.")
swap("PITCH = 2.2", "PITCH = 2.6")
swap("FRAMES = 190", "FRAMES = 230")
swap('''# What's under it, in inches. It fills the old pile's collision box: x +-32, y +-44, z 0 to 62.4.
BOXES = [((-31, -43, 0), (31, 43, 30)), ((-27, -41, 30), (27, -2, 58)), ((-24, 6, 30), (-2, 38, 46))]
DRUM = ((12.0, 22.0), 13.0, 30.0, 61.5)
RIVER = np.random.default_rng(4417)''', '''# What's under it, in inches: a generator set on its skid, the canopy, a housing on top and a fuel box at one end, and the exhaust
# silencer standing up beside it. It fills the old cover's collision box: x +-65, y +-70, z 0 to 90.
BOXES = [((-63, -68, 0), (63, 68, 9)), ((-58, -66, 9), (58, 38, 70)), ((-40, -58, 70), (30, -8, 84)), ((-52, 40, 9), (8, 66, 46))]
DRUM = ((28.0, 50.0), 13.0, 9.0, 89.5)
HALF = (65.0, 70.0)
RIVER = np.random.default_rng(6121)''')
swap('''# What stands by it in the map, in the model's axes: a bollard at one corner, which the cloth has to rest on. Fuel Processing's wall is about 70 in off at -y, which the walls below keep it short of.
BOLLARD = ((31.18, -48.05), 3.7, 0.0, 40.0)
SHEET_PX_PER_IN = 8.25''', '''# What's by it on the deck: its railings, 30 in off at -x (the map's south) and 40 in off at +y (its west). The walls stop short of both.
SHEET_PX_PER_IN = 6.0''')
swap('''    collider("bollard", *drum_mesh(BOLLARD), 8.0, 0.012)
''', "")
swap('''    for name, axis, sign, start, end, span in (("+x", 0, 1, 106.0, 44.0, 170), ("-x", 0, -1, 106.0, 44.0, 170), ("+y", 1, 1, 118.0, 57.0, 170), ("-y", 1, -1, 118.0, 57.0, 170)):
        wall = [(0, -span, 0), (0, span, 0), (0, span, 110), (0, -span, 110)] if axis == 0 else [(-span, 0, 0), (span, 0, 0), (span, 0, 110), (-span, 0, 110)]''',
     '''    for name, axis, sign, start, end, span in (("+x", 0, 1, 152.0, 76.0, 240), ("-x", 0, -1, 152.0, 76.0, 240), ("+y", 1, 1, 158.0, 81.0, 240), ("-y", 1, -1, 158.0, 81.0, 240)):
        wall = [(0, -span, 0), (0, span, 0), (0, span, 140), (0, -span, 140)] if axis == 0 else [(-span, 0, 0), (span, 0, 0), (span, 0, 140), (-span, 0, 140)]''')
swap('''        for frame, at in ((1, start), (46, start), (120, end), (138, end), (158, end + (6.0 if name == "-y" else 12.0))):''',
     '''        # They step back to 12 in off the load: inside the railings at -x and +y.
        for frame, at in ((1, start), (64, start), (150, end), (170, end), (192, end + 12.0)):''')
swap('''            x, y = (i / ni - 0.5) * SHEET_X + 1.5, (j / nj - 0.5) * SHEET_Y - 2.5''', '''            x, y = (i / ni - 0.5) * SHEET_X + 2.0, (j / nj - 0.5) * SHEET_Y - 3.0''')
swap('''            z = 66.0 + 2.2 * math.sin(x * 0.041 + 1.0) * math.sin(y * 0.033 + 0.4) + float(RIVER.uniform(-0.04, 0.04))''',
     '''            z = 97.0 + 2.6 * math.sin(x * 0.031 + 1.0) * math.sin(y * 0.027 + 0.4) + float(RIVER.uniform(-0.04, 0.04))''')
# Clay renders: ochre, and cameras for the bigger load.
swap('mat = bpy.data.materials.new("olive")', 'mat = bpy.data.materials.new("ochre")')
swap('inputs["Base Color"].default_value = (0.09, 0.11, 0.05, 1)', 'inputs["Base Color"].default_value = (0.32, 0.2, 0.06, 1)')
swap('''    for name, eye in (("a", (150, -150, 80)), ("b", (-170, 90, 100))):
        co.location = eye
        co.rotation_euler = (Vector((0, 0, 24)) - Vector(eye)).to_track_quat("-Z", "Y").to_euler()''',
     '''    for name, eye in (("a", (300, -250, 150)), ("b", (-300, 200, 170)), ("c", (330, 40, 60))):
        co.location = eye
        co.rotation_euler = (Vector((0, 0, 45)) - Vector(eye)).to_track_quat("-Z", "Y").to_euler()''')
# The straps: like the tarp's ropes, but flat webbing lying close, ending at hooks on the skid instead of on the hem.
swap('''def rope_over(tree, centre, across):''', '''def rope_over(tree, centre, across, lift=0.34, low=0.45):''')
swap('''    hull = convex_top([p for p in hits if a0 < p[0] < a1] + [(a0, 0.45), (a1, 0.45)])''', '''    hull = convex_top([p for p in hits if a0 < p[0] < a1] + [(a0, low), (a1, low)])''')
swap('''    path = path + normal * 0.34''', '''    path = path + normal * lift''')
swap('''    path3 = [Vector((centre[0], centre[1], 0.0)) + h * float(a) + Vector((0, 0, float(max(z, 0.3)))) for a, z in path]
    ends = [Vector((centre[0], centre[1], 0.0)) + h * float(path[k, 0]) for k in (0, -1)]''',
     '''    path3 = [Vector((centre[0], centre[1], 0.0)) + h * float(a) + Vector((0, 0, float(max(z, 0.3)))) for a, z in path]
    # A strap stops at its hooks on the skid, where the cloth comes down past it.
    keep = [k for k, p in enumerate(path3) if p.z > 7.0]
    path3 = path3[keep[0] : keep[-1] + 1]
    ends = [path3[0], path3[-1]]''')
sandbag_start = src.index("def sandbag(at, along):")
sandbag_end = src.index("def build_stage():")
src = src[:sandbag_start] + '''def buckle(tree, at, along):
    """A ratchet on the strap: its steel body lying on the cloth, the handle folded flat on it."""
    near = tree.find_nearest(at)
    out = near[1] if near[1].dot(at - Vector((0, 0, 45))) > 0 else -near[1]
    m = kit.frame(tuple(at + out * 0.75), tuple(out), tuple(along))
    kit.box(add(Part(BUCKLE, 2, bevel=0.06, angle=40, name="ratchet")), (-1.9, -1.35, -0.55), (1.9, 1.35, 0.55), m)
    kit.box(add(Part(BUCKLE, 1, bevel=0.04, angle=40, name="ratchet handle")), (-1.0, -1.1, 0.55), (3.6, 1.1, 0.85), m)


def hook(at, out):
    """The strap's flat hook, caught under the skid's edge."""
    m = kit.frame(tuple(at), (0, 0, 1), (out.x, out.y, 0))
    kit.box(add(Part(BUCKLE, 1, bevel=0.04, angle=40, name="hook")), (-0.4, -1.1, -5.0), (0.4, 1.1, 0.4), m)


''' + src[sandbag_end:]
swap('''    # A corner the walls left standing lies down: nothing past the sides' fall stands higher than a ripple.
    off = np.maximum(np.maximum(np.abs(flat[:, 0]) - 31.0, np.abs(flat[:, 1]) - 43.0), 0.0)''',
     '''    # A corner the walls left standing lies down: nothing past the sides' fall stands higher than a ripple.
    off = np.maximum(np.maximum(np.abs(flat[:, 0]) - HALF[0], np.abs(flat[:, 1]) - HALF[1]), 0.0)''')
swap('''    cap = 60.0 * np.clip(1.0 - off / 15.5, 0.0, 1.0) + ripple''', '''    cap = 91.0 * np.clip(1.0 - off / 15.5, 0.0, 1.0) + ripple''')
bulge_start = src.index("    # The tucking wall can shove the sheet through something as thin as the bollard.")
bulge_end = src.index("    tree = BVHTree.FromPolygons([tuple(p) for p in flat], faces)")
src = src[:bulge_start] + src[bulge_end:]
swap('''    # Three ropes: two across and one along. Each ends under a sandbag.
    ropes = [rope_over(tree, (0.0, -24.0), (1, 0.03)), rope_over(tree, (0.0, 20.0), (1, -0.02)), rope_over(tree, (2.0, 0.0), (0.02, 1))]''',
     '''    # Two straps across, along X, where the old strap boxes were (the map's e 1500 and 1600).
    ropes = [rope_over(tree, (0.0, 47.0), (1, 0.015), lift=0.2, low=4.0), rope_over(tree, (0.0, -49.0), (1, -0.02), lift=0.2, low=4.0)]''')
swap('''            if d < 2.1:
                grid[j, i] -= nor[j, i] * 0.5 * (1 - d / 2.1) ** 2''', '''            if d < 1.8:
                grid[j, i] -= nor[j, i] * 0.35 * (1 - d / 1.8) ** 2''')
check_start = src.index("    # Is the bollard really under the cloth now?")
check_end = src.index("    # A torn or dragged sheet shows as an edge far longer")
src = src[:check_start] + '''    final = BVHTree.FromPolygons([tuple(p) for p in inner.reshape(-1, 3)], faces)
''' + src[check_end:]
swap('''    print("bollard check: longest cloth edge %.1f in" % longest, flush=True)''', '''    print("longest cloth edge %.1f in" % longest, flush=True)
    print("sheet bounds", inner.reshape(-1, 3).min(0).round(1), inner.reshape(-1, 3).max(0).round(1), flush=True)''')
swap('''    if longest > 14.0:''', '''    if longest > 16.0:''')
swap('''    for path, ends, h in ropes:
        tube(add(Part(ROPE, 1, name="rope")), path, 0.27, 6)
        for k, end in enumerate(ends):
            # Rope lands on the hem, and the bag sits on its end, across it and a little askew.
            out = h * (1 if k else -1)
            spread = float(RIVER.uniform(-0.5, 0.5))
            sandbag(end + out * 1.5, (-out.y + out.x * spread, out.x + out.y * spread))''',
     '''    for path, ends, h in ropes:
        # Two-inch polyester webbing, flat on the cloth.
        tube(add(Part(STRAP, 3, name="strap")), path, 1.0, 8, flatten=0.1)
        for k, end in enumerate(ends):
            hook(end, h * (1 if k else -1))
        # The ratchet halfway down the +X side, the map's north, where it was pulled tight from.
        side = [p for p in path if (p - Vector((0, 0, 0))).dot(h) > 0]
        at = min(side, key=lambda p: abs(p.z - 44.0))
        k = path.index(at)
        buckle(final, at, tuple((path[min(k + 1, len(path) - 1)] - path[max(k - 1, 0)]).normalized()))''')
# The engine lights a face's back as if it faced the way its front does, so cloth seen from its inner side draws dark. The tarp turned
# over only folds lying upside down on the floor; on this taller load, folds of the skirt that turn over showed as dark blots. So every
# face turns to face away from the load (cloth lying on the deck faces up), which is the side anyone can see.
swap('''    bmesh.ops.reverse_faces(bm, faces=[f for f in bm.faces if f.normal.z < -0.25 and f.calc_center_median().z < 16.0], flip_multires=False)''',
     """    def facing_in(f):
        c = f.calc_center_median()
        if c.z < 5.0:
            return f.normal.z < -0.25
        near = Vector((min(max(c.x, -HALF[0]), HALF[0]), min(max(c.y, -HALF[1]), HALF[1]), min(max(c.z, 0.0), 90.0)))
        out = c - near
        if out.length < 0.5:
            out = Vector((0, 0, 1))
        return f.normal.dot(out.normalized()) < -0.2

    turned = [f for f in bm.faces if facing_in(f)]
    bmesh.ops.reverse_faces(bm, faces=turned, flip_multires=False)
    print("faces turned to face out:", len(turned), "of", len(bm.faces), flush=True)""")
swap('hw = kit.join_parts(kit.parts, "tp_lod0")', 'hw = kit.join_parts(kit.parts, "cc_lod0")')
swap('lod("tp_lod1", 1, 0.42)', 'lod("cc_lod1", 1, 0.42)')
swap('lod("tp_lod2", 2, 0.14)', 'lod("cc_lod2", 2, 0.14)')
swap('with open(os.path.join(WORK, "tarp.json"), "w") as h:', 'with open(os.path.join(WORK, "canvas.json"), "w") as h:')
swap('hw = bpy.data.objects["tp_lod0"]', 'hw = bpy.data.objects["cc_lod0"]')
swap('"baked_uv_hash.txt"', '"canvas_baked_uv_hash.txt"', 2)
for kind in ("pos", "nor", "facts", "sheet", "ao"):
    swap(f'"bake_tp_{kind}"', f'"bake_cc_{kind}"')
swap('if uv_hash(bpy.data.objects["tp_lod0"])', 'if uv_hash(bpy.data.objects["cc_lod0"])')
swap('ob = bpy.data.objects[f"tp_lod{lod}"]', 'ob = bpy.data.objects[f"cc_lod{lod}"]')
swap("tarp_pile_lod{lod}.obj", "canvas_cover_lod{lod}.obj")
swap('h.write("# Generated by Sources/Orion/tarp_pile_v2/tarp.py\\nmtllib tarp_pile.mtl\\n")', 'h.write("# Generated by Sources/Spillway/canvas-cover-v2/canvas.py\\nmtllib canvas_cover.mtl\\n")')
swap('h.write("usemtl tp_tarp\\n")', 'h.write("usemtl cc_canvas\\n")')
swap('"tarp_pile.mtl"), "w", newline="\\n") as h:\n        h.write("newmtl tp_tarp\\nKd 1 1 1\\nd 1\\n")', '"canvas_cover.mtl"), "w", newline="\\n") as h:\n        h.write("newmtl cc_canvas\\nKd 1 1 1\\nd 1\\n")')
swap('filename = "{MODEL}/tarp_pile_lod{l}.obj"', 'filename = "{MODEL}/canvas_cover_lod{l}.obj"')
swap("zip(counts, (0.0, 28.0, 80.0))", "zip(counts, (0.0, 30.0, 90.0))")
swap("// Generated by Sources/Orion/tarp_pile_v2/tarp.py", "// Generated by Sources/Spillway/canvas-cover-v2/canvas.py", 2)
swap('{{ from = "tp_tarp.vmat" to = "{MATS}/tp_tarp.vmat" }}', '{{ from = "cc_canvas.vmat" to = "{MATS}/cc_canvas.vmat" }}')
swap('"tarp_pile.vmdl"', '"canvas_cover.vmdl"')
for map_name in ("ao", "color", "metal", "normal", "rough"):
    swap(f'"{{MATS}}/tp_tarp_{map_name}.png"', f'"{{MATS}}/cc_canvas_{map_name}.png"')
swap('os.path.join(mats, "tp_tarp.vmat")', 'os.path.join(mats, "cc_canvas.vmat")')
swap('print("tarp stages done", flush=True)', 'print("canvas stages done", flush=True)')
for word in ("bollard", "BOLLARD", "sandbag", "tp_", "tarp_pile"):
    if word in src:
        lines = [l for l in src.split("\n") if word in l]
        raise SystemExit(f"left over {word!r}: {lines[:3]}")
open(os.path.join(HERE, "canvas.py"), "w", encoding="utf-8", newline="\n").write(src)
print("wrote canvas.py")
