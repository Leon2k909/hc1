"""Riverside sandbag review assets: closed, compressed hessian sacks with hems and tied mouths.

python build.py <project-root>
Only the new assets are written; the existing map, collision and generator are untouched.
"""
from pathlib import Path
import ctypes
import json
import math
import sys
import numpy as np
from PIL import Image
from scipy import ndimage as ndi

ROOT = Path(sys.argv[1]).resolve()
sys.path.insert(0, str(ROOT / "Tools"))
import map_kit as K
# These seams are far smaller than map walls; retain sub-millimetre vertex precision.
K.obj_vector = lambda p: f"{p[1]:.5f} {p[2]:.5f} {p[0]:.5f}"

try:
    ctypes.windll.kernel32.SetPriorityClass(ctypes.windll.kernel32.GetCurrentProcess(), 0x4000)
except AttributeError:
    pass

MODEL = "models/props/riverside/sandbag_v2"
MAT = "materials/riverside/sandbag_v2"
OUT, TEX = ROOT / "Assets" / MODEL, ROOT / "Assets" / MAT
REPORT = ROOT / "output/asset-improvement-20261030/riverside-sandbags"
for path in (OUT, TEX, REPORT):
    path.mkdir(parents=True, exist_ok=True)
AW = AH = 2048
PPI = 48


def unit(v):
    v = np.asarray(v, float)
    return v / max(np.linalg.norm(v), 1e-10)


def plan(v):
    return np.asarray((-v[1], v[0], v[2]))


def field(shape, sigma, seed):
    a = ndi.gaussian_filter(np.random.default_rng(seed).normal(size=shape), sigma, mode="wrap")
    return a / (3 * a.std() + 1e-8)


def paint():
    source = ROOT / "Assets/materials/lowtide/sacks/lt_jute_color.png"
    tile = np.asarray(Image.open(source).convert("RGB"), float) / 255
    # Existing authored jute, sampled at a 5.25-inch field rather than stretched over a whole bag.
    size = round(5.25 * PPI)
    tile = np.asarray(Image.fromarray(np.uint8(tile * 255)).resize((size, size), Image.Resampling.LANCZOS), float) / 255
    grey = tile.mean(-1)
    low = ndi.gaussian_filter(grey, 18, mode="wrap")
    tile *= (np.median(low) / np.maximum(low, .05))[:, :, None]
    yy, xx = np.mgrid[0:AH, 0:AW]
    rgb = tile[yy % size, xx % size].astype(np.float32)
    grain = rgb.mean(-1)
    cloud = field((AH, AW), (30, 75), 13).astype(np.float32)
    blotch = field((AH, AW), (12, 25), 14).astype(np.float32)
    upper = yy < 960
    damp = np.where(upper, .06, .35) + .13 * np.clip(cloud + .7, 0, 1)
    damp += .12 * np.exp(-((xx / PPI - 25) / 2.2) ** 2)
    mud = np.clip((blotch + cloud * .4 - .2) * .4, 0, .55) * np.where(upper, .18, .7)
    rgb *= np.array((.90, .88, .82)) * (1 - .26 * damp[:, :, None])
    rgb *= (1 + .045 * cloud[:, :, None])
    rgb = rgb * (1 - mud[:, :, None]) + np.array((.25, .205, .15)) * mud[:, :, None]
    # Fibre relief only: broad dirt/water stains must not turn into rocky normals.
    height = (ndi.gaussian_filter(grain, .5) - ndi.gaussian_filter(grain, 5)) * .018
    dy, dx = np.gradient(height)
    normal = np.stack((-dx * PPI, dy * PPI, np.ones_like(height)), -1)
    normal /= np.linalg.norm(normal, axis=-1, keepdims=True)
    rough = np.clip(.91 + .045 * (1 - grain) - .08 * damp + .025 * blotch, .77, .98)
    ao = np.clip(.87 + .13 * grain / max(grain.mean(), .1), .85, 1)
    # Rolled hem and cord have their own atlas strips, with aligned fibre directions.
    for kind, (x0, y0, w, h), base in (
        ("cord", (1800, 24, 224, 160), (.42, .34, .24)),
        ("hem", (1800, 220, 224, 180), (.45, .37, .26))):
        y, x = np.mgrid[0:h, 0:w]
        twist = .5 + .5 * np.cos(x * .55 + y * .15)
        colour = np.array(base) * (.91 + .18 * twist[:, :, None])
        sl = (slice(y0, y0 + h), slice(x0, x0 + w))
        rgb[sl], rough[sl], normal[sl], ao[sl] = colour, .91, (0, 0, 1), 1
    for name, data in (("color", rgb), ("normal", normal * .5 + .5), ("rough", rough), ("ao", ao)):
        Image.fromarray(np.uint8(np.clip(data, 0, 1) * 255 + .5)).save(TEX / ("sandbag_" + name + ".png"))


