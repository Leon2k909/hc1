"""Detailed, illuminated cast-iron bridge lanterns for Lowtide.

    rtk proxy python Tools/lowtide_lanterns.py

Replace only the four legacy lanterns in Fleet's render mesh and add their
point lights to the saved scene. Other render triangles and physics stay intact.
The map generator calls the same geometry and light definitions.
"""
import json
import math
import re
import uuid

import numpy as np

import map_kit as K
import railhead_props as P
import lowtide_lamps as L

RESOURCE = "materials/lowtide/lanterns"
DIRECTORY = K.ASSETS / RESOURCE
REPORT = K.ROOT / "output/lowtide/lanterns-pass"
COAT, GLASS, BULB, BRASS = ("lt_lantern_iron", "lt_lantern_glass", "lt_lantern_bulb", "lt_lantern_brass")
SIDES = 48
LIGHT_HEIGHT = 130.0
LIGHT_COLOR = "3.4,2.30,1.25,1"
LIGHT_RADIUS = 330.0
# Move the bridge-end assemblies inwards to keep the lantern roof clear of
# the adjoining brick warehouses. The posts and matching lights follow.
BRIDGE_END_INSET = 8.0


def placements():
    return [(e, n, 58.0) for e in (-240.0, 240.0)
            for n in (1159.0 + BRIDGE_END_INSET, 1441.0 - BRIDGE_END_INSET)]


def lights():
    return [(f"Bridge Lantern {'West' if e < 0 else 'East'} {'South' if n < 1300 else 'North'}",
             (e, n, z + LIGHT_HEIGHT), LIGHT_COLOR, LIGHT_RADIUS, True) for e, n, z in placements()]


def write_materials():
    DIRECTORY.mkdir(parents=True, exist_ok=True)
    coat = (K.ASSETS / "materials/buildings/iron_green.vmat").read_text()
    coat = coat.replace("// Tools/building_textures.py", "// Tools/lowtide_lanterns.py: aged green enamel over cast iron")
    coat = coat.replace('g_flRoughnessScaleFactor "1"', 'g_flRoughnessScaleFactor "0.68"')
    coat = coat.replace('g_vColorTint "[1.0 1.0 1.0 1.0]"', 'g_vColorTint "[0.62 0.78 0.66 1.0]"')
    K.write_text(DIRECTORY / f"{COAT}.vmat", coat)
    glass = (K.ASSETS / "materials/railhead/rw_glass.vmat").read_text()
    glass = glass.replace("// Tools/railhead_materials.py", "// Tools/lowtide_lanterns.py: clear, slightly aged lantern glazing")
    glass = glass.replace('AlbedoAbsorption "0.15"', 'AlbedoAbsorption "0.045"')
    glass = glass.replace('g_flBlurAmount "0.02"', 'g_flBlurAmount "0.005"')
    glass = glass.replace('[0.920000 0.950000 0.940000 0.000000]', '[0.96 0.97 0.94 0.0]')
    K.write_text(DIRECTORY / f"{GLASS}.vmat", glass)
    import railhead_materials as RM
    brass = RM.painted_vmat(BRASS, (132, 110, 66), .68, .35)
    K.write_text(DIRECTORY / f"{BRASS}.vmat", brass.replace("Tools/railhead_materials.py", "Tools/lowtide_lanterns.py"))
    bulb = RM.painted_vmat(BULB, (255, 236, 193), 0.0, .22)
    bulb = bulb.replace('    F_SPECULAR "1"', '''    F_SPECULAR "1"
    F_SELF_ILLUM "1"
    TextureSelfIllumMask "[1.0 1.0 1.0 0.0]"
    g_flSelfIllumBrightness "4.0"
    g_flSelfIllumAlbedoFactor "1.0"
    g_vSelfIllumTint "[1.0 0.86 0.64 0.0]"''')
    K.write_text(DIRECTORY / f"{BULB}.vmat", bulb.replace("Tools/railhead_materials.py", "Tools/lowtide_lanterns.py"))
    for paint in (COAT, GLASS, BULB, BRASS):
        path = DIRECTORY / f"{paint}.vmat.meta"
        if not path.exists():
            guid = uuid.uuid5(uuid.NAMESPACE_URL, "hc1/lowtide/lantern/" + paint)
            K.write_text(path, json.dumps({"guid": str(guid)}, indent=2) + "\n")


