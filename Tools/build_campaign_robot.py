"""Build the campaign combat robot on the soldiers' rigged_human skeleton.

Run with Blender 5.1:  blender -b --python Tools/build_campaign_robot.py
or in a running Blender: exec(compile(open(p).read(), p, "exec"), {"__file__": p, "__name__": "__main__"})
The build empties the open .blend first, so in a running Blender use a new file (see reset_scene).

The skeleton is imported from the CT soldier's FBX and exported again unchanged (Blender round-trips its
bind pose exactly; the armature object itself does not become a bone in ModelDoc), so the robot uses the
soldiers' animation list, hitboxes, ragdoll, IK and `rigged_human.vanmgrph`.
Every part is rigid on one bone. ModelDoc drops bones with no skinned vertices, so the robot puts geometry
on exactly the 72 bones the soldier keeps (KEEP_BONES). The soldiers' clips don't animate the twist,
elbow, eye or penis bones, so those ride rigidly with their parents and carry ordinary robot parts.
Units while modelling: centimetres, world space, the robot faces -Y with its left side at +X.
"""
import bpy
import bmesh
import json
import math
import random
import struct
import tempfile
import zlib
from pathlib import Path

import numpy as np
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree

SCRIPT = Path(globals().get("__file__") or r"D:\Documents\s&box projects\hc1\forked-shooter-main\Tools\build_campaign_robot.py").resolve()
ROOT = SCRIPT.parents[1]
SKELETON_FBX = ROOT / "Assets/models/player/ct_side/ct_side_player_01/ct_side_player_01_V2.fbx"
OUT = ROOT / "Assets/models/campaign/robot"
ASSET = "models/campaign/robot"
NAME = "combat_robot"
STAGES = globals().get("ROBOT_STAGES", "all")
# Preview and beauty renders go outside the project unless PREVIEW_DIR says otherwise.
PREVIEW_DIR = Path(globals().get("PREVIEW_DIR") or Path(tempfile.gettempdir()) / "combat_robot_preview")

KEEP_BONES = """pelvis r_hip r_knee r_foot r_knee_twist_02 r_foot_twist_01 r_hip_twist_02 l_hip l_knee l_foot
l_knee_twist_02 l_foot_twist_01 l_hip_twist_02 spine1 spine2 spine3 l_clavicle l_upperarm l_forearm l_hand neck
head r_clavicle r_upperarm r_forearm r_hand r_toe r_knee_twist_01 r_hip_twist_01 l_toe l_hip_twist_01 l_thumb1
l_thumb2 l_thumb3 l_index1 l_index2 l_index3 l_little1 l_little2 l_little3 l_middle1 l_middle2 l_middle3 l_ring1
l_ring2 l_ring3 l_elbow l_forearm_twist_01 l_upperarmtwist_02 l_upperarmtwist_01 r_eye l_eye r_thumb1 r_thumb2
r_thumb3 r_index1 r_index2 r_index3 r_little1 r_little2 r_little3 r_middle1 r_middle2 r_middle3 r_ring1 r_ring2
r_ring3 r_forearm_twist_02 r_elbow r_upperarm_twist_01 r_upperarm_twist_02 penis""".split()

# Bones whose names differ by side, or which only survive on one side in the soldier model.
UPPERARM_TWIST = {"l": ("l_upperarmtwist_01", "l_upperarmtwist_02"), "r": ("r_upperarm_twist_01", "r_upperarm_twist_02")}
WRIST_BONE = {"l": "l_forearm_twist_01", "r": "r_forearm_twist_02"}
CALF_BONE = {"l": "l_knee", "r": "r_knee_twist_01"}

# Surface types: preview colour (linear), roughness, metalness. The bake turns them into the texture atlas.
SURFACES = {
    "armor": ((0.50, 0.50, 0.46), 0.5, 0.0),
    "accent": ((0.72, 0.20, 0.035), 0.45, 0.0),
    "dark": ((0.045, 0.048, 0.052), 0.45, 0.35),
    "steel": ((0.42, 0.43, 0.45), 0.28, 1.0),
    "rubber": ((0.018, 0.018, 0.018), 0.85, 0.0),
    "glass": ((0.006, 0.008, 0.01), 0.06, 0.0),
    "glow": ((1.0, 0.12, 0.03), 0.3, 0.0),
}

PARTS = []
PART_INFO = []  # (name, bone, surface) per part index, kept once the parts are joined
MATS = {}
COLL = None
ARM = None
ROBOT = None  # the joined mesh object

TEX = globals().get("ROBOT_TEX", 2048)  # atlas size
POS_LO, POS_SPAN = Vector((-1.2, -1.2, -0.1)), 2.4  # bake encoding of positions (metres) into 0..1


# ---------------------------------------------------------------------------------------------------------
# Scene setup


def reset_scene():
    """Empty the open .blend. Only a new file, an earlier build or the robot's own .blend is emptied without
    ROBOT_FORCE_RESET, so running this in a file with other work in it fails instead of deleting that work.
    (bpy.data.is_dirty can't tell: edits made by scripts don't set it.)"""
    keep = bpy.context.window.scene if bpy.context.window else bpy.context.scene
    fresh = (not bpy.data.filepath and len(bpy.data.scenes) == 1
             and {o.name for o in bpy.data.objects} <= {"Cube", "Camera", "Light"})
    own_file = bool(bpy.data.filepath) and Path(bpy.data.filepath).resolve() == (OUT / f"{NAME}.blend").resolve()
    earlier_build = keep.get("combat_robot_build") and len(bpy.data.scenes) == 1
    if not (fresh or own_file or earlier_build or globals().get("ROBOT_FORCE_RESET")):
        raise RuntimeError("The robot builder empties the open .blend. Run it in a new file, or set "
                           "ROBOT_FORCE_RESET to empty this one.")
    if bpy.context.object and bpy.context.object.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")
    for scene in list(bpy.data.scenes):
        if scene != keep:
            bpy.data.scenes.remove(scene)
    for data in (bpy.data.objects, bpy.data.meshes, bpy.data.armatures, bpy.data.materials, bpy.data.actions,
                 bpy.data.cameras, bpy.data.lights, bpy.data.curves, bpy.data.node_groups, bpy.data.textures,
                 bpy.data.worlds):
        for item in list(data):
            data.remove(item)
    for image in list(bpy.data.images):
        if image.type == "IMAGE":
            bpy.data.images.remove(image)
    for coll in list(bpy.data.collections):
        bpy.data.collections.remove(coll)
    keep.name = "Robot"
    keep["combat_robot_build"] = True
    return keep


def load_skeleton(scene):
    global ARM
    bpy.ops.import_scene.fbx(filepath=str(SKELETON_FBX))
    arm = next(o for o in scene.objects if o.type == "ARMATURE")
    for obj in list(scene.objects):
        if obj is not arm:
            bpy.data.objects.remove(obj, do_unlink=True)
    for data in (bpy.data.meshes, bpy.data.materials, bpy.data.images, bpy.data.actions):
        for item in list(data):
            if item.users == 0:
                data.remove(item)
    arm.animation_data_clear()
    for pb in arm.pose.bones:
        pb.matrix_basis = Matrix.Identity(4)
    arm.name = arm.data.name = "robot_rig"
    arm.data.display_type = "STICK"
    arm.show_in_front = True
    ARM = arm
    return arm


def J(bone):
    """Bone head in world centimetres."""
    return (ARM.matrix_world @ ARM.data.bones[bone].head_local) * 100.0


def make_materials():
    for surf, (color, rough, metal) in SURFACES.items():
        mat = bpy.data.materials.new(f"robot_{surf}")
        mat.diffuse_color = (*color, 1.0)
        mat.roughness = rough
        mat.metallic = metal
        bsdf = mat.node_tree.nodes.get("Principled BSDF")
        bsdf.inputs["Base Color"].default_value = (*color, 1.0)
        bsdf.inputs["Roughness"].default_value = rough
        bsdf.inputs["Metallic"].default_value = metal
        if surf == "glow":
            bsdf.inputs["Emission Color"].default_value = (*color, 1.0)
            bsdf.inputs["Emission Strength"].default_value = 6.0
        MATS[surf] = mat


# ---------------------------------------------------------------------------------------------------------
# Geometry helpers (centimetres)


class Frame:
    """Origin plus an axis `a`, a forward-ish `f` and an outward-ish `w`, orthonormal. p(t, f, w)."""

    def __init__(self, origin, axis, fwd, out):
        self.o = Vector(origin)
        self.a = Vector(axis).normalized()
        f = Vector(fwd)
        self.f = (f - f.dot(self.a) * self.a).normalized()
        w = self.a.cross(self.f)
        self.w = w if w.dot(Vector(out)) >= 0 else -w

    def p(self, t, f=0.0, w=0.0):
        return self.o + self.a * t + self.f * f + self.w * w


WORLD = Frame((0, 0, 0), (0, 0, 1), (0, -1, 0), (1, 0, 0))  # t = z, f = -y (front), w = x (robot's left)


def sec(fr, t, f0, f1, w0, w1, ch=None):
    """Chamfered rectangle across the frame axis at t, spanning f0..f1 and w0..w1."""
    if ch is None:
        ch = 0.3 * min(f1 - f0, w1 - w0)
    ch = min(ch, 0.49 * (f1 - f0), 0.49 * (w1 - w0))
    pts = [(f0 + ch, w0), (f1 - ch, w0), (f1, w0 + ch), (f1, w1 - ch),
           (f1 - ch, w1), (f0 + ch, w1), (f0, w1 - ch), (f0, w0 + ch)]
    return [fr.p(t, a, b) for a, b in pts]


def dedupe(points, eps=1e-4):
    out = []
    for p in points:
        if all((p - q).length > eps for q in out):
            out.append(Vector(p))
    return out


def new_part(name, bone, surf, bm, bevel=0.0, segments=1, smooth=True, sharp=38):
    assert bone in KEEP_BONES, bone
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    me.transform(Matrix.Scale(0.01, 4))
    obj = bpy.data.objects.new(name, me)
    COLL.objects.link(obj)
    obj["bone"] = bone
    obj["surf"] = surf
    me.materials.append(MATS[surf])
    if smooth:
        me.shade_smooth()
        me.set_sharp_from_angle(angle=math.radians(sharp))
    if bevel > 0:
        mod = obj.modifiers.new("bevel", "BEVEL")
        mod.width = bevel * 0.01
        mod.segments = segments
        mod.limit_method = "ANGLE"
        mod.angle_limit = math.radians(32)
        mod.miter_outer = "MITER_ARC"
    wn = obj.modifiers.new("weighted normals", "WEIGHTED_NORMAL")
    wn.keep_sharp = True
    wn.weight = 60
    PARTS.append(obj)
    return obj


def hull(name, bone, surf, points, bevel=0.3, segments=1, sharp=38):
    bm = bmesh.new()
    for p in dedupe(points):
        bm.verts.new(p)
    res = bmesh.ops.convex_hull(bm, input=bm.verts[:], use_existing_faces=False)
    loose = {g for g in res["geom_interior"] + res["geom_unused"] if isinstance(g, bmesh.types.BMVert) and g.is_valid}
    loose |= {v for v in bm.verts if not v.link_faces}
    if loose:
        bmesh.ops.delete(bm, geom=list(loose), context="VERTS")
    bmesh.ops.dissolve_limit(bm, angle_limit=math.radians(1.5), verts=bm.verts[:], edges=bm.edges[:])
    return new_part(name, bone, surf, bm, bevel, segments, sharp=sharp)


def stack(name, bone, surf, fr, sections, bevel=0.3, extra=(), segments=1):
    """Convex hull of chamfered sections: (t, f0, f1, w0, w1[, ch])."""
    pts = list(extra)
    for s in sections:
        pts += sec(fr, *s)
    return hull(name, bone, surf, pts, bevel, segments)


def lerp(a, b, x):
    return a + (b - a) * x


def tri(x, c=0.5, w=0.5):
    """Tent function: 1 at c, falling to 0 at c +- w."""
    return max(0.0, 1.0 - abs(x - c) / w)


def prof(*pts):
    """Smooth curve (cubic Hermite, finite-difference tangents) through (x, y) points; clamped outside."""
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    n = len(xs)

    def slope(i):
        a, b = max(i - 1, 0), min(i + 1, n - 1)
        return (ys[b] - ys[a]) / (xs[b] - xs[a])

    def f(x):
        if x <= xs[0]:
            return ys[0]
        if x >= xs[-1]:
            return ys[-1]
        i = max(k for k in range(n - 1) if xs[k] <= x)
        h = xs[i + 1] - xs[i]
        k = (x - xs[i]) / h
        k2, k3 = k * k, k * k * k
        return ((2 * k3 - 3 * k2 + 1) * ys[i] + (k3 - 2 * k2 + k) * h * slope(i)
                + (-2 * k3 + 3 * k2) * ys[i + 1] + (k3 - k2) * h * slope(i + 1))
    return f


def superellipse(fr, t, a, rf, rw, ex):
    c, s = math.cos(a), math.sin(a)
    return fr.p(t, math.copysign(abs(c) ** (2 / ex), c) * rf, math.copysign(abs(s) ** (2 / ex), s) * rw)


