"""Tidal-bank surface maps and smoothly shaded, irregular buried cobbles."""
from functools import lru_cache
import math

import numpy as np
from PIL import Image
from scipy import ndimage
from scipy.spatial import ConvexHull

import map_kit as K
from lowtide_brick import metadata

WET_SOURCE = K.ROOT / "Sources/Lowtide/visual-target/estuary-wet-silt-source.png"
WET_RESOURCE = "materials/lowtide/finish/wet_silt"
STONE_RESOURCE = "materials/lowtide/marine"
LANDINGS = (-1450, -1280, -870, -560, -315, 205, 465, 725, 1020)


def landing_clear(n, radius):
    return min(abs(n-x) for x in LANDINGS) >= 45+radius


def bake_wet_silt():
    rgb = np.asarray(Image.open(WET_SOURCE).convert("RGB").resize((2048, 2048), Image.Resampling.LANCZOS), float)/255
    lum = rgb @ np.array([.2126, .7152, .0722])
    # Numerical surface maps only; keep the generated colour pixels unchanged.
    relief = ndimage.gaussian_filter(lum, 1.2, mode="wrap") - ndimage.gaussian_filter(lum, 18, mode="wrap")
    height = relief * .0018  # shallow millimetre-scale relief over a one-metre tile
    dx = (np.roll(height, -1, 1)-np.roll(height, 1, 1))*1024
    dy = (np.roll(height, -1, 0)-np.roll(height, 1, 0))*1024
    normal = np.stack([-dx, dy, np.ones_like(height)], axis=-1)
    normal /= np.linalg.norm(normal, axis=-1, keepdims=True)
    for suffix, values in (("color", rgb), ("normal", normal*.5+.5)):
        path = K.ASSETS / f"{WET_RESOURCE}_{suffix}.png"
        Image.fromarray(np.rint(values*255).clip(0, 255).astype(np.uint8)).save(path)
        metadata(path)


@lru_cache(maxsize=2)
def sphere(subdivisions):
    phi = (1 + math.sqrt(5))/2
    vertices = np.array([(0, a, b*phi) for a in (-1, 1) for b in (-1, 1)]
                        + [(a, b*phi, 0) for a in (-1, 1) for b in (-1, 1)]
                        + [(b*phi, 0, a) for a in (-1, 1) for b in (-1, 1)], float)
    vertices /= np.linalg.norm(vertices, axis=1, keepdims=True)
    faces = ConvexHull(vertices).simplices.tolist()
    for _ in range(subdivisions):
        points = vertices.tolist()
        mids = {}
        def midpoint(a, b):
            key = tuple(sorted((a, b)))
            if key not in mids:
                value = vertices[a] + vertices[b]
                value /= np.linalg.norm(value)
                mids[key] = len(points)
                points.append(value.tolist())
            return mids[key]
        refined = []
        for a, b, c in faces:
            ab, bc, ca = midpoint(a, b), midpoint(b, c), midpoint(c, a)
            refined.extend(((a, ab, ca), (b, bc, ab), (c, ca, bc), (ab, bc, ca)))
        vertices, faces = np.asarray(points), refined
    faces = np.asarray(faces)
    for face in faces:
        a, b, c = vertices[face]
        if np.dot(np.cross(b-a, c-a), (a+b+c)/3) < 0:
            face[1], face[2] = face[2], face[1]
    return vertices, faces