def configure(model):
    for paint in (COAT, GLASS, BULB, BRASS):
        if paint in model.polygons:
            model.material_overrides[paint] = f"{RESOURCE}/{paint}.vmat"
            model.tile_overrides[paint] = 48.0


def square_ring(model, frame, paint, inner, outer, z0, z1, bevel=.15):
    """A mitred, hollow casting; the underside is open for the light to escape."""
    rings = [(outer - bevel, z0), (outer, z0 + bevel), (outer, z1 - bevel), (outer - bevel, z1),
             (inner + bevel, z1), (inner, z1 - bevel), (inner, z0 + bevel), (inner + bevel, z0)]
    for (r0, h0), (r1, h1) in zip(rings, rings[1:] + rings[:1]):
        for k in range(4):
            angle = k * math.pi / 2
            out = np.array((math.cos(angle), math.sin(angle), 0))
            tangent = np.array((-out[1], out[0], 0))
            pts = [frame.p(*(out * r0 + tangent * -r0 + (0, 0, h0))),
                   frame.p(*(out * r0 + tangent * r0 + (0, 0, h0))),
                   frame.p(*(out * r1 + tangent * r1 + (0, 0, h1))),
                   frame.p(*(out * r1 + tangent * -r1 + (0, 0, h1)))]
            direction = (h1 - h0) * out + np.array((0, 0, r0 - r1))
            direction = direction[0] * frame.x + direction[1] * frame.y + direction[2] * frame.z
            P.outward(model, paint, pts, direction)


def fluted_shaft(model, frame):
    """Fine rounded flutes, with smooth radial normals and a tapered upper shaft."""
    profile = [(2.75, 16.0), (2.75, 18.0), (2.42, 104.0), (2.27, 109.0), (2.24, 114.5)]
    rows, normals = [], []
    for index, (radius, z) in enumerate(profile):
        before, after = profile[max(0, index - 1)], profile[min(len(profile) - 1, index + 1)]
        slope = (after[0] - before[0]) / (after[1] - before[1])
        row, nrow = [], []
        for t in np.linspace(0, math.tau, SIDES + 1):
            flute = .065 * math.cos(12 * t)
            r, dr = radius + flute, -.78 * math.sin(12 * t)
            c, s = math.cos(t), math.sin(t)
            row.append(frame.p(r * c, r * s, z))
            nrm = K.normalise((r * c + dr * s, r * s - dr * c, -r * slope))
            nrow.append(frame.x * nrm[0] + frame.y * nrm[1] + frame.z * nrm[2])
        rows.append(row)
        normals.append(nrow)
    for k in range(len(rows) - 1):
        for j in range(SIDES):
            L.smooth(model, COAT, [rows[k][j], rows[k][j + 1], rows[k + 1][j + 1], rows[k + 1][j]],
                     [normals[k][j], normals[k][j + 1], normals[k + 1][j + 1], normals[k + 1][j]])