def wrap(name, bone, surf, fr, t, th, r, thick=0.8, nu=16, nv=10, ex=2.0, bevel=0.12, segments=1, sharp=30):
    """Curved armour plate `thick` deep, wrapped round the frame axis; u runs across it and v along it (0..1).
    t(u, v): position along fr.a.  th(u, v): angle round the axis (0 = fr.f, pi/2 = fr.w).
    r(u, v, t): (f, w) radii of the superellipse section the plate's outer face lies on.
    Every vertex keeps where it is on the plate for the texture bake: "puv" = (u, v, 1) as fractions of the
    arc lengths across and along, "plen" = (those arc lengths in cm, 0). The plate is unwrapped by the same
    arc lengths, one island per face and side wall ("pside": 1 outer, 2 inner, 3 wall)."""
    bm = bmesh.new()
    puv = bm.verts.layers.float_vector.new("puv")
    plen = bm.verts.layers.float_vector.new("plen")
    uv = bm.loops.layers.uv.new("UVMap")
    pside = bm.faces.layers.int.new("pside")
    grid = []
    for j in range(nv + 1):
        v = j / nv
        row = []
        for i in range(nu + 1):
            u = i / nu
            tt = t(u, v)
            rf, rw = r(u, v, tt)
            outer = superellipse(fr, tt, th(u, v), rf, rw, ex)
            axis_pt = fr.o + fr.a * tt
            n = (outer - axis_pt).normalized()
            row.append((bm.verts.new(outer), bm.verts.new(outer - n * thick)))
        grid.append(row)
    across = [[0.0] for _ in range(nv + 1)]
    along = [[0.0] * (nu + 1)]
    for j in range(nv + 1):
        for i in range(nu):
            across[j].append(across[j][-1] + (grid[j][i + 1][0].co - grid[j][i][0].co).length)
        if j:
            along.append([along[-1][i] + (grid[j][i][0].co - grid[j - 1][i][0].co).length for i in range(nu + 1)])
    for j in range(nv + 1):
        for i in range(nu + 1):
            lu, lv = across[j][-1], along[-1][i]
            for vert in grid[j][i]:
                vert[puv] = (across[j][i] / lu, along[j][i] / lv, 1.0)
                vert[plen] = (lu, lv, 0.0)

    def face(verts, uvs, kind):
        f = bm.faces.new([vert for vert, _ in verts])
        f[pside] = kind
        for loop, (_, (x, y)) in zip(f.loops, verts):
            loop[uv].uv = uvs(x, y)

    def su(j, i):
        return across[j][i] / 100.0

    def sv(j, i):
        return along[j][i] / 100.0
    depth = thick / 100.0
    for j in range(nv):
        for i in range(nu):
            corners = ((j, i), (j, i + 1), (j + 1, i + 1), (j + 1, i))
            face([(grid[a][b][0], (su(a, b), sv(a, b))) for a, b in corners], lambda x, y: (x, y), 1)
            face([(grid[a][b][1], (su(a, b), sv(a, b))) for a, b in reversed(corners)], lambda x, y: (-x, y), 2)
    for j in range(nv):
        for i in (0, nu):
            a, d = grid[j][i], grid[j + 1][i]
            face([(a[0], (sv(j, i), 0)), (d[0], (sv(j + 1, i), 0)), (d[1], (sv(j + 1, i), depth)),
                  (a[1], (sv(j, i), depth))], lambda x, y: (x, y), 3)
    for i in range(nu):
        for j in (0, nv):
            a, b = grid[j][i], grid[j][i + 1]
            face([(a[0], (su(j, i), 0)), (a[1], (su(j, i), depth)), (b[1], (su(j, i + 1), depth)),
                  (b[0], (su(j, i + 1), 0))], lambda x, y: (-x, y), 3)
    return new_part(name, bone, surf, bm, bevel, segments, sharp=sharp)


def sloft(name, bone, surf, fr, ts, section, bevel=0.15, segments=1, sharp=40):
    """Solid lofted through closed sections along the frame axis: section(t) -> [(f, w), ...], same length each t.
    Unlike a hull it can be concave along its length (an instep, a waist)."""
    bm = bmesh.new()
    loops = [[bm.verts.new(fr.p(t, f, w)) for f, w in section(t)] for t in ts]
    n = len(loops[0])
    for a, b in zip(loops, loops[1:]):
        for i in range(n):
            j = (i + 1) % n
            bm.faces.new((a[i], a[j], b[j], b[i]))
    bm.faces.new(list(reversed(loops[0])))
    bm.faces.new(loops[-1])
    return new_part(name, bone, surf, bm, bevel, segments, sharp=sharp)


def rings_hull(name, bone, surf, fr, rings, seg=16, ex=2.0, **kw):
    """Convex hull of superellipse rings (t, centre_f, centre_w, rf, rw) across the frame axis."""
    pts = []
    for t, cf, cw, rf, rw in rings:
        for i in range(seg):
            p = superellipse(fr, t, math.tau * (i + 0.5) / seg, rf, rw, ex)
            pts.append(p + fr.f * cf + fr.w * cw)
    return hull(name, bone, surf, pts, **kw)


def perpendicular(axis):
    helper = Vector((0, 0, 1)) if abs(axis.z) < 0.9 else Vector((1, 0, 0))
    u = axis.cross(helper).normalized()
    return u, axis.cross(u).normalized()


def loft(name, bone, surf, rings, seg=16, bevel=0.0, cap=True, segments=1):
    """rings: (centre, axis, radius_u, radius_v[, exponent]) cross-sections, superellipse profile."""
    bm = bmesh.new()
    loops = []
    for ring in rings:
        c, axis, ru, rv = Vector(ring[0]), Vector(ring[1]).normalized(), ring[2], ring[3]
        e = ring[4] if len(ring) > 4 else 2.0
        u, v = perpendicular(axis)
        loop = []
        for i in range(seg):
            th = math.tau * (i + 0.5) / seg
            cu, sv = math.cos(th), math.sin(th)
            x = math.copysign(abs(cu) ** (2 / e), cu) * ru
            y = math.copysign(abs(sv) ** (2 / e), sv) * rv
            loop.append(bm.verts.new(c + u * x + v * y))
        loops.append(loop)
    for a, b in zip(loops, loops[1:]):
        for i in range(seg):
            j = (i + 1) % seg
            bm.faces.new((a[i], a[j], b[j], b[i]))
    if cap:
        bm.faces.new(list(reversed(loops[0])))
        bm.faces.new(loops[-1])
    return new_part(name, bone, surf, bm, bevel, segments)


def cyl(name, bone, surf, a, b, r1, r2=None, seg=12, bevel=0.1):
    a, b = Vector(a), Vector(b)
    axis = b - a
    return loft(name, bone, surf, [(a, axis, r1, r1), (b, axis, r2 or r1, r2 or r1)], seg=seg, bevel=bevel)


def sphere(name, bone, surf, c, r, seg=14, rings=8):
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=rings, radius=r)
    bmesh.ops.translate(bm, vec=Vector(c), verts=bm.verts[:])
    return new_part(name, bone, surf, bm)


def box(name, bone, surf, fr, t0, t1, f0, f1, w0, w1, bevel=0.1, ch=0.0):
    return stack(name, bone, surf, fr, [(t0, f0, f1, w0, w1, ch), (t1, f0, f1, w0, w1, ch)], bevel=bevel)


def surface_hit(obj, origin, direction):
    """Ray-cast a part's base mesh (world cm). Returns (point, normal) or None."""
    me = obj.data
    bm = bmesh.new()
    bm.from_mesh(me)
    bm.transform(Matrix.Scale(100.0, 4))
    tree = BVHTree.FromBMesh(bm)
    hit = tree.ray_cast(Vector(origin), Vector(direction).normalized())
    bm.free()
    if hit[0] is None:
        return None
    return hit[0], hit[1]


def on_surface(target, origin, direction, up_hint):
    """A Frame sitting on a part's surface: a = surface normal, f = up_hint along the surface."""
    p, n = surface_hit(target, origin, direction)
    side = n.cross(Vector(up_hint))
    return Frame(p, n, up_hint, side if side.length > 1e-6 else Vector((1, 0, 0)))


# ---------------------------------------------------------------------------------------------------------
# Body


def sides():
    return (("l", 1), ("r", -1))


def span(s, inner, outer):
    """World-x interval from `inner` to `outer` on side s (1 = left, -1 = right)."""
    return (inner, outer) if s > 0 else (-outer, -inner)


def rad(deg):
    return math.radians(deg)


def build_torso():
    W = WORLD
    CH = Frame((0, -1.0, 0), (0, 0, 1), (0, -1, 0), (1, 0, 0))  # chest axis, a little in front of the spine
    # Chest section radii (front, back, half-width); the armour shells lie on them and the dark
    # ribcage sits just inside, showing in the seams and under the arms.
    rf = prof((113, 8.8), (118, 10.6), (124, 12.2), (130, 13.0), (136, 12.4), (140, 10.8), (144, 8.4))
    rb = prof((117, 9.2), (124, 10.8), (130, 11.6), (136, 11.4), (142, 9.8))
    rw = prof((113, 10.0), (118, 11.6), (124, 13.4), (130, 14.6), (136, 15.0), (140, 14.3), (144, 12.6))
    rings = []
    for z in (113.6, 116.5, 120.0, 124.0, 128.0, 132.0, 136.0, 139.5, 142.6):
        front, back = rf(z) - 1.7, rb(z) - 1.5
        rings.append((z, (front - back) / 2, 0.0, (front + back) / 2, rw(z) - 1.7))
    rings_hull("ribcage", "spine3", "dark", CH, rings, seg=20, ex=2.6, bevel=0.0, sharp=50)

    # Breastplate: one keeled shell, cut in a V at the bottom so the chest tapers into the waist.
    wrap("breastplate", "spine3", "armor", CH,
         t=lambda u, v: lerp(114.8 + 9.0 * abs(2 * u - 1) ** 1.3, 142.8 - 2.2 * tri(u, 0.5, 0.28), v),
         th=lambda u, v: (2 * u - 1) * rad(lerp(78, 97, v)),
         r=lambda u, v, t: (rf(t) * (1 + 0.07 * tri(u, 0.5, 0.2)), rw(t)),
         thick=1.2, nu=20, nv=10, ex=2.6, bevel=0.15)
    wrap("back_plate", "spine3", "armor", CH,
         t=lambda u, v: lerp(118.6 + 1.6 * abs(2 * u - 1), 142.2 - 1.2 * tri(u, 0.5, 0.3), v),
         th=lambda u, v: math.pi + (2 * u - 1) * rad(lerp(70, 78, v)),
         r=lambda u, v, t: (rb(t), rw(t) - 0.2),
         thick=1.0, nu=16, nv=8, ex=2.6, bevel=0.12)

    # Gorget round the neck socket, and yoke plates arching over the shoulders from chest to back.
    cyl("collar", "spine3", "dark", (0, 1.6, 140.8), (0, 1.2, 146.6), 7.0, 6.2, seg=16, bevel=0.15)
    for side, s in sides():
        TR = Frame((s * 4.0, 0.8, 136.0), (s, 0, 0), (0, 0, 1), (0, -1, 0))  # f = up, w = forward
        up = prof((0, 11.4), (5, 10.6), (9, 8.8), (13.4, 6.6))
        fb = prof((0, 9.0), (5, 9.4), (9, 9.0), (13.4, 7.6))
        wrap(f"yoke_{side}", f"{side}_clavicle", "armor", TR,
             t=lambda u, v: lerp(0.8, 13.4, v),
             th=lambda u, v: rad(lerp(-74, 48, u)),
             r=lambda u, v, t: (up(t), fb(t)),
             thick=1.6, nu=14, nv=8, ex=2.4, bevel=0.15)

    # Power pack on the back plate.
    pack = stack("pack", "spine3", "armor", W, [
        (120.2, -17.4, -10.0, -9.0, 9.0, 2.4),
        (136.2, -18.2, -10.0, -9.8, 9.8, 2.8),
        (140.4, -14.6, -10.0, -8.0, 8.0, 2.4),
    ], bevel=0.3, segments=2)
    for i, w in enumerate((-4.5, -1.5, 1.5, 4.5)):
        box(f"fin{i}", "spine3", "dark", W, 124.8, 135.4, -19.8, -17.6, w - 0.35, w + 0.35, bevel=0.0)
    for side, s in sides():
        cyl(f"cell_{side}", "spine3", "dark", (s * 10.4, 14.0, 120.6), (s * 10.4, 14.2, 136.0), 2.5, seg=12)
        for k, (z0, z1) in enumerate(((120.0, 121.6), (134.8, 136.4))):
            cyl(f"cell_{side}_cap{k}", "spine3", "steel", (s * 10.4, 14.0, z0), (s * 10.4, 14.1, z1), 2.75, seg=12)
        box(f"exhaust_{side}", "spine3", "dark", W, 138.8, 142.6, -15.6, -11.6, *span(s, 2.2, 6.4), bevel=0.1, ch=0.6)
    fr = on_surface(pack, W.p(123.6, -40, 0), W.f, (0, 0, 1))
    stack("core_frame", "spine3", "dark", fr, [(-0.8, -2.2, 2.2, -4.2, 4.2, 0.6), (0.4, -2.0, 2.0, -4.0, 4.0, 0.6)], bevel=0.08)
    box("core", "spine3", "glow", fr, 0.2, 0.6, -0.9, 0.9, -3.0, 3.0, bevel=0.0)

    # Waist: dark core segments with shingled plates in front and vertebrae behind.
    AB = Frame((0, -0.2, 0), (0, 0, 1), (0, -1, 0), (1, 0, 0))
    af = prof((99.0, 7.0), (104.0, 7.6), (109.0, 7.6), (114.0, 8.0), (118.5, 8.6))
    aw = prof((99.0, 8.8), (104.0, 9.2), (109.0, 9.0), (114.0, 9.4), (118.5, 10.0))

    def waist_rings(zs):
        return [(z, (af(z) - 7.0) / 2, 0.0, (af(z) + 7.0) / 2, aw(z)) for z in zs]
    rings_hull("abdomen_lower", "spine1", "dark", AB, waist_rings((99.4, 102.0, 105.0, 108.0, 110.4)), seg=18, ex=2.4, bevel=0.0, sharp=50)
    rings_hull("abdomen_upper", "spine2", "dark", AB, waist_rings((108.8, 111.5, 114.5, 118.2)), seg=18, ex=2.4, bevel=0.0, sharp=50)
    for i, (z0, z1, bone) in enumerate(((110.8, 114.6, "spine2"), (106.6, 110.4, "spine1"), (102.4, 106.2, "spine1"))):
        wrap(f"abs{i}", bone, "armor", AB,
             t=lambda u, v, z0=z0, z1=z1: lerp(z0 + 0.6 * abs(2 * u - 1), z1, v),
             th=lambda u, v: (2 * u - 1) * rad(lerp(50, 56, v)),
             r=lambda u, v, t, z0=z0: ((af(t) + 1.1 + 0.16 * (t - z0)) * (1 + 0.06 * tri(u, 0.5, 0.25)), aw(t) + 1.2 + 0.14 * (t - z0)),
             thick=0.9, nu=12, nv=4, ex=2.4, bevel=0.12)
    for i, (z0, bone) in enumerate(((101.0, "spine1"), (105.0, "spine1"), (109.0, "spine2"), (113.0, "spine2"))):
        box(f"vertebra{i}", bone, "steel", W, z0, z0 + 2.8, -8.4, -6.0, -2.2, 2.2, bevel=0.1, ch=0.7)

    # Pelvis: girdle, belt, tassets over the hips, glute plates and the groin plate on its own bone.
    PV = Frame((0, -0.4, 0), (0, 0, 1), (0, -1, 0), (1, 0, 0))
    gf = prof((87.6, 6.6), (91.0, 8.2), (95.0, 9.0), (99.0, 8.6), (102.4, 7.6))
    gk = prof((87.6, 6.4), (91.0, 8.0), (95.0, 8.6), (99.0, 8.2), (102.4, 7.2))
    gw = prof((87.6, 9.6), (91.0, 11.6), (95.0, 12.4), (99.0, 11.6), (102.4, 10.0))
    rings = []
    for z in (87.6, 89.5, 91.5, 94.0, 96.5, 99.0, 101.0, 102.4):
        rings.append((z, (gf(z) - gk(z)) / 2, 0.0, (gf(z) + gk(z)) / 2, gw(z)))
    rings_hull("girdle", "pelvis", "dark", PV, rings, seg=20, ex=2.6, bevel=0.0, sharp=50)
    # Belt with a buckle block, a narrow guard over the groin, tassets over the hips and a keeled plate behind.
    wrap("belt", "pelvis", "armor", PV,
         t=lambda u, v: lerp(98.6, 101.6, v),
         th=lambda u, v: (2 * u - 1) * rad(162),
         r=lambda u, v, t: (max(gf(t), gk(t)) + 1.2, gw(t) + 1.1),
         thick=0.9, nu=28, nv=2, ex=2.6, bevel=0.1)
    fr = on_surface(bpy.data.objects["belt"], W.p(100.1, 30, 0), W.f * -1, (0, 0, 1))
    stack("buckle", "pelvis", "dark", fr, [(-0.4, -2.0, 2.0, -3.4, 3.4, 0.8), (0.9, -1.7, 1.7, -3.0, 3.0, 0.7)], bevel=0.08)
    pts = []
    for z, f0, f1, hw in ((98.4, 7.6, 10.6, 4.4), (93.0, 7.8, 11.2, 3.6), (89.0, 7.2, 10.2, 2.2)):
        pts += [W.p(z, f, s * hw * (0.82 if f == f0 else 1.0)) for f in (f0, f1) for s in (-1, 1)]
    pts += [W.p(95.6, 11.9, 0), W.p(90.4, 11.0, 0)]
    hull("fauld", "pelvis", "armor", pts, bevel=0.12, segments=2)
    stack("groin_block", "penis", "dark", W, [(91.0, 6.0, 8.8, -3.4, 3.4, 0.8), (87.2, 5.6, 8.2, -2.4, 2.4, 0.7)], bevel=0.1)
    for side, s in sides():
        wrap(f"tasset_{side}", "pelvis", "armor", PV,
             t=lambda u, v: lerp(98.6, 91.2 - 1.6 * tri(u, 0.45, 0.45), v),
             th=lambda u, v, s=s: s * rad(lerp(52, 122, u)),
             r=lambda u, v, t: (gf(t) + 1.9 + 0.14 * (98.6 - t), gw(t) + 1.5 + 0.18 * (98.6 - t)),
             thick=0.9, nu=10, nv=6, ex=2.6, bevel=0.12)
    wrap("rear_plate", "pelvis", "armor", PV,
         t=lambda u, v: lerp(98.6, 89.4 + 3.0 * abs(2 * u - 1) ** 1.2, v),
         th=lambda u, v: math.pi + (2 * u - 1) * rad(40),
         r=lambda u, v, t: ((gk(t) + 1.7 + 0.06 * (98.6 - t)) * (1 + 0.07 * tri(u, 0.5, 0.2)), gw(t) + 1.2),
         thick=1.0, nu=12, nv=6, ex=2.6, bevel=0.12)

    # Neck: core and two rings.
    n0, n1 = Vector((0, 2.4, 142.0)), Vector((0, -1.0, 155.2))
    cyl("neck_core", "neck", "dark", n0, n1, 3.9, 3.5, seg=14)
    axis = (n1 - n0).normalized()
    for i, k in enumerate((0.45, 0.7)):
        c = n0.lerp(n1, k)
        cyl(f"neck_ring{i}", "neck", "steel", c - axis * 0.55, c + axis * 0.55, 4.8, seg=16)


