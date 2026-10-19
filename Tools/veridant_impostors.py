"""Image impostors for Veridant's distant headland and anchored boats.

The generated PNGs retain their original RGBA pixels. UV rectangles select the
boats directly from the atlas; no cropped copies or separate alpha maps are needed.
Run --stage DIR to build only the two backdrop models and their new materials for
native editor import. The normal map generator calls replace() after constructing
the old scenery, preserving the mainland's existing random placements and UVs.
"""
import argparse
import json
import math
from pathlib import Path
import shutil

import numpy as np

import map_kit as K
from riverdale_parts import UP, unit, v

PAINTS = ("vr_bay_headland", "vr_bay_boats")
BOAT_PAINTS = {
    "vr_beacon_red", "vr_hull_dark", "vr_mast", "vr_sail", "vr_timber",
    "vr_white", "vr_yacht", "vr_yacht_glass", "vr_yacht_lit", "vr_yacht_trim",
}
REFERENCE = v(-1650, 200, 100)
SEA_Z = -420.0
# Pixel rectangles (left, top, right, bottom), measured on the selected PNGs.
HEADLAND_RECT = (12, 110, 2160, 637)
HEADLAND_SIZE = (2172, 724)
BOAT_SIZE = (1774, 887)
YACHT_RECT = (255, 36, 1528, 426)
SAIL_RECTS = ((155, 430, 636, 871), (1128, 430, 1612, 871))


def _retain_mainland(model, land, boats=False):
    """Retain original polygon data outside the image-covered headland/bay."""
    result = K.Model()
    result.material_overrides = dict(model.material_overrides)
    result.tile_overrides = dict(model.tile_overrides)
    result.grain_paints = set(model.grain_paints)
    for paint, polygons in model.polygons.items():
        if paint in PAINTS:
            continue
        if boats and paint in BOAT_PAINTS:
            continue
        centres = np.array([np.mean(points, axis=0) for points, _ in polygons])
        if not len(centres):
            continue
        e, n = centres[:, 0], centres[:, 1]
        d_main, (dist, _, half_width), _ = land.parts(e, n)
        replaced = (dist < half_width * 1.12) & (d_main < 120)
        for index, ((points, normal), remove) in enumerate(zip(polygons, replaced)):
            if remove:
                continue
            result.polygon(paint, points, normal,
                           uv=model.polygon_uvs.get((paint, index)),
                           normals=model.polygon_normals.get((paint, index)))
    # These are visual-only models. Accidentally carrying physics into a vista
    # would change gameplay and make compilation unnecessarily expensive.
    assert not model.boxes and not model.hulls and not model.props
    return result


def _uv(rect, size, s, t):
    x0, y0, x1, y1 = rect
    return ((x0 + (x1 - x0) * s) / size[0],
            1.0 - (y1 + (y0 - y1) * t) / size[1])


def headland_card(model):
    """A fixed, curved strip: stable when the player moves or turns their head."""
    count = 48
    radius = 16000.0
    height = 4350.0
    bottom = SEA_Z - 35.0
    columns = []
    for u in np.linspace(0, 1, count + 1):
        # Keep the castle near the old summit's bearing (195 degrees), the
        # peninsula's root to the south, and its town/tip to the north-west.
        bearing = np.interp(u, [0, .32, 1], [254, 195, 156])
        angle = math.radians(bearing)
        columns.append(v(radius * math.cos(angle), radius * math.sin(angle), bottom))
    for j in range(count):
        a, b = columns[j:j + 2]
        points = [a, b, b + UP * height, a + UP * height]
        model.polygon(PAINTS[0], points, normal=unit(REFERENCE - (a + b) / 2),
                      uv=[_uv(HEADLAND_RECT, HEADLAND_SIZE, s, t)
                          for s, t in ((j/count, 0), ((j+1)/count, 0),
                                       ((j+1)/count, 1), (j/count, 1))])


def boat_card(model, at, width, rect, sink=4.0, height=None):
    """One fixed quad at the original anchorage; water occludes its lower edge."""
    centre = v(at[0], at[1], SEA_Z - sink)
    outward = unit((REFERENCE - centre) * v(1, 1, 0))
    right = unit(np.cross(UP, outward))
    x0, y0, x1, y1 = rect
    height = width * (y1 - y0) / (x1 - x0) if height is None else height
    left, right_point = centre - right * width/2, centre + right * width/2
    model.polygon(PAINTS[1], [left, right_point, right_point + UP*height, left + UP*height],
                  normal=outward, uv=[_uv(rect, BOAT_SIZE, s, t)
                                     for s, t in ((0, 0), (1, 0), (1, 1), (0, 1))])