def build(model, e, n, z0):
    frame = P.Frame((e, n, z0), (0, 1))
    def turned(paint, profile, sides=SIDES):
        L.shell(model, frame, paint, [(r, r, z) for r, z in profile], sides=sides)

    turned(COAT, [(5.3, .08), (5.5, .5), (5.5, 1.5), (5.0, 2.0), (4.55, 2.4),
                  (4.55, 8.0), (4.25, 9.0), (3.65, 10.1), (3.25, 11.5),
                  (2.95, 13.5), (2.95, 15.5), (2.75, 16.4)])
    for t in (math.pi / 4, math.pi * 3 / 4, math.pi * 5 / 4, math.pi * 7 / 4):
        centre = (4.85 * math.cos(t), 4.85 * math.sin(t))
        L.shell(model, frame, BRASS, [(.29, .29, 1.85), (.34, .34, 2.0), (.34, .34, 2.36),
                                    (.27, .27, 2.46)], centre=centre, sides=6)
    fluted_shaft(model, frame)
    turned(COAT, [(2.3, 111.5), (2.85, 112), (3.1, 113), (3.1, 114.7), (2.8, 115.3),
                  (2.8, 116.5), (3.3, 117.2), (4.0, 118.5), (4.0, 120.0), (3.2, 121.0), (3.0, 123.3)])
    square_ring(model, frame, COAT, 5.0, 6.5, 123.0, 125.0)
    # Four open support arms connect the lantern's rim to the pole's cast saddle.
    for k in range(4):
        t = k * math.pi / 2
        P.rod(model, frame.p(2.6 * math.cos(t), 2.6 * math.sin(t), 121.6),
              frame.p(5.4 * math.cos(t), 5.4 * math.sin(t), 123.4), .42, COAT, sides=12)
    bottom, top, zb, zt = 5.65, 8.15, 125.1, 149.4
    for k in range(4):
        angle = k * math.pi / 2
        out = np.array((math.cos(angle), math.sin(angle), 0))
        tangent = np.array((-out[1], out[0], 0))
        pts = [out * bottom + tangent * -bottom + (0, 0, zb),
               out * bottom + tangent * bottom + (0, 0, zb),
               out * top + tangent * top + (0, 0, zt),
               out * top + tangent * -top + (0, 0, zt)]
        normal = out + np.array((0, 0, -(top - bottom) / (zt - zb)))
        P.outward(model, GLASS, [frame.p(*p) for p in pts],
                  normal[0] * frame.x + normal[1] * frame.y + normal[2] * frame.z)
        # Rounded cast corner stiles conceal the glazing joins, including the inside edges.
        P.rod(model, frame.p(*(out * (bottom + .18) + tangent * (bottom + .18) + (0, 0, 124.3))),
              frame.p(*(out * (top + .20) + tangent * (top + .20) + (0, 0, 150.4))),
              .53, COAT, sides=16, caps=(True, True))
        # Glazing retainers and hinge pins sit on the upper rim, not across the glass.
        for sign in (-1, 1):
            p = frame.p(*(out * 8.45 + tangent * (sign * 6.5) + (0, 0, 150.2)))
            P.disc(model, BRASS, p, out[0] * frame.x + out[1] * frame.y, .18, sides=12)
    square_ring(model, frame, COAT, 7.65, 8.95, 149.2, 151.0)
    square_ring(model, frame, COAT, 7.5, 10.1, 151.0, 152.3, bevel=.25)
    # Suspended porcelain socket and a small warm frosted bulb, visible through the glass.
    turned(BRASS, [(1.0, 141.0), (1.25, 141.35), (1.25, 144.0), (1.5, 144.4), (1.5, 145.5), (1.0, 146.0), (1.0, 151.2)], sides=32)
    turned(BULB, [(.30, 131.5), (1.1, 131.8), (1.75, 132.9), (2.1, 134.7),
                  (2.1, 136.6), (1.75, 138.2), (1.2, 139.7), (1.0, 141.0)], sides=32)
    # Four bevel-edged hipped roof panels; the vented crown has its own rounded cap.
    roof = [(9.8, 152.2), (10.15, 152.65), (9.95, 153.2), (3.25, 164.0), (2.55, 164.8)]
    for (r0, h0), (r1, h1) in zip(roof, roof[1:]):
        for k in range(4):
            t = k * math.pi / 2
            out, side = np.array((math.cos(t), math.sin(t), 0)), np.array((-math.sin(t), math.cos(t), 0))
            pts = [out * r0 + side * -r0 + (0, 0, h0), out * r0 + side * r0 + (0, 0, h0),
                   out * r1 + side * r1 + (0, 0, h1), out * r1 + side * -r1 + (0, 0, h1)]
            normal = out * (h1 - h0) + (0, 0, r0 - r1)
            P.outward(model, COAT, [frame.p(*p) for p in pts],
                      frame.x * normal[0] + frame.y * normal[1] + frame.z * normal[2])
    turned(COAT, [(2.85, 164.5), (2.85, 165.3), (2.1, 165.7)])
    for k in range(12):
        t = k * math.tau / 12
        P.rod(model, frame.p(2.1 * math.cos(t), 2.1 * math.sin(t), 165.3),
              frame.p(2.1 * math.cos(t), 2.1 * math.sin(t), 168.0), .18, COAT, sides=8)
    turned(COAT, [(2.7, 167.5), (2.9, 168.0), (2.7, 168.6), (2.15, 169.3),
                  (1.4, 169.85), (.55, 170.1), (.65, 170.5), (.85, 171.3), (.75, 172.0), (.30, 173.0), (.08, 174.5)])
    return e, n, z0 + LIGHT_HEIGHT


