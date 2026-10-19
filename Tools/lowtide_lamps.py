"""Smooth, detailed street lamps for Lowtide, replacing its shared box lights.

    rtk proxy python Tools/lowtide_lamps.py

Patch only lamp render triangles in the existing dressing models. Preserve all
other geometry, material remaps, scene placements and collision data.
"""
import json
import math
import re
import uuid

import numpy as np

import map_kit as K
import railhead_props as P

RESOURCE = "materials/lowtide/lamps"
DIRECTORY = K.ASSETS / RESOURCE
REPORT = K.ROOT / "output/lowtide/lamps-pass"
COAT, TRIM, LENS = "lt_lamp_coat", "lt_lamp_trim", "lt_lamp_lens"
SIDES = 48


def metadata(path):
    sidecar = path.with_name(path.name + ".meta")
    if not sidecar.exists():
        guid = uuid.uuid5(uuid.NAMESPACE_URL, "hc1/lowtide/lamp/" + path.relative_to(K.ASSETS).as_posix())
        K.write_text(sidecar, json.dumps({"guid": str(guid)}, indent=2) + "\n")


def write_materials():
    DIRECTORY.mkdir(parents=True, exist_ok=True)
    source = (K.ASSETS / "materials/railhead/rw_steel_dark.vmat").read_text()
    source = source.replace("// Tools/railhead_materials.py", "// Tools/lowtide_lamps.py: graphite-coated lamp casting")
    K.write_text(DIRECTORY / f"{COAT}.vmat", source)
    lens = (K.ASSETS / "materials/railhead/rw_lamp_cool.vmat").read_text()
    lens = lens.replace("// Tools/railhead_materials.py", "// Tools/lowtide_lamps.py: softly lit prismatic diffuser")
    lens = re.sub(r'g_flSelfIllumBrightness\s+"[^"]+"', 'g_flSelfIllumBrightness "1.7"', lens)
    lens = re.sub(r'g_vSelfIllumTint\s+"[^"]+"', 'g_vSelfIllumTint "[1.0 0.96 0.88 0.0]"', lens)
    K.write_text(DIRECTORY / f"{LENS}.vmat", lens)
    K.write_text(DIRECTORY / f"{TRIM}.vmat", '''// Tools/lowtide_lamps.py: recessed rubber seals and access-cover joints.
"Layer0"
{
    shader "shaders/complex.shader"
    F_SPECULAR "1"
    g_flMetalness "0.0"
    TextureColor "materials/default/default_color.tga"
    TextureNormal "materials/default/default_normal.tga"
    TextureRoughness "[0.8 0.8 0.8 0.0]"
    TextureAmbientOcclusion "materials/default/default_ao.tga"
    g_vColorTint "[0.045 0.050 0.048 1.0]"
    g_flModelTintAmount "1.0"
}
''')
    for paint in (COAT, TRIM, LENS):
        metadata(DIRECTORY / f"{paint}.vmat")


def configure(model):
    for paint in (COAT, TRIM, LENS):
        if paint in model.polygons:
            model.material_overrides[paint] = f"{RESOURCE}/{paint}.vmat"
            model.tile_overrides[paint] = 48.0
    if "rw_steel_grey" in model.polygons:
        model.material_overrides["rw_steel_grey"] = "materials/railhead/rw_steel_grey.vmat"
        model.tile_overrides["rw_steel_grey"] = 48.0


def smooth(model, paint, points, normals):
    points = [np.asarray(p, dtype=float) for p in points]
    normals = [K.normalise(n) for n in normals]
    face = np.cross(points[1] - points[0], points[2] - points[0])
    if len(points) == 4:
        face += np.cross(points[2] - points[0], points[3] - points[0])
    if np.linalg.norm(face) < 1e-9:
        return
    if np.dot(face, np.sum(normals, axis=0)) < 0:
        points = points[:1] + points[:0:-1]
        normals = normals[:1] + normals[:0:-1]
    model.polygon(paint, points, normals=normals)