def cobble(model, e, n, ground, radius, height, seed, brick=False, terrain=None):
    rng = np.random.default_rng(seed)
    unit, faces = sphere(2 if radius > 5.5 else 1)
    # Low-frequency deformation leaves a rounded worn silhouette, rather than
    # the former flat polygon cap and straight vertical sides.
    direction = rng.normal(size=(2, 3))
    direction /= np.linalg.norm(direction, axis=1, keepdims=True)
    radial = 1 + .10*np.sin(unit@direction[0]*3.2+rng.uniform(0, 6))
    radial += .045*np.sin(unit@direction[1]*5+rng.uniform(0, 6))
    shaped = unit * radial[:, None]
    if brick:
        # Broken fired clay retains broad faces and worn corners.
        squared = unit / np.max(np.abs(unit), axis=1, keepdims=True)
        shaped = (squared*.82 + unit*.18) * radial[:, None]
    else:
        # Worn fractures leave broad faces within the rounded outer silhouette.
        # This avoids making every partly buried stone a smooth dome.
        for direction, offset in zip(rng.normal(size=(3, 3)), rng.uniform(.68, .88, 3)):
            direction /= np.linalg.norm(direction)
            shaped -= np.maximum(shaped@direction-offset, 0)[:, None]*direction
    points = shaped * (radius, radius*rng.uniform(.68, 1.02), height*1.45)
    theta = rng.uniform(0, math.tau)
    rotation = np.array([[math.cos(theta), -math.sin(theta), 0], [math.sin(theta), math.cos(theta), 0], [0, 0, 1]])
    points = points@rotation.T + (e, n, ground-height*.45)
    normals = np.zeros_like(points)
    for face in faces:
        a, b, c = points[face]
        value = np.cross(b-a, c-a)
        normals[face] += value
    normals /= np.linalg.norm(normals, axis=1, keepdims=True)
    paint = "lt_tidal_brick" if brick else "lt_tidal_granite"
    # Sample only inside one source block, never across masonry mortar joints.
    du = min(.23, radius*2/78.74)
    dv = min(.16, height*2.9/78.74)
    offset = (rng.uniform(.065, .12), rng.uniform(.04, .07))
    uv = np.column_stack((np.arctan2(unit[:, 1], unit[:, 0])/math.tau+.5,
                          np.arccos(np.clip(unit[:, 2], -1, 1))/math.pi))
    buried = float(np.min(terrain(points[:, 0], points[:, 1]))) - 1.0 if terrain else -math.inf
    for face in faces:
        # Normals still include the closed shape. Omit only faces guaranteed to
        # lie below the surrounding bank, with a full inch of safety margin.
        if np.max(points[face, 2]) < buried:
            continue
        coords = uv[face].copy()
        if np.ptp(coords[:, 0]) > .5:
            coords[coords[:, 0] < .5, 0] += 1
        if brick:
            # A small island inside a single clay brick in the existing scan.
            coords = np.column_stack((.102+coords[:, 0]*.09, 1-(.009+coords[:, 1]*.022)))
        else:
            coords = np.column_stack((offset[0]+coords[:, 0]*du, 1-(offset[1]+coords[:, 1]*dv)))
        model.polygon(paint, points[face], uv=coords, normals=normals[face])


def stone_material_sources():
    result = {}
    for name, color, normal, tint in (
        ("lt_tidal_granite", "masonry/granite_color", "masonry/granite_normal", ".20 .22 .20"),
        ("lt_tidal_brick", "lt_brick_v2_color", "lt_brick_v2_normal", ".30 .24 .18"),
    ):
        result[f"{STONE_RESOURCE}/{name}.vmat"] = f'''// Tools/lowtide_banks.py: worn stone with elevation-dependent moisture.
"Layer0"
{{
    shader "shaders/hc1_lowtide_stone.shader"
    TextureColor "materials/lowtide/{color}.png"
    TextureNormal "materials/lowtide/{normal}.png"
    TextureRoughness "[0.70 0.70 0.70 0]"
    TextureMetalness "materials/default/default_black_mask.tga"
    TextureAmbientOcclusion "materials/default/default_ao.tga"
    g_flTintColor "[{tint}]"
}}
'''
    return result


def write_stone_materials():
    for relative, source in stone_material_sources().items():
        path = K.ASSETS / relative
        K.write_text(path, source)
        metadata(path)
    metadata(K.ASSETS / "shaders/hc1_lowtide_stone.shader")


def configure(model):
    for paint in ("lt_tidal_granite", "lt_tidal_brick"):
        if paint in model.polygons:
            model.material_overrides[paint] = f"{STONE_RESOURCE}/{paint}.vmat"