def build_head():
    W = WORLD
    HD = Frame((0, 0, 0), (0, 0, 1), (0, -1, 0), (1, 0, 0))
    # Skull: smooth helmet shell, with armoured temple plates over the sides.
    rings = [(154.6, -3.4, 0, 5.2, 5.6), (157.4, -1.6, 0, 7.8, 7.2), (161.0, -0.6, 0, 9.0, 8.0), (165.0, -0.2, 0, 9.3, 8.3),
             (168.6, -0.4, 0, 9.1, 8.2), (171.4, -0.8, 0, 8.2, 7.5), (173.4, -1.1, 0, 6.4, 5.9), (174.5, -1.4, 0, 3.8, 3.5)]
    rings_hull("skull", "head", "armor", HD, rings, seg=20, ex=2.3, bevel=0.0, sharp=60)
    TP = Frame((0, 0.2, 0), (0, 0, 1), (0, -1, 0), (1, 0, 0))
    tpf = prof((156.0, 8.2), (160.0, 9.4), (165.0, 9.8), (169.5, 9.4))
    tpw = prof((156.0, 7.6), (160.0, 8.6), (165.0, 8.9), (169.5, 8.6))
    for side, s in sides():
        wrap(f"temple_{side}", "head", "armor", TP,
             t=lambda u, v: lerp(157.0 + 1.5 * u, 168.6 - 2.6 * u, v),
             th=lambda u, v, s=s: s * rad(lerp(58, 132, u)),
             r=lambda u, v, t: (tpf(t), tpw(t)),
             thick=0.9, nu=10, nv=6, ex=2.3, bevel=0.1)
    # Brow: two plates meeting low over the nose, so the face reads as a scowl.
    for side, s in sides():
        pts = [W.p(z, f, s * w) for z, f, w in (
            (164.8, 11.8, 0.25), (167.0, 11.0, 0.25), (166.0, 10.2, 7.2), (168.6, 9.4, 7.4), (167.2, 7.0, 8.6),
            (166.0, 5.0, 0.25), (167.2, 4.0, 6.5), (169.0, 5.0, 0.25))]
        hull(f"brow_{side}", "head", "armor", pts, bevel=0.15, segments=2)
    # Dark mask band behind the visor.
    pts = [W.p(162.6, 10.6, 0), W.p(165.2, 10.8, 0), W.p(162.6, 5.0, 0), W.p(165.6, 5.0, 0)]
    for s in (-1, 1):
        pts += [W.p(z, f, s * w) for z, f, w in (
            (162.8, 10.2, 4.0), (165.8, 10.4, 4.0), (163.0, 8.8, 7.4), (166.4, 9.0, 7.4), (163.2, 6.0, 8.6), (166.2, 6.0, 8.6))]
    hull("mask", "head", "glass", pts, bevel=0.1)
    # Visor: one V-shaped glowing band under the brow, a half on each eye bone.
    for side, s in sides():
        pts = []
        for w, zb, zt, f in ((0.0, 163.55, 164.45, 11.05), (3.4, 163.95, 165.0, 10.75), (6.8, 164.4, 165.55, 9.75)):
            pts += [W.p(zb, f, s * w), W.p(zt, f, s * w), W.p(zb, f - 0.9, s * w), W.p(zt, f - 0.9, s * w)]
        hull(f"visor_{side}", f"{side}_eye", "glow", pts, bevel=0.0)
    # Faceplate: a keeled muzzle narrowing to the chin, with vents on the cheeks.
    pts = [W.p(162.0, 4.0, 0), W.p(154.0, 3.0, 0)]
    for z, row in ((162.6, ((10.6, 0), (10.2, 4.2), (8.6, 7.6), (5.0, 8.6))),
                   (158.6, ((11.7, 0), (10.4, 4.4), (7.8, 7.5), (4.0, 8.2))),
                   (153.6, ((10.9, 0), (9.8, 2.6), (6.6, 4.8), (3.0, 5.6))),
                   (152.6, ((9.6, 0), (8.8, 2.0)))):
        for f, w in row:
            pts += [W.p(z, f, w), W.p(z, f, -w)]
    face = hull("faceplate", "head", "armor", pts, bevel=0.15, segments=2)
    for side, s in sides():
        fr = on_surface(face, W.p(157.6, 30, s * 5.6), W.f * -1, (0, 0, 1))
        for i in range(3):
            box(f"cheek_vent_{side}{i}", "head", "dark", fr, -0.5, 0.12, -1.4 + i * 1.0, -0.95 + i * 1.0, -1.1, 1.1, bevel=0.0)
    # Sensor pods on the sides, neck guard behind, collar under the head.
    for side, s in sides():
        EAR = Frame((s * 8.8, 0.4, 162.4), (s, 0, 0), (0, 0, 1), (0, -1, 0))
        stack(f"ear_{side}", "head", "dark", EAR, [(-0.4, -2.9, 2.9, -2.4, 2.4, 1.2), (1.6, -2.6, 2.6, -2.1, 2.1, 1.0)], bevel=0.1)
        cyl(f"ear_lens_{side}", "head", "steel", EAR.p(1.5), EAR.p(2.0), 1.25, 1.05, seg=12, bevel=0.05)
    pts = []
    for z, f0, f1, w in ((158.2, -9.4, -5.0, 6.2), (153.4, -10.6, -5.0, 5.8), (152.2, -9.0, -5.0, 4.8)):
        pts += [W.p(z, f, s * w) for f in (f0, f1) for s in (-1, 1)]
    hull("neck_guard", "head", "armor", pts, bevel=0.2)
    cyl("head_collar", "head", "dark", (0, -0.4, 151.4), (0, -0.8, 155.0), 5.2, 5.6, seg=16, bevel=0.1)


def build_arm(side):
    s = 1 if side == "l" else -1
    S, E, Wr = J(f"{side}_upperarm"), J(f"{side}_forearm"), J(f"{side}_hand")
    tw1, tw2 = UPPERARM_TWIST[side]
    UA = Frame(S, E - S, (0, -1, 0), (s, 0, 0.8))  # f forward, w up and out
    L = (E - S).length
    sphere(f"shoulder_ball_{side}", f"{side}_upperarm", "steel", S, 5.2, seg=14, rings=8)
    pr = prof((-7.5, 4.8), (-4.5, 7.4), (0, 8.7), (4, 8.9), (8, 8.4), (12, 7.6))
    wrap(f"pauldron_{side}", tw1, "armor", UA,
         t=lambda u, v: lerp(-7.2, 9.4 + 2.6 * tri(u, 0.5, 0.5), v),
         th=lambda u, v: rad(lerp(-14, 194, u)),
         r=lambda u, v, t: (pr(t) * 0.94, pr(t) * (1 + 0.09 * tri(u, 0.5, 0.14))),
         thick=1.2, nu=18, nv=10, ex=2.2, bevel=0.15)
    lr = prof((9, 7.9), (15, 6.9))
    wrap(f"pauldron_lame_{side}", tw1, "armor", UA,
         t=lambda u, v: lerp(10.2, 13.2 + 1.8 * tri(u, 0.5, 0.5), v),
         th=lambda u, v: rad(lerp(-4, 184, u)),
         r=lambda u, v, t: (lr(t) * 0.94, lr(t) * (1 + 0.08 * tri(u, 0.5, 0.14))),
         thick=0.8, nu=14, nv=4, ex=2.2, bevel=0.12)
    cyl(f"upperarm_core_{side}", f"{side}_upperarm", "dark", UA.p(3.0), UA.p(L - 2.0), 3.3, 3.0, seg=12)
    cyl(f"arm_band_{side}", tw2, "dark", UA.p(12.2), UA.p(14.2), 4.0, seg=16, bevel=0.1)
    ur = prof((13, 4.3), (18, 4.7), (25, 4.0))
    wrap(f"upperarm_shell_{side}", f"{side}_upperarm", "armor", UA,
         t=lambda u, v: lerp(14.0, 23.4 + 1.4 * tri(u, 0.5, 0.5), v),
         th=lambda u, v: rad(lerp(10, 170, u)),
         r=lambda u, v, t: (ur(t), ur(t) * (1 + 0.07 * tri(u, 0.5, 0.2))),
         thick=0.8, nu=12, nv=6, ex=2.2, bevel=0.1)
    cyl(f"bicep_piston_{side}", f"{side}_upperarm", "steel", UA.p(14.5, 1.4, -3.4), UA.p(24.0, 1.2, -3.0), 0.5, seg=8, bevel=0.0)

    FA = Frame(E, Wr - E, (0, -1, 0), (s, 0, 0.3))
    Lf = (Wr - E).length
    sphere(f"elbow_ball_{side}", f"{side}_elbow", "steel", E, 3.6, seg=12, rings=8)
    pts = []
    for t, f0, f1, hw in ((-3.8, -5.4, -2.6, 2.2), (-0.4, -7.4, -1.8, 3.0), (3.8, -5.8, -1.6, 2.8)):
        pts += [FA.p(t, f, w) for f in (f0, f1) for w in (-hw, hw)]
    pts.append(FA.p(0.2, -8.4, 0))
    hull(f"elbow_cap_{side}", f"{side}_elbow", "armor", pts, bevel=0.2)
    cyl(f"forearm_core_{side}", f"{side}_forearm", "dark", FA.p(2.2), FA.p(Lf - 2.6), 3.1, 2.8, seg=12)
    gr = prof((2.5, 4.4), (7.5, 5.3), (14, 4.8), (20, 4.0), (23, 3.6))
    wrap(f"gauntlet_{side}", f"{side}_forearm", "armor", FA,
         t=lambda u, v: lerp(2.8 + 1.0 * tri(u, 0.5, 0.5), 21.2 + 1.4 * tri(u, 0.5, 0.5), v),
         th=lambda u, v: rad(lerp(-20, 200, u)),
         r=lambda u, v, t: (gr(t), gr(t) * (1 + 0.1 * tri(u, 0.5, 0.16))),
         thick=0.9, nu=18, nv=10, ex=2.3, bevel=0.12)
    for i, f in enumerate((-1.6, 1.6)):
        cyl(f"forearm_cylinder_{side}{i}", f"{side}_forearm", "dark", FA.p(3.6, f, -3.1), FA.p(11.0, f, -3.0), 0.9, seg=10)
        cyl(f"forearm_piston_{side}{i}", f"{side}_forearm", "steel", FA.p(10.6, f, -3.0), FA.p(19.0, f, -2.8), 0.45, seg=8, bevel=0.0)
    cyl(f"wrist_cuff_{side}", WRIST_BONE[side], "dark", FA.p(Lf - 3.8), FA.p(Lf - 1.3), 3.5, 3.3, seg=16, bevel=0.12)
    sphere(f"wrist_ball_{side}", f"{side}_hand", "steel", Wr, 2.4, seg=12, rings=6)


FINGERS = ("thumb", "index", "middle", "ring", "little")
FINGER_R = {"thumb": 1.05, "index": 0.86, "middle": 0.9, "ring": 0.85, "little": 0.74}


