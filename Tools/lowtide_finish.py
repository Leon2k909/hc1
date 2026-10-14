"""Lowtide's visual finish; additive geometry, scoped materials and lighting.

Run this independently to preserve all previously authored map meshes:
    rtk proxy python Tools/lowtide_finish.py [--silt-source generated.png]
The main map generator also includes the finish on subsequent rebuilds.
"""
import argparse
import json
import math
import shutil
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage

import map_kit as K
from lowtide_brick import metadata
import lowtide_banks as BANKS

SOURCE = K.ROOT / "Sources/Lowtide/visual-target/estuary-silt-source.png"
DIRECTORY = K.ASSETS / "materials/lowtide/finish"
RESOURCE = "materials/lowtide/finish"
MODEL = "lowtide_finish"


def bake_silt(source):
    SOURCE.parent.mkdir(parents=True, exist_ok=True)
    if Path(source).resolve() != SOURCE.resolve():
        shutil.copy2(source, SOURCE)
    # Technical map bake only: preserve the generated source, resize to the
    # engine's power-of-two format and derive very shallow submillimetre relief.
    rgb = np.asarray(Image.open(SOURCE).convert("RGB").resize((2048, 2048), Image.Resampling.LANCZOS), float) / 255
    lum = rgb @ np.array([.2126, .7152, .0722])
    detail = lum - ndimage.gaussian_filter(lum, 9, mode="wrap")
    h = ndimage.gaussian_filter(detail, 1.2, mode="wrap") * .55
    dx = (np.roll(h, -1, 1) - np.roll(h, 1, 1)) * 2.5
    dy = (np.roll(h, -1, 0) - np.roll(h, 1, 0)) * 2.5
    normal = np.stack([-dx, dy, np.ones_like(h)], -1)
    normal /= np.linalg.norm(normal, axis=-1, keepdims=True)
    maps = {"color": rgb, "normal": normal * .5 + .5,
            "rough": np.clip(.78 + detail * .24, .65, .9)}
    DIRECTORY.mkdir(parents=True, exist_ok=True)
    for suffix, data in maps.items():
        path = DIRECTORY / f"silt_{suffix}.png"
        Image.fromarray(np.rint(data * 255).clip(0, 255).astype(np.uint8)).save(path)
        metadata(path)


def write_materials():
    DIRECTORY.mkdir(parents=True, exist_ok=True)
    if not (DIRECTORY / "silt_color.png").exists():
        raise FileNotFoundError("Bake the generated silt source before writing finish materials")
    for name in ("lt_mud", "lt_mud_wet"):
        path = K.ASSETS / f"materials/lowtide/{name}.vmat"
        K.write_text(path, f'''// Tools/lowtide_finish.py: one continuous estuary surface.
"Layer0"
{{
    shader "shaders/hc1_lowtide_silt.shader"
    F_SPECULAR "1"
    TextureColor "{RESOURCE}/silt_color.png"
    TextureNormal "{RESOURCE}/silt_normal.png"
    TextureRoughness "{RESOURCE}/silt_rough.png"
    TextureWetColor "{BANKS.WET_RESOURCE}_color.png"
    TextureWetNormal "{BANKS.WET_RESOURCE}_normal.png"
    TextureAmbientOcclusion "materials/default/default_ao.tga"
    TextureMetalness "materials/default/default_black_mask.tga"
}}
''')
        metadata(path)
    # Share the verified generated-granite definition with the masonry pass.
    # Re-running finish must not restore the old placeholder ashlar material.
    from lowtide_masonry import granite_material_text
    K.write_text(DIRECTORY / "lt_quay_stone.vmat", granite_material_text(128 / 78.7402, 1.0))
    for name, tint, metal, rough, scan in (
        ("lt_drain_iron", ".48 .51 .48", .45, .62, "lt_bridge_steel"),
        ("lt_drain_edge", ".72 .74 .70", .6, .48, "lt_bridge_steel"),
        ("lt_rope_detail", ".70 .62 .50", 0, .85, "sacks/lt_jute"),
        ("lt_bank_stone", ".65 .64 .61", 0, .69, "finish/silt"),
    ):
        K.write_text(DIRECTORY / f"{name}.vmat", f'''"Layer0"
{{
    shader "shaders/complex.shader"
    F_SPECULAR "1"
    TextureColor "materials/lowtide/{scan}_color.png"
    TextureNormal "materials/lowtide/{scan}_normal.png"
    TextureRoughness "[{rough} {rough} {rough} 0]"
    g_vColorTint "[{tint} 1]"
    g_flMetalness "{metal}"
}}
''')
    for path in DIRECTORY.glob("*.vmat"):
        metadata(path)
    for name, tint in (("lt_hull_black", ".19 .22 .22"), ("lt_hull_red", ".44 .16 .11")):
        # The barge used untextured solid colours; reuse a generated steel scan
        # at its authored UV scale for fine paint wear and restrained relief.
        K.write_text(K.ASSETS / f"materials/lowtide/{name}.vmat", f'''"Layer0"
{{
    shader "shaders/complex.shader"
    F_SPECULAR "1"
    TextureColor "materials/lowtide/lt_bridge_steel_color.png"
    TextureNormal "materials/lowtide/lt_bridge_steel_normal.png"
    TextureRoughness "[0.58 0.58 0.58 0]"
    g_flMetalness "0.2"
    g_vColorTint "[{tint} 1]"
}}
''')
    metadata(K.ASSETS / "shaders/hc1_lowtide_silt.shader")


