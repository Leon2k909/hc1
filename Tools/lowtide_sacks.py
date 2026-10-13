"""Photographic jute and rounded, filled cargo sacks for Lowtide.

python Tools/lowtide_sacks.py --textures --patch-models

Only replace the sacks' visual faces in the three existing map meshes. Other props,
the map scene and the authored collision in the VMDLs remain intact. The map
generator uses sack() so future rebuilds retain the same finish.
"""
import argparse
import hashlib
import io
import json
import math
import uuid
import zlib
from pathlib import Path

import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter

import map_kit as K

TILE = 12.0  # one photographic tile is 30 cm of cloth, not the old 64-inch canvas tile
SOURCE = Path(__file__).with_name("lowtide_sack_jute_source.png")
TEXTURES = K.ASSETS / "materials/lowtide/sacks"
MATERIAL = K.ASSETS / "materials/lowtide/lt_jute.vmat"
OUTPUT = K.ROOT / "output/lowtide/sacks-pass"
MODEL_NAMES = ("lowtide_dress_east", "lowtide_dress_west", "lowtide_fleet")
PATCH_MARKER = "# Lowtide filled sacks v1, Tools/lowtide_sacks.py"


def write_bytes(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists() or path.read_bytes() != data:
        temp = path.with_name(path.name + ".writing")
        temp.write_bytes(data)
        temp.replace(path)


def meta(path):
    sidecar = path.with_suffix(path.suffix + ".meta")
    if not sidecar.exists():
        key = "hc1/lowtide/sacks/" + str(path.relative_to(K.ASSETS)).replace("\\", "/")
        K.write_text(sidecar, json.dumps({"guid": str(uuid.uuid5(uuid.NAMESPACE_URL, key))}, indent=2) + "\n")


def write_materials():
    TEXTURES.mkdir(parents=True, exist_ok=True)
    colour = Image.open(SOURCE).convert("RGB").resize((1024, 1024), Image.Resampling.LANCZOS)
    rgb = np.asarray(colour, dtype=float) / 255
    lum = rgb @ np.array((.2126, .7152, .0722))
    # Remove staining from the height field: fibre relief responds to light, while
    # the image's broad mottling stays in the albedo. Normals use DirectX's Y sign.
    height = gaussian_filter(lum, .65, mode="wrap") - gaussian_filter(lum, 12, mode="wrap")
    dx = (np.roll(height, -1, 1) - np.roll(height, 1, 1)) * 3.2
    dy = (np.roll(height, -1, 0) - np.roll(height, 1, 0)) * 3.2
    normals = np.stack((-dx, -dy, np.ones_like(height)), axis=-1)
    normals /= np.linalg.norm(normals, axis=-1, keepdims=True)
    normal = Image.fromarray(np.rint((normals * .5 + .5) * 255).clip(0, 255).astype(np.uint8))
    rough = Image.fromarray(np.rint((.91 + .07 * (1 - lum)) * 255).clip(0, 255).astype(np.uint8))
    for suffix, image in (("color", colour), ("normal", normal), ("roughness", rough)):
        path = TEXTURES / f"lt_jute_{suffix}.png"
        buffer = io.BytesIO()
        image.save(buffer, format="PNG", optimize=True)
        write_bytes(path, buffer.getvalue())
        meta(path)
    K.write_text(MATERIAL, '''// Tools/lowtide_sacks.py: built-in ImageGen photographic jute
"Layer0"
{
    shader "shaders/complex.shader"
    F_SPECULAR "1"
    g_flRoughnessScaleFactor "1"
    g_flMetalness "0.0"
    TextureColor "materials/lowtide/sacks/lt_jute_color.png"
    TextureNormal "materials/lowtide/sacks/lt_jute_normal.png"
    TextureRoughness "materials/lowtide/sacks/lt_jute_roughness.png"
    TextureAmbientOcclusion "materials/default/default_ao.tga"
    g_vColorTint "[1.0 1.0 1.0 1.0]"
    g_flModelTintAmount "1.0"
}
''')


def sack(model, lo, size):
    """A compressed filled sack, 120 triangles with smooth normals; stays inside its old cover bounds."""
    lo, size = np.asarray(lo, float), np.asarray(size, float)
    hx, hy = size[0] / 2, size[1] / 2
    radius = min(hx, hy) * .25
    outline = []
    for cx, cy, start in ((hx-radius, hy-radius, 0), (-hx+radius, hy-radius, 90),
                          (-hx+radius, -hy+radius, 180), (hx-radius, -hy+radius, 270)):
        for angle in (start, start+45, start+90):
            a = math.radians(angle)
            outline.append(np.array((cx+radius*math.cos(a), cy+radius*math.sin(a))))
    perimeter = [0.0]
    for i, point in enumerate(outline):
        perimeter.append(perimeter[-1] + np.linalg.norm(outline[(i+1) % len(outline)]-point))
    seed = zlib.crc32(np.round(lo, 3).tobytes())
    phase = (seed % 1009) * .023
    shift = ((seed & 255) / 255, ((seed >> 8) & 255) / 255)
    centre = lo + size / 2
    rings = ((0, .79), (.13, .94), (.50, 1), (.83, .95), (.975, .74))
    points = []
    for height, scale in rings:
        for i, p in enumerate(outline):
            crease = .14 * math.sin(i * 2.1 + phase) * math.sin(math.pi * height)
            points.append(np.array((centre[0]+p[0]*scale, centre[1]+p[1]*scale, lo[2]+size[2]*height+crease)))
    bottom, top = len(points), len(points)+1
    points.extend((np.array((centre[0], centre[1], lo[2])), np.array((centre[0], centre[1], lo[2]+size[2]))))
    count, faces = len(outline), []
    for ring in range(len(rings)-1):
        for i in range(count):
            j = (i+1) % count
            ids = (ring*count+i, ring*count+j, (ring+1)*count+j, (ring+1)*count+i)
            uv = ((perimeter[i]/TILE+shift[0], rings[ring][0]*size[2]/TILE+shift[1]),
                  (perimeter[i+1]/TILE+shift[0], rings[ring][0]*size[2]/TILE+shift[1]),
                  (perimeter[i+1]/TILE+shift[0], rings[ring+1][0]*size[2]/TILE+shift[1]),
                  (perimeter[i]/TILE+shift[0], rings[ring+1][0]*size[2]/TILE+shift[1]))
            faces.append((ids, uv))
    for i in range(count):
        j = (i+1) % count
        for ids in ((bottom, j, i), (top, (len(rings)-1)*count+i, (len(rings)-1)*count+j)):
            faces.append((ids, tuple(((points[k][0]-lo[0])/TILE+shift[0], (points[k][1]-lo[1])/TILE+shift[1]) for k in ids)))
    normals = np.zeros((len(points), 3))
    for ids, _ in faces:
        p = [points[k] for k in ids]
        normal = np.cross(p[1]-p[0], p[2]-p[0])
        for k in ids:
            normals[k] += normal
    normals /= np.linalg.norm(normals, axis=1, keepdims=True)
    for ids, uv in faces:
        model.polygon("lt_jute", [points[k] for k in ids], uv=uv, normals=[normals[k] for k in ids])
    model.tile_overrides["lt_jute"] = TILE


def patch_model(name):
    """Replace only the old paired box faces; preserve all other mesh faces and collision resources."""
    path = K.ASSETS / f"models/maps/lowtide/{name}.obj"
    lines = path.read_text(encoding="utf-8").splitlines()
    if PATCH_MARKER in lines:
        return {"model": name, "already_current": True}
    vertices = [tuple(map(float, line.split()[1:4])) for line in lines if line.startswith("v ")]
    counts = (len(vertices), sum(s.startswith("vt ") for s in lines), sum(s.startswith("vn ") for s in lines))
    paint, original = None, []
    for line in lines:
        if line.startswith("usemtl "):
            paint = line[7:]
        if line.startswith("f ") and paint == "lt_jute":
            original.append(line)
    if original and len(original) % 120 == 0:
        ids = {int(v.split("/")[0])-1 for line in original[:120] for v in line.split()[1:]}
        existing = np.array([vertices[i] for i in ids])
        extent = existing.max(axis=0)-existing.min(axis=0)
        if len(np.unique(existing, axis=0)) >= 50 and np.allclose(sorted(extent), (11, 21, 33), atol=.01):
            # A full map rebuild renumbers faces and doesn't need the patch marker.
            return {"model": name, "already_current": True}
    if len(original) % 24:
        raise ValueError(f"{name}: already rounded or unexpected sack topology; no patch applied")
    replacement = K.Model()
    for offset in range(0, len(original), 24):
        ids = {int(v.split("/")[0])-1 for line in original[offset:offset+24] for v in line.split()[1:]}
        points = np.array([(-vertices[i][0], vertices[i][2], vertices[i][1]) for i in ids])
        lo, hi = points.min(axis=0), points.max(axis=0)
        size = hi-lo
        assert np.allclose(sorted(size[:2]), (21, 33), atol=.01) and abs(size[2]-11)<.01, (name, lo, size)
        sack(replacement, lo, size)
    OUTPUT.mkdir(parents=True, exist_ok=True)
    addition = OUTPUT / f"{name}_sack_faces.obj"
    triangles = K.write_obj(addition, replacement, name)
    assert triangles == len(original)//24 * 120
    added = addition.read_text().splitlines()
    records = [PATCH_MARKER] + [line for line in lines if not line.startswith(("f ", "usemtl "))]
    records += [line for line in added if line.startswith(("v ", "vt ", "vn "))]
    faces, paint = [], None
    for line in lines:
        if line.startswith("usemtl "):
            paint = line[7:]
            if paint != "lt_jute":
                faces.append(line)
        elif line.startswith("f ") and paint != "lt_jute":
            faces.append(line)
    faces.append("usemtl lt_jute")
    for line in added:
        if line.startswith("f "):
            indices = ["/".join(str(int(v)+counts[i]) for i, v in enumerate(token.split("/"))) for token in line.split()[1:]]
            faces.append("f " + " ".join(indices))
    K.write_text(path, "\n".join(records+faces)+"\n")
    return {"model": name, "sacks": len(original)//24, "old_sack_triangles": len(original), "new_sack_triangles": triangles}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--textures", action="store_true")
    parser.add_argument("--patch-models", action="store_true")
    args = parser.parse_args()
    if args.textures:
        write_materials()
        print("Photographic jute: 1024x1024 albedo, fibre normal and cloth roughness")
    if args.patch_models:
        models = [K.ASSETS/f"models/maps/lowtide/{name}.vmdl" for name in MODEL_NAMES]
        collision = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in models}
        report = [patch_model(name) for name in MODEL_NAMES]
        assert all(hashlib.sha256(p.read_bytes()).hexdigest()==collision[str(p)] for p in models), "Collision VMDLs must be unchanged"
        K.write_text(OUTPUT/"geometry.json", json.dumps(report, indent=2)+"\n")
        print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