def build_hand(side):
    s = 1 if side == "l" else -1
    Wr = J(f"{side}_hand")
    k1 = {f: J(f"{side}_{f}1") for f in FINGERS}
    h = (k1["middle"] - Wr).normalized()
    across = (k1["index"] - k1["little"]).normalized()
    d = across.cross(h).normalized()
    if d.x * s < 0:  # dorsal faces away from the body in the A-pose
        d = -d
    across = h.cross(d).normalized() * (1 if (k1["index"] - k1["little"]).dot(h.cross(d)) > 0 else -1)
    pts = []
    for f in ("index", "middle", "ring", "little"):
        k = k1[f] - h * 0.7
        pts += [k + d * 1.25, k - d * 1.35]
    pts += [k1["index"] - h * 1.2 + across * 0.8 + d * 1.1, k1["index"] - h * 1.2 + across * 0.8 - d * 1.2,
            k1["little"] - h * 1.2 - across * 0.7 + d * 1.0, k1["little"] - h * 1.2 - across * 0.7 - d * 1.1]
    for a in (-2.2, 2.2):
        for dd in (1.4, -1.2):
            pts.append(Wr + h * 1.5 + across * a + d * dd)
    t1 = k1["thumb"]
    pts += [t1 + d * 0.9 - h * 0.3, t1 - d * 1.1 - h * 0.3]
    hull(f"palm_{side}", f"{side}_hand", "dark", pts, bevel=0.15)
    # Armoured back of the hand and a knuckle bar.
    plate = []
    for a, t, lift in ((-2.3, 1.8, 1.45), (2.3, 1.8, 1.45), (-3.2, 6.6, 1.55), (3.6, 6.6, 1.55)):
        base = Wr + h * t + across * a
        plate += [base + d * lift, base + d * (lift + 0.75)]
    hull(f"hand_plate_{side}", f"{side}_hand", "armor", plate, bevel=0.12)
    kb = []
    for f in ("index", "little"):
        k = k1[f] - h * 1.1 + (across * 0.5 if f == "index" else -across * 0.5)
        kb += [k + d * 1.3, k + d * 2.1, k + d * 1.3 - h * 1.1, k + d * 1.9 - h * 1.1]
    hull(f"knuckle_bar_{side}", f"{side}_hand", "armor", kb, bevel=0.1)

    for f in FINGERS:
        r = FINGER_R[f]
        joints = [J(f"{side}_{f}{i}") for i in (1, 2, 3)]
        last = joints[2] - joints[1]
        tip_len = (2.6 if f == "thumb" else 2.2 if f != "little" else 1.8)
        joints.append(joints[2] + last.normalized() * tip_len)
        for i in range(3):
            a, b = joints[i], joints[i + 1]
            axis = (b - a).normalized()
            bone = f"{side}_{f}{i + 1}"
            gap = 0.28 * r
            rr = r * (1.0 - 0.07 * i)
            fr = Frame(a, axis, d, across)
            end_taper = 0.72 if i == 2 else 1.0
            stack(f"{f}{i + 1}_{side}", bone, "dark" if i < 2 else "rubber", fr, [
                (gap + 0.25 * r, -rr * 1.02, rr * 1.02, -rr, rr, 0.38 * rr),
                ((b - a).length - gap, -rr * end_taper, rr * end_taper, -rr * end_taper, rr * end_taper, 0.45 * rr * end_taper),
            ], bevel=0.06)
            if i < 2 and f != "thumb":  # dorsal armour on the first two segments of the fingers
                stack(f"{f}{i + 1}_plate_{side}", bone, "armor", fr, [
                    (gap + 0.5 * r, rr * 0.55, rr * 1.32, -rr * 0.8, rr * 0.8, 0.3 * rr),
                    ((b - a).length - gap - 0.2 * r, rr * 0.55, rr * 1.25, -rr * 0.75, rr * 0.75, 0.3 * rr),
                ], bevel=0.05)
            sphere(f"{f}{i + 1}_knuckle_{side}", bone, "steel", a, r * (0.95 if i == 0 else 0.82), seg=8, rings=5)


def build_leg(side):
    s = 1 if side == "l" else -1
    H, K, A, T = J(f"{side}_hip"), J(f"{side}_knee"), J(f"{side}_foot"), J(f"{side}_toe")
    TH = Frame(H, K - H, (0, -1, 0), (s, 0, 0))  # f forward, w outward
    Lt = (K - H).length
    sphere(f"hip_ball_{side}", f"{side}_hip", "steel", H, 5.6, seg=14, rings=8)
    cyl(f"thigh_core_{side}", f"{side}_hip", "dark", TH.p(4.0), TH.p(Lt - 3.5), 5.0, 4.2, seg=14)
    tf = prof((3, 6.4), (10, 7.6), (18, 7.8), (26, 7.0), (33, 5.8), (37, 5.2))
    tw = prof((3, 6.6), (10, 7.2), (18, 7.0), (26, 6.2), (33, 5.2), (37, 4.8))
    wrap(f"thigh_plate_{side}", f"{side}_hip", "armor", TH,
         t=lambda u, v: lerp(6.4 - 3.4 * u, 33.4 + 2.2 * tri(u, 0.5, 0.5), v),
         th=lambda u, v: rad(lerp(-72, 74, u)),
         r=lambda u, v, t: (tf(t) * (1 + 0.08 * tri(u, 0.5, 0.18)), tw(t)),
         thick=1.1, nu=16, nv=10, ex=2.4, bevel=0.15)
    wrap(f"thigh_side_{side}", f"{side}_hip_twist_01", "armor", TH,
         t=lambda u, v: lerp(3.4, 21.0 + 3.0 * tri(u, 0.5, 0.5), v),
         th=lambda u, v: rad(lerp(58, 150, u)),
         r=lambda u, v, t: (tf(t) + 0.9, tw(t) + 0.9),
         thick=0.9, nu=10, nv=8, ex=2.4, bevel=0.12)
    cyl(f"thigh_band_{side}", f"{side}_hip_twist_02", "dark", TH.p(34.8), TH.p(38.4), 5.0, 4.8, seg=16, bevel=0.12)
    cyl(f"hamstring_{side}", f"{side}_hip", "dark", TH.p(9.0, -4.8), TH.p(29.0, -4.4), 1.9, 1.7, seg=10)
    cyl(f"hamstring_rod_{side}", f"{side}_hip", "steel", TH.p(28.0, -4.4), TH.p(36.0, -3.4), 0.75, seg=8, bevel=0.0)

    SH = Frame(K, A - K, (0, -1, 0), (s, 0, 0))
    Ls = (A - K).length
    cyl(f"knee_hinge_{side}", f"{side}_knee", "dark", K - SH.w * 5.0, K + SH.w * 5.0, 4.0, seg=16, bevel=0.12)
    for k in (-1, 1):
        cyl(f"knee_hub_{side}{'io'[k > 0]}", f"{side}_knee", "steel", K + SH.w * k * 4.9, K + SH.w * k * 5.7, 2.4, 2.1, seg=12, bevel=0.06)
    kf = prof((-6.5, 5.6), (-2.0, 7.0), (2.5, 7.1), (6.5, 6.0), (8.5, 5.2))
    wrap(f"knee_cap_{side}", f"{side}_knee", "armor", SH,
         t=lambda u, v: lerp(-6.6 + 2.4 * abs(2 * u - 1), 7.8 - 1.8 * abs(2 * u - 1), v),
         th=lambda u, v: rad(lerp(-64, 64, u)),
         r=lambda u, v, t: (kf(t) * (1 + 0.1 * tri(u, 0.5, 0.2)), 4.9),
         thick=1.3, nu=12, nv=8, ex=2.2, bevel=0.15)
    cyl(f"shin_core_{side}", f"{side}_knee", "dark", SH.p(2.0), SH.p(Ls - 1.0), 3.4, 2.8, seg=14)
    sf = prof((5, 5.2), (11, 6.2), (20, 5.8), (28, 4.8), (35, 4.0))
    sw = prof((5, 4.8), (11, 5.4), (20, 5.0), (28, 4.2), (35, 3.6))
    wrap(f"shin_guard_{side}", f"{side}_knee", "armor", SH,
         t=lambda u, v: lerp(7.6 - 2.2 * tri(u, 0.5, 0.5), 32.6 + 1.8 * tri(u, 0.5, 0.5), v),
         th=lambda u, v: rad(lerp(-72, 72, u)),
         r=lambda u, v, t: (sf(t) * (1 + 0.1 * tri(u, 0.5, 0.18)), sw(t)),
         thick=0.9, nu=14, nv=10, ex=2.4, bevel=0.12)
    cf = prof((3, 5.8), (9, 8.2), (15, 8.0), (22, 6.2), (28, 4.4))
    cw = prof((3, 4.4), (9, 5.2), (15, 5.0), (22, 4.2), (28, 3.4))
    wrap(f"calf_{side}", CALF_BONE[side], "armor", SH,
         t=lambda u, v: lerp(3.6 + 1.2 * tri(u, 0.5, 0.5), 25.6 + 1.6 * tri(u, 0.5, 0.5), v),
         th=lambda u, v: rad(lerp(116, 244, u)),
         r=lambda u, v, t: (cf(t) * (1 + 0.05 * tri(u, 0.5, 0.2)), cw(t)),
         thick=1.0, nu=14, nv=10, ex=2.4, bevel=0.12)
    cyl(f"calf_cylinder_{side}", CALF_BONE[side], "dark", SH.p(22.0, -3.9), SH.p(29.0, -3.5), 1.15, seg=10)
    cyl(f"calf_rod_{side}", CALF_BONE[side], "steel", SH.p(28.0, -3.6), SH.p(35.2, -2.9), 0.65, seg=8, bevel=0.0)
    for k in (-1, 1):
        w0, w1 = (3.4, 5.0) if k > 0 else (-5.0, -3.4)
        stack(f"shin_side_{side}{'io'[k > 0]}", f"{side}_knee_twist_02", "dark", SH, [(12.0, -2.2, 2.4, w0, w1, 0.6), (26.0, -1.8, 2.0, w0 + 0.2 * k, w1 - 0.2 * k, 0.6)], bevel=0.1)
    cyl(f"ankle_cuff_{side}", f"{side}_foot_twist_01", "dark", SH.p(Ls - 5.4), SH.p(Ls - 1.6), 3.9, 3.7, seg=16, bevel=0.12)
    sphere(f"ankle_ball_{side}", f"{side}_foot", "steel", A, 3.3, seg=12, rings=6)

    # Boot: sole, a domed upper with a curved instep and a tongue plate, hubs over the ankle, toe cap.
    fo = Vector((T.x - A.x, T.y - A.y, 0)).normalized()
    FO = Frame((A.x, A.y, 0), fo, (0, 0, 1), (s, 0, 0))  # t forward along the foot, f up, w outward
    FT = Frame((A.x, A.y, 2.2), fo, (0, 0, 1), (s, 0, 0))  # the same, standing on the sole
    ball = Vector((T.x - A.x, T.y - A.y, 0)).length
    stack(f"sole_{side}", f"{side}_foot", "rubber", FO, [(-8.8, 0.0, 2.2, -4.0, 4.1, 1.2), (-3.0, 0.0, 2.2, -4.4, 4.6, 1.0), (ball - 0.2, 0.0, 2.2, -5.0, 5.2, 1.0)], bevel=0.1)
    hf = prof((-8.6, 4.0), (-6.4, 6.4), (-3.0, 8.2), (0.5, 8.4), (4.0, 6.4), (8.0, 4.2), (ball - 0.4, 2.8))
    hw = prof((-8.6, 3.5), (-5.5, 4.2), (0.0, 4.6), (6.0, 4.9), (ball - 0.4, 5.0))

    def dome(t, lift=0.0, grow=0.0, n=10, ex=2.8):
        return [(math.copysign(abs(math.cos(a)) ** (2 / ex), math.cos(a)) * (hf(t) + lift),
                 math.copysign(abs(math.sin(a)) ** (2 / ex), math.sin(a)) * (hw(t) + grow))
                for a in (lerp(-math.pi / 2, math.pi / 2, i / n) for i in range(n + 1))]
    sloft(f"foot_{side}", f"{side}_foot", "armor", FT, [lerp(-8.6, ball - 0.4, k / 12) for k in range(13)], dome, bevel=0.15)
    wrap(f"tongue_{side}", f"{side}_foot", "armor", FT,
         t=lambda u, v: lerp(-1.2 + 0.8 * abs(2 * u - 1), 8.6 - 1.0 * abs(2 * u - 1), v),
         th=lambda u, v: rad(lerp(-50, 50, u)),
         r=lambda u, v, t: ((hf(t) + 0.55) * (1 + 0.04 * tri(u, 0.5, 0.25)), hw(t) + 0.55),
         thick=0.8, nu=10, nv=8, ex=2.8, bevel=0.1)
    for k in (-1, 1):
        c = Vector((A.x, A.y, A.z)) + FO.w * k * 4.3
        cyl(f"ankle_hub_{side}{'io'[k > 0]}", f"{side}_foot", "steel", c, c + FO.w * k * 0.8, 2.3, 2.0, seg=12, bevel=0.06)
    cyl(f"toe_hinge_{side}", f"{side}_toe", "dark", FO.p(ball, 2.1, -4.6), FO.p(ball, 2.1, 4.8), 1.6, seg=12, bevel=0.06)
    th_ = prof((ball, 2.9), (ball + 4.0, 2.5), (ball + 6.6, 1.8), (ball + 7.8, 0.9))
    tw_ = prof((ball, 5.0), (ball + 4.0, 4.7), (ball + 6.6, 3.9), (ball + 7.8, 2.8))

    def toe(t, n=10, ex=2.6):
        return [(math.copysign(abs(math.cos(a)) ** (2 / ex), math.cos(a)) * th_(t),
                 math.copysign(abs(math.sin(a)) ** (2 / ex), math.sin(a)) * tw_(t))
                for a in (lerp(-math.pi / 2, math.pi / 2, i / n) for i in range(n + 1))]
    sloft(f"toe_{side}", f"{side}_toe", "armor", FT, [lerp(ball + 0.2, ball + 7.8, k / 6) for k in range(7)], toe, bevel=0.12)
    stack(f"toe_sole_{side}", f"{side}_toe", "rubber", FO, [(ball + 0.2, 0.0, 2.2, -5.0, 5.2, 1.0), (ball + 7.4, 0.0, 2.2, -3.4, 3.6, 1.0), (ball + 8.2, 0.4, 2.0, -2.6, 2.8, 0.8)], bevel=0.1)


# ---------------------------------------------------------------------------------------------------------
# Preview