class Mesh:
    def __init__(self):
        self.model = K.Model()
        self.model.material_overrides["sb_cloth"] = MAT + "/sandbag.vmat"
        self.model.tile_overrides["sb_cloth"] = 5.25

    def polygon(self, pts, uv, normals):
        pts, uv, normals = np.asarray(pts), np.asarray(uv), np.asarray(normals)
        if normals.ndim == 1:
            normals = np.tile(normals, (len(pts), 1))
        # Folded quads are not planar. Validate each exported triangle against its smooth
        # normals rather than assuming the first half's winding applies to the second half.
        for i in range(1, len(pts) - 1):
            ids = [0, i, i + 1]
            p, t, n = np.round(pts[ids], 5), uv[ids], normals[ids]
            cross = np.cross(p[1] - p[0], p[2] - p[0])
            if np.linalg.norm(cross) < 1e-9:
                continue
            if np.dot(cross, n.mean(0)) < 0:
                p, t, n = p[::-1], t[::-1], n[::-1]
            self.model.polygon("sb_cloth", [plan(v) for v in p], plan(n.mean(0)),
                               uv=[(u / AW, 1 - v / AH) for u, v in t], normals=[plan(unit(v)) for v in n])

    def tube(self, points, radius, sides, kind="cord"):
        points = np.asarray(points, float)
        if len(points) < 2:
            return
        distance = np.r_[0, np.cumsum(np.linalg.norm(np.diff(points, axis=0), axis=1))]
        rings, ns = [], []
        previous = None
        for k, p in enumerate(points):
            tangent = unit(points[min(k + 1, len(points) - 1)] - points[max(0, k - 1)])
            if previous is None:
                ref = (0, 0, 1) if abs(tangent[2]) < .9 else (1, 0, 0)
                across = unit(np.cross(tangent, ref))
            else:
                across = unit(previous - tangent * np.dot(previous, tangent))
            previous = across
            up = np.cross(tangent, across)
            normal = [across * math.cos(a) + up * math.sin(a) for a in np.linspace(0, 2 * math.pi, sides, endpoint=False)]
            ns.append(normal)
            rings.append([p + n * radius for n in normal])
        x0, y0 = (1804, 28) if kind == "cord" else (1804, 224)
        for k in range(len(points) - 1):
            u0, u1 = x0 + distance[k] * 6, x0 + distance[k + 1] * 6
            for j in range(sides):
                j1 = (j + 1) % sides
                self.polygon([rings[k][j], rings[k][j1], rings[k + 1][j1], rings[k + 1][j]],
                             [(u0, y0 + j / sides * 100), (u0, y0 + (j + 1) / sides * 100), (u1, y0 + (j + 1) / sides * 100), (u1, y0 + j / sides * 100)],
                             [ns[k][j], ns[k][j1], ns[k + 1][j1], ns[k + 1][j]])
        for k, n in ((0, -unit(points[1] - points[0])), (-1, unit(points[-1] - points[-2]))):
            for j in range(sides):
                a, b = 2 * math.pi * j / sides, 2 * math.pi * (j + 1) / sides
                self.polygon([points[k], rings[k][j], rings[k][(j + 1) % sides]],
                             [(x0 + 10, y0 + 10), (x0 + 10 + 8 * math.cos(a), y0 + 10 + 8 * math.sin(a)),
                              (x0 + 10 + 8 * math.cos(b), y0 + 10 + 8 * math.sin(b))], n)


PROFILE_X = np.array([-12.65, -12.1, -11.1, -9, -6, -3, 0, 3, 6, 8.5, 9.8, 10.7, 11.35, 11.85, 12.2])
PROFILE_W = np.array([5.5, 6.8, 7.05, 7.1, 7.15, 7.2, 7.2, 7.15, 7.05, 7.0, 6.9, 6.6, 5.3, .85, .5])
PROFILE_H = np.array([.13, 2.5, 2.8, 2.9, 2.9, 2.9, 2.85, 2.9, 2.85, 2.8, 2.75, 2.65, 2.1, .4, .32])