def configure(model):
    for paint in model.polygons:
        if paint in ("lt_drain_iron", "lt_drain_edge", "lt_rope_detail", "lt_bank_stone"):
            model.material_overrides[paint] = f"{RESOURCE}/{paint}.vmat"
            model.tile_overrides[paint] = 36
        elif paint == "ashlar_grey":
            model.material_overrides[paint] = f"{RESOURCE}/lt_quay_stone.vmat"
    return model


def drainpipe(m, L, e, n, top, out, bottom=3):
    """Four-inch cast iron pipe, socket joints, wall fixings and rain hopper."""
    out = np.asarray(out, float)
    foot = np.array([e, n, bottom], float) + out * 5
    head = np.array([e, n, top - 10], float) + out * 5
    L.bar(m, foot, head, 2.0, "lt_drain_iron", sides=12)
    for z in np.arange(bottom + 16, top - 20, 92):
        at = np.array([e, n, z], float) + out * 5
        L.bar(m, at, at + (0, 0, 4), 2.55, "lt_drain_edge", sides=12)
        m.beam(at, at - out * 5, (1.1, 1.1), "lt_drain_iron")
    L.bar(m, foot + (0, 0, 9), foot + out * 6, 2.0, "lt_drain_iron", sides=12)
    m.box(head + (-4.3, -4.3, 0), head + (4.3, 4.3, 8), "lt_drain_iron")
    m.box(head + (-5, -5, 8), head + (5, 5, 9), "lt_drain_edge")


def grate(m, e, n, width=23, length=32):
    # Flush grates have no new collision; the existing pavement supports players.
    m.box((e-width/2, n-length/2, .02), (e+width/2, n+length/2, .10), "lt_drain_iron")
    for x in (-width/2, width/2):
        m.box((e+x-.6, n-length/2-.8, .10), (e+x+.6, n+length/2+.8, .45), "lt_drain_edge")
    for y in np.arange(-length/2, length/2+1, 3):
        m.box((e-width/2, n+y-.45, .12), (e+width/2, n+y+.45, .40), "lt_drain_edge")