def preview(tag="geo", views=("front", "side", "back", "three_quarter")):
    scene = bpy.context.scene
    cam_data = bpy.data.cameras.get("preview_cam") or bpy.data.cameras.new("preview_cam")
    cam = bpy.data.objects.get("preview_cam") or bpy.data.objects.new("preview_cam", cam_data)
    if cam.name not in scene.collection.objects:
        scene.collection.objects.link(cam)
    cam_data.type = "ORTHO"
    cam_data.ortho_scale = 2.05
    scene.camera = cam
    scene.render.engine = "BLENDER_WORKBENCH"
    shading = scene.display.shading
    shading.light = "STUDIO"
    shading.color_type = "MATERIAL"
    shading.show_cavity = True
    shading.cavity_type = "BOTH"
    shading.show_shadows = False
    shading.show_specular_highlight = True
    scene.render.resolution_x = 900
    scene.render.resolution_y = 1000
    scene.render.film_transparent = False
    ARM.hide_render = True
    body = (Vector((0, 0, 0.9)), 2.05)
    shots = {  # view: (direction to the camera, target in metres, ortho scale)
        "front": (Vector((0, -1, 0.05)), *body), "side": (Vector((1, 0, 0.05)), *body),
        "back": (Vector((0, 1, 0.05)), *body), "three_quarter": (Vector((0.8, -1, 0.25)), *body),
        "high": (Vector((0.5, -0.8, 0.9)), *body),
        "head": (Vector((0.6, -1, 0.12)), Vector((0, -0.02, 1.645)), 0.42),
        "torso": (Vector((0.55, -1, 0.2)), Vector((0, 0, 1.22)), 0.95),
        "back_detail": (Vector((-0.6, 1, 0.3)), Vector((0, 0.05, 1.25)), 0.95),
        "leg": (Vector((0.9, -1, 0.15)), Vector((0.15, 0, 0.3)), 0.8),
        "hand": (Vector((1, -0.4, 0.15)), Vector((0.54, -0.05, 0.95)), 0.34),
    }
    paths = []
    out_dir = PREVIEW_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    for v in views:
        d, target, scale = shots[v]
        d = d.normalized()
        cam_data.ortho_scale = scale
        cam.location = target + d * 6.0
        cam.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()
        scene.render.filepath = str(out_dir / f"{tag}_{v}.png")
        bpy.ops.render.render(write_still=True)
        paths.append(scene.render.filepath)
    return paths


# ---------------------------------------------------------------------------------------------------------


def build_geometry():
    global COLL
    scene = reset_scene()
    load_skeleton(scene)
    COLL = bpy.data.collections.new("robot_parts")
    scene.collection.children.link(COLL)
    make_materials()
    build_torso()
    build_head()
    for side in ("l", "r"):
        build_arm(side)
        build_hand(side)
        build_leg(side)
    missing = sorted(set(KEEP_BONES) - {p["bone"] for p in PARTS})
    assert not missing, f"bones with no geometry: {missing}"
    return scene


# ---------------------------------------------------------------------------------------------------------
# One mesh: the parts joined, each rigid on its bone, unwrapped into one atlas


def assemble():
    """Apply every part's modifiers, tag its faces with its part and surface, bind it to its bone and join the
    lot into one mesh, still in world metres. "rest" keeps each vertex's position for the bakes."""
    global ROBOT
    dg = bpy.context.evaluated_depsgraph_get()
    surfs = list(SURFACES)
    rng = random.Random(1307)
    for i, obj in enumerate(PARTS):
        me = bpy.data.meshes.new_from_object(obj.evaluated_get(dg), preserve_all_data_layers=True, depsgraph=dg)
        old = obj.data
        obj.modifiers.clear()
        obj.data = me
        bpy.data.meshes.remove(old)
        nf, nv = len(me.polygons), len(me.vertices)
        for name, value in (("surf_id", surfs.index(obj["surf"])), ("part_id", i), ("prand", rng.random())):
            me.attributes.new(name, "FLOAT", "FACE").data.foreach_set("value", [float(value)] * nf)
        me.attributes.new("pidx", "INT", "POINT").data.foreach_set("value", [i] * nv)
        obj.vertex_groups.new(name=obj["bone"]).add(range(nv), 1.0, "REPLACE")
    PART_INFO[:] = [(o.name, o["bone"], o["surf"]) for o in PARTS]
    body = PARTS[0]
    with bpy.context.temp_override(active_object=body, object=body, selected_objects=PARTS,
                                   selected_editable_objects=PARTS):
        bpy.ops.object.join()
    PARTS[:] = []
    for me in list(bpy.data.meshes):
        if me.users == 0:
            bpy.data.meshes.remove(me)
    body.name = body.data.name = NAME
    body["robot_parts"] = json.dumps(PART_INFO)
    me = body.data
    co = np.empty(len(me.vertices) * 3, np.float32)
    me.vertices.foreach_get("co", co)
    me.attributes.new("rest", "FLOAT_VECTOR", "POINT").data.foreach_set("vector", co)
    ROBOT = body
    return body


# Texel density of an island relative to the rest: plates' outsides get more, what hides under them less.
ISLAND_SCALE = {"outer": 1.15, "inner": 0.35, "wall": 0.8, "dark": 0.6, "rubber": 0.6, "glass": 0.6, "glow": 0.5}


def mesh_array(me, name, width, domain_len):
    arr = np.empty(domain_len * width, np.float32 if width != 1 or me.attributes[name].data_type == "FLOAT" else np.int32)
    field = "vector" if width == 3 else "value"
    me.attributes[name].data.foreach_get(field, arr)
    return arr.reshape(-1, width) if width > 1 else arr


def uv_islands(me):
    """Island of every face: faces sharing an edge whose UVs match on both ends are in one island."""
    nl, nf = len(me.loops), len(me.polygons)
    uv = np.empty(nl * 2, np.float32)
    me.uv_layers["UVMap"].data.foreach_get("uv", uv)
    uv = uv.reshape(-1, 2)
    start = np.empty(nf, np.int32)
    total = np.empty(nf, np.int32)
    me.polygons.foreach_get("loop_start", start)
    me.polygons.foreach_get("loop_total", total)
    face = np.repeat(np.arange(nf), total)
    nxt = start[face] + (np.arange(nl) - start[face] + 1) % total[face]
    edge = np.empty(nl, np.int32)
    me.loops.foreach_get("edge_index", edge)
    order = np.argsort(edge, kind="stable")
    pair = np.nonzero(edge[order][1:] == edge[order][:-1])[0]
    l1, l2 = order[pair], order[pair + 1]
    same = (np.abs(uv[l1] - uv[nxt[l2]]).max(1) < 1e-6) & (np.abs(uv[nxt[l1]] - uv[l2]).max(1) < 1e-6)
    parent = list(range(nf))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    for a, b in zip(face[l1[same]].tolist(), face[l2[same]].tolist()):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb
    return np.array([find(f) for f in range(nf)]), face, uv


def unwrap(obj):
    """Plates keep the arc-length UVs wrap() gave them; everything else is smart-projected. Islands are then
    brought to one texel density, scaled by ISLAND_SCALE, and packed into one square."""
    me = obj.data
    nf = len(me.polygons)
    pside = mesh_array(me, "pside", 1, nf)
    rest = pside == 0
    loops_face = np.repeat(np.arange(nf), [p.loop_total for p in me.polygons])
    vsel = np.zeros(len(me.vertices), bool)
    corner_vert = np.empty(len(me.loops), np.int32)
    me.loops.foreach_get("vertex_index", corner_vert)
    vsel[corner_vert[rest[loops_face]]] = True
    ev = np.empty(len(me.edges) * 2, np.int32)
    me.edges.foreach_get("vertices", ev)
    me.vertices.foreach_set("select", vsel)
    me.edges.foreach_set("select", vsel[ev.reshape(-1, 2)].all(1))
    me.polygons.foreach_set("select", rest)
    bpy.context.view_layer.objects.active = obj
    for o in bpy.context.view_layer.objects:
        o.select_set(o is obj)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.uv.smart_project(angle_limit=math.radians(66), island_margin=0.0, area_weight=0.0,
                             correct_aspect=True, scale_to_bounds=False)
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.select_all(action="SELECT")
    bpy.ops.uv.average_islands_scale()
    bpy.ops.object.mode_set(mode="OBJECT")

    island, face, uv = uv_islands(me)
    surf = np.rint(mesh_array(me, "surf_id", 1, nf)).astype(int)
    fac = np.ones(nf)
    for name, scale in ISLAND_SCALE.items():
        if name in SURFACES:
            fac[surf == list(SURFACES).index(name)] = scale
    fac[pside == 1] *= ISLAND_SCALE["outer"]
    fac[pside == 2] = ISLAND_SCALE["inner"]
    fac[pside == 3] = ISLAND_SCALE["wall"]
    lab = island[face]
    count = np.bincount(lab, minlength=nf).clip(1)
    centre = np.stack([np.bincount(lab, uv[:, k], nf) / count for k in (0, 1)], axis=1)
    uv = centre[lab] + (uv - centre[lab]) * fac[lab][:, None]
    me.uv_layers["UVMap"].data.foreach_set("uv", uv.astype(np.float32).ravel())

    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.select_all(action="SELECT")
    bpy.ops.uv.pack_islands(udim_source="CLOSEST_UDIM", rotate=True, rotate_method="ANY", scale=True,
                            merge_overlap=False, margin_method="FRACTION", margin=4.0 / TEX, pin=False,
                            shape_method="CONCAVE")
    bpy.ops.object.mode_set(mode="OBJECT")


# ---------------------------------------------------------------------------------------------------------
# Bakes. Cycles writes facts about every texel of the atlas into float images: which part and surface it is
# on, where it is, its normal, how occluded it is, how near an edge, and some noise. numpy paints from them.


def bone_group(bone):
    """Body region a bone moves with, for the occlusion bakes, which pull the regions apart so an arm
    doesn't darken the side of the chest it swings away from."""
    if bone in ("head", "l_eye", "r_eye"):
        return "head"
    if bone[:2] in ("l_", "r_") and "clavicle" not in bone:
        return bone[:2] + ("leg" if any(k in bone for k in ("hip", "knee", "foot", "toe")) else "arm")
    return "torso"


GROUP_OFFSET = {"torso": (0, 0, 0), "head": (0, 0, 0.6), "l_arm": (1.4, 0, 0), "r_arm": (-1.4, 0, 0),
                "l_leg": (0.7, 0, 0), "r_leg": (-0.7, 0, 0)}


