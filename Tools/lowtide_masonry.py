"""Scoped Lowtide masonry finish: generated granite, profiled sills and arch bricks.

This writes only a new visual detail mesh, its materials and its scene entry.
The original models, their collision and all gameplay objects are retained.
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

NAME = "lowtide_masonry"
DIRECTORY = K.ASSETS / "materials/lowtide/masonry"
RESOURCE = "materials/lowtide/masonry"
SOURCE = K.ROOT / "Sources/Lowtide/visual-target/granite-source.png"


def bake(source):
    SOURCE.parent.mkdir(parents=True, exist_ok=True)
    if Path(source).resolve() != SOURCE.resolve():
        shutil.copy2(source, SOURCE)
    rgb = np.asarray(Image.open(SOURCE).convert("RGB").resize((2048, 2048), Image.Resampling.LANCZOS), float) / 255
    lum = rgb @ np.array([.2126, .7152, .0722])
    detail = lum - ndimage.gaussian_filter(lum, 6, mode="wrap")
    # Geometry-scale joint relief, separate from variations in stone colour.
    # Coordinates trace the four courses in the unchanged generated source.
    y, x = np.mgrid[:2048, :2048] / 2048
    distance = np.minimum(y % .25, .25 - y % .25)
    for row, joints in enumerate(((.031, .409, .776), (.251, .710), (.032, .441, .786), (.281, .654))):
        for joint in joints:
            d = np.abs(x - joint)
            distance = np.minimum(distance, np.where((y >= row / 4) & (y < (row + 1) / 4), d, 1))
    groove = 1 - np.clip(distance / .0065, 0, 1)
    height = -.003 * ndimage.gaussian_filter(groove, 2, mode="wrap") + detail * .0012
    dx = (np.roll(height, -1, 1) - np.roll(height, 1, 1)) * 512
    dy = (np.roll(height, -1, 0) - np.roll(height, 1, 0)) * 512
    normal = np.stack([-dx, dy, np.ones_like(height)], -1)
    normal /= np.linalg.norm(normal, axis=-1, keepdims=True)
    DIRECTORY.mkdir(parents=True, exist_ok=True)
    for suffix, data in {"color": rgb, "normal": normal * .5 + .5,
                         "rough": np.clip(.76 + detail * .18 + groove * .10, .63, .91)}.items():
        path = DIRECTORY / f"granite_{suffix}.png"
        Image.fromarray(np.rint(data * 255).clip(0, 255).astype(np.uint8)).save(path)
        metadata(path)


def granite_material_text(scale, biofilm):
    from lowtide_weathering import material_inputs
    from lowtide_shed_weathering import material_inputs as shed_inputs
    return f'''// Tools/lowtide_masonry.py: generated granite with metre-scale weathering.
"Layer0"
{{
    shader "shaders/hc1_brick.shader"
    F_SPECULAR "1"
    TextureColor "{RESOURCE}/granite_color.png"
    TextureNormal "{RESOURCE}/granite_normal.png"
    TextureRoughness "{RESOURCE}/granite_rough.png"
    TextureAmbientOcclusion "materials/default/default_ao.tga"
    TextureMetalness "materials/default/default_black_mask.tga"
    g_vBrickScale "[{scale:.6f} {scale:.6f} 0 0]"
    g_flTintColor "[0.94 0.96 0.93]"
{material_inputs(biofilm)}{shed_inputs(.7)}
}}
'''


def write_materials():
    DIRECTORY.mkdir(parents=True, exist_ok=True)
    if not (DIRECTORY / "granite_color.png").exists():
        raise FileNotFoundError("Bake the generated granite before writing masonry materials")
    for path, scale in ((K.ASSETS / "materials/lowtide/finish/lt_quay_stone.vmat", 128 / 78.7402),
                        (DIRECTORY / "lt_granite_trim.vmat", 1)):
        K.write_text(path, granite_material_text(scale, 1.0 if path.stem == 'lt_quay_stone' else .9))
        metadata(path)
    K.write_text(DIRECTORY / "lt_arch_clay.vmat", '''// Individual radial bricks share the facade's clay scan.
"Layer0"
{
    shader "shaders/hc1_brick.shader"
    TextureColor "materials/lowtide/lt_brick_v2_color.png"
    TextureNormal "materials/lowtide/lt_brick_v2_normal.png"
    TextureRoughness "[0.52 0.52 0.52 0]"
    TextureAmbientOcclusion "materials/default/default_ao.tga"
    TextureMetalness "materials/default/default_black_mask.tga"
    g_vBrickScale "[1 1 0 0]"
    g_flTintColor "[0.67 0.60 0.55]"
}
''')
    metadata(DIRECTORY / "lt_arch_clay.vmat")


def configure(m):
    for paint in ("lt_granite_trim", "lt_arch_clay"):
        if paint in m.polygons:
            m.material_overrides[paint] = f"{RESOURCE}/{paint}.vmat"
            m.tile_overrides[paint] = 78.7402


def stone_uv(seed, width, height):
    # UV islands stay within a single granite block; thin sills cannot acquire
    # giant masonry joints from a wall texture. The source pixels are unchanged.
    rng = np.random.default_rng(seed)
    x, y = rng.uniform(.06, .09), rng.uniform(.035, .07)
    du, dv = min(width / 100, .28), min(height / 100, .14)
    return [(x, 1-y), (x + du, 1-y), (x + du, 1-y-dv), (x, 1-y-dv)]


def extrusion(m, L, wall, r0, r1, profile, seed):
    """Extrude a shaped stone section along a wall, with real bevel normals."""
    d, sign, _ = L.wall_out(wall)
    def point(r, dz):
        return wall.point(r, d + sign * dz[0], dz[1])
    centre = (point(r0, np.mean(profile, axis=0)) + point(r1, np.mean(profile, axis=0))) / 2
    for k, a in enumerate(profile):
        b = profile[(k + 1) % len(profile)]
        pts = [point(r0, a), point(r1, a), point(r1, b), point(r0, b)]
        L.card(m, "lt_granite_trim", pts, np.mean(pts, axis=0) - centre,
               uv=stone_uv(seed, r1-r0, float(np.linalg.norm(np.subtract(a, b)))))
    for r in (r0, r1):
        pts = [point(r, p) for p in profile]
        uv = [(0.20 + p[0] / 220, .89 - (p[1] - profile[0][1]) / 220) for p in profile]
        L.card(m, "lt_granite_trim", pts, np.mean(pts, axis=0) - centre, uv=uv)


def sill(m, L, wall, o):
    z = o.z0
    # The undercut is a small drip moulding; the top slopes away from the frame.
    profile = [(-1.1, z-4.4), (3.5, z-4.4), (4.0, z-3.8), (4.0, z-.55),
               (3.35, z+.15), (-1.1, z+.85)]
    extrusion(m, L, wall, o.r0-4.35, o.r1+4.35, profile, L.keyed(*wall.across, o.r0, z))


def arch(m, L, wall, o):
    if not o.arched:
        return
    d, sign, out = L.wall_out(wall)
    rc = (o.r0 + o.r1) / 2
    count = max(13, int(math.pi * (o.radius + 3.5) / 2.8))
    rng = np.random.default_rng(L.keyed(*wall.across, rc, o.z0))
    for k in range(count):
        a = math.pi * k / count + .006
        b = math.pi * (k + 1) / count - .006
        proud = rng.uniform(1.35, 1.75)
        def p(t, radius, depth):
            return wall.point(rc + math.cos(t) * radius, d + sign * depth,
                              o.spring + math.sin(t) * radius)
        points = [p(a, o.radius+.06, proud), p(b, o.radius+.06, proud),
                  p(b, o.radius+7.12, proud), p(a, o.radius+7.12, proud)]
        # Sample inside one clay brick and rotate its long axis around the arch.
        col = int(rng.integers(0, 5))
        u = .098 + col / 6
        uv = [(u, .992), (u, .966), (u+.14, .966), (u+.14, .992)]
        L.card(m, "lt_arch_clay", points, out, uv=uv)
        centre = np.mean(points, axis=0) - out * .3
        for j in range(4):
            face = [points[j], points[(j+1)%4], points[(j+1)%4]-out*(proud-.98), points[j]-out*(proud-.98)]
            L.card(m, "lt_arch_clay", face, np.mean(face, axis=0)-centre, uv=uv)


def build(L):
    east = K.Model()
    original = L.window
    records = []
    def collect(m, wall, o, style, pane=None, glass=None):
        records.append((wall, o))
    # Query the authoritative layout in memory without writing/rebuilding any
    # existing asset. The replacement is restored even if generation fails.
    try:
        L.window = collect
        L.half()
    finally:
        L.window = original
    for wall, opening in records:
        sill(east, L, wall, opening)
        d, _, _ = L.wall_out(wall)
        # Fine brick edges are reserved for the playable approaches and hero
        # canal facades; distant boundary blocks retain their original arches.
        hero = (wall.axis == "n" and abs(d-L.FLEET) < .1) or (wall.axis == "e" and abs(d+400) < .1)
        if hero or opening.z0 < 200:
            arch(east, L, wall, opening)
    wall = K.Wall("n", (L.QUAY_N, L.SPEICHER[2]), (L.FLEET, L.FLEET+22), (-10, 1), "-e")
    profile = [(-22.7, -8.4), (2.5, -8.4), (3.0, -7.8), (3.0, -.2), (2.15, .65), (-21.9, .65), (-22.7, -.15)]
    for a in np.arange(L.QUAY_N, L.SPEICHER[2], 43.0):
        extrusion(east, L, wall, a+.15, min(a+42.85, L.SPEICHER[2]), profile, L.keyed(a, "coping"))
    model = K.Model().extend(east).extend(east.mirrored())
    configure(model)
    assert not model.boxes and not model.hulls and not model.props
    return model


def apply_scene(scene, L):
    children = next(o for o in scene["GameObjects"] if o.get("Name") == "Lowtide")["Children"]
    index = next((i for i, o in enumerate(children) if o.get("Name") == "Masonry Details"), len(children))
    children[:] = [o for o in children if o.get("Name") != "Masonry Details"]
    children.insert(index, L.model_object("Masonry Details", "world/lowtide_masonry", NAME, False, True))
    import lowtide_static
    lowtide_static.apply_scene(scene)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path)
    args = parser.parse_args()
    import lowtide_map as L
    if args.source:
        bake(args.source)
    write_materials()
    count = K.write_model(L.OUT_DIR, L.RESOURCE_DIR, NAME, build(L))
    scene = json.loads(L.SCENE_FILE.read_text())
    apply_scene(scene, L)
    K.write_text(L.SCENE_FILE, json.dumps(scene, indent=2) + "\n", newline=None)
    print(f"Masonry pass: {count} visual triangles, no new collision")


if __name__ == "__main__":
    main()
