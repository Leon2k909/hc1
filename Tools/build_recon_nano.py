"""Build the hand-launched Nano Drone in a fresh, background Blender 5.1 process.

    blender -b --factory-startup --python Tools/build_recon_nano.py -- --stages all

Metres, X forward/Y left/Z up; exported OBJ uses ModelDoc's Y-up convention and inches.
The 245 mm airframe has a 190 mm main rotor, a slender tail boom and a vertical tail
rotor. Body, stabilised nose camera, both hubs, both props and both blur discs are
separate models. All solid parts share one baked 1024 px PBR atlas. No third-party
branding. The existing recon tablet is shared by the equipment, not duplicated.

Reuse the octocopter's mesh/UV/bake/export helpers in a private module instance;
none of that aircraft's files or configuration is changed by this build.
"""
import argparse
import importlib.util
import json
import math
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Matrix, Vector

ROOT = Path(__file__).resolve().parents[1]
NAME = "recon_nano"
OUT = ROOT / "Assets/models" / NAME
PREVIEW = ROOT / "output/recon-nano"
INCH = 39.37008
MAIN_R, TAIL_R = 0.095, 0.018
MAIN_HUB = np.array((-0.012, 0.0, 0.045))
TAIL_HUB = np.array((-0.181, -0.006, 0.029))
CAMERA = np.array((0.054, 0.0, -0.006))
CAMERA_R = 0.009
TAIL_FRAME = np.array(((1., 0., 0.), (0., 0., -1.), (0., 1., 0.)))

spec = importlib.util.spec_from_file_location("nano_mesh_pipeline", ROOT / "Tools/build_recon_octocopter.py")
p = importlib.util.module_from_spec(spec)
spec.loader.exec_module(p)
rd = p.rd
p.NAME, p.OUT, p.ASSET = NAME, OUT, f"models/{NAME}"
p.TEX, p.PAD = 1024, 8 / 1024
p.POS_LO, p.POS_SPAN = np.array((-0.26, -0.12, -0.06)), 0.40
p.RECTS = {"drone": {}}
p.SURF = {
    "shell": ((55, 58, 60), 0.57, 0.0),
    "boom": ((32, 34, 35), 0.44, 0.0),
    "fin": ((51, 54, 55), 0.58, 0.0),
    "metal": ((48, 50, 52), 0.36, 1.0),
    "camera": ((39, 42, 44), 0.45, 0.0),
    "blade": ((24, 25, 26), 0.40, 0.0),
}
I = np.eye(3)
body = {"body": [I]}
LODS = {0: (28, 32), 1: (16, 20), 2: (8, 12)}


def pod(a, b):
    t, th = np.pi * a, 2 * np.pi * b
    x = 0.003 - 0.055 * np.cos(t)
    w = 0.017 * np.sin(t) * (0.80 + 0.20 * np.sin(t))
    zc = 0.003 + 0.004 * np.cos(t)
    z = zc + 0.017 * np.sin(t) * p.sgnpow(np.sin(th), 0.78)
    return p.stack3(x, w * p.sgnpow(np.cos(th), 0.85), z), p.stack3(x, 0, zc)


def tube(start, end, r0, r1):
    start, end = np.asarray(start), np.asarray(end)
    length = np.linalg.norm(end - start)
    axis = (end - start) / length
    stations = rd.Stations([(0., 0.), (0., r0), (length, r1), (length, 0.)])
    side = (0., 1., 0.) if abs(axis[1]) < 0.9 else (1., 0., 0.)
    return p.lathe(stations, start, axis, side), stations.sampler({0: range(4), 1: range(4), 2: range(4)})


def ball(a, b):
    phi, beta = np.pi * a, 2 * np.pi * b - np.pi
    d = p.stack3(np.sin(phi) * np.cos(beta), np.cos(phi), np.sin(phi) * np.sin(beta))
    return CAMERA_R * d, np.zeros_like(d)


def scaled(fn, scale):
    def shape(a, b):
        P, C = fn(a, b)
        return P * scale, C * scale
    return shape


