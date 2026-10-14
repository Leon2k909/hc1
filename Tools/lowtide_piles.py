"""Worn mooring timber with continuous grain, end grain and formed iron straps."""
import math
import zlib

import numpy as np
from PIL import Image
from scipy import ndimage
from scipy.spatial import ConvexHull

import map_kit as K
from lowtide_brick import metadata

RESOURCE = "materials/lowtide/piles"
POSITIONS = ((205, -720), (-205, -690), (208, 360), (-206, 1000), (204, -1440), (-204, -1460))
PAINTS = ("lt_pile_timber", "lt_pile_end", "lt_pile_iron")


def bake_textures(output=None):
    output = output or K.ASSETS / RESOURCE
    output.mkdir(parents=True, exist_ok=True)
    for name, size, metres, depth in (("timber", 2048, (.6, 1.2), .0024), ("end", 1024, (.32, .32), .0007)):
        source = K.ROOT / "Sources/Lowtide/visual-target" / f"pile-{name}-source.png"
        rgb = np.asarray(Image.open(source).convert("RGB").resize((size, size), Image.Resampling.LANCZOS), float)/255
        lum = rgb @ np.array([.2126, .7152, .0722])
        relief = (ndimage.gaussian_filter(lum, 1, mode="wrap") - ndimage.gaussian_filter(lum, 22, mode="wrap"))*depth
        dx = (np.roll(relief, -1, 1)-np.roll(relief, 1, 1))*size/(2*metres[0])
        dy = (np.roll(relief, -1, 0)-np.roll(relief, 1, 0))*size/(2*metres[1])
        normal = np.stack((-dx, dy, np.ones_like(relief)), axis=-1)
        normal /= np.linalg.norm(normal, axis=-1, keepdims=True)
        roughness = np.clip(.77 + (ndimage.gaussian_filter(lum, 3)-lum)*.6, .66, .9)
        for suffix, values in (("color", rgb), ("normal", normal*.5+.5), ("rough", roughness)):
            path = output / f"{name}_{suffix}.png"
            Image.fromarray(np.rint(values*255).clip(0, 255).astype(np.uint8)).save(path)
            if path.is_relative_to(K.ASSETS):
                metadata(path)


def material_sources():
    result = {}
    for name, image, tint in (("lt_pile_timber", "timber", ".24 .23 .21"), ("lt_pile_end", "end", ".30 .28 .24")):
        result[f"{RESOURCE}/{name}.vmat"] = f'''// Tools/lowtide_piles.py: generated harbour timber.
"Layer0"
{{
    shader "shaders/hc1_lowtide_pile.shader"
    TextureColor "{RESOURCE}/{image}_color.png"
    TextureNormal "{RESOURCE}/{image}_normal.png"
    TextureRoughness "{RESOURCE}/{image}_rough.png"
    TextureMetalness "materials/default/default_black_mask.tga"
    TextureAmbientOcclusion "materials/default/default_ao.tga"
    g_flTintColor "[{tint}]"
}}
'''
    result[f"{RESOURCE}/lt_pile_iron.vmat"] = '''// Formed iron retaining straps.
"Layer0"
{
    shader "shaders/complex.shader"
    F_SPECULAR "1"
    TextureColor "materials/lowtide/marine/paint_color.png"
    TextureNormal "materials/lowtide/marine/paint_normal.png"
    TextureRoughness "[0.67 0.67 0.67 0]"
    TextureMetalness "[0.5 0.5 0.5 0]"
    TextureAmbientOcclusion "materials/default/default_ao.tga"
    g_vColorTint "[0.50 0.48 0.43 1]"
}
'''
    return result


def write_materials():
    for relative, text in material_sources().items():
        K.write_text(K.ASSETS / relative, text)
        metadata(K.ASSETS / relative)
    metadata(K.ASSETS / "shaders/hc1_lowtide_pile.shader")


def configure(model):
    for paint in PAINTS:
        if paint in model.polygons:
            model.material_overrides[paint] = f"{RESOURCE}/{paint}.vmat"
            model.tile_overrides[paint] = 36


