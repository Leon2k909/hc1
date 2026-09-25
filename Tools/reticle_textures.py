#!/usr/bin/env python3
"""Draw the gunsmith reticle shapes.

Each reticle gets two images in Assets/gunsmith/reticles/textures/:
  <name>.png          lens mask for shaders/m4_optic_lens.shader: white shape on black, centred on UV (0.5, 0.5),
                      sized in the same lens-UV units as the shader's built-in dot (radius 0.01).
  <name>_preview.png  the same shape filling a small transparent square, for the Customize tab
                      (tinted with the chosen reticle colour there).

Run: python Tools/reticle_textures.py
"""

from __future__ import annotations

import json
import math
import uuid
from pathlib import Path

import numpy as np
from PIL import Image

PROJECT = Path(__file__).resolve().parents[1]
OUT = PROJECT / "Assets" / "gunsmith" / "reticles" / "textures"
MASK_SIZE = 1024
PREVIEW_SIZE = 128
PREVIEW_SPAN = 0.11  # lens-UV width shown across the preview square
SUPERSAMPLE = 4


def segment_distance(x, y, ax, ay, bx, by):
    dx, dy = bx - ax, by - ay
    t = np.clip(((x - ax) * dx + (y - ay) * dy) / (dx * dx + dy * dy), 0.0, 1.0)
    return np.hypot(x - ax - t * dx, y - ay - t * dy)


def dot(x, y, radius):
    return np.hypot(x, y) <= radius


def ring(x, y, radius, half_width):
    return np.abs(np.hypot(x, y) - radius) <= half_width


def bar(x, y, ax, ay, bx, by, half_width):
    return segment_distance(x, y, ax, ay, bx, by) <= half_width


def ellipse(x, y, cx, cy, rx, ry):
    return ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2 <= 1


def polygon(x, y, points):
    """Small vector silhouettes, evaluated at supersampled pixel centres."""
    inside = np.zeros(x.shape, dtype=bool)
    for (ax, ay), (bx, by) in zip(points, points[1:] + points[:1]):
        if ay == by:
            continue
        crosses = ((ay > y) != (by > y)) & (x < (bx - ax) * (y - ay) / (by - ay) + ax)
        inside ^= crosses
    return inside


def star(x, y, outer=0.040, inner=0.018, tips=5):
    points = []
    for i in range(tips * 2):
        angle = -math.pi / 2 + i * math.pi / tips
        radius = outer if i % 2 == 0 else inner
        points.append((math.cos(angle) * radius, math.sin(angle) * radius))
    return polygon(x, y, points)


def skull(x, y):
    head = ellipse(x, y, 0, -0.010, 0.029, 0.030)
    jaw = polygon(x, y, [(-0.020, 0.005), (0.020, 0.005), (0.017, 0.035),
                         (0.009, 0.041), (-0.009, 0.041), (-0.017, 0.035)])
    eyes = ellipse(x, y, -0.011, -0.010, 0.0065, 0.008) | ellipse(x, y, 0.011, -0.010, 0.0065, 0.008)
    nose = polygon(x, y, [(0, 0.000), (-0.005, 0.011), (0.005, 0.011)])
    teeth = ((np.abs(x) < 0.0016) | (np.abs(np.abs(x) - 0.008) < 0.0013)) & (y > 0.025) & (y < 0.039)
    return (head | jaw) & ~(eyes | nose | teeth)


def crossbones(x, y):
    bones = (bar(x, y, -0.040, -0.034, 0.040, 0.036, 0.0035)
             | bar(x, y, 0.040, -0.034, -0.040, 0.036, 0.0035))
    for cx in (-0.039, 0.039):
        for cy in (-0.035, 0.035):
            bones |= ellipse(x, y, cx, cy, 0.006, 0.005)
    return bones | skull(x / 0.70, (y + 0.002) / 0.70)