def body_point(x, angle, seed):
    phase = seed * .73
    c, s = math.cos(angle), math.sin(angle)
    w, h = np.interp(x, PROFILE_X, PROFILE_W), np.interp(x, PROFILE_X, PROFILE_H)
    ends = math.exp(-((x + 10.6) / 2.1) ** 2) + math.exp(-((x - 9.8) / 2.0) ** 2)
    wrinkle = ends * math.sin(angle * 6 + x * .7 + phase) * .15
    y = math.copysign(abs(c) ** .64, c) * (w + wrinkle)
    z = math.copysign(abs(s) ** .30, s) * h
    z += ends * .16 * math.sin(angle * 5 + phase + x)
    z -= .27 * math.exp(-((x - seed % 4) / 6) ** 2) * max(0, s) ** 3
    y += .19 * math.sin(x * .4 + phase) * (1 - (abs(x) / 13) ** 2)
    # Folds pull into the seam and the gathered mouth, rather than wrinkling the whole bag evenly.
    y += .12 * math.sin(x * .6 + phase) * abs(c) ** 4
    z += ends * .10 * math.sin(x * 2 + phase) * abs(c) ** 3
    z = max(z, -2.6)
    return np.array((x, y, z))


def build(lod, variant):
    m = Mesh()
    seed = (7, 19, 31)[variant]
    xs = PROFILE_X if lod == 0 else PROFILE_X[[0, 1, 2, 4, 6, 8, 10, 12, 14]] if lod == 1 else PROFILE_X[[0, 2, 6, 10, 14]]
    sides = (20, 12, 8)[lod]
    angles = np.linspace(0, 2 * math.pi, sides, endpoint=False)
    points = np.array([[body_point(x, a, seed) for a in angles] for x in xs])
    # A continuous cylindrical cloth unwrap: V follows actual arc length around each ring.
    # A planar top/bottom projection stretches the yarns along the steep sides.
    ring_uvs = []
    reference = np.array([body_point(0, a, seed) for a in angles])
    distances = np.r_[0, np.cumsum(np.linalg.norm(np.roll(reference, -1, axis=0) - reference, axis=1))]
    for x, ring in zip(xs, points):
        ring_uvs.append([(32 + (x + 13) * PPI + seed % 3 * 8, 32 + d * PPI) for d in distances])
    normals = np.zeros_like(points)
    for i in range(len(xs) - 1):
        for j in range(sides):
            jj = (j + 1) % sides
            q = [(i, j), (i, jj), (i + 1, jj), (i + 1, j)]
            cross = np.cross(points[q[1]] - points[q[0]], points[q[2]] - points[q[0]])
            for r, c in q:
                normals[r, c] += cross
    normals /= np.maximum(np.linalg.norm(normals, axis=-1, keepdims=True), 1e-8)
    for i in range(len(xs) - 1):
        for j in range(sides):
            jj = (j + 1) % sides
            ids = [(i, j), (i, jj), (i + 1, jj), (i + 1, j)]
            ps = [points[r, c] for r, c in ids]
            uv = [ring_uvs[i][j], ring_uvs[i][j + 1], ring_uvs[i + 1][j + 1], ring_uvs[i + 1][j]]
            m.polygon(ps, uv, [normals[r, c] for r, c in ids])
    for end, sign in ((0, -1), (-1, 1)):
        centre = points[end].mean(0)
        for j in range(sides):
            ps = [centre, points[end, j], points[end, (j + 1) % sides]]
            uv = [(1820 + (p[1] + 7.3) * 12, 850 - p[2] * 16) for p in ps]
            m.polygon(ps, uv, (sign, 0, 0))
    if lod < 2:
        # Rolled longitudinal hems follow the actual filled sack's sides.
        for side in (-1, 1):
            angle = 0 if side == 1 else math.pi
            xx = np.linspace(-12.0, 10.2, (15, 8)[lod])
            seam = [body_point(x, angle, seed) + (0, side * .035, .04) for x in xx]
            m.tube(seam, .065, (5, 4)[lod], "hem")
            if lod == 0:
                for x in np.arange(-11.5, 9.8, .75):
                    p = body_point(x, angle, seed) + (0, side * .10, .04)
                    m.tube([p + (-.1, 0, -.10), p + (.1, 0, .10)], .023, 3)
        m.tube([(-12.69, y, .025 * (-1) ** k) for k, y in enumerate(np.linspace(-5.45, 5.45, (25, 12)[lod]))], .05, 4, "hem")
    # Two wraps of twine bind the gathered mouth. The knot and ends rest against the sack.
    rope_sides = (6, 4, 3)[lod]
    segs = (28, 16, 8)[lod]
    tie = []
    for a in np.linspace(0, math.pi * 4, segs + 1):
        tie.append((11.85 + .08 * a / (math.pi * 2), .92 * math.cos(a), .48 * math.sin(a)))
    m.tube(tie, .07, rope_sides)
    if lod < 2:
        m.tube([(11.95, -.85, .22), (11.55, -1.12, .1), (12.05, -1.35, .05), (12.35, -.9, .18), (11.95, -.85, .22)], .10, rope_sides)
        m.tube([(11.95, -1.15, .05), (11.1, -1.6, -.2), (10.8, -1.9, -.35)], .05, 4)
        m.tube([(12.1, -1.1, .05), (12.7, -1.4, -.1), (12.9, -1.3, -.45)], .05, 4)
        # Short gathered cloth above the tie, with an actual thickness at its open edge.
        sections = 12 if lod == 0 else 8
        rings = []
        for t in (0, .5, 1):
            rings.append([np.array((12.15 + t * 1.1, (.5 + .65 * t) * math.cos(a), (.32 + .18 * t) * math.sin(a) + .08 * math.sin(a * 4) * t))
                          for a in np.linspace(0, 2 * math.pi, sections, endpoint=False)])
        for i in range(2):
            for j in range(sections):
                jj = (j + 1) % sections
                ps = [rings[i][j], rings[i][jj], rings[i + 1][jj], rings[i + 1][j]]
                centre = np.mean(ps, 0)
                normal = unit((0, centre[1], centre[2]))
                uv = [(1810 + i * 80, 530 + j * 10), (1810 + i * 80, 530 + (j + 1) * 10), (1810 + (i + 1) * 80, 530 + (j + 1) * 10), (1810 + (i + 1) * 80, 530 + j * 10)]
                m.polygon(ps, uv, normal)
                inside = [p - normal * .03 for p in ps]
                m.polygon(inside[::-1], uv[::-1], -normal)
                if i == 1:
                    m.polygon([ps[2], ps[3], inside[3], inside[2]], [(1950, 750), (1960, 750), (1960, 754), (1950, 754)], (1, 0, 0))
    return m.model