def rotor_disc(radius, side):
    def shape(a, b):
        r = radius * (0.012 + 1.012 * a)
        th = 2 * np.pi * b * side
        P = p.stack3(r * np.cos(th), r * np.sin(th), radius * 0.0012 * side)
        return P, P - p.stack3(0, 0, 0.003 * side)
    return shape


def disc_uv(radius):
    return lambda a, b, P: np.stack((0.5 + P[..., 0] / (2.05 * radius),
                                     0.5 + P[..., 1] / (2.05 * radius)), axis=-1)


parts = [p.Part("pod", "shell", pod, LODS, body, density=1.8),
         p.Part("camera", "camera", ball, {0: (24, 32), 1: (12, 20)}, {"gimbal": [I]}, density=2.3),
         p.Part("battery", "shell", p.rbox((-0.016, 0, -0.010), (0.024, 0.012, 0.006), 0.4), LODS, body),
         p.Part("mast_fairing", "shell", p.rbox((-0.012, 0, 0.020), (0.008, 0.007, 0.009), 0.5), LODS, body),
         p.Part("tail_fin", "fin", p.rbox((-0.175, 0, 0.033), (0.012, 0.0012, 0.022), 0.5),
                {0: (14, 16), 1: (8, 12), 2: (6, 8)}, body),
         p.Part("tailplane", "fin", p.rbox((-0.133, 0, 0.015), (0.009, 0.024, 0.0012), 0.5),
                {0: (10, 16), 1: (6, 12), 2: (4, 8)}, body)]

for name, surf, start, end, r0, r1 in [
    ("tail_boom", "boom", (-0.033, 0, 0.008), (-0.184, 0, 0.029), 0.0033, 0.0017),
    ("main_shaft", "metal", (-0.012, 0, 0.018), tuple(MAIN_HUB), 0.002, 0.002),
    ("tail_motor", "metal", (-0.181, 0.002, 0.029), tuple(TAIL_HUB), 0.004, 0.003),
]:
    fn, rows = tube(start, end, r0, r1)
    parts.append(p.Part(name, surf, fn, {0: (3, 20), 1: (3, 12), 2: (3, 8)}, body, a_rows=rows))

# The blades and the analytic blur have the same scaled airfoil/chord/twist.
for which, radius in (("main", MAIN_R), ("tail", TAIL_R)):
    scale = radius / p.PROP_R
    prop, hub, disc = f"prop_{which}", f"hub_{which}", f"disc_{which}"
    parts.append(p.Part(f"blade_{which}", "blade", scaled(p.blade, scale), {0: (30, 22), 1: (14, 12)},
                        {prop: [I, p.rot_z(180)]}, density=1.8,
                        a_rows=rd.ends_rounded({0: 22, 1: 10}, {0: 4, 1: 2}, 0.,
                                              1 - 0.014 / (p.PROP_R - p.BLADE_R0)),
                        b_rows=rd.tau_rows(p.PROP_FOIL)))
    # A narrow root bridges the airfoil to its spindle; it rotates with the blades.
    parts.append(p.Part(f"root_{which}", "blade", p.rbox((0, 0, 0),
                       (p.BLADE_R0 * scale, 0.009 * scale, 0.003 * scale), 0.55),
                       {0: (8, 12), 1: (6, 8)}, {prop: [I]}))
    parts.append(p.Part(f"hub_{which}", "metal", scaled(p.lathe(p.HUB, (0, 0, 0), (0, 0, 1), (1, 0, 0)), scale),
                       {0: (8, 24), 1: (8, 12)}, {hub: [I]},
                       a_rows=p.HUB.sampler({0: range(len(p.HUB.a)), 1: range(len(p.HUB.a))})))
    for side in (1, -1):
        parts.append(p.Part(f"disc_{which}_{side}", "blade", rotor_disc(radius, side), {0: (2, 48)},
                            {disc: [I]}, atlas=None, material=f"{NAME}_disc", uv=disc_uv(radius)))