def gutter(m, L, e0, e1, n, height):
    """Open half-round iron gutter, rolled lips, stop ends and real brackets."""
    angles = np.linspace(-math.pi, 0, 13)
    def point(e, radius, angle):
        return np.array((e, n + radius * math.cos(angle), height + radius * math.sin(angle)))
    for radius, inside in ((2.6, False), (2.32, True)):
        for a, b in zip(angles, angles[1:]):
            normal = np.array((0, math.cos((a+b)/2), math.sin((a+b)/2))) * (-1 if inside else 1)
            L.card(m, "lt_drain_iron", [point(e0, radius, a), point(e1, radius, a),
                point(e1, radius, b), point(e0, radius, b)], normal)
    for e, sign in ((e0, -1), (e1, 1)):
        for a, b in zip(angles, angles[1:]):
            L.card(m, "lt_drain_edge", [point(e, 2.6, a), point(e, 2.6, b),
                point(e, 2.32, b), point(e, 2.32, a)], (sign, 0, 0))
        L.card(m, "lt_drain_iron", [point(e, 2.32, a) for a in angles], (sign, 0, 0))
    for side in (-1, 1):
        L.bar(m, (e0, n+side*2.5, height), (e1, n+side*2.5, height), .28, "lt_drain_edge", sides=6)
    for e in np.arange(e0+24, e1-12, 72):
        for a, b in zip(angles, angles[1:]):
            L.card(m, "lt_drain_edge", [point(e-.5, 2.82, a), point(e+.5, 2.82, a),
                point(e+.5, 2.82, b), point(e-.5, 2.82, b)], (0, math.cos((a+b)/2), math.sin((a+b)/2)))


def build(L):
    m = K.Model()
    for s in (-1, 1):
        # The canal's tidal courses now share one plane, with no raised cap.
        # Locate pipes on solid piers, away from doors and window openings.
        for n in (-378, 205, 724, 1126):
            drainpipe(m, L, s*240, n, 942, (-s, 0, 0), bottom=-94)
        for n in (-372, 207, 727, 1126):
            drainpipe(m, L, s*1000, n, 942, (s, 0, 0))
        for e in (370, 870):
            drainpipe(m, L, s*e, -400, 936, (0, -1, 0))
        for bounds, eaves in ((L.QUAY_SHED, 276), (L.YARD_SHED, 236)):
            e0, e1, n0, n1 = bounds
            left, right = sorted((s*e0, s*e1))
            for n, direction in ((n0, -1), (n1, 1)):
                gutter(m, L, left-.5, right+.5, n+direction*2.8, eaves-.5)
                for e in (e0+14, e1-16):
                    drainpipe(m, L, s*e, n, eaves, (0, direction, 0))
        # Raised anchor plates and bolt ends give long facades construction detail.
        for n in (-245, 140, 530, 920):
            for z in (334, 634):
                e = s*237.8
                L.bar(m, (e, n, z-7), (e, n, z+7), 1.1, "lt_drain_iron")
                L.bar(m, (e, n-7, z), (e, n+7, z), 1.1, "lt_drain_iron")
                L.bar(m, (e+s, n, z), (e-s*2, n, z), 2.2, "lt_drain_edge", sides=6)
        for e in (390, 770, 1160, 1420, 1880, 2110):
            grate(m, s*e, -1540)
        for n in (-870, -505, -170, 180, 540, 920):
            grate(m, s*1030, n, 16, 26)
        # Fine rope coils beside bollards; no route or cover silhouette changes.
        for e in (690, 1350, 2010):
            centre = np.array([s*(e+18), -1560, 1.0])
            for turn in range(3):
                L.torus(m, centre+(0, 0, turn*.6), (1, 0, 0), (0, 1, 0), 7+turn*1.3, .55,
                        "lt_rope_detail", segments=26, sides=5)
        # Low irregular stones along the wall foot; they sit below ankle height.
        rng = np.random.default_rng(1352 + s)
        for _ in range(95):
            n = rng.uniform(-1510, 1120)
            e = s*rng.uniform(194, 231)
            z = float(L.mud_z(e, n))
            radius = rng.uniform(1.2, 3.4)
            if BANKS.landing_clear(n, radius):
                BANKS.cobble(m, e, n, z, radius, radius*.5, L.keyed(e, n, "wall cobble"), terrain=L.mud_z)
    L.INTERIOR.add_fixtures(m, L)
    import lowtide_perimeter
    m.extend(lowtide_perimeter.build(L))
    import lowtide_shed_details
    m.extend(lowtide_shed_details.build(L))
    assert not m.boxes and not m.hulls
    L.configure(m)
    return configure(m)