def post(model, centre, z0, top, seed):
    rng = np.random.default_rng(seed)
    sides = 32
    angles = np.arange(sides)*math.tau/sides
    phase = rng.uniform(0, math.tau, 3)
    radius = 6.35*(1 + .018*np.sin(angles*3+phase[0]) + .009*np.sin(angles*7+phase[1]))
    heights = (z0, top-95, top-55, top-25, top-1.05, top-.32)
    scales = (1.035, 1.022, 1.015, 1.008, 1, .945)
    lean = rng.uniform(-.23, .23, 2)
    rings = []
    for z, scale in zip(heights, scales):
        fraction = (z-z0)/(top-z0)
        xy = np.asarray(centre) + lean*fraction + np.column_stack((np.cos(angles), np.sin(angles)))*radius[:, None]*scale
        crown = -.10*(1+np.sin(angles*2+phase[2])) if z == heights[-1] else 0
        rings.append(np.column_stack((xy, np.full(sides, z)+crown)))
    points = np.concatenate(rings)
    faces = []
    for row in range(len(rings)-1):
        for k in range(sides):
            j = (k+1)%sides
            faces.append((row*sides+k, row*sides+j, (row+1)*sides+j, (row+1)*sides+k))
    normals = np.zeros_like(points)
    for face in faces:
        a, b, c, d = points[list(face)]
        normal = np.cross(b-a, c-a) + np.cross(c-a, d-a)
        normals[list(face)] += normal
    normals /= np.linalg.norm(normals, axis=1, keepdims=True)
    offset = rng.uniform(0, 1, 2)
    for index, face in enumerate(faces):
        row, k = divmod(index, sides)
        u0, u1 = k/sides*2+offset[0], (k+1)/sides*2+offset[0]
        vertices = points[list(face)]
        uv = [(u, (p[2]-z0)/47.244+offset[1]) for u, p in zip((u0, u1, u1, u0), vertices)]
        model.polygon("lt_pile_timber", vertices, uv=uv, normals=normals[list(face)])
    # A shallow worn bevel meets a separate end-grain cap; cap UVs rotate with
    # each post while preserving the tree-ring centre at its actual centre.
    cap = rings[-1]
    middle = cap.mean(axis=0)
    spin = rng.uniform(0, math.tau)
    rotation = np.array(((math.cos(spin), -math.sin(spin)), (math.sin(spin), math.cos(spin))))
    coords = (cap[:, :2]-middle[:2])@rotation.T/13.0 + .5
    for k in range(sides):
        j = (k+1)%sides
        model.polygon("lt_pile_end", (middle, cap[k], cap[j]), uv=((.5, .5), coords[k], coords[j]), normal=(0, 0, 1))


def strap(model, centres, z, radius=6.85):
    samples = np.concatenate([np.asarray(c) + radius*np.column_stack((np.cos(np.arange(48)*math.tau/48),
        np.sin(np.arange(48)*math.tau/48))) for c in centres])
    outline = samples[ConvexHull(samples).vertices]
    count = len(outline)
    tangents = np.roll(outline, -1, axis=0)-outline
    edge_normals = np.column_stack((tangents[:, 1], -tangents[:, 0]))
    edge_normals /= np.linalg.norm(edge_normals, axis=1, keepdims=True)
    normals = edge_normals + np.roll(edge_normals, 1, axis=0)
    normals /= np.linalg.norm(normals, axis=1, keepdims=True)
    # Rolled edges and a shallow lip give the strap physical thickness.
    profile = ((0, z), (.13, z+.15), (.13, z+3.35), (0, z+3.5), (-.10, z+3.35), (-.10, z+.15))
    for i, (offset0, z0) in enumerate(profile):
        offset1, z1 = profile[(i+1)%len(profile)]
        for k in range(count):
            j = (k+1)%count
            pts = ((* (outline[k]+normals[k]*offset0), z0), (* (outline[j]+normals[j]*offset0), z0),
                   (* (outline[j]+normals[j]*offset1), z1), (* (outline[k]+normals[k]*offset1), z1))
            model.polygon("lt_pile_iron", pts)
    # Overlapping strap ends and two small rivet heads on the long front face.
    k = int(np.argmax(np.linalg.norm(tangents, axis=1)))
    centre = (outline[k]+outline[(k+1)%count])/2
    along = tangents[k]/np.linalg.norm(tangents[k])
    normal = edge_normals[k]
    model.beam((* (centre-along*3+normal*.2), z+1.75),
               (* (centre+along*3+normal*.2), z+1.75), (.28, 3.15), "lt_pile_iron")
    for shift in (-1.1, 1.1):
        c = centre + along*shift + normal*.37
        for step in range(8):
            a, b = step*math.tau/8, (step+1)*math.tau/8
            p0 = np.array((*c, z+1.75)) + np.array((*normal, 0))*.19
            p1 = np.array((*c, z+1.75)) + np.array((*along, 0))*(math.cos(a)*.40) + (0, 0, math.sin(a)*.40)
            p2 = np.array((*c, z+1.75)) + np.array((*along, 0))*(math.cos(b)*.40) + (0, 0, math.sin(b)*.40)
            if np.dot(np.cross(p1-p0, p2-p0), (*normal, 0)) < 0:
                p1, p2 = p2, p1
            model.polygon("lt_pile_iron", (p0, p1, p2))


def cluster(model, e, n, z0, top=-8):
    centres = [(e+8*math.cos(math.tau*k/3+.4), n+8*math.sin(math.tau*k/3+.4)) for k in range(3)]
    for k, centre in enumerate(centres):
        seed = zlib.crc32(f"pile:{e}:{n}:{k}".encode())
        post(model, centre, z0, top-k*3, seed)
    for z in (top-24, top-86):
        strap(model, centres, z)
    configure(model)