p.PARTS, p.PART_INDEX = parts, {v.name: i for i, v in enumerate(parts)}
p.MODELS = {
    "body": dict(file=NAME, lods=(0, 1, 2), thresholds=(0., 6., 18.), at=np.zeros(3)),
    "gimbal": dict(file=f"{NAME}_gimbal", lods=(0, 1), thresholds=(0., 5.), at=CAMERA),
}
for i, which in enumerate(("main", "tail")):
    offset = np.array((0.0, 0.0, 0.5 + i * 0.25))
    for kind in ("prop", "hub", "disc"):
        name = f"{kind}_{which}"
        p.MODELS[name] = dict(file=f"{NAME}_{name}", lods=(0,) if kind == "disc" else (0, 1),
                              thresholds=(0.,) if kind == "disc" else (0., 5.),
                              at=None if kind == "disc" else offset)


def pack(atlas="drone"):
    items = sorted([(q.name, max(q.around, q.along) * q.density,
                     min(q.around, q.along) * q.density, q.along > q.around)
                    for q in parts if q.atlas == atlas], key=lambda q: -q[2])

    def place(scale):
        x = y = row = 0.
        rects = {}
        for name, w, h, rotate in items:
            W, H = w * scale + 2 * p.PAD, h * scale + 2 * p.PAD
            if W > 1:
                return None
            if x + W > 1:
                x, y, row = 0., y + row, 0.
            rects[name] = (x + p.PAD, y + p.PAD, w * scale, h * scale, rotate)
            x, row = x + W, max(row, H)
        return rects if y + row <= 1 else None

    lo, hi = 0., 4000.
    for _ in range(50):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if place(mid) else (lo, mid)
    p.RECTS[atlas] = place(lo)
    return lo
p.pack = pack


def bake_pos(nt):
    return rd.vmath(nt, "MULTIPLY_ADD", rd.attr(nt, "rest"), (1 / p.POS_SPAN,) * 3,
                    tuple(-c / p.POS_SPAN for c in p.POS_LO))


def bake_noise(nt):
    v = rd.attr(nt, "rest")
    return rd.xyz(nt, rd.noise(nt, v, 1470, 4, .55), rd.noise(nt, v, 210, 5, .6),
                  rd.noise(nt, v, 32, 3, .5))


rd.BAKE_PASSES = {
    "ids": ("EMIT", rd.pass_ids, 1, None), "pos": ("EMIT", bake_pos, 1, None),
    "nrm": ("EMIT", rd.pass_nrm, 1, None), "noise": ("EMIT", bake_noise, 1, None),
    "edge": ("EMIT", rd.pass_edge, 16, None), "ao": ("AO", None, 128, .025),
    "cav": ("AO", None, 64, .0025),
}


def geometry():
    fresh = not bpy.data.filepath and {q.name for q in bpy.data.objects} <= {"Cube", "Camera", "Light"}
    if not fresh:
        raise RuntimeError("Run the nano builder with -b --factory-startup; it requires its own Blender process.")
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.name = "Nano Drone"
    scene.unit_settings.system = "METRIC"
    print(f"Nano atlas UV scale: {pack():.3f} per metre", flush=True)
    for model, info in p.MODELS.items():
        for lod in info["lods"]:
            v, f, uv, part, mats, rest = p.build(model, lod)
            obj = p.make_object(f"{info['file']}_lod{lod}", v, f, uv, part, mats, rest)
            obj.hide_render = lod != 0 or model not in ("body", "gimbal")
            obj.hide_set(lod != 0)
            if model == "gimbal":
                obj.location = CAMERA
            print(f"{obj.name}: {sum(len(q) - 2 for q in f)} triangles", flush=True)
    for which, hub, frame in (("main", MAIN_HUB, I), ("tail", TAIL_HUB, TAIL_FRAME)):
        for kind in ("prop", "hub"):
            src = bpy.data.objects[f"{NAME}_{kind}_{which}_lod0"]
            obj = bpy.data.objects.new(f"view_{kind}_{which}", src.data)
            obj.location = hub
            obj.rotation_euler = Matrix(frame.tolist()).to_euler()
            scene.collection.objects.link(obj)