def replace(far, props, land):
    before = far.triangle_count() + props.triangle_count()
    # Each original sailboat has two double-sided triangular sails (four
    # polygons). The first vertex is its mast; the low aft vertex determines
    # its exact length and heading, even after triangle winding is reversed.
    anchorages = []
    sails = props.polygons.get("vr_sail", [])
    for index in range(0, len(sails), 4):
        points = sails[index][0]
        mast = points[0]
        aft = min(points[1:], key=lambda p: p[2])
        direction = unit((mast - aft) * v(1, 1, 0))
        length = np.linalg.norm((mast - aft)[:2]) / .42
        anchorages.append((mast - direction * length * .08, length))
    far = _retain_mainland(far, land)
    props = _retain_mainland(props, land, boats=True)
    headland_card(far)
    boat_card(props, (-9500, 5200), 3000, YACHT_RECT, sink=7)
    # Keep the authored anchorage and mast height, with one quad per sailboat.
    for k, (at, length) in enumerate(anchorages):
        boat_card(props, at, length, SAIL_RECTS[k % 2], height=length * 1.35)
    after = far.triangle_count() + props.triangle_count()
    print(f"image backdrop: {before:,} -> {after:,} triangles; 96 headland + 20 boat triangles")
    return far, props


def material_text(paint):
    texture = "headland" if paint == PAINTS[0] else "boats"
    return (f'// Tools/veridant_impostors.py\n"Layer0"\n{{\n'
            '    shader "shaders/hc1_veridant_impostor.shader"\n'
            '    F_ALPHA_TEST "1"\n'
            f'    TextureVista "materials/veridant/vista/{texture}.png"\n'
            '    g_flAlphaTestReference "0.55"\n'
            '    g_flVistaBrightness "1.0"\n}\n')


def write_materials(out):
    out.mkdir(parents=True, exist_ok=True)
    for paint in PAINTS:
        (out / f"{paint}.vmat").write_text(material_text(paint), encoding="utf-8")


def read_obj(path):
    """Read an existing map_kit mesh without rebuilding surrounding scenery."""
    model = K.Model()
    points, coords, normals = [], [], []
    paint = None
    for line in Path(path).open(encoding="utf-8"):
        if line.startswith("v "):
            x, z, n = map(float, line.split()[1:])
            points.append(v(-x, n, z))
        elif line.startswith("vt "):
            coords.append(tuple(map(float, line.split()[1:])))
        elif line.startswith("vn "):
            x, z, n = map(float, line.split()[1:])
            normals.append(v(-x, n, z))
        elif line.startswith("usemtl "):
            paint = line.split()[1]
        elif line.startswith("f "):
            indices = [tuple(int(n)-1 for n in part.split("/")) for part in line.split()[1:]]
            face_points = [points[a] for a, _, _ in indices]
            face_normals = [normals[c] for _, _, c in indices]
            model.polygon(paint, face_points, normal=np.mean(face_normals, axis=0),
                          uv=[coords[b] for _, b, _ in indices], normals=face_normals)
    return model


def stage(destination, source=None):
    import veridant_backdrop as BD
    import veridant_map as VM
    destination = Path(destination).resolve()
    assets = destination / "Assets"
    if source:
        source = Path(source)
        far = read_obj(source / "veridant_backdrop.obj")
        props = read_obj(source / "veridant_backdrop_props.obj")
        far, props = replace(far, props, BD.Land())
    else:
        far, _, _, props = BD.build()
    counts = {}
    for name, model in (("veridant_backdrop", far), ("veridant_backdrop_props", props)):
        VM.configure(model)
        counts[name] = K.write_model(assets / "models/maps/veridant", "models/maps/veridant", name, model)
    write_materials(assets / "materials/veridant")
    for image in ("headland.png", "boats.png"):
        target = assets / "materials/veridant/vista" / image
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(K.ROOT / "Assets/materials/veridant/vista" / image, target)
    shader = assets / "shaders/hc1_veridant_impostor.shader"
    shader.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(K.ROOT / "Sources/Veridant/impostors/hc1_veridant_impostor.shader.txt", shader)
    manifest = {"triangles": counts, "impostor_triangles": 116,
                "collision": False, "casts_shadows": False,
                "files": [str(p.relative_to(destination)).replace("\\", "/")
                          for p in sorted(assets.rglob("*")) if p.is_file()]}
    (destination / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", required=True)
    parser.add_argument("--source", help="existing backdrop OBJ directory; preserves all retained geometry/UVs")
    args = parser.parse_args()
    stage(args.stage, args.source)