def patch_model():
    path = K.ASSETS / "models/maps/lowtide/lowtide_fleet.obj"
    original = path.read_text()
    if f"usemtl {COAT}" in original:
        raise ValueError("Lanterns already installed; regenerate Fleet with lowtide_map.py to change their mesh")
    lines = original.splitlines()
    vertices = np.array([list(map(float, line.split()[1:4])) for line in lines if line.startswith("v ")])
    removed, material = set(), None
    for index, line in enumerate(lines):
        if line.startswith("usemtl "):
            material = line.split()[1]
        if not line.startswith("f ") or material not in ("iron_green", "rw_opal_glass", "iron_black"):
            continue
        points = vertices[[int(ref.split("/")[0]) - 1 for ref in line.split()[1:]]]
        for e, n, z in placements():
            # Exclude the bridge's post cap, whose top face is exactly z=58.
            if (np.all(np.abs(points[:, 0] + e) <= 10.05) and np.all(np.abs(points[:, 2] - n) <= 10.05)
                and points[:, 1].min() >= z - .01 and points[:, 1].max() > z + .01
                and points[:, 1].max() <= z + 175.01):
                removed.add(index)
                break
    # Each legacy lantern: three octagonal cylinders, two boxes, panes, four rods, pyramid.
    if len(removed) != 4 * 146:
        raise ValueError(f"Expected 584 legacy lantern triangles, found {len(removed)}")
    model = K.Model()
    for pose in placements():
        build(model, *pose)
    configure(model)
    fragment = REPORT / "lowtide_fleet-lanterns.obj"
    K.write_obj(fragment, model, "lowtide_fleet")
    additions = fragment.read_text().splitlines()
    counts = [sum(line.startswith(prefix) for line in lines) for prefix in ("v ", "vt ", "vn ")]
    geometry = [line for line in additions if line.startswith(("v ", "vt ", "vn "))]
    faces = []
    for line in additions:
        if line.startswith("usemtl "):
            faces.append(line)
        elif line.startswith("f "):
            refs = ["/".join(str(value + offset) for value, offset in zip(map(int, ref.split("/")), counts))
                    for ref in line.split()[1:]]
            faces.append("f " + " ".join(refs))
    first_face = next(i for i, line in enumerate(lines) if line.startswith("usemtl "))
    output = lines[:first_face] + geometry + [line for i, line in enumerate(lines[first_face:], first_face) if i not in removed] + faces
    surviving = [line for i, line in enumerate(lines) if line.startswith("f ") and i not in removed]
    assert [line for line in output if line.startswith("f ")][:len(surviving)] == surviving
    mtl_path, vmdl_path = path.with_suffix(".mtl"), path.with_suffix(".vmdl")
    mtl, vmdl = mtl_path.read_text(), vmdl_path.read_bytes()
    marker = re.search(rb'(remaps\s*=\s*\[\s*)(?=\{)', vmdl)
    if not marker:
        raise ValueError("Fleet's material remap list is missing")
    remaps = ""
    for paint in model.polygons:
        if f"newmtl {paint}\n" not in mtl:
            mtl += f"newmtl {paint}\nKd 1 1 1\nd 1\n"
        if f'from = "{paint}.vmat"'.encode() not in vmdl:
            remaps += f'{{ from = "{paint}.vmat" to = "{model.material_overrides[paint]}" }},\n\t\t\t\t\t\t\t'
    added = remaps.encode()
    updated = vmdl[:marker.end()] + added + vmdl[marker.end():]
    assert updated.replace(added, b"", 1) == vmdl
    if path.read_text() != original or vmdl_path.read_bytes() != vmdl:
        raise ValueError("Fleet changed during patch preparation; rerun to preserve those edits")
    K.write_text(mtl_path, mtl)
    K.write_text(vmdl_path, updated.decode(), newline="")
    K.write_text(path, "\n".join(output) + "\n")
    report = {"lanterns": 4, "legacy_triangles_removed": len(removed), "new_triangles": sum(x.startswith("f ") for x in faces),
              "other_triangles_and_collision_preserved": True, "shaft_segments": SIDES,
              "point_lights": [{"name": name, "position_plan": pos, "color": color, "radius": radius, "shadows": shadows}
                               for name, pos, color, radius, shadows in lights()]}
    K.write_text(REPORT / "model-remap.json", json.dumps(report, indent=2) + "\n")
    print(f"Fleet: replaced 4 bridge lanterns; {len(removed)} original triangles removed")