def paint(maps):
    c = p.Canvas(maps)
    x, y, z = np.moveaxis(c.P, -1, 0)
    nx, ny, nz = np.moveaxis(c.N, -1, 0)
    shell = c.on("pod", "battery", "mast_fairing", "tail_fin", "tailplane")
    # Fine shell join, battery end seam and nose heat exhaust slots.
    join = c.on("pod") * rd.groove(z - .001, .00027)
    battery = c.on("battery") * rd.groove(x + .035, .0003)
    slots = c.on("pod") & (x > -.005) & (x < .018) & (z > .007) & (z < .014) & (np.abs(ny) > .65)
    vents = slots * rd.groove((x + .001) % .003 - .0015, .0004)
    c.paint(join + battery + vents, (17, 19, 20), .72, 0.)
    c.height -= (join + battery + vents) * .00015
    # Two small coated sensor windows in the camera ball: blue EO and amber IR.
    front = c.on("camera") & (nx > .6)
    for cy, cz, radius, colour in ((.0031, .0015, .0026, (12, 28, 38)),
                                  (-.0031, -.0015, .0021, (44, 30, 19))):
        distance = np.hypot(y - cy, z - cz)
        rim = front & (distance < radius + .0005)
        lens = front & (distance < radius)
        c.paint(rim, (72, 75, 78), .29, 1.)
        c.paint(lens, colour, .09, .65)
        c.height -= lens * .00015
    c.text(c.on("pod") & (ny < -.6), x + .005, z - .007, "RZ 04107", .0032,
           (174, 177, 174), texel=.00009)
    c.text(c.on("battery") & (nz < -.65), x + .015, y, "NANO", .003,
           (151, 154, 150), texel=.00009)
    # Small countersunk fasteners, kept at the scale of a palm-sized aircraft.
    for sx in (-.028, .023):
        d = np.hypot(x - sx, z - .002)
        c.screw(c.on("pod") & (np.abs(ny) > .55), d, r=.0007, slot=z - .002)
    c.wear(shell.astype(np.float32) * .30, shell.astype(np.float32) * .06)
    c.height += (c.grain - .5) * .000006 * shell
    return c.finish(OUT, NAME)


def inches(v):
    return [round(float(q) * INCH, 5) for q in v]


def export():
    OUT.mkdir(parents=True, exist_ok=True)
    info = {}
    for model, m in p.MODELS.items():
        info[m["file"]] = {}
        mats = {}
        for lod in m["lods"]:
            obj = bpy.data.objects[f"{m['file']}_lod{lod}"]
            tris, lo, hi = p.write_obj(OUT / f"{m['file']}_lod{lod}.obj", obj, mats)
            info[m["file"]][f"lod{lod}"] = dict(triangles=tris, bounds_min=list(map(float, lo)),
                                                bounds_max=list(map(float, hi)))
        p.write_vmdl(m["file"], m["lods"], m["thresholds"], list(mats))
    info.update({"units": "inches; X forward, Y left, Z up", "atlas": p.TEX,
                 "gimbal_pivot": inches(CAMERA), "gimbal_lens": inches((CAMERA_R, 0, 0)),
                 "rotors": [dict(name="main", position=inches(MAIN_HUB), rotation=[0, 0, 0, 1], spin=1,
                                  radius=MAIN_R * INCH, rpm_scale=1., shader_scale=p.PROP_R / MAIN_R),
                             dict(name="tail", position=inches(TAIL_HUB),
                                  rotation=[math.sqrt(.5), 0, 0, math.sqrt(.5)], spin=1,
                                  radius=TAIL_R * INCH, rpm_scale=4.2, shader_scale=p.PROP_R / TAIL_R)],
                 # Swept flight box, including the main rotor and the tail, with a few mm of margin.
                 "hull_min": inches((-.204, -.098, -.020)), "hull_max": inches((.088, .098, .056))})
    (OUT / "asset-info.json").write_text(json.dumps(info, indent=2) + "\n", encoding="utf-8")
    (OUT / f"{NAME}.vmat").write_text(p.atlas_vmat(NAME), encoding="utf-8")
    (OUT / f"{NAME}_disc.vmat").write_text(p.DISC_VMAT, encoding="utf-8")
    for q in OUT.iterdir():
        if q.suffix in (".obj", ".mtl", ".vmat", ".vmdl"):
            text = q.read_text(encoding="utf-8").replace("Tools/build_recon_octocopter.py", "Tools/build_recon_nano.py")
            q.write_text(text, encoding="utf-8", newline="\n")
    if (OUT / f"{NAME}_color.png").exists():
        p.final_material(NAME)
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT / f"{NAME}.blend"), copy=True, compress=True, relative_remap=True)
    (OUT / f"{NAME}.blend1").unlink(missing_ok=True)
    return info