def alien(x, y):
    head = ellipse(x, y, 0, -0.008, 0.031, 0.034)
    chin = polygon(x, y, [(-0.022, 0.012), (0.022, 0.012), (0, 0.044)])
    eyes = ellipse(x, y, -0.013, 0.001, 0.010, 0.006) | ellipse(x, y, 0.013, 0.001, 0.010, 0.006)
    mouth = bar(x, y, -0.006, 0.024, 0.006, 0.024, 0.0015)
    return (head | chin) & ~(eyes | mouth)


def heart(x, y):
    lobes = ellipse(x, y, -0.013, -0.012, 0.019, 0.020) | ellipse(x, y, 0.013, -0.012, 0.019, 0.020)
    point = polygon(x, y, [(-0.032, -0.010), (0.032, -0.010), (0, 0.041)])
    return lobes | point


def smile(x, y):
    face = ring(x, y, 0.040, 0.0028)
    eyes = dot(x + 0.014, y + 0.010, 0.004) | dot(x - 0.014, y + 0.010, 0.004)
    mouth = ring(x, y - 0.001, 0.024, 0.0028) & (y > 0.006) & (np.abs(x) < 0.022)
    return face | eyes | mouth


def crown(x, y):
    outline = polygon(x, y, [(-0.038, 0.020), (-0.038, -0.027), (-0.018, -0.007),
                             (0, -0.037), (0.018, -0.007), (0.038, -0.027), (0.038, 0.020)])
    base = polygon(x, y, [(-0.038, 0.020), (0.038, 0.020), (0.038, 0.032), (-0.038, 0.032)])
    gems = dot(x + 0.020, y - 0.010, 0.003) | dot(x, y - 0.010, 0.003) | dot(x - 0.020, y - 0.010, 0.003)
    return outline | base | gems


def paw(x, y):
    pad = ellipse(x, y, 0, 0.018, 0.022, 0.018)
    toes = (ellipse(x, y, -0.026, -0.008, 0.007, 0.010)
            | ellipse(x, y, -0.009, -0.019, 0.007, 0.010)
            | ellipse(x, y, 0.009, -0.019, 0.007, 0.010)
            | ellipse(x, y, 0.026, -0.008, 0.007, 0.010))
    return pad | toes


def flower(x, y):
    petals = np.zeros(x.shape, dtype=bool)
    for i in range(6):
        angle = i * math.pi / 3
        petals |= ellipse(x, y, math.cos(angle) * 0.023, math.sin(angle) * 0.023, 0.013, 0.013)
    return petals | dot(x, y, 0.008)