def ensure_remaps():
    """Repair an interrupted patch without touching existing geometry or physics."""
    path = K.ASSETS / "models/maps/lowtide/lowtide_fleet.vmdl"
    original = path.read_text()
    marker = re.search(r'(remaps\s*=\s*\[\s*)(?=\{)', original)
    if not marker:
        raise ValueError("Fleet's material remap list is missing")
    added = "".join(f'{{ from = "{paint}.vmat" to = "{RESOURCE}/{paint}.vmat" }},\n\t\t\t\t\t\t\t'
                    for paint in (COAT, GLASS, BULB, BRASS) if f'from = "{paint}.vmat"' not in original)
    if added:
        K.write_text(path, original[:marker.end()] + added + original[marker.end():])


def patch_lights():
    import lowtide_map as M
    path = K.ASSETS / "scenes/maps/Lowtide/lowtide.scene"
    original = path.read_text()
    root = json.loads(original)
    group = next(o for o in root["GameObjects"] if o.get("Name") == "Lights")
    for name, position, color, radius, shadows in lights():
        key = f"light/{name}"
        obj = K.game_object(M.ids, name, key, K.to_world(position), tags="light_point,light", components=[
            K.component(M.ids, "Sandbox.PointLight", key + "/light", Attenuation=1, FogMode="Enabled", FogStrength=.15,
                        LightColor=color, Radius=radius, Shadows=shadows)])
        existing = next((i for i, child in enumerate(group["Children"]) if child.get("Name") == name), None)
        if existing is None:
            group["Children"].append(obj)
        else:
            group["Children"][existing] = obj
    if path.read_text() != original:
        raise ValueError("Scene changed during light patch preparation; rerun to preserve those edits")
    K.write_text(path, json.dumps(root, indent=2) + "\n")
    print("Scene: four enabled warm point lights, with shadows and 330-inch falloff")


def main():
    REPORT.mkdir(parents=True, exist_ok=True)
    write_materials()
    if f"usemtl {COAT}" not in (K.ASSETS / "models/maps/lowtide/lowtide_fleet.obj").read_text():
        patch_model()
    ensure_remaps()
    patch_lights()


if __name__ == "__main__":
    main()