def render(tag, painted):
    scene = bpy.context.scene
    PREVIEW.mkdir(parents=True, exist_ok=True)
    if painted:
        rd.use_cycles(scene)
        scene.cycles.samples = 64
        scene.cycles.use_denoising = True
        p.final_material(NAME)
    else:
        scene.render.engine = "BLENDER_WORKBENCH"
        scene.display.shading.light = "STUDIO"
        scene.display.shading.color_type = "SINGLE"
        scene.display.shading.single_color = (.30, .32, .34)
        scene.display.shading.show_cavity = True
        scene.display.shading.cavity_type = "BOTH"
    scene.render.resolution_x, scene.render.resolution_y = 1200, 800
    scene.render.resolution_percentage = 100
    scene.view_settings.view_transform = "AgX" if painted else "Standard"
    scene.world = bpy.data.worlds.new("Nano studio")
    scene.world.color = (.13, .14, .16)
    created = []
    if painted:
        for name, location, energy, size in (("key", (.18, -.3, .4), 10., .3),
                                             ("fill", (.3, .25, .12), 4., .3),
                                             ("rim", (-.3, .1, .3), 8., .2)):
            light = bpy.data.lights.new(name, "AREA")
            light.energy, light.size = energy, size
            obj = bpy.data.objects.new(name, light)
            scene.collection.objects.link(obj)
            obj.location = location
            obj.rotation_euler = (Vector((-.05, 0, .015)) - obj.location).to_track_quat("-Z", "Y").to_euler()
            created.append(obj)
    data = bpy.data.cameras.new("Nano preview")
    camera = bpy.data.objects.new("Nano preview", data)
    scene.collection.objects.link(camera)
    scene.camera = camera
    data.clip_start, data.clip_end = .001, 10.
    data.type = "ORTHO"
    data.ortho_scale = .39
    target = Vector((-.055, 0, .015))
    for view, direction in (("three_quarter", (.9, -1.5, .9)), ("side", (0, -1, .12)), ("top", (0, 0, 1))):
        camera.location = target + Vector(direction).normalized() * .6
        camera.rotation_euler = (target - camera.location).to_track_quat("-Z", "Y").to_euler()
        scene.render.filepath = str(PREVIEW / f"{tag}_{view}.png")
        bpy.ops.render.render(write_still=True)
    scene.camera = None
    for obj in created + [camera]:
        bpy.data.objects.remove(obj, do_unlink=True)


def main():
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--stages", default="all")
    stages = parser.parse_args(args).stages.split(",")
    wants = lambda name: "all" in stages or name in stages
    geometry()
    if wants("preview"):
        render("geometry", False)
    if wants("textures"):
        OUT.mkdir(parents=True, exist_ok=True)
        paint(p.bake("drone"))
    if wants("export"):
        export()
    if wants("beauty"):
        render("painted", True)
    print("Nano build complete.", flush=True)


if __name__ == "__main__":
    main()