# Coordinates are lens UV relative to the centre; +y is down the texture (towards the bottom of the sight).
SHAPES = {
    "red_dot": lambda x, y: dot(x, y, 0.010),
    "circle_dot": lambda x, y: ring(x, y, 0.042, 0.0028) | dot(x, y, 0.0055),
    "cross": lambda x, y: (
        bar(x, y, 0.012, 0, 0.045, 0, 0.0022) | bar(x, y, -0.012, 0, -0.045, 0, 0.0022)
        | bar(x, y, 0, 0.012, 0, 0.045, 0.0022) | bar(x, y, 0, -0.012, 0, -0.045, 0.0022)
        | dot(x, y, 0.0045)),
    # The tip sits on the point of aim, the arms run down and out.
    "chevron": lambda x, y: bar(x, y, 0, 0, -0.030, 0.026, 0.0030) | bar(x, y, 0, 0, 0.030, 0.026, 0.0030),
    "micro_dot": lambda x, y: dot(x, y, 0.005),
    "hollow_dot": lambda x, y: ring(x, y, 0.011, 0.0025),
    "segmented_ring": lambda x, y: (ring(x, y, 0.041, 0.003) & (np.abs(x) > 0.008) & (np.abs(y) > 0.008)) | dot(x, y, 0.004),
    "circle_cross": lambda x, y: (ring(x, y, 0.036, 0.0025)
        | bar(x, y, -0.048, 0, -0.012, 0, 0.002) | bar(x, y, 0.012, 0, 0.048, 0, 0.002)
        | bar(x, y, 0, -0.048, 0, -0.012, 0.002) | bar(x, y, 0, 0.012, 0, 0.048, 0.002)),
    "t_post": lambda x, y: (bar(x, y, -0.030, -0.025, 0.030, -0.025, 0.0028)
        | bar(x, y, 0, -0.025, 0, 0.012, 0.0028) | dot(x, y, 0.004)),
    "german_four": lambda x, y: (bar(x, y, -0.048, 0, -0.011, 0, 0.003)
        | bar(x, y, 0.011, 0, 0.048, 0, 0.003) | bar(x, y, 0, 0.011, 0, 0.049, 0.003)
        | dot(x, y, 0.0035)),
    "triangle": lambda x, y: (polygon(x, y, [(0, -0.041), (-0.036, 0.029), (0.036, 0.029)])
        & ~polygon(x, y, [(0, -0.030), (-0.026, 0.023), (0.026, 0.023)])) | dot(x, y, 0.004),
    "diamond": lambda x, y: ((np.abs(x) + np.abs(y) >= 0.029)
        & (np.abs(x) + np.abs(y) <= 0.035)) | dot(x, y, 0.004),
    "double_chevron": lambda x, y: (bar(x, y, 0, -0.026, -0.030, -0.001, 0.0028)
        | bar(x, y, 0, -0.026, 0.030, -0.001, 0.0028)
        | bar(x, y, 0, 0.003, -0.026, 0.027, 0.0028)
        | bar(x, y, 0, 0.003, 0.026, 0.027, 0.0028)),
    "horseshoe": lambda x, y: (ring(x, y, 0.039, 0.003) & (y > -0.024)) | dot(x, y, 0.0045),
    "mil_dot": lambda x, y: (bar(x, y, -0.048, 0, -0.008, 0, 0.0017)
        | bar(x, y, 0.008, 0, 0.048, 0, 0.0017)
        | bar(x, y, 0, -0.048, 0, -0.008, 0.0017)
        | bar(x, y, 0, 0.008, 0, 0.048, 0.0017)
        | dot(x, y, 0.0035) | dot(x + 0.026, y, 0.003)
        | dot(x - 0.026, y, 0.003) | dot(x, y + 0.026, 0.003)
        | dot(x, y - 0.026, 0.003)),
    "range_ladder": lambda x, y: (dot(x, y, 0.0045)
        | bar(x, y, 0, 0.008, 0, 0.048, 0.002)
        | bar(x, y, -0.010, 0.018, 0.010, 0.018, 0.002)
        | bar(x, y, -0.017, 0.031, 0.017, 0.031, 0.002)
        | bar(x, y, -0.025, 0.044, 0.025, 0.044, 0.002)),
    "bullseye": lambda x, y: ring(x, y, 0.021, 0.0025) | ring(x, y, 0.043, 0.0025) | dot(x, y, 0.004),
    "brackets": lambda x, y: (dot(x, y, 0.0045)
        | bar(x, y, -0.041, -0.030, -0.041, 0.030, 0.0025)
        | bar(x, y, -0.041, -0.030, -0.025, -0.030, 0.0025)
        | bar(x, y, -0.041, 0.030, -0.025, 0.030, 0.0025)
        | bar(x, y, 0.041, -0.030, 0.041, 0.030, 0.0025)
        | bar(x, y, 0.025, -0.030, 0.041, -0.030, 0.0025)
        | bar(x, y, 0.025, 0.030, 0.041, 0.030, 0.0025)),
    "quad_dots": lambda x, y: (dot(x, y, 0.004)
        | dot(x + 0.029, y, 0.0045) | dot(x - 0.029, y, 0.0045)
        | dot(x, y + 0.029, 0.0045) | dot(x, y - 0.029, 0.0045)),
    "split_cross": lambda x, y: (bar(x, y, -0.048, 0, -0.012, 0, 0.0028)
        | bar(x, y, 0.012, 0, 0.048, 0, 0.0028)
        | bar(x, y, 0, -0.048, 0, -0.012, 0.0028)
        | bar(x, y, 0, 0.012, 0, 0.048, 0.0028)),
    "skull": skull,
    "crossbones": crossbones,
    "alien": alien,
    "heart": heart,
    "smile": smile,
    "star": star,
    "lightning": lambda x, y: polygon(x, y, [(-0.007, -0.045), (0.022, -0.045),
        (0.004, -0.008), (0.025, -0.008), (-0.020, 0.046), (-0.009, 0.010), (-0.028, 0.010)]),
    "crown": crown,
    "paw": paw,
    "flower": flower,
}