def pose_vertices(obj, mode):
    """rest: as built.  parts: every part 2 m from the next (the bevel bake then sees no neighbour's faces).
    groups: body regions apart (GROUP_OFFSET)."""
    me = obj.data
    n = len(me.vertices)
    rest = mesh_array(me, "rest", 3, n)
    pidx = mesh_array(me, "pidx", 1, n)
    if mode == "parts":
        off = np.stack([(pidx % 16) * 2.0, (pidx // 16) * 2.0 + 4.0, np.zeros(n)], axis=1)
    elif mode == "groups":
        table = np.array([GROUP_OFFSET[bone_group(bone)] for _, bone, _ in PART_INFO], np.float32)
        off = table[pidx]
    else:
        off = 0.0
    me.vertices.foreach_set("co", (rest + off).astype(np.float32).ravel())
    me.update()


def socket(nt, value, target):
    if isinstance(value, bpy.types.NodeSocket):
        nt.links.new(value, target)
    else:
        target.default_value = value


def vmath(nt, op, *inputs):
    n = nt.nodes.new("ShaderNodeVectorMath")
    n.operation = op
    for i, value in enumerate(inputs):
        socket(nt, value, n.inputs[i])
    return n.outputs["Value" if op == "DOT_PRODUCT" else "Vector"]


def smath(nt, op, *inputs):
    n = nt.nodes.new("ShaderNodeMath")
    n.operation = op
    for i, value in enumerate(inputs):
        socket(nt, value, n.inputs[i])
    return n.outputs[0]


def xyz(nt, *values):
    n = nt.nodes.new("ShaderNodeCombineXYZ")
    for i, value in enumerate(values):
        socket(nt, value, n.inputs[i])
    return n.outputs[0]


def attr(nt, name, out="Vector"):
    n = nt.nodes.new("ShaderNodeAttribute")
    n.attribute_type = "GEOMETRY"
    n.attribute_name = name
    return n.outputs[out]


def noise(nt, vector, scale, detail, roughness):
    n = nt.nodes.new("ShaderNodeTexNoise")
    n.noise_dimensions = "3D"
    nt.links.new(vector, n.inputs["Vector"])
    n.inputs["Scale"].default_value = scale
    n.inputs["Detail"].default_value = detail
    n.inputs["Roughness"].default_value = roughness
    return n.outputs["Fac"]


def pass_ids(nt):
    """(surface + 1) / 16, part / 1024, the part's random value. Red is 0 only where nothing was baked."""
    return xyz(nt, smath(nt, "MULTIPLY_ADD", attr(nt, "surf_id", "Fac"), 1 / 16, 1 / 16),
               smath(nt, "MULTIPLY", attr(nt, "part_id", "Fac"), 1 / 1024), attr(nt, "prand", "Fac"))


def pass_pos(nt):
    return vmath(nt, "MULTIPLY_ADD", attr(nt, "rest"), (1 / POS_SPAN,) * 3, tuple(-c / POS_SPAN for c in POS_LO))


def pass_nrm(nt):
    geo = nt.nodes.new("ShaderNodeNewGeometry")
    return vmath(nt, "MULTIPLY_ADD", geo.outputs["Normal"], (0.5,) * 3, (0.5,) * 3)


def pass_puv(nt):
    return attr(nt, "puv")


def pass_plen(nt):
    """Plate arc lengths across and along / 200 cm, and which side of the plate (pside / 4)."""
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(attr(nt, "plen"), sep.inputs[0])
    return xyz(nt, smath(nt, "MULTIPLY", sep.outputs[0], 1 / 200), smath(nt, "MULTIPLY", sep.outputs[1], 1 / 200),
               smath(nt, "MULTIPLY", attr(nt, "pside", "Fac"), 1 / 4))


def pass_edge(nt):
    """1 - cos of the angle between the normal rounded over a small and a larger radius and the shading
    normal: how near an edge a texel is (both convex and concave; the cavity bake tells them apart)."""
    geo = nt.nodes.new("ShaderNodeNewGeometry")
    outs = []
    for radius in (0.0035, 0.012):
        bev = nt.nodes.new("ShaderNodeBevel")
        bev.samples = 8
        bev.inputs["Radius"].default_value = radius
        outs.append(smath(nt, "SUBTRACT", 1.0, vmath(nt, "DOT_PRODUCT", bev.outputs["Normal"], geo.outputs["Normal"])))
    return xyz(nt, *outs, 0.0)


def pass_noise(nt):
    rest = attr(nt, "rest")
    return xyz(nt, noise(nt, rest, 45, 6, 0.55), noise(nt, rest, 9, 5, 0.6), noise(nt, rest, 2.2, 3, 0.5))


def pass_grain(nt):
    """Fine grain, a few millimetres across."""
    return noise(nt, attr(nt, "rest"), 160, 2, 0.5)


# name: (bake type, emission builder, samples, AO distance, vertex pose)
BAKE_PASSES = {
    "ids": ("EMIT", pass_ids, 1, None, "rest"),
    "pos": ("EMIT", pass_pos, 1, None, "rest"),
    "nrm": ("EMIT", pass_nrm, 1, None, "rest"),
    "puv": ("EMIT", pass_puv, 1, None, "rest"),
    "plen": ("EMIT", pass_plen, 1, None, "rest"),
    "noise": ("EMIT", pass_noise, 1, None, "rest"),
    "grain": ("EMIT", pass_grain, 1, None, "rest"),
    "edge": ("EMIT", pass_edge, 16, None, "parts"),
    "ao": ("AO", None, 160, 0.12, "groups"),
    "cav": ("AO", None, 64, 0.02, "groups"),
}


def use_cycles(scene):
    scene.render.engine = "CYCLES"
    prefs = bpy.context.preferences.addons["cycles"].preferences
    prefs.get_devices()
    gpu = prefs.compute_device_type != "NONE" and any(d.use and d.type != "CPU" for d in prefs.devices)
    scene.cycles.device = "GPU" if gpu else "CPU"
    if scene.world is None:
        scene.world = bpy.data.worlds.new("robot_world")


def bake(obj, names=None):
    """Bake the passes into float arrays (TEX, TEX, 4), rows bottom-up as Blender stores them."""
    scene = bpy.context.scene
    use_cycles(scene)
    mat = bpy.data.materials.get("robot_bake") or bpy.data.materials.new("robot_bake")
    me = obj.data
    me.materials.clear()
    me.materials.append(mat)
    me.polygons.foreach_set("material_index", np.zeros(len(me.polygons), np.int32))
    bpy.context.view_layer.objects.active = obj
    for o in bpy.context.view_layer.objects:
        o.select_set(o is obj)
    out = {}
    for name in names or BAKE_PASSES:
        kind, build, samples, distance, pose = BAKE_PASSES[name]
        pose_vertices(obj, pose)
        img = bpy.data.images.new(f"robot_bake_{name}", TEX, TEX, alpha=True, float_buffer=True)
        img.colorspace_settings.name = "Non-Color"
        nt = mat.node_tree
        nt.nodes.clear()
        output = nt.nodes.new("ShaderNodeOutputMaterial")
        shader = nt.nodes.new("ShaderNodeEmission" if build else "ShaderNodeBsdfDiffuse")
        nt.links.new(shader.outputs[0], output.inputs["Surface"])
        if build:
            nt.links.new(build(nt), shader.inputs["Color"])
        tex = nt.nodes.new("ShaderNodeTexImage")
        tex.image = img
        nt.nodes.active = tex
        scene.cycles.samples = samples
        if distance:
            scene.world.light_settings.distance = distance
        bpy.ops.object.bake(type=kind, margin=0, use_clear=True, target="IMAGE_TEXTURES")
        px = np.empty(TEX * TEX * 4, np.float32)
        img.pixels.foreach_get(px)
        bpy.data.images.remove(img)
        out[name] = px.reshape(TEX, TEX, 4)
    pose_vertices(obj, "rest")
    return out


def dilate(maps, covered, steps=24):
    """Grow every island `steps` texels into the empty space round it, copying its edge texels outwards, so
    filtering and mipmaps never reach the background. All maps take the same source texel."""
    h, w = covered.shape
    idx = np.where(covered, np.arange(h * w).reshape(h, w), -1)
    for _ in range(steps):
        empty = idx < 0
        if not empty.any():
            break
        new = idx.copy()
        for dy, dx in ((0, 1), (0, -1), (1, 0), (-1, 0), (1, 1), (1, -1), (-1, 1), (-1, -1)):
            shifted = np.roll(idx, (dy, dx), axis=(0, 1))
            take = (new < 0) & (shifted >= 0)
            new[take] = shifted[take]
        idx = new
    src = np.maximum(idx, 0).ravel()
    filled = idx >= 0
    return {k: v.reshape(h * w, -1)[src].reshape(v.shape) for k, v in maps.items()}, filled


def write_png(path, arr):
    """8-bit PNG of a (h, w[, c]) array in 0..1 (or uint8) whose row 0 is the bottom, as Blender's are."""
    a = arr if arr.dtype == np.uint8 else np.clip(np.rint(arr * 255.0), 0, 255).astype(np.uint8)
    a = np.ascontiguousarray(a[::-1])
    h, w = a.shape[:2]
    c = 1 if a.ndim == 2 else a.shape[2]
    rows = a.reshape(h, w * c).astype(np.int16)
    up = rows.copy()
    up[1:] -= rows[:-1]  # PNG "up" filter
    raw = np.empty((h, w * c + 1), np.uint8)
    raw[:, 0] = 2
    raw[:, 1:] = (up & 0xFF).astype(np.uint8)

    def chunk(tag, data):
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
    header = struct.pack(">IIBBBBB", w, h, 8, {1: 0, 2: 4, 3: 2, 4: 6}[c], 0, 0, 0)
    Path(path).write_bytes(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header)
                           + chunk(b"IDAT", zlib.compress(raw.tobytes(), 6)) + chunk(b"IEND", b""))


# ---------------------------------------------------------------------------------------------------------
# Paint: numpy turns the bakes into the material's maps. Colours are sRGB 0..255, the maths is linear.
# The markings are the robot's own: its unit number (07) and RZ, for Razed.

PAINT = {
    "accent": (200, 92, 26),     # signal orange
    "marking": (212, 208, 194),  # stencil white
    "ink": (22, 22, 22),         # label print, hazard stripes
    "primer": (86, 76, 68),      # showing where the paint is rubbed thin
    "bare": (178, 178, 176),     # steel, where the paint has chipped through
    "dark": (46, 48, 52),        # frame and mechanisms
    "steel": (166, 168, 172),
    "rubber": (30, 30, 30),
    "glass": (12, 14, 17),
    "grime": (50, 45, 39),
    "dust": (104, 96, 84),
    "soot": (18, 17, 16),
}
# Armour paint schemes, each with its optics (and stencil colour, if not PAINT's). "" is the model's default
# material; the others are material groups.
SCHEMES = {
    "": {"armor": (90, 96, 103), "armor2": (50, 54, 59), "optics": ""},  # gunmetal, red optics
    "light": {"armor": (148, 152, 154), "armor2": (86, 90, 95), "marking": (38, 40, 44), "optics": "cyan"},  # pale
}
FINISH = {  # surface: (roughness, metalness)
    "armor": (0.5, 0.0), "accent": (0.5, 0.0), "dark": (0.46, 0.55), "steel": (0.3, 1.0),
    "rubber": (0.88, 0.0), "glass": (0.06, 0.0), "glow": (0.3, 0.0),
}
OPTICS = {"": (255, 70, 30), "amber": (255, 150, 20), "cyan": (40, 190, 255)}  # glow colour per material group


def scheme_name(key=""):
    """The main material (and colour map) of a paint scheme."""
    return NAME + (f"_{key}" if key else "")


def glow_name(variant=""):
    return f"{NAME}_glow" + (f"_{variant}" if variant else "")


def lin(c):
    c = np.asarray(c, np.float32) / 255.0
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4).astype(np.float32)


def to_srgb(c):
    c = np.clip(c, 0.0, 1.0)
    return np.where(c <= 0.0031308, c * 12.92, 1.055 * np.power(c, 1 / 2.4) - 0.055)


def smoothstep(a, b, x):
    t = np.clip((x - a) / (b - a), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def mix(a, b, t):
    t = np.asarray(t, np.float32)
    if np.ndim(a) == 3 or np.ndim(b) == 3:
        t = t[..., None]
    return a + (b - a) * t


def text_mask(text):
    """Coverage (h, w) of `text` in Blender's own font, cropped, rows bottom-up: rendered white on clear."""
    cache = bpy.app.driver_namespace.setdefault("robot_text", {})
    if text in cache:
        return cache[text]
    sc = bpy.data.scenes.new("robot_text")
    cu = bpy.data.curves.new("robot_text", "FONT")
    cu.body = text
    cu.align_x, cu.align_y = "CENTER", "CENTER"
    cu.offset = 0.03  # a heavier stroke
    cu.space_character = 1.1
    ob = bpy.data.objects.new("robot_text", cu)
    ob.scale.x = 0.88
    sc.collection.objects.link(ob)
    cam = bpy.data.objects.new("robot_text_cam", bpy.data.cameras.new("robot_text_cam"))
    cam.data.type = "ORTHO"
    cam.data.ortho_scale = 0.8 * len(text) + 1.0
    cam.location = (0, 0, 5)
    sc.collection.objects.link(cam)
    sc.camera = cam
    sc.render.engine = "BLENDER_WORKBENCH"
    sc.display.shading.light = "FLAT"
    sc.display.shading.color_type = "SINGLE"
    sc.display.shading.single_color = (1, 1, 1)
    sc.display.render_aa = "16"
    sc.render.film_transparent = True
    sc.render.resolution_x = sc.render.resolution_y = 1024
    sc.render.resolution_percentage = 100
    sc.render.image_settings.file_format = "PNG"
    sc.render.image_settings.color_mode = "RGBA"
    path = Path(bpy.app.tempdir or str(OUT)) / f"robot_text_{len(cache)}.png"
    sc.render.filepath = str(path)
    bpy.ops.render.render(write_still=True, scene=sc.name)
    img = bpy.data.images.load(str(path))
    px = np.empty(img.size[0] * img.size[1] * 4, np.float32)
    img.pixels.foreach_get(px)
    a = px.reshape(img.size[1], img.size[0], 4)[..., 3]
    bpy.data.images.remove(img)
    for data, item in ((bpy.data.objects, ob), (bpy.data.objects, cam), (bpy.data.curves, cu),
                       (bpy.data.cameras, cam.data), (bpy.data.scenes, sc)):
        data.remove(item)
    path.unlink(missing_ok=True)
    rows, cols = np.nonzero(a.max(1) > 0.02)[0], np.nonzero(a.max(0) > 0.02)[0]
    a = np.ascontiguousarray(a[rows[0]:rows[-1] + 1, cols[0]:cols[-1] + 1])
    cache[text] = a
    return a


def label_mask(seed, cols=26, rows=5):
    """A small printed label: coverage of the label and of its print (a bar code and a line of 'text')."""
    rng = np.random.default_rng(seed)
    h, w = rows * 8, cols * 6
    label = np.ones((h, w), np.float32)
    ink = np.zeros((h, w), np.float32)
    x = 3
    while x < w - 4:
        bw = int(rng.integers(1, 4))
        ink[14:h - 4, x:x + bw] = 1.0
        x += bw + int(rng.integers(1, 3))
    for x0 in range(3, w - 10, 7):
        if rng.random() < 0.8:
            ink[4:9, x0:x0 + 5] = 1.0  # the "text" line along the top (rows are bottom-up)
    return label, ink[::-1].copy()


def sample(mask, x, y):
    """Bilinear lookup of mask (h, w; row 0 at the bottom) at x, y in 0..1."""
    h, w = mask.shape
    fx, fy = np.clip(x, 0, 1) * (w - 1), np.clip(y, 0, 1) * (h - 1)
    x0, y0 = np.clip(np.floor(fx).astype(int), 0, w - 2), np.clip(np.floor(fy).astype(int), 0, h - 2)
    tx, ty = fx - x0, fy - y0
    return (mask[y0, x0] * (1 - tx) * (1 - ty) + mask[y0, x0 + 1] * tx * (1 - ty)
            + mask[y0 + 1, x0] * (1 - tx) * ty + mask[y0 + 1, x0 + 1] * tx * ty)


def shrink(mask, texels):
    """Box-filter a mask down to about 3x the texels it will cover, so stamping it doesn't alias."""
    k = max(1, mask.shape[0] // max(1, int(texels * 3)))
    h, w = (mask.shape[0] // k) * k, (mask.shape[1] // k) * k
    return mask[:h, :w].reshape(h // k, k, w // k, k).mean(axis=(1, 3))


def stamp(where, x_cm, y_cm, mask, height_cm, width_cm=None):
    """Coverage of `mask` centred on (0, 0) in the given surface coordinates (cm), height_cm tall."""
    width_cm = width_cm or height_cm * mask.shape[1] / mask.shape[0]
    x, y = x_cm / width_cm + 0.5, y_cm / height_cm + 0.5
    inside = where & (x >= 0) & (x <= 1) & (y >= 0) & (y <= 1)
    out = np.zeros(where.shape, np.float32)
    small = shrink(mask, height_cm * 10)
    out[inside] = sample(small, x[inside], y[inside])
    return out


def hash01(x, *salt):
    """A repeatable pseudo-random 0..1 per integer-valued x."""
    v = np.sin(np.asarray(x, np.float64) * 12.9898 + sum(s * (78.233 + 37.719 * i) for i, s in enumerate(salt))) * 43758.5453
    return (v - np.floor(v)).astype(np.float32)


def scratch_lines(P, N, seed=7, spacing=2.2, cell=4.0, keep=0.3):
    """Straight scratches: the model cut by sets of parallel planes (P in cm), each cut broken into segments
    about `cell` long, a third of them kept. Lines are measured across the surface, so they come out a
    millimetre or two wide wherever the planes meet it, fading where a surface runs nearly parallel to them."""
    rng = np.random.default_rng(seed)
    out = np.zeros(P.shape[:-1], np.float32)
    for k in range(3):
        d = rng.normal(size=3)
        d /= np.linalg.norm(d)
        e = np.cross(d, rng.normal(size=3))
        e /= np.linalg.norm(e)
        f = np.cross(d, e)
        s = P @ d.astype(np.float32) / spacing
        n = np.floor(s)
        slant = np.sqrt(np.clip(1 - (N @ d.astype(np.float32)) ** 2, 0.09, 1))
        dist = np.abs(s - n - (0.2 + 0.6 * hash01(n, k, 1))) * spacing / slant  # cm, across the surface
        line = (1 - smoothstep(0.03, 0.12, dist)) * smoothstep(0.3, 0.55, slant)
        c1 = np.floor(P @ e.astype(np.float32) / cell + hash01(n, k, 2))
        c2 = np.floor(P @ f.astype(np.float32) / cell + hash01(n, k, 3))
        seg = hash01(n * 131.0 + c1 * 17.0 + c2, k, 4)
        out = np.maximum(out, line * (seg < keep) * (0.5 + 0.5 * hash01(n + c1 * 7.0 + c2 * 3.0, k, 5)))
    return out


def deriv(a, ok, axis):
    """Central difference along an axis, one-sided where a neighbour isn't on the same part."""
    fwd, bwd = np.roll(a, -1, axis), np.roll(a, 1, axis)
    okf, okb = np.roll(ok, -1, axis), np.roll(ok, 1, axis)
    if a.ndim == 3:
        okf, okb = okf[..., None], okb[..., None]
    return np.where(okf & okb, (fwd - bwd) * 0.5, np.where(okf, fwd - a, np.where(okb, a - bwd, 0.0)))


def compose(maps, out_dir):
    """Paint the maps from the bakes: a colour map per paint scheme; roughness, metalness, ambient occlusion
    and normals shared."""
    covered = maps["ids"][..., 0] > 0.5 / 16
    maps, _ = dilate(maps, covered)
    ids = maps["ids"]
    surf = np.clip(np.rint(ids[..., 0] * 16 - 1), 0, len(SURFACES) - 1).astype(np.int32)
    part = np.clip(np.rint(ids[..., 1] * 1024), 0, len(PART_INFO) - 1).astype(np.int32)
    prand = ids[..., 2]
    P = (maps["pos"][..., :3] * POS_SPAN + np.array(POS_LO, np.float32)) * 100.0  # cm
    N = maps["nrm"][..., :3] * 2.0 - 1.0
    ao, cav = maps["ao"][..., 0], maps["cav"][..., 0]
    e_small, e_big = maps["edge"][..., 0], maps["edge"][..., 1]
    u, v = maps["puv"][..., 0], maps["puv"][..., 1]
    Lu, Lv = maps["plen"][..., 0] * 200.0, maps["plen"][..., 1] * 200.0
    outer = np.rint(maps["plen"][..., 2] * 4) == 1
    n_fine, n_med, n_big = (maps["noise"][..., k] for k in range(3))
    micro = maps["grain"][..., 0]
    names = [p[0] for p in PART_INFO]

    def parts(*patterns):
        """Texels on the named parts; a pattern ending in * matches the start of a name."""
        return np.array([any(n.startswith(p[:-1]) if p.endswith("*") else n == p for p in patterns)
                         for n in names])[part]

    def facing(d, limit=0.35):
        return (N @ np.array(d, np.float32)) > limit

    def world(where, centre, right, up, mask, h, w=None):
        rel = P - np.array(centre, np.float32)
        return stamp(where, rel @ np.array(right, np.float32), rel @ np.array(up, np.float32), mask, h, w)

    def plate(where, uc, vc, mask, h, w=None):
        return stamp(where, (u - uc) * Lu, -(v - vc) * Lv, mask, h, w)

    def band(where, lo_cm, hi_cm, along):
        return where * smoothstep(lo_cm - 0.06, lo_cm + 0.06, along) * (1 - smoothstep(hi_cm - 0.06, hi_cm + 0.06, along))

    kind = {name: surf == i for i, name in enumerate(SURFACES)}
    painted = kind["armor"] | kind["accent"]

    # Panel lines 1.1 cm in from the edge of every sizeable plate, and rivets inside them on some.
    du, dv = np.minimum(u, 1 - u) * Lu, np.minimum(v, 1 - v) * Lv
    border = np.minimum(du, dv)
    big = outer & painted & (np.minimum(Lu, Lv) > 7.0)
    groove = big * (1 - smoothstep(0.07, 0.19, np.abs(border - 1.1)))
    rivets = big & parts("pauldron_l", "pauldron_r", "back_plate", "thigh_plate_*", "shin_guard_*", "gauntlet_*",
                         "calf_l", "calf_r")
    side_u = du < dv
    along, length = np.where(side_u, v * Lv, u * Lu), np.where(side_u, Lv, Lu)
    step = np.maximum(length / np.maximum(np.round(length / 4.2), 1), 0.1)
    dx = along - (np.floor(along / step) + 0.5) * step
    dy = np.where(side_u, du, dv) - 2.0
    rivet_r = np.sqrt(dx * dx + dy * dy) / 0.3
    dome = rivets * (np.minimum(along, length - along) > 1.6) * np.sqrt(np.clip(1 - rivet_r ** 2, 0, 1))
    height = -0.06 * groove + 0.06 * dome  # cm, for the normal map

    # Two-tone: a darker stripe up the breastplate's keel, ending in a chevron like the visor's, and the back of
    # the helmet.
    across = np.abs(u - 0.5) * Lu
    keel = (1 - smoothstep(2.1, 2.3, across)) * (1 - smoothstep(-0.1, 0.1, v * Lv + 0.9 * across - 0.72 * Lv))
    armor2 = parts("breastplate") * outer * keel
    armor2 = np.maximum(armor2, parts("skull") * smoothstep(1.5, 3.5, P[..., 1]) * (P[..., 2] > 156)) * painted

    # Markings: unit number 07 and RZ, printed labels, orange unit stripes, hazard stripes on the pack.
    chest = parts("breastplate") & outer & facing((0, -1, 0))
    white = world(chest, (7.4, 0, 133.4), (1, 0, 0), (0, 0, 1), text_mask("07"), 3.0)
    white = np.maximum(white, plate(parts("pauldron_l") & outer, 0.5, 0.52, text_mask("07"), 4.6))
    white = np.maximum(white, world(parts("thigh_plate_l") & outer & facing((0, -1, 0)), (11.2, 0, 76.0), (1, 0, 0),
                                    (0, 0, 1), text_mask("RZ"), 2.4))
    white = np.maximum(white, world(parts("rear_plate") & outer & facing((0, 1, 0)), (0, 0, 94.6), (-1, 0, 0),
                                    (0, 0, 1), text_mask("RZ-07"), 2.0))
    label, ink = label_mask(3)
    tag = world(chest, (7.4, 0, 129.9), (1, 0, 0), (0, 0, 1), label, 1.3, 4.0)
    tag_ink = world(chest, (7.4, 0, 129.9), (1, 0, 0), (0, 0, 1), ink, 1.3, 4.0)
    thigh_r = parts("thigh_plate_r") & outer & facing((0, -1, 0))
    label, ink = label_mask(11)
    tag = np.maximum(tag, world(thigh_r, (-11.0, 0, 76.0), (1, 0, 0), (0, 0, 1), label, 1.6, 5.0))
    tag_ink = np.maximum(tag_ink, world(thigh_r, (-11.0, 0, 76.0), (1, 0, 0), (0, 0, 1), ink, 1.6, 5.0))
    rim = (1 - v) * Lv  # cm from a plate's far end
    orange = band(parts("pauldron_r") & outer, 2.2, 4.0, rim)
    orange = np.maximum(orange, band(parts("gauntlet_*") & outer, 2.4, 3.3, rim))
    orange = np.maximum(orange, parts("skull") * (1 - smoothstep(0.75, 0.9, np.abs(P[..., 0])))
                        * (P[..., 2] > 164.5) * (P[..., 1] < 1.0))
    hazard = parts("pack") & facing((0, 0, 1), 0.7) & (P[..., 2] > 139.0)
    stripes = np.mod((P[..., 0] + P[..., 1]) / 2.4, 1.0) < 0.5
    orange = np.maximum(orange, hazard * stripes)
    black = hazard * ~stripes
    fade = smoothstep(0.18, 0.42, n_fine + 0.35 * (micro - 0.5) + 0.12)  # stencils worn patchy
    stencil = np.maximum(white, tag) * fade

    # Wear: paint rubbed thin, then chipped through to steel, on convex edges; scratches in patches.
    crease = 1 - smoothstep(0.45, 0.85, cav)
    edge = np.clip(e_big * 3.4, 0, 1) * (1 - crease)
    sharp = np.clip(e_small * 12.0, 0, 1) * (1 - crease)
    wear = edge * 0.85 + sharp * 0.35 + (n_fine - 0.5) * (0.3 + 0.9 * edge) + (micro - 0.5) * (0.12 + 0.3 * edge)
    scratches = scratch_lines(P, N) * smoothstep(0.58, 0.7, n_big + (n_med - 0.5) * 0.6)
    thin = smoothstep(0.40, 0.52, wear) * painted
    chips = np.maximum(smoothstep(0.58, 0.66, wear), scratches * 0.6) * painted
    worn_metal = (kind["dark"] | kind["steel"]) * np.maximum(smoothstep(0.55, 0.68, wear), scratches * 0.6)
    height -= 0.012 * chips

    # Grime in creases and occluded places, dust low on the legs and on what faces up, soot by the exhausts.
    grime = np.clip((1 - ao) * 0.95 + crease * 0.45 + (n_med - 0.5) * 0.55 - 0.12, 0, 1) ** 1.3
    dust = np.clip(smoothstep(40.0, 2.0, P[..., 2]) * (0.6 + (n_med - 0.5) * 1.2)
                   + smoothstep(0.6, 0.95, N[..., 2]) * 0.4 * n_big, 0, 1)
    soot = np.zeros(surf.shape, np.float32)
    for ex in ("exhaust_l", "exhaust_r"):
        pts = P[parts(ex)]
        if len(pts):
            top = np.array([pts[:, 0].mean(), pts[:, 1].mean(), pts[:, 2].max()], np.float32)
            d = P - top
            soot = np.maximum(soot, np.exp(-(d[..., 0] ** 2 + d[..., 1] ** 2) / 18.0 - np.maximum(-d[..., 2], 0) / 1.6))
    soot = np.clip(soot * (0.55 + 0.8 * (n_med - 0.5)), 0, 1)
    grime *= ~(kind["glow"] | kind["glass"])
    dust *= ~kind["glow"]

    rough = np.zeros(surf.shape, np.float32)
    metal = np.zeros(surf.shape, np.float32)
    for name, (r, m) in FINISH.items():
        rough[kind[name]] = r
        metal[kind[name]] = m
    rough = mix(rough, 0.42, stencil)
    rough = mix(rough, 0.33 + 0.1 * micro, chips)
    metal = mix(metal, 1.0, chips)
    metal = mix(metal, 1.0, worn_metal * kind["dark"] * 0.7)
    rough = mix(rough, rough - 0.08, worn_metal)
    rough += np.where(kind["steel"], 0.12 * (n_fine - 0.5) + 0.1 * scratches, 0.05 * (n_fine - 0.5))
    rough += np.where(kind["glass"], 0.14 * smoothstep(0.5, 0.75, n_med), 0.0)
    rough = np.clip(rough + grime * 0.1 + dust * 0.12 + soot * 0.2, 0.04, 1.0)
    metal = np.clip(metal * (1 - dust * 0.4) * (1 - soot * 0.6), 0, 1)

    tone = (1 + 0.08 * (prand - 0.5) + 0.07 * (n_big - 0.5) + 0.04 * (n_med - 0.5))[..., None]
    shade = (1 + 0.06 * (n_big - 0.5))[..., None]

    def paint(scheme):
        base = np.zeros(surf.shape + (3,), np.float32)
        for name in FINISH:
            if name != "glow":
                base[kind[name]] = lin(scheme.get(name) or PAINT[name])
        base *= tone
        base = mix(base, lin(scheme["armor2"]) * shade, armor2)
        base = mix(base, lin(PAINT["accent"]) * shade, orange * fade)
        base = mix(base, lin(PAINT["ink"]), black * fade)
        base = mix(base, lin(scheme.get("marking") or PAINT["marking"]), white * fade)
        base = mix(base, lin(PAINT["marking"]), tag * fade)
        base = mix(base, lin(PAINT["ink"]), tag_ink * tag * fade)
        base = mix(base, base * 1.18 + lin(PAINT["primer"]) * 0.12, thin * (1 - chips))
        base = mix(base, lin(PAINT["bare"]) * (0.85 + 0.3 * micro)[..., None], chips)
        base = mix(base, lin(PAINT["bare"]) * 0.8, worn_metal * np.where(kind["dark"], 0.55, 0.3))
        base = mix(base, lin(PAINT["grime"]), grime * 0.55)
        base = mix(base, lin(PAINT["dust"]), dust * 0.22)
        base = mix(base, lin(PAINT["soot"]), soot * 0.8)
        base *= (1 - 0.5 * groove)[..., None]
        base[kind["glow"]] = lin(OPTICS[scheme["optics"]])
        return base

    occlusion = np.clip(ao * (0.72 + 0.28 * cav) * (1 - 0.4 * groove), 0, 1)
    occlusion[kind["glow"]] = 1.0

    # Normals: OpenGL style (green up the picture), as s&box reads them. The height is in cm, so its slope
    # comes from the distance a texel spans on the model.
    slope = []
    for axis in (1, 0):
        dh = deriv(height, covered, axis)
        dp = np.linalg.norm(deriv(P, covered, axis), axis=-1)
        slope.append(np.where(dp > 1e-4, dh / np.maximum(dp, 1e-4), 0.0))
    normal = np.stack([-slope[0], -slope[1], np.ones_like(slope[0])], axis=-1)
    normal /= np.linalg.norm(normal, axis=-1, keepdims=True)

    out_dir.mkdir(parents=True, exist_ok=True)
    paths = {}
    for key, arr in (("rough", rough), ("metal", metal), ("ao", occlusion), ("normal", normal * 0.5 + 0.5)):
        paths[key] = out_dir / f"{NAME}_{key}.png"
        write_png(paths[key], arr)
    for key, scheme in SCHEMES.items():
        paths[scheme_name(key)] = out_dir / f"{scheme_name(key)}_color.png"
        write_png(paths[scheme_name(key)], to_srgb(paint(scheme)))
    for variant, colour in OPTICS.items():
        write_png(out_dir / f"{glow_name(variant)}.png", np.tile(np.array(colour, np.uint8), (16, 16, 1)))
    return paths


# ---------------------------------------------------------------------------------------------------------
# Export: the mesh goes into the rig's space and out as FBX beside the vmdl and its materials.


def load_image(path, colorspace):
    img = bpy.data.images.load(str(path), check_existing=True)
    img.reload()
    img.colorspace_settings.name = colorspace
    return img


def final_materials(tex_dir=OUT, scheme=""):
    """combat_robot (the painted maps) and combat_robot_glow, named as the vmdl's remaps expect; `scheme`
    picks the paint shown."""
    main = bpy.data.materials.get(NAME) or bpy.data.materials.new(NAME)
    nt = main.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    nt.links.new(bsdf.outputs[0], out.inputs["Surface"])
    for key, sock, space in (("color", "Base Color", "sRGB"), ("rough", "Roughness", "Non-Color"),
                             ("metal", "Metallic", "Non-Color"), ("normal", None, "Non-Color")):
        tex = nt.nodes.new("ShaderNodeTexImage")
        stem = scheme_name(scheme) if key == "color" else NAME
        tex.image = load_image(Path(tex_dir) / f"{stem}_{key}.png", space)
        if sock:
            nt.links.new(tex.outputs["Color"], bsdf.inputs[sock])
        else:
            nm = nt.nodes.new("ShaderNodeNormalMap")
            nm.uv_map = "UVMap"
            nt.links.new(tex.outputs["Color"], nm.inputs["Color"])
            nt.links.new(nm.outputs["Normal"], bsdf.inputs["Normal"])
    glow = bpy.data.materials.get(glow_name()) or bpy.data.materials.new(glow_name())
    bsdf = glow.node_tree.nodes.get("Principled BSDF")
    colour = tuple(lin(OPTICS[SCHEMES[scheme]["optics"]]).tolist()) + (1.0,)
    bsdf.inputs["Base Color"].default_value = colour
    bsdf.inputs["Emission Color"].default_value = colour
    bsdf.inputs["Emission Strength"].default_value = 3.0
    return main, glow


def assign_materials(obj, tex_dir=OUT, scheme=""):
    main, glow = final_materials(tex_dir, scheme)
    me = obj.data
    me.materials.clear()
    me.materials.append(main)
    me.materials.append(glow)
    surf = np.rint(mesh_array(me, "surf_id", 1, len(me.polygons))).astype(np.int32)
    me.polygons.foreach_set("material_index", (surf == list(SURFACES).index("glow")).astype(np.int32))


def finalize(obj):
    """One material slot per material, the mesh in the rig's space, parented and bound to it."""
    assign_materials(obj)
    me = obj.data
    me.transform(ARM.matrix_world.inverted())
    obj.parent = ARM
    obj.matrix_parent_inverse = Matrix.Identity(4)
    obj.matrix_basis = Matrix.Identity(4)
    obj.modifiers.new("rig", "ARMATURE").object = ARM
    for name in ("rest", "pidx", "puv", "plen", "pside", "part_id", "prand", "surf_id"):
        if name in me.attributes:
            me.attributes.remove(me.attributes[name])
    for mat in list(bpy.data.materials):
        if mat.users == 0:
            bpy.data.materials.remove(mat)
    coll = bpy.data.collections.get("robot_parts")
    if coll is not None and not coll.objects:
        bpy.data.collections.remove(coll)


def export_fbx(obj):
    for o in bpy.context.view_layer.objects:
        o.select_set(o in (obj, ARM))
    bpy.context.view_layer.objects.active = ARM
    path = OUT / f"{NAME}.fbx"
    bpy.ops.export_scene.fbx(filepath=str(path), use_selection=True, object_types={"ARMATURE", "MESH"},
                             add_leaf_bones=False, bake_anim=False, use_armature_deform_only=False,
                             apply_scale_options="FBX_SCALE_NONE", axis_forward="-Z", axis_up="Y",
                             primary_bone_axis="Y", secondary_bone_axis="X", mesh_smooth_type="OFF",
                             use_mesh_modifiers=True, path_mode="STRIP", embed_textures=False)
    return path


SOLDIER_PREFABS = "models/player/prefabs_v2"
SURFACE = "metal"  # the soldiers' hitboxes and ragdoll are flesh: shots at the robot should spark and clank instead


def kv_prefab(cls, target, extra=""):
    return f"""			{{
				_class = "{cls}"
				children =
				[
					{{
						_class = "Prefab"
						target_file = "{target}"
					}},
				]{extra}
			}},
"""


def soldier_prefab(prefab):
    return f"{SOLDIER_PREFABS}/{prefab}.vmdl_prefab"


def metal_prefab(prefab, name):
    """A copy of one of the soldiers' prefabs beside the model, in SURFACE instead of flesh."""
    text = (ROOT / "Assets" / soldier_prefab(prefab)).read_text(encoding="utf-8")
    for key in ("surface_property", "surface_prop"):
        text = text.replace(f'{key} = "flesh"', f'{key} = "{SURFACE}"')
    assert '"flesh"' not in text, prefab
    (OUT / f"{NAME}_{name}.vmdl_prefab").write_text(text, newline="\n")
    return f"{ASSET}/{NAME}_{name}.vmdl_prefab"


def kv_remap(a, b):
    return f"""							{{
								from = "{a}"
								to = "{b}"
							}},
"""


def write_vmdl():
    """The CT soldier's vmdl with the robot's mesh and materials: the same animation list, weight lists,
    ragdoll, hitboxes, game data, IK, attachments and animgraph, from the soldiers' shared prefabs (the
    hitboxes and ragdoll shapes from metal copies). Material groups swap the optics' colour, and the paint
    with its optics."""
    groups = ""

    def group(name, remaps):
        body = "".join(kv_remap(f"{ASSET}/{a}.vmat", f"{ASSET}/{b}.vmat") for a, b in remaps)
        return f"""					{{
						_class = "MaterialGroup"
						name = "{name}"
						remaps =
						[
{body}						]
					}},
"""
    for variant in OPTICS:
        if variant:
            groups += group(variant, [(glow_name(), glow_name(variant))])
    for key, scheme in SCHEMES.items():
        if key:
            remaps = [(NAME, scheme_name(key))]
            if scheme["optics"]:
                remaps.append((glow_name(), glow_name(scheme["optics"])))
            groups += group(key, remaps)
    prefabs = (kv_prefab("AnimationList", soldier_prefab("prefab_animation_list"), '\n\t\t\t\tdefault_root_bone_name = ""')
               + kv_prefab("WeightListList", soldier_prefab("prefab_weight_list_list"))
               + kv_prefab("PhysicsJointList", soldier_prefab("prefab_physics_joints"))
               + kv_prefab("PhysicsShapeList", metal_prefab("prefab_physics_shapes", "physics_shapes"))
               + kv_prefab("HitboxSetList", metal_prefab("prefab_hitbox_set_list", "hitboxes"))
               + kv_prefab("GameDataList", soldier_prefab("prefab_gamedatalist"))
               + kv_prefab("IKData", soldier_prefab("prefab_ikdata"))
               + kv_prefab("AttachmentList", soldier_prefab("prefab_attachments")))
    text = f"""<!-- kv3 encoding:text:version{{e21c7f3c-8a33-41c5-9977-a76d3a32aa0d}} format:modeldoc29:version{{3cec427c-1b0e-4d48-a90a-0436f33a6041}} -->
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
{kv_remap(f"{NAME}.vmat", f"{ASSET}/{NAME}.vmat")}{kv_remap(f"{glow_name()}.vmat", f"{ASSET}/{glow_name()}.vmat")}						]
						use_global_default = false
						global_default_material = "materials/default.vmat"
					}},
{groups}				]
			}},
			{{
				_class = "RenderMeshList"
				children =
				[
					{{
						_class = "RenderMeshFile"
						filename = "{ASSET}/{NAME}.fbx"
						import_translation = [ 0.0, 0.0, 0.0 ]
						import_rotation = [ 0.0, 0.0, 0.0 ]
						import_scale = 1.0
						align_origin_x_type = "None"
						align_origin_y_type = "None"
						align_origin_z_type = "None"
						parent_bone = ""
						import_filter =
						{{
							exclude_by_default = false
							exception_list = [  ]
						}}
					}},
				]
			}},
			{{
				_class = "ModelModifierList"
				children =
				[
					{{
						_class = "ModelModifier_ScaleAndMirror"
						scale = 0.3937
						mirror_x = false
						mirror_y = false
						mirror_z = false
						flip_bone_forward = false
						swap_left_and_right_bones = false
					}},
				]
			}},
{prefabs}		]
		model_archetype = ""
		primary_associated_entity = ""
		anim_graph_name = "animgraphs/rigged_human.vanmgrph"
		base_model_name = ""
	}}
}}"""
    path = OUT / f"{NAME}.vmdl"
    path.write_text(text, newline="\n")
    return path


def write_vmats():
    paths = []
    for key in SCHEMES:
        path = OUT / f"{scheme_name(key)}.vmat"
        path.write_text(f"""// Generated by Tools/build_campaign_robot.py

Layer0
{{
	shader "shaders/complex.shader"

	//---- PBR ----
	F_METALNESS_TEXTURE 1
	F_SPECULAR 1

	//---- Ambient Occlusion ----
	g_flAmbientOcclusionDirectDiffuse "0.600"
	g_flAmbientOcclusionDirectSpecular "0.700"
	TextureAmbientOcclusion "{ASSET}/{NAME}_ao.png"

	//---- Color ----
	g_flModelTintAmount "1.000"
	g_vColorTint "[1.000000 1.000000 1.000000 0.000000]"
	TextureColor "{ASSET}/{scheme_name(key)}_color.png"

	//---- Fog ----
	g_bFogEnabled "1"

	//---- Metalness ----
	TextureMetalness "{ASSET}/{NAME}_metal.png"

	//---- Normal ----
	TextureNormal "{ASSET}/{NAME}_normal.png"

	//---- Roughness ----
	g_flRoughnessScaleFactor "1.000"
	TextureRoughness "{ASSET}/{NAME}_rough.png"
}}
""", newline="\n")
        paths.append(path)
    for variant in OPTICS:
        name = glow_name(variant)
        path = OUT / f"{name}.vmat"
        path.write_text(f"""// Generated by Tools/build_campaign_robot.py: the optics, self-lit

Layer0
{{
	shader "shaders/complex.shader"
	F_SELF_ILLUM 1
	TextureColor "{ASSET}/{name}.png"
	TextureSelfIllumMask "{ASSET}/{name}.png"
	g_flSelfIllumBrightness "6.0"
	g_flSelfIllumAlbedoFactor "1.0"
	g_vColorTint "[1.000000 1.000000 1.000000 0.000000]"
	g_flModelTintAmount "0.000"
	g_flMetalness "0.000"
	g_bFogEnabled "1"
}}
""", newline="\n")
        paths.append(path)
    return paths


def save_blend():
    """A copy of the scene beside the model, textures linked relatively; the session keeps its own file."""
    path = OUT / f"{NAME}.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(path), copy=True, relative_remap=True, compress=True)
    Path(str(path) + "1").unlink(missing_ok=True)
    return path


# ---------------------------------------------------------------------------------------------------------
# Beauty renders: Cycles, the painted materials, a grey studio.


def clear_beauty():
    """Take the studio down (a failed run can leave it behind)."""
    for obj in [o for o in bpy.data.objects if o.name.startswith("beauty_")]:
        bpy.data.objects.remove(obj)
    for coll in (bpy.data.meshes, bpy.data.lights, bpy.data.cameras, bpy.data.materials):
        for item in list(coll):
            if item.name.startswith("beauty_") and item.users == 0:
                coll.remove(item)


def beauty(tag="beauty", views=("three_quarter", "front", "back", "side")):
    scene = bpy.context.scene
    clear_beauty()
    use_cycles(scene)
    scene.cycles.samples = 128
    scene.cycles.use_denoising = True
    scene.render.resolution_x, scene.render.resolution_y = 1000, 1200
    scene.render.film_transparent = False
    scene.world.color = (0.05, 0.055, 0.06)
    def add(obj):
        scene.collection.objects.link(obj)
        return obj
    floor_me = bpy.data.meshes.new("beauty_floor")
    floor_me.from_pydata([(-3, -3, 0), (3, -3, 0), (3, 3, 0), (-3, 3, 0)], [], [(0, 1, 2, 3)])
    add(bpy.data.objects.new("beauty_floor", floor_me))
    floor_mat = bpy.data.materials.new("beauty_floor")
    fb = floor_mat.node_tree.nodes.get("Principled BSDF")
    fb.inputs["Base Color"].default_value = (0.09, 0.09, 0.095, 1)
    fb.inputs["Roughness"].default_value = 0.7
    floor_me.materials.append(floor_mat)
    scene.view_settings.view_transform = "AgX"
    scene.view_settings.look = "AgX - Medium High Contrast"
    # Watts for about 3 W/m² from the key and rim at the chest (E = P / (pi d²)) and a quarter of that from the fill.
    for name, loc, energy, size, colour in (("key", (-2.2, -2.6, 3.2), 160, 1.6, (1.0, 0.96, 0.9)),
                                            ("fill", (2.8, -2.0, 1.4), 28, 2.5, (0.85, 0.9, 1.0)),
                                            ("rim", (1.2, 3.0, 2.8), 120, 1.2, (0.9, 0.95, 1.0))):
        light = bpy.data.lights.new(f"beauty_{name}", "AREA")
        light.energy, light.size, light.color = energy, size, colour
        obj = add(bpy.data.objects.new(f"beauty_{name}", light))
        obj.location = loc
        obj.rotation_euler = (Vector((0, 0, 1.0)) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    cam_data = bpy.data.cameras.new("beauty_cam")
    cam_data.lens = 70
    cam = add(bpy.data.objects.new("beauty_cam", cam_data))
    scene.camera = cam
    ARM.hide_render = True
    shots = {  # view: direction to the camera, height looked at (m), distance (m)
        "three_quarter": ((0.75, -1, 0.18), 0.9, 5.2), "front": ((0, -1, 0.08), 0.9, 5.2),
        "back": ((-0.2, 1, 0.12), 0.9, 5.2), "side": ((1, -0.1, 0.08), 0.9, 5.2), "low": ((0.55, -1, -0.05), 0.9, 5.2),
        "close_front": ((0.35, -1, 0.1), 1.45, 1.6), "close_back": ((-0.3, 1, 0.15), 1.45, 1.6),
        "close_legs": ((0.5, -1, 0.1), 0.45, 1.8),
    }
    out_dir = PREVIEW_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    try:
        for view in views:
            direction, height, distance = shots[view]
            d = Vector(direction).normalized()
            cam.location = Vector((0, 0, height)) + d * distance
            cam.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()
            scene.render.filepath = str(out_dir / f"{tag}_{view}.png")
            bpy.ops.render.render(write_still=True)
            paths.append(scene.render.filepath)
    finally:
        clear_beauty()
    return paths


def want(stage):
    return STAGES == "all" or stage in STAGES.split(",")


def resume():
    """Pick up a robot built by an earlier run in this Blender session, for running later stages alone."""
    global ROBOT, ARM
    ROBOT = bpy.data.objects.get(NAME)
    ARM = bpy.data.objects.get("robot_rig")
    if ROBOT is not None:
        PART_INFO[:] = [tuple(p) for p in json.loads(ROBOT["robot_parts"])]


if __name__ == "__main__":
    # Stages (ROBOT_STAGES, comma separated, default all): geometry, preview (workbench shots of the parts), bake,
    # textures, export, beauty. Later stages alone pick up what an earlier run left in this Blender session.
    if want("geometry"):
        build_geometry()
        if want("preview"):
            RESULT_PREVIEWS = preview(views=globals().get("PREVIEW_VIEWS") or ("front", "side", "back", "three_quarter"))
    else:
        resume()
    if want("bake"):
        if ROBOT is None:
            assemble()
            unwrap(ROBOT)
        assert ROBOT.parent is None, "the robot is already exported; rebuild it (stage geometry) to bake again"
        bpy.app.driver_namespace["robot_bake"] = bake(ROBOT)
    if want("textures"):
        RESULT_TEXTURES = compose(bpy.app.driver_namespace["robot_bake"], OUT)
    if want("export"):
        if ROBOT.parent is None:
            finalize(ROBOT)
        else:
            final_materials()
        RESULT_EXPORT = [export_fbx(ROBOT), write_vmdl(), *write_vmats(), save_blend()]
    if want("beauty"):
        RESULT_BEAUTY = beauty(views=globals().get("BEAUTY_VIEWS") or ("three_quarter", "front", "back", "side"))