def shell(model, frame, paint, rings, centre=(0, 0), caps=True, sides=SIDES):
    """Elliptical revolved shell, with analytical smooth normals in both directions."""
    angles = np.linspace(0, math.tau, sides + 1)
    points, normals = [], []
    for index, (a, b, z) in enumerate(rings):
        before, after = rings[max(0, index - 1)], rings[min(len(rings) - 1, index + 1)]
        da, db, dz = np.asarray(after) - np.asarray(before)
        row, normal_row = [], []
        for angle in angles:
            c, s = math.cos(angle), math.sin(angle)
            row.append(frame.p(centre[0] + a * c, centre[1] + b * s, z))
            local = K.normalise((b * c * dz, a * s * dz, -a * db * s * s - b * da * c * c))
            normal_row.append(local[0] * frame.x + local[1] * frame.y + local[2] * frame.z)
        points.append(row)
        normals.append(normal_row)
    for row in range(len(rings) - 1):
        for side in range(sides):
            smooth(model, paint,
                   [points[row][side], points[row][side + 1], points[row + 1][side + 1], points[row + 1][side]],
                   [normals[row][side], normals[row][side + 1], normals[row + 1][side + 1], normals[row + 1][side]])
    if caps:
        for row, direction in ((0, -frame.z), (-1, frame.z)):
            P.outward(model, paint, points[row][:-1], direction)


def round_outline(half_width, half_height, radius, steps=5):
    points = []
    for x, z, start in ((half_width - radius, half_height - radius, 0),
                        (-half_width + radius, half_height - radius, 90),
                        (-half_width + radius, -half_height + radius, 180),
                        (half_width - radius, -half_height + radius, 270)):
        for angle in np.linspace(start, start + 90, steps + 1):
            radians = math.radians(angle)
            points.append((x + radius * math.cos(radians), z + radius * math.sin(radians)))
    return points


def access_cover(model, frame):
    for paint, half_width, half_height, radius, y in ((TRIM, 1.32, 5.45, .48, 2.68),
                                                    (COAT, 1.14, 5.23, .40, 2.74)):
        outline = round_outline(half_width, half_height, radius)
        model.polygon(paint, [frame.p(x, y, 25 + z) for x, z in outline], normal=frame.y)
    for z in (20.6, 29.4):
        P.disc(model, "rw_steel_grey", frame.p(0, 2.78, z), frame.y, .16, sides=12)


def build(model, e, n, height, z0=0.0, along="n"):
    directions = {"n": (0, 1), "+n": (0, 1), "-n": (0, -1),
                  "e": (1, 0), "+e": (1, 0), "-e": (-1, 0)}
    if along not in directions:
        raise ValueError(f"Unknown street lamp facing: {along}")
    frame = P.Frame((e, n, z0), directions[along])
    # Chamfered anchor flange and cast pedestal, followed by the smooth tapered shaft.
    profile = [(3.55, .12), (3.55, .8), (3.40, 1.05), (2.98, 1.35), (2.98, 12.6),
               (2.88, 13.2), (2.72, 13.65), (2.70, 15.0), (2.67, 16.0),
               (1.48, height - 7), (1.48, height - .8)]
    shell(model, frame, COAT, [(r, r, z) for r, z in profile])
    for angle in (45, 135, 225, 315):
        t = math.radians(angle)
        centre = (3.25 * math.cos(t), 3.25 * math.sin(t))
        shell(model, frame, "rw_steel_grey", [(.24, .24, 1.0), (.27, .27, 1.08),
                                            (.27, .27, 1.40), (.22, .22, 1.48)], centre, sides=6)
    access_cover(model, frame)
    # Slip-fit mounting collar; its clamping screw and the hood's separate seam.
    shell(model, frame, COAT, [(1.53, 1.53, height - 5.6), (1.78, 1.78, height - 5.2),
                              (1.78, 1.78, height + .8), (1.62, 1.62, height + 1.1)], sides=32)
    P.disc(model, "rw_steel_grey", frame.p(0, 1.82, height - 3.3), frame.y, .26, sides=6)
    centre = (0, 13.0)
    shell(model, frame, TRIM, [(6.10, 14.10, height + .32), (6.32, 14.30, height + .45),
                              (6.32, 14.30, height + .72), (6.10, 14.10, height + .85)], centre)
    shell(model, frame, COAT, [(6.3, 14.3, height + .66), (6.6, 14.8, height + 1.1),
                              (6.7, 15.0, height + 2.0), (6.45, 14.7, height + 3.1),
                              (5.95, 14.1, height + 4.0), (4.65, 12.7, height + 4.75),
                              (2.25, 8.2, height + 5.25), (.12, 1.0, height + 5.35)], centre)
    # Domed opal/prismatic lens, recessed inside a narrow dark gasket.
    shell(model, frame, LENS, [(.15, .8, height - 1.15), (1.6, 5.8, height - 1.05),
                              (3.4, 8.8, height - .85), (4.5, 10.0, height - .50),
                              (5.0, 10.5, height - .10), (5.25, 10.8, height + .20),
                              (4.9, 10.3, height + .50)], centre)
    # Downward retaining screws sit outside the illuminated lens.
    for x in (-5.7, 5.7):
        P.disc(model, "rw_steel_grey", frame.p(x, centre[1], height + .25), -frame.z, .18, sides=12)
    model.collision_box((e - 3.6, n - 3.6, z0), (e + 3.6, n + 3.6, z0 + height), "metal")
    return e, n, z0 + height - 2.0