def vmdl(name, meshes):
    tail = 'import_translation = [ 0.0, 0.0, 0.0 ] import_rotation = [ 0.0, 0.0, 0.0 ] import_scale = 1.0 align_origin_x_type = "None" align_origin_y_type = "None" align_origin_z_type = "None" parent_bone = "" import_filter = { exclude_by_default = false exception_list = [ ] }'
    render = '\n'.join('{ _class = "RenderMeshFile" name = "lod%d" filename = "%s/%s_lod%d.obj" %s },' % (k, MODEL, name, k, tail) for k in range(3))
    (OUT / (name + ".vmdl")).write_text('''<!-- kv3 encoding:text:version{e21c7f3c-8a33-41c5-9977-a76d3a32aa0d} format:modeldoc29:version{3cec427c-1b0e-4d48-a90a-0436f33a6041} -->
{ rootNode = { _class = "RootNode" children = [
{ _class = "MaterialGroupList" children = [ { _class = "DefaultMaterialGroup" remaps = [ { from = "sb_cloth.vmat" to = "%MAT%/sandbag.vmat" } ] use_global_default = false global_default_material = "" } ] },
{ _class = "RenderMeshList" children = [ %RENDER% ] },
{ _class = "LODGroupList" children = [
{ _class = "LODGroup" switch_threshold = 0.0 meshes = [ "lod0" ] },
{ _class = "LODGroup" switch_threshold = 20.0 meshes = [ "lod1" ] },
{ _class = "LODGroup" switch_threshold = 60.0 meshes = [ "lod2" ] }
] } ] } }
'''.replace("%MAT%", MAT).replace("%RENDER%", render))


if __name__ == "__main__":
    paint()
    report = []
    for variant in range(3):
        name = "sandbag_" + str(variant)
        counts = [K.write_obj(OUT / (name + f"_lod{k}.obj"), build(k, variant), name) for k in range(3)]
        vmdl(name, counts)
        report.append(dict(model=name, triangles=counts))
        print(report[-1], flush=True)
    (TEX / "sandbag.vmat").write_text('''Layer0
{
 shader "shaders/complex.shader"
 F_SPECULAR 1
 TextureColor "%MAT%/sandbag_color.png"
 TextureNormal "%MAT%/sandbag_normal.png"
 TextureRoughness "%MAT%/sandbag_rough.png"
 TextureAmbientOcclusion "%MAT%/sandbag_ao.png"
 g_flRoughnessScaleFactor "1.0"
 g_flMetalness "0.0"
 g_flAmbientOcclusionDirectDiffuse "0.3"
 g_flAmbientOcclusionDirectSpecular "0.5"
 g_flModelTintAmount "1.0"
 g_vColorTint "[1 1 1 0]"
 g_bFogEnabled "1"
}
'''.replace("%MAT%", MAT))
    (REPORT / "mesh-report.json").write_text(json.dumps(dict(models=report, atlas=[AW, AH], installed=False), indent=2))