LABELS = {
    "micro_dot": "Micro Dot", "hollow_dot": "Hollow Dot", "segmented_ring": "Broken Ring",
    "circle_cross": "Circle Cross", "t_post": "T-Post", "german_four": "German #4",
    "triangle": "Triangle", "diamond": "Diamond", "double_chevron": "Double Chevron",
    "horseshoe": "Horseshoe", "mil_dot": "Mil-Dot", "range_ladder": "Range Ladder",
    "bullseye": "Bullseye", "brackets": "Brackets", "quad_dots": "Quad Dots",
    "split_cross": "Split Cross", "skull": "Skull", "crossbones": "Crossbones",
    "alien": "Alien", "heart": "Heart", "smile": "Smiley", "star": "Star",
    "lightning": "Lightning", "crown": "Crown", "paw": "Paw Print", "flower": "Flower",
}


def rasterise(shape, size: int, span: float) -> np.ndarray:
    """Coverage (0..1) of the shape over a size x size grid spanning `span` lens-UV units, centred."""
    # The lens marks occupy only the central ~10% of a 1024px mask. Rasterising
    # that square keeps supersampling cheap while retaining the full black lens UV.
    margin = math.ceil(0.07 / span * size) + 1 if size == MASK_SIZE else size // 2
    low, high = size // 2 - margin, size // 2 + margin
    sample_indices = np.arange(low * SUPERSAMPLE, high * SUPERSAMPLE)
    axis = (sample_indices + 0.5) / (size * SUPERSAMPLE) * span - span / 2
    x, y = np.meshgrid(axis, axis)
    hit = shape(x, y).astype(np.float32)
    coverage = hit.reshape(high - low, SUPERSAMPLE, high - low, SUPERSAMPLE).mean(axis=(1, 3))
    image = np.zeros((size, size), dtype=np.float32)
    image[low:high, low:high] = coverage
    return image


def write_meta(path: Path) -> None:
    meta = path.with_name(path.name + ".meta")
    if not meta.exists():
        guid = uuid.uuid5(uuid.NAMESPACE_URL, f"hc1-reticle/{path.relative_to(PROJECT).as_posix()}")
        meta.write_text(json.dumps({"guid": str(guid)}, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for name, shape in SHAPES.items():
        coverage = rasterise(shape, MASK_SIZE, 1.0)
        grey = (coverage * 255).round().astype(np.uint8)
        mask_path = OUT / f"{name}.png"
        Image.fromarray(np.dstack([grey, grey, grey]), "RGB").save(mask_path, optimize=True)
        write_meta(mask_path)

        preview = rasterise(shape, PREVIEW_SIZE, PREVIEW_SPAN)
        white = np.full((PREVIEW_SIZE, PREVIEW_SIZE), 255, np.uint8)
        alpha = (preview * 255).round().astype(np.uint8)
        preview_path = OUT / f"{name}_preview.png"
        Image.fromarray(np.dstack([white, white, white, alpha]), "RGBA").save(preview_path, optimize=True)
        write_meta(preview_path)

        if name in LABELS:
            resource_path = OUT.parent / f"reticle_{name}.gnsmth"
            resource = {
                "Name": LABELS[name],
                "Description": "Custom optic reticle",
                "Category": "Reticle",
                "CamoTexture": f"gunsmith/reticles/textures/{name}.png",
                "ReticlePreview": f"gunsmith/reticles/textures/{name}_preview.png",
                "RequiredLevel": 1,
                "__version": 0,
            }
            resource_path.write_text(json.dumps(resource, indent=2) + "\n", encoding="utf-8")
            write_meta(resource_path)
    print(f"wrote {len(SHAPES)} reticles ({len(LABELS)} new) to {OUT}")


if __name__ == "__main__":
    main()
