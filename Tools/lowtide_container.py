"""ImageGen finishes and physical corrugated sheets for Lowtide containers.

rtk proxy python Tools/lowtide_container.py --textures --patch-models

Only the four Lowtide containers are replaced in the current dressing meshes.
The shared Railhead prop, corner fittings, door hardware and collision stay intact.
Generated originals live in Tools; the native textures use a 2048-pixel bake grid.
"""
import argparse
from collections import Counter
import hashlib
import io
import json
import shutil
import uuid

import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter

import map_kit as K
import railhead_props as P

RESOURCE = "materials/lowtide/containers"
OUT = K.ASSETS / RESOURCE
COLOURS = ("blue", "red", "grey")
TILE = 48.0
RIB_PITCH = 12.0
WALL_DEPTH = 1.25
ROOF_DEPTH = .625
REPORT = K.ROOT / "output/lowtide/containers"
# Compatibility with the earlier red-only material pass.
PAINT = "rw_container_red"
MATERIAL = f"{RESOURCE}/lt_container_red.vmat"
COLOUR = OUT / "lt_container_red_color.png"


def write_bytes(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists() or path.read_bytes() != data:
        temp = path.with_name(path.name + ".writing")
        temp.write_bytes(data)
        temp.replace(path)


def meta(path):
    sidecar = path.with_suffix(path.suffix + ".meta")
    if not sidecar.exists():
        key = "hc1/lowtide/container/" + path.relative_to(K.ASSETS).as_posix()
        K.write_text(sidecar, json.dumps({"guid": str(uuid.uuid5(uuid.NAMESPACE_URL, key))}, indent=2) + "\n")


def save_image(path, data):
    buffer = io.BytesIO()
    Image.fromarray(data).save(buffer, format="PNG", optimize=True)
    write_bytes(path, buffer.getvalue())
    meta(path)


def write_materials():
    report = {}
    for colour in COLOURS:
        source = K.ROOT / f"Tools/lowtide_container_{colour}_source.png"
        original = Image.open(source).convert("RGB")
        sample = original.resize((2048, 2048), Image.Resampling.LANCZOS)
        rgb = np.asarray(sample, dtype=np.float32) / 255.0
        lum = rgb @ np.array((.2126, .7152, .0722), dtype=np.float32)
        maximum = rgb.max(axis=-1) + .01
        if colour == "blue":
            paint = np.clip(((rgb[..., 2] - rgb[..., 0]) / maximum - .10) / .25, 0, 1)
        elif colour == "red":
            paint = np.clip(((rgb[..., 0] - rgb[..., 1]) / maximum - .15) / .30, 0, 1)
        else:
            paint = 1 - np.clip((.52 - lum) / .27, 0, 1)
        chip = 1 - paint
        rust = np.clip((rgb[..., 0] - rgb[..., 1] - .055) / .12, 0, 1) * chip
        fine = gaussian_filter(lum, .65, mode="wrap") - gaussian_filter(lum, 4, mode="wrap")
        height = .004 * fine - .005 * gaussian_filter(chip, .7, mode="wrap")
        scale = sample.width / TILE
        dx = (np.roll(height, -1, 1) - np.roll(height, 1, 1)) * .5 * scale
        dy = (np.roll(height, -1, 0) - np.roll(height, 1, 0)) * .5 * scale
        # OpenGL tangent normals. The corrugations now come from the mesh:
        # the texture only contributes shallow chips and paint grain.
        for suffix, strength in (("normal", 1.0), ("frame_normal", .55)):
            normal = np.stack((-dx * strength, dy * strength, np.ones_like(lum)), axis=-1)
            normal /= np.linalg.norm(normal, axis=-1, keepdims=True)
            save_image(OUT / f"lt_container_{colour}_{suffix}.png",
                       np.rint((normal * .5 + .5) * 255).clip(0, 255).astype(np.uint8))
        rough = np.clip(.64 + .15 * chip + .05 * rust + .08 * fine, .58, .88)
        metal = .72 * chip * (1 - rust)
        save_image(OUT / f"lt_container_{colour}_color.png", np.asarray(sample))
        save_image(OUT / f"lt_container_{colour}_roughness.png", np.rint(rough * 255).astype(np.uint8))
        save_image(OUT / f"lt_container_{colour}_metalness.png", np.rint(metal * 255).astype(np.uint8))
        for frame in (False, True):
            name = f"lt_container_{colour}" + ("_frame" if frame else "")
            normal_suffix = "frame_normal" if frame else "normal"
            K.write_text(OUT / f"{name}.vmat", f'''// Tools/lowtide_container.py: built-in ImageGen, {"smooth frame" if frame else "corrugated sheets"}
"Layer0"
{{
    shader "shaders/complex.shader"
    F_SPECULAR "1"
    F_METALNESS_TEXTURE "1"
    g_flRoughnessScaleFactor "{.90 if frame else 1.0}"
    g_flMetalness "0"
    TextureColor "{RESOURCE}/lt_container_{colour}_color.png"
    TextureNormal "{RESOURCE}/lt_container_{colour}_{normal_suffix}.png"
    TextureRoughness "{RESOURCE}/lt_container_{colour}_roughness.png"
    TextureMetalness "{RESOURCE}/lt_container_{colour}_metalness.png"
    TextureAmbientOcclusion "materials/default/default_ao.tga"
    g_vColorTint "[1.0 1.0 1.0 1.0]"
    g_flModelTintAmount "1.0"
}}
''')
            meta(OUT / f"{name}.vmat")
        report[colour] = {
            "source": source.relative_to(K.ROOT).as_posix(),
            "source_dimensions": original.size,
            "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
            "native_dimensions": sample.size,
            "tile_inches": TILE,
            "normal_convention": "OpenGL, micro paint relief only; ribs are physical geometry",
            "roughness_range": [float(rough.min()), float(rough.max())],
            "metalness_range": [float(metal.min()), float(metal.max())],
        }
    REPORT.mkdir(parents=True, exist_ok=True)
    K.write_text(REPORT / "surface.json", json.dumps(report, indent=2) + "\n")


def configure(model):
    for colour in COLOURS:
        for paint in (f"rw_container_{colour}", f"lt_container_{colour}", f"lt_container_{colour}_frame"):
            if paint in model.polygons:
                name = f"lt_container_{colour}" if paint.startswith("rw_") else paint
                model.material_overrides[paint] = f"{RESOURCE}/{name}.vmat"
                model.tile_overrides[paint] = TILE


def sheet(model, paint, points, normal, frame, shift):
    """Fold a rectangular painted sheet inward; preserve its outer footprint."""
    points = np.asarray(points, float)
    normal = K.normalise(normal)
    along = frame.x if abs(normal[2]) > .9 else np.array((0., 0., 1.))
    across = np.cross(along, normal)
    centre = points.mean(axis=0)
    us, vs = (points - centre) @ across, (points - centre) @ along
    u0, u1, v0, v1 = us.min(), us.max(), vs.min(), vs.max()
    depth = ROOF_DEPTH if abs(normal[2]) > .9 else WALL_DEPTH
    # Crest / slope / valley / slope, 12-inch pitch. Both panel ends meet
    # the original plane. No ribs are stamped on the rails or corner posts.
    ribs = max(1, int(round((u1 - u0) / RIB_PITCH)))
    pitch = (u1 - u0) / ribs
    knots = [(u0 + (i + t) * pitch, h * depth)
             for i in range(ribs) for t, h in ((0., 0.), (.30, 0.), (.50, -1.), (.80, -1.))]
    knots.append((u1, 0.))
    for (a, ha), (b, hb) in zip(knots, knots[1:]):
        pts = [centre + across * u + along * v + normal * h
               for u, v, h in ((a, v0, ha), (b, v0, hb), (b, v1, hb), (a, v1, ha))]
        uv = [[(u - u0) / TILE + shift[0], (v - v0) / TILE + shift[1]]
              for u, v in ((a, v0), (b, v0), (b, v1), (a, v1))]
        model.polygon(paint, pts, uv=uv)


def build(model, e, n, z0, size="20", axis="n", paint="rw_container_blue",
          doors_open=False, high_cube=False, door_end=+1):
    """Use Railhead's checked prop, replacing only its painted sheets and rails."""
    if paint not in {f"rw_container_{colour}" for colour in COLOURS}:
        return P.container(model, e, n, z0, size, axis, paint, doors_open, high_cube, door_end)
    source = K.Model()
    P.container(source, e, n, z0, size, axis, paint, doors_open, high_cube, door_end)
    colour = paint.removeprefix("rw_container_")
    panel, rail = f"lt_container_{colour}", f"lt_container_{colour}_frame"
    frame = P.Frame((e, n, z0), (door_end, 0) if axis == "e" else (0, door_end))
    items = source.polygons.pop(paint)
    shift = ((abs(e) * .0031) % 1, (abs(n) * .0043) % 1)
    for index, (points, normal) in enumerate(items):
        extents = np.sort(np.ptp(np.array(points), axis=0))
        if extents[-2] >= 80:
            sheet(source, panel, points, normal, frame, shift)
        else:
            # Rails retain their original flat faces and world-scale sampling.
            world_normal = K.to_world(normal)
            uv = [K.face_uv(K.to_world(point), world_normal, rail, shift, TILE) for point in points]
            source.polygon(rail, points, normal, uv=uv,
                           normals=source.polygon_normals.get((paint, index)))
    source.polygon_uvs = {key: value for key, value in source.polygon_uvs.items() if key[0] != paint}
    source.polygon_normals = {key: value for key, value in source.polygon_normals.items() if key[0] != paint}
    configure(source)
    return model.extend(source)


def layouts():
    """Capture the current map's container placements without rebuilding its props."""
    import lowtide_map as LT
    saved = {name: getattr(LT, name) for name in ("use", "sacks", "crates", "quay_crane", "skip_bin", "tree")}
    records = []
    def record(name, model, *args, **kwargs):
        if name == "container":
            records.append((args, kwargs))
    try:
        LT.use = record
        for name in saved:
            if name != "use":
                setattr(LT, name, lambda *args, **kwargs: None)
        out = {}
        for side, sign in (("east", 1), ("west", -1)):
            records = []
            LT.dress_side(sign)
            out[f"lowtide_dress_{side}"] = records
        return out
    finally:
        for name, value in saved.items():
            setattr(LT, name, value)


def parse_obj(text):
    """Only collect geometry for container groups; retain all index counts."""
    counts = Counter()
    positions = []
    groups = {}
    paint = None
    target = lambda name: name is not None and name.startswith(("rw_container_", "lt_container_"))
    for line in text.splitlines():
        fields = line.split()
        if not fields:
            continue
        if fields[0] in ("v", "vt", "vn"):
            counts[fields[0]] += 1
            if fields[0] == "v":
                positions.append(tuple(float(c) for c in fields[1:]))
        elif fields[0] == "usemtl":
            paint = fields[1]
        elif fields[0] == "f" and target(paint):
            triangles = groups.setdefault(paint, Counter())
            vertices = tuple(positions[int(field.split("/")[0]) - 1] for field in fields[1:])
            triangles[vertices] += 1
    return counts, groups


def painted_model(records, old=False):
    whole = K.Model()
    for args, kwargs in records:
        (P.container if old else build)(whole, *args, **kwargs)
    out = K.Model()
    for paint, items in whole.polygons.items():
        if paint.startswith(("rw_container_", "lt_container_")):
            for i, (points, normal) in enumerate(items):
                out.polygon(paint, points, normal, uv=whole.polygon_uvs.get((paint, i)),
                            normals=whole.polygon_normals.get((paint, i)))
    configure(out)
    return out


def patch_models():
    """Replace just the container face groups in the latest map OBJs."""
    report = {}
    for name, records in layouts().items():
        assert len(records) == 2, (name, records)
        generated = REPORT / "generated" / f"{name}.obj"
        generated.parent.mkdir(parents=True, exist_ok=True)
        current = painted_model(records)
        K.write_obj(generated, current, name)
        replacement = generated.read_text()
        _, expected = parse_obj(replacement)
        original_small = generated.with_name(name + "_original.obj")
        K.write_obj(original_small, painted_model(records, old=True), name)
        _, expected_old = parse_obj(original_small.read_text())
        path = K.ASSETS / f"models/maps/lowtide/{name}.obj"
        original = path.read_bytes()
        text = original.decode()
        counts, actual = parse_obj(text)
        if actual == expected:
            print(f"{name}: container geometry already current")
            continue
        assert actual == expected_old, f"{name}: container faces changed outside this pass; preserve them for review"
        # Capture each current file immediately before editing it.
        for suffix in (".obj", ".mtl", ".vmdl"):
            source = path.with_suffix(suffix)
            backup = REPORT / "current-before" / source.relative_to(K.ROOT)
            backup.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, backup)
        new_vertices = [line for line in replacement.splitlines() if line.startswith(("v ", "vt ", "vn "))]
        new_faces = []
        for line in replacement.splitlines():
            if line.startswith("usemtl "):
                new_faces.append(line)
            elif line.startswith("f "):
                fields = []
                for vertex in line.split()[1:]:
                    vi, ti, ni = (int(value) for value in vertex.split("/"))
                    fields.append(f"{vi + counts['v']}/{ti + counts['vt']}/{ni + counts['vn']}")
                new_faces.append("f " + " ".join(fields))
        output = []
        skipping, inserted = False, False
        for line in text.splitlines():
            if line.startswith("usemtl "):
                if not inserted:
                    output.extend(new_vertices)
                    inserted = True
                paint = line.split()[1]
                skipping = paint.startswith(("rw_container_", "lt_container_"))
            if not skipping:
                output.append(line)
        output.extend(new_faces)
        updated = ("\n".join(output) + "\n").encode()
        # Never overwrite an external edit that arrived while parsing the mesh.
        assert path.read_bytes() == original, f"{name}: mesh changed during preparation"
        write_bytes(path, updated)
        mtl = path.with_suffix(".mtl")
        text = mtl.read_text()
        for paint in sorted(current.polygons):
            if f"newmtl {paint}\n" not in text:
                text += f"newmtl {paint}\nKd 1 1 1\nd 1\n"
        K.write_text(mtl, text)
        vmdl = path.with_suffix(".vmdl")
        text = vmdl.read_text()
        anchor = next(line for line in text.splitlines() if 'from = "rw_container_' in line)
        prefix = anchor[:len(anchor) - len(anchor.lstrip())]
        for paint in sorted(current.polygons):
            if f'from = "{paint}.vmat"' not in text:
                remap = f'{prefix}{{ from = "{paint}.vmat" to = "{RESOURCE}/{paint}.vmat" }},'
                text = text.replace(anchor, remap + "\n" + anchor)
        K.write_text(vmdl, text)
        report[name] = {
            "placements": [{"args": list(args), "kwargs": kwargs} for args, kwargs in records],
            "removed_triangles": sum(sum(group.values()) for group in actual.values()),
            "added_triangles": sum(sum(group.values()) for group in expected.values()),
            "rib_pitch_inches": RIB_PITCH, "wall_depth_inches": WALL_DEPTH,
            "roof_depth_inches": ROOF_DEPTH, "collision": "original model collision retained",
        }
        print(f"{name}: two containers updated; {report[name]['removed_triangles']} triangles replaced with "
              f"{report[name]['added_triangles']}; original hardware and collision retained")
    if report:
        K.write_text(REPORT / "mesh.json", json.dumps(report, indent=2) + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--textures", action="store_true")
    parser.add_argument("--patch-models", action="store_true")
    args = parser.parse_args()
    if args.textures:
        write_materials()
        print("Blue, red and grey ImageGen materials baked on a 2048-pixel grid")
    if args.patch_models:
        patch_models()


if __name__ == "__main__":
    main()