def placements(side):
    # The cross-street fixtures project into the road, and the northern
    # pavement fixtures face south away from the warehouse walls.
    return [(side * 1285, n, 190.0, 0.0, "-e" if side > 0 else "+e")
            for n in (-820.0, -100.0, 620.0)] + \
           [(side * e, 1425, 190.0, 5.0, "-n") for e in (900.0, 1700.0)]


def refresh_fragment(path, name, side):
    """Refresh our appended geometry only; leave the original model records intact."""
    fragment = REPORT / f"{name}-lamps.obj"
    lines = path.read_text().splitlines()
    old = fragment.read_text().splitlines()
    old_geometry = [line for line in old if line.startswith(("v ", "vt ", "vn "))]
    first_face = next(i for i, line in enumerate(lines) if line.startswith("usemtl "))
    start = first_face - len(old_geometry)
    if lines[start:first_face] != old_geometry:
        print(f"{name}: lamps already built by the full map generator")
        return
    first_added = next(i for i, line in enumerate(lines) if line == f"usemtl {COAT}")
    base = lines[:start] + lines[first_face:first_added]
    model = K.Model()
    for pose in placements(side):
        build(model, *pose)
    configure(model)
    K.write_obj(fragment, model, name)
    fresh = fragment.read_text().splitlines()
    geometry = [line for line in fresh if line.startswith(("v ", "vt ", "vn "))]
    counts = [sum(line.startswith(prefix) for line in base) for prefix in ("v ", "vt ", "vn ")]
    faces = []
    for line in fresh:
        if line.startswith("usemtl "):
            faces.append(line)
        elif line.startswith("f "):
            refs = ["/".join(str(value + offset) for value, offset in zip(map(int, ref.split("/")), counts))
                    for ref in line.split()[1:]]
            faces.append("f " + " ".join(refs))
    position = next(i for i, line in enumerate(base) if line.startswith("usemtl "))
    output = base[:position] + geometry + base[position:] + faces
    K.write_text(path, "\n".join(output) + "\n")
    print(f"{name}: refreshed only the lamp fragment")