def apply_scene(scene, L):
    objects = {o.get("Name"): o for o in scene["GameObjects"]}
    def component(name, kind):
        return next(c for c in objects[name]["Components"] if c["__type"] == kind)
    sun = component("Sun", "Sandbox.DirectionalLight")
    sun.update(LightColor="1.45,1.26,1.02,1", SkyColor="0.42,0.48,0.58,1",
               ShadowHardness=.35, ContactShadows=True)
    fog = component("Fog", "Sandbox.GradientFog")
    fog.update(Color="0.42,0.49,0.57,0.55", StartDistance=2200, EndDistance=34000, FalloffExponent=1.3)
    component("Look", "Sandbox.AmbientOcclusion").update(Intensity=.8, Radius=28, ThinCompensation=1.5)
    component("Look", "Sandbox.ColorGrading").update(ColorTempK=6400, BlendFactor=.22)
    component("Look", "Sandbox.Vignette").update(Intensity=.10)
    component("Look", "Sandbox.Tonemapping").update(MinimumExposure=2.0, MaximumExposure=3.0, Rate=1.3)
    children = objects["Lowtide"]["Children"]
    index = next((i for i, o in enumerate(children) if o.get("Name") == "Harbour Details"), len(children))
    children[:] = [o for o in children if o.get("Name") != "Harbour Details"]
    children.insert(index, L.model_object("Harbour Details", "world/lowtide_finish", MODEL, False, True))
    L.WATER.apply_scene(scene, L)
    # Outdoor metal and damp paving previously had only sky reflections.
    probes = objects["Reflection Probes"]["Children"]
    names = {p["Name"] for p in probes}
    for s, side in ((-1, "West"), (1, "East")):
        lo, hi = sorted((s*245, s*2210))
        name = f"{side} Quay"
        if f"Probe {name}" not in names:
            probes.append(L.probe_object(name, (s*1120, -1360, 90), (lo, hi, -1610, -1020, -30, 450)))
    for obj in probes:
        probe = next(c for c in obj["Components"] if c["__type"] == "Sandbox.EnvmapProbe")
        # A 512-inch update radius left much of each probe's own box without a
        # captured cubemap when viewed from the opposite quay or canal mouth.
        probe.update(MaxDistance=4096, Mode="Realtime", Resolution="Medium", ZFar=6000)
    import lowtide_lighting
    lowtide_lighting.apply_scene(scene)
    import lowtide_static
    lowtide_static.apply_scene(scene)


def remap_stone():
    for path in (K.ASSETS / "models/maps/lowtide").glob("*.vmdl"):
        source = path.read_text()
        updated = source.replace('to = "materials/buildings/ashlar_grey.vmat"',
                                 f'to = "{RESOURCE}/lt_quay_stone.vmat"')
        if updated != source:
            K.write_text(path, updated)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--silt-source", type=Path)
    args = parser.parse_args()
    import lowtide_map as L
    if args.silt_source:
        bake_silt(args.silt_source)
    write_materials()
    L.MARINE.write_materials()
    L.MASONRY.write_materials()
    L.FRAMES.write_materials()
    L.ROOFS.write_materials()
    L.INTERIOR.write_materials()
    L.WATER.write_materials()
    model = build(L)
    count = K.write_model(L.OUT_DIR, L.RESOURCE_DIR, MODEL, model)
    remap_stone()
    scene = json.loads(L.SCENE_FILE.read_text())
    apply_scene(scene, L)
    K.write_text(L.SCENE_FILE, json.dumps(scene, indent=2) + "\n", newline=None)
    print(f"Lowtide finish: {count} render triangles, no new collision")


if __name__ == "__main__":
    main()
