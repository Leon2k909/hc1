"""Build a small, reclaimed-plank Riverside supply crate as a separate review asset.

python build.py <project-root>
Engine X is the long side, Y the short side, Z up; origin is the bottom centre.
No existing map, material, model, generator or collision file is modified.
"""
from pathlib import Path
import ctypes
import json
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage as ndi

try:
    ctypes.windll.kernel32.SetPriorityClass(ctypes.windll.kernel32.GetCurrentProcess(), 0x4000)
except AttributeError:
    pass

ROOT = Path(sys.argv[1]).resolve()
MODEL = "models/props/riverside/crate_v2"
MAT = "materials/riverside/crate_v2"
OUT = ROOT / "Assets" / MODEL
TEX = ROOT / "Assets" / MAT
REPORT = ROOT / "output/asset-improvement-20261030/riverside-crate"
for p in (OUT, TEX, REPORT):
    p.mkdir(parents=True, exist_ok=True)
AW = AH = 2048
PPI = 30
SW, SH = 1008, 152
SLOTS = [(8 + (k % 2) * 1024, 8 + (k // 2) * 168) for k in range(24)]


def unit(x):
    x = np.asarray(x, float)
    return x / max(np.linalg.norm(x), 1e-10)


def smooth(a, b, x):
    t = np.clip((x - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)


def noise(shape, sigma, seed):
    a = ndi.gaussian_filter(np.random.default_rng(seed).normal(size=shape), sigma, mode="wrap")
    return a / (3 * a.std() + 1e-8)


def paint():
    """Individual plank crops from the project's existing CC0 scan, with object-specific wear.

    Crops avoid the photographed joints; those are actual gaps in the mesh. Normal XY is rotated
    with the scan, so its grain remains aligned to the board's tangent basis.
    """
    scan = ROOT / "Assets/materials/belltower/scans"
    maps = {name: Image.open(scan / ("brown_planks_03_" + suffix + "_4k.png")).convert(mode)
            for name, suffix, mode in (("color", "diffuse", "RGB"), ("normal", "nor_gl", "RGB"),
                                      ("rough", "rough", "L"), ("ao", "ao", "L"))}
    colour = np.full((AH, AW, 3), 0.3, np.float32)
    normal = np.zeros((AH, AW, 3), np.float32)
    normal[:, :, 2] = 1
    rough = np.full((AH, AW), .8, np.float32)
    ao = np.ones((AH, AW), np.float32)
    metal = np.zeros((AH, AW), np.float32)
    covered = np.zeros((AH, AW), bool)
    # Interiors of the seven photographed boards, with no baked black joint at their edges.
    crops = [(35, 440), (485, 945), (990, 1420), (1470, 1820), (1870, 2250), (2300, 2770), (2825, 3240), (3290, 3650), (3700, 4060)]
    yy, xx = np.mgrid[0:SH, 0:SW].astype(np.float32)
    for k, (x0, y0) in enumerate(SLOTS[:23]):
        r = np.random.default_rng(410 + k)
        left, right = crops[k % len(crops)]
        top = int(r.integers(50, 850))
        box = (left, top, right, top + 3000)
        crops_k = {key: np.asarray(img.crop(box).transpose(Image.Transpose.ROTATE_90).resize((SW, SH), Image.Resampling.LANCZOS), np.float32) / 255
                   for key, img in maps.items()}
        c = crops_k["color"]
        n = crops_k["normal"] * 2 - 1
        n = np.stack((-n[:, :, 1], n[:, :, 0], n[:, :, 2]), -1)
        # Lanczos resampling can overshoot at the scan's deepest cracks; keep normals in the outward hemisphere.
        n[:, :, 2] = np.maximum(n[:, :, 2], .06)
        n /= np.maximum(np.linalg.norm(n, axis=-1, keepdims=True), 1e-8)
        cloud = noise((SH, SW), (12, 45), 720 + k)
        pores = noise((SH, SW), (.45, 1.8), 750 + k)
        # Grey reclaimed pine with some warmer replacement boards; no painted-brown box.
        tint = np.array((1.17, 1.09, .94)) * r.uniform(.94, 1.11)
        c = np.clip(c * tint + .012 * cloud[:, :, None], 0, 1)
        edge = np.minimum(yy, SH - 1 - yy) / PPI
        rubbed = smooth(.12, .015, edge) * (.4 + .25 * cloud)
        c = c * (1 - .18 * rubbed[:, :, None]) + np.array((.55, .49, .39)) * .18 * rubbed[:, :, None]
        # Water and mud are strongest on the bottom row; battens have a tide line at their foot.
        if k < 16:
            row = k % 4
            mud = (1 - row / 4) ** 4 * smooth(.42, .75, .52 + .22 * cloud + .07 * pores) * .65
        elif k in (21, 22):
            mud = smooth(6, 1, xx / PPI) * smooth(.3, .7, .5 + .2 * cloud) * .75
        else:
            mud = smooth(.78, 1.05, .5 + .2 * cloud) * .2
        water = smooth(.2, .8, .5 + .3 * noise((SH, SW), (10, 80), 780 + k)) * (.12 if k < 16 else .06)
        c *= 1 - water[:, :, None]
        c = c * (1 - mud[:, :, None]) + np.array((.28, .23, .17)) * mud[:, :, None]
        # Original shop stencils on two front boards, abraded through to the grain.
        if k in (1, 2):
            mask = Image.new("L", (SW, SH))
            d = ImageDraw.Draw(mask)
            font = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", 49 if k == 2 else 43)
            d.text((SW / 2 - 50, SH / 2), "LUCKY STOP" if k == 2 else "DRY GOODS", font=font, fill=255, anchor="mm", stroke_width=0)
            ink = np.asarray(mask, np.float32) / 255
            broken = np.clip(.6 + .5 * pores + .5 * cloud, 0, 1)
            ink *= broken * .72
            c = c * (1 - ink[:, :, None]) + np.array((.105, .115, .10)) * ink[:, :, None]
        # Small rust bleed around the actual nails on the upright battens.
        if k in (21, 22):
            stain = np.zeros((SH, SW), np.float32)
            for u in (2.9, 7.8, 12.8, 17.8):
                stain += np.exp(-((xx / PPI - u + .25) / .8) ** 2 - ((yy / PPI - 1.28) / .18) ** 2)
            stain = np.clip(stain * (.4 + .2 * cloud), 0, .65)
            c = c * (1 - stain[:, :, None]) + np.array((.22, .12, .055)) * stain[:, :, None]
        sl = (slice(y0, y0 + SH), slice(x0, x0 + SW))
        colour[sl], normal[sl] = c, n
        rough[sl] = np.clip(crops_k["rough"] * .85 + .14 + .12 * mud - .1 * water, .55, .99)
        ao[sl] = np.clip(crops_k["ao"] * .25 + .75 - .1 * mud, .65, 1)
        covered[sl] = True
    # End grain, not the long grain wrapped over the sawn ends.
    x0, y0 = SLOTS[23]
    yy, xx = np.mgrid[0:SH, 0:SW].astype(np.float32)
    radial = np.sqrt(((xx - SW * .4) * .16) ** 2 + ((yy + 120) * 1.1) ** 2)
    rings = .5 + .5 * np.sin(radial * .34 + .4 * noise((SH, SW), 4, 820))
    fibres = noise((SH, SW), .65, 821)
    colour[y0:y0 + SH, x0:x0 + SW] = np.clip(np.array((.38, .32, .24)) * (1 + .12 * rings + .045 * fibres)[:, :, None], 0, 1)
    covered[y0:y0 + SH, x0:x0 + SW] = True
    # One nail patch; using this region as a proper 2D patch keeps UV tangents well-defined.
    ns = (slice(1950, 2014), slice(1950, 2014))
    rust = noise((64, 64), 2, 830) * .5 + .5
    colour[ns] = np.array((.13, .11, .09)) + np.array((.17, .06, .005)) * rust[:, :, None]
    rough[ns] = .68 + .2 * rust
    metal[ns] = .2 + .45 * (1 - rust)
    normal[ns] = (0, 0, 1)
    ao[ns] = 1
    # Pad every island before mip generation to prevent dark atlas borders at distance.
    fill = tuple(ndi.distance_transform_edt(~covered, return_distances=False, return_indices=True))
    for name, data in (("color", colour), ("normal", normal * .5 + .5), ("rough", rough), ("metal", metal), ("ao", ao)):
        Image.fromarray(np.uint8(np.clip(data[fill], 0, 1) * 255 + .5)).save(TEX / ("crate_" + name + ".png"))


class Mesh:
    def __init__(self):
        self.p, self.t, self.n = [], [], []

    def tri(self, p, uv, normal=None):
        p = np.asarray(p, float)
        cross = np.cross(p[1] - p[0], p[2] - p[0])
        if np.linalg.norm(cross) < 1e-8:
            return
        n = unit(cross) if normal is None else np.asarray(normal, float)
        if n.ndim == 1:
            n = np.tile(n, (3, 1))
        if np.dot(cross, n.mean(0)) < 0:
            p, uv, n = p[[0, 2, 1]], np.asarray(uv)[[0, 2, 1]], n[[0, 2, 1]]
        self.p.append(p)
        self.t.append(np.asarray(uv))
        self.n.append(n)

    def quad(self, p, uv, normal=None):
        p, uv = np.asarray(p), np.asarray(uv)
        self.tri(p[[0, 1, 2]], uv[[0, 1, 2]], normal)
        self.tri(p[[0, 2, 3]], uv[[0, 2, 3]], normal)

    def plank(self, centre, along, widthdir, length, width, thick, slot, lod, seed=0, bevel=.065):
        a, b = unit(along), unit(widthdir)
        n = unit(np.cross(a, b))
        centre = np.asarray(centre, float)
        w, h = width / 2, thick / 2
        e = bevel if lod < 2 else .0
        profile = [(w - e, h), (-w + e, h), (-w, h - e), (-w, -h + e), (-w + e, -h), (w - e, -h), (w, -h + e), (w, h - e)] if e else [(w, h), (-w, h), (-w, -h), (w, -h)]
        fractions = np.linspace(0, 1, (7, 3, 2)[lod])
        rng = np.random.default_rng(seed)
        ring = []
        for t in fractions:
            bow = np.sin(np.pi * t) * (.035 if lod < 2 else 0)
            ring.append([centre + a * ((t - .5) * length) + b * y + n * (z + bow) for y, z in profile])
        x0, y0 = SLOTS[slot]
        for i in range(len(ring) - 1):
            u0, u1 = x0 + fractions[i] * length * PPI + 2, x0 + fractions[i + 1] * length * PPI + 2
            for j in range(len(profile)):
                j1 = (j + 1) % len(profile)
                y, z = profile[j]
                yy, zz = profile[j1]
                normal = unit(b * (zz - z) - n * (yy - y))
                # +widthdir is +texture V, keeping the shop stencils upright on vertical boards.
                v0, v1 = y0 + (w - y) * PPI + 1, y0 + (w - yy) * PPI + 1
                if abs(v0 - v1) < .1:
                    v1 = v0 + max(thick * PPI, 1)
                self.quad([ring[i][j], ring[i + 1][j], ring[i + 1][j1], ring[i][j1]], [(u0, v0), (u1, v0), (u1, v1), (u0, v1)], normal)
        ex, ey = SLOTS[23]
        for end, sign in ((0, -1), (-1, 1)):
            c = np.mean(ring[end], 0)
            for j in range(len(profile)):
                j1 = (j + 1) % len(profile)
                uv = [(ex + 200, ey + 76)] + [(ex + 200 + y * 30, ey + 76 + z * 30) for y, z in (profile[j], profile[j1])]
                self.tri([c, ring[end][j], ring[end][j1]], uv, a * sign)

    def nail(self, centre, normal, lod):
        if lod == 2:
            return
        n = unit(normal)
        a = unit(np.cross(n, (0, 0, 1) if abs(n[2]) < .9 else (1, 0, 0)))
        b = np.cross(n, a)
        c = np.asarray(centre, float)
        seg = 8 if lod == 0 else 5
        for i in range(seg):
            theta = np.array((i, i + 1)) * 2 * np.pi / seg
            edge = [a * np.cos(q) + b * np.sin(q) for q in theta]
            ps = [c + n * .045, c + edge[0] * .14, c + edge[1] * .14]
            uv = [(1982, 1982), (1982 + np.cos(theta[0]) * 20, 1982 + np.sin(theta[0]) * 20), (1982 + np.cos(theta[1]) * 20, 1982 + np.sin(theta[1]) * 20)]
            self.tri(ps, uv, n)


def build(lod):
    m = Mesh()
    # Long walls: four separate, slightly bowed boards. All perimeter battens lap over them.
    rowheight = 4.87
    for side in (-1, 1):
        for row in range(4):
            z = .7 + rowheight / 2 + row * (rowheight + .1)
            slot = row if side == -1 else row + 4
            m.plank((0, side * 11.0, z), (1, 0, 0), (0, 0, 1), 29.5, rowheight, .7, slot, lod, row + (side + 1) * 4)
        for x in (-13.25, 13.25):
            # Grain runs vertically along the reinforcing corner battens.
            m.plank((x, side * 11.7, 10.65), (0, 0, 1), (1, 0, 0), 21.2, 2.6, .6, 21, lod)
            for row in range(4):
                m.nail((x + .18 * (-1) ** row, side * 12.015, 2.95 + row * 4.97), (0, side, 0), lod)
    # Short walls butt into the long walls; their battens are narrower to avoid shared faces.
    for side in (-1, 1):
        for row in range(4):
            z = .7 + rowheight / 2 + row * (rowheight + .1)
            m.plank((side * 14.0, 0, z), (0, 1, 0), (0, 0, 1), 21.3, rowheight, .7, 8 + row + (4 if side == 1 else 0), lod, row + 20)
        for y in (-9.55, 9.55):
            m.plank((side * 14.67, y, 10.65), (0, 0, 1), (0, 1, 0), 21.2, 2.0, .6, 22, lod)
            for row in range(4):
                m.nail((side * 14.985, y + .12 * (-1) ** row, 2.95 + row * 4.97), (side, 0, 0), lod)
    # Five lid planks and two transverse battens; the solid floor can be seen through the seams.
    for k in range(5):
        y = -8.85 + k * 4.425
        m.plank((0, y, 20.85), (1, 0, 0), (0, 1, 0), 29.5, 4.32, .7, 16 + k, lod, 40 + k)
        if lod < 2:
            m.plank((0, y, .35), (1, 0, 0), (0, 1, 0), 28.0, 4.32, .7, 16 + k, lod, 50 + k)
    for x in (-10.4, 10.4):
        m.plank((x, 0, 21.6), (0, 1, 0), (1, 0, 0), 22.1, 2.6, .8, 22, lod, bevel=.08)
        for y in (-8.85, -4.425, 0, 4.425, 8.85):
            m.nail((x, y, 22.015), (0, 0, 1), lod)
    return m


def write_obj(mesh, path):
    p, t, n = np.array(mesh.p), np.array(mesh.t), np.array(mesh.n)
    assert np.isfinite(p).all() and np.isfinite(t).all() and np.isfinite(n).all()
    n /= np.maximum(np.linalg.norm(n, axis=-1, keepdims=True), 1e-9)
    face = np.cross(p[:, 1] - p[:, 0], p[:, 2] - p[:, 0])
    assert np.all((face * n.mean(1)).sum(-1) > 0)
    # UVs are authored in atlas pixels; the OBJ importer expects +V up.
    uv = np.stack((t[:, :, 0] / AW, 1 - t[:, :, 1] / AH), -1)
    po, no = p[:, :, [1, 2, 0]], n[:, :, [1, 2, 0]]
    tables, lines, faces = ({}, {}, {}), ([], [], []), []

    def index(k, prefix, value):
        key = tuple(np.round(value, 5))
        if key not in tables[k]:
            tables[k][key] = len(tables[k]) + 1
            lines[k].append(prefix + " ".join(f"{v:.5f}" for v in key) + "\n")
        return tables[k][key]

    for k in range(len(po)):
        faces.append("f " + " ".join("%d/%d/%d" % (index(0, "v ", po[k, c]), index(1, "vt ", uv[k, c]), index(2, "vn ", no[k, c])) for c in range(3)) + "\n")
    with path.open("w", newline="\n") as h:
        h.write("# Sources/Riverside/crate-v2/build.py\nmtllib crate.mtl\n")
        for block in lines:
            h.writelines(block)
        h.write("usemtl crate\n")
        h.writelines(faces)
    result = dict(triangles=len(po), bounds=[p.reshape(-1, 3).min(0).tolist(), p.reshape(-1, 3).max(0).tolist()])
    print(path.name, result, flush=True)
    return result


def resources(counts):
    (OUT / "crate.mtl").write_text("newmtl crate\n")
    tail = 'import_translation = [ 0.0, 0.0, 0.0 ] import_rotation = [ 0.0, 0.0, 0.0 ] import_scale = 1.0 align_origin_x_type = "None" align_origin_y_type = "None" align_origin_z_type = "None" parent_bone = "" import_filter = { exclude_by_default = false exception_list = [ ] }'
    meshes = "\n".join(f'{{ _class = "RenderMeshFile" name = "lod{k}" filename = "{MODEL}/crate_lod{k}.obj" {tail} }},' for k in range(3))
    (OUT / "crate.vmdl").write_text('''<!-- kv3 encoding:text:version{e21c7f3c-8a33-41c5-9977-a76d3a32aa0d} format:modeldoc29:version{3cec427c-1b0e-4d48-a90a-0436f33a6041} -->
{
 rootNode = {
  _class = "RootNode"
  children = [
   { _class = "MaterialGroupList" children = [
    { _class = "DefaultMaterialGroup" remaps = [ { from = "crate.vmat" to = "%MAT%/crate.vmat" } ] use_global_default = false global_default_material = "" }
   ] },
   { _class = "RenderMeshList" children = [ %MESHES% ] },
   { _class = "LODGroupList" children = [
    { _class = "LODGroup" switch_threshold = 0.0 meshes = [ "lod0" ] },
    { _class = "LODGroup" switch_threshold = 25.0 meshes = [ "lod1" ] },
    { _class = "LODGroup" switch_threshold = 70.0 meshes = [ "lod2" ] }
   ] }
  ]
 }
}
'''.replace("%MAT%", MAT).replace("%MESHES%", meshes))
    (TEX / "crate.vmat").write_text('''// Reclaimed wood from the project's existing CC0 brown_planks_03 scan; see Sources/Riverside/crate-v2/README.md.
Layer0
{
 shader "shaders/complex.shader"
 F_METALNESS_TEXTURE 1
 F_SPECULAR 1
 TextureColor "%MAT%/crate_color.png"
 TextureNormal "%MAT%/crate_normal.png"
 TextureRoughness "%MAT%/crate_rough.png"
 TextureMetalness "%MAT%/crate_metal.png"
 TextureAmbientOcclusion "%MAT%/crate_ao.png"
 g_flAmbientOcclusionDirectDiffuse "0.3"
 g_flAmbientOcclusionDirectSpecular "0.5"
 g_flRoughnessScaleFactor "1.0"
 g_flModelTintAmount "1.0"
 g_vColorTint "[1.0 1.0 1.0 0.0]"
 g_bFogEnabled "1"
}
'''.replace("%MAT%", MAT))
    (REPORT / "mesh-report.json").write_text(json.dumps(dict(lods=counts, atlas=[AW, AH], pixels_per_inch=PPI, installed=False), indent=2))


if __name__ == "__main__":
    paint()
    counts = [write_obj(build(k), OUT / f"crate_lod{k}.obj") for k in range(3)]
    resources(counts)