def patch_models():
    reports = []
    for side, name in ((1, "lowtide_dress_east"), (-1, "lowtide_dress_west")):
        path = K.ASSETS / "models/maps/lowtide" / f"{name}.obj"
        original = path.read_bytes()
        if f"usemtl {COAT}".encode() in original:
            refresh_fragment(path, name, side)
            continue
        lines = original.decode().splitlines()
        vertices = np.array([list(map(float, line.split()[1:4])) for line in lines if line.startswith("v ")])
        poses = placements(side)
        removed, material = set(), None
        for index, line in enumerate(lines):
            if line.startswith("usemtl "):
                material = line.split()[1]
            if not line.startswith("f ") or material not in (P.DARK, "rw_lamp_cool"):
                continue
            points = vertices[[int(ref.split("/")[0]) - 1 for ref in line.split()[1:]]]
            for e, n, height, z0, _along in poses:
                if (np.all(np.abs(points[:, 0] + e) <= 5.01) and np.all(np.abs(points[:, 2] - n) <= 14.01)
                    and points[:, 1].min() >= z0 - .01 and points[:, 1].max() <= z0 + height + 3.91):
                    removed.add(index)
                    break
        legacy, replacement = K.Model(), K.Model()
        for e, n, height, z0, along in poses:
            P.lamp_post(legacy, e, n, height, z0)
            build(replacement, e, n, height, z0, along)
        expected = sum(len(points) - 2 for faces in legacy.polygons.values() for points, _ in faces)
        if len(removed) != expected:
            raise ValueError(f"{name}: expected {expected} legacy lamp triangles, found {len(removed)}")
        configure(replacement)
        replacement.material_overrides["rw_steel_grey"] = "materials/railhead/rw_steel_grey.vmat"
        fragment = REPORT / f"{name}-lamps.obj"
        K.write_obj(fragment, replacement, name)
        additions = fragment.read_text().splitlines()
        counts = {prefix: sum(line.startswith(prefix) for line in lines) for prefix in ("v ", "vt ", "vn ")}
        geometry = [line for line in additions if line.startswith(("v ", "vt ", "vn "))]
        faces = []
        for line in additions:
            if line.startswith("usemtl "):
                faces.append(line)
            elif line.startswith("f "):
                refs = []
                for item in line.split()[1:]:
                    v, uv, normal = map(int, item.split("/"))
                    refs.append(f"{v + counts['v ']}/{uv + counts['vt ']}/{normal + counts['vn ']}")
                faces.append("f " + " ".join(refs))
        first_face = next(index for index, line in enumerate(lines) if line.startswith("usemtl "))
        output = lines[:first_face] + geometry + [line for index, line in enumerate(lines[first_face:], first_face)
                                                if index not in removed] + faces
        # The surviving original triangles retain their exact indices and all original vertices.
        surviving = [line for index, line in enumerate(lines) if line.startswith("f ") and index not in removed]
        assert [line for line in output if line.startswith("f ")][:len(surviving)] == surviving
        mtl_path, vmdl_path = path.with_suffix(".mtl"), path.with_suffix(".vmdl")
        mtl = mtl_path.read_text()
        for paint in replacement.polygons:
            if f"newmtl {paint}\n" not in mtl:
                mtl += f"newmtl {paint}\nKd 1 1 1\nd 1\n"
        vmdl = vmdl_path.read_bytes()
        marker = re.search(rb'(remaps\s*=\s*\[\s*)(?=\{)', vmdl)
        if not marker:
            raise ValueError(f"{name}: material remap list is missing")
        new_remaps = []
        for paint in replacement.polygons:
            if f'from = "{paint}.vmat"'.encode() not in vmdl:
                target = replacement.material_overrides[paint]
                new_remaps.append(f'{{ from = "{paint}.vmat" to = "{target}" }},\n\t\t\t\t\t\t\t')
        inserted = "".join(new_remaps).encode()
        updated_vmdl = vmdl[:marker.end()] + inserted + vmdl[marker.end():]
        assert updated_vmdl.replace(inserted, b"", 1) == vmdl
        K.write_text(path, "\n".join(output) + "\n")
        K.write_text(mtl_path, mtl)
        vmdl_path.write_bytes(updated_vmdl)
        reports.append({"model": name, "lamps": len(poses), "old_triangles_removed": len(removed),
                        "new_triangles": sum(line.startswith("f ") for line in faces),
                        "circular_segments": SIDES, "other_triangles_and_collision_preserved": True})
        print(f"{name}: replaced {len(poses)} lamps, {len(removed)} old triangles; smooth 48-sided shafts and cast hoods")
    if reports:
        K.write_text(REPORT / "model-remap.json", json.dumps(reports, indent=2) + "\n")


def main():
    REPORT.mkdir(parents=True, exist_ok=True)
    write_materials()
    patch_models()


if __name__ == "__main__":
    main()
