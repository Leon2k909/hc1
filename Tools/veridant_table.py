"""A honed stone bistro top: a flat slab with a small eased edge, in plan inches."""
import math

import numpy as np

from riverdale_parts import UP, card, cylinder, lathe, v

PAINT = "vr_table_honed"
MATERIAL = "materials/veridant/table-v2/honed.vmat"
SIDES = 128
RADIUS = 15.0
BOTTOM = 28.0
TOP = 29.5
EASE = .12  # 3 mm edge easing; the 38 mm slab keeps its flat, straight side.


def legacy_pedestal(model, centre, z0=0.0):
    cylinder(model, centre, 9, z0, z0+1, "vr_steel", 12, top="vr_steel")
    cylinder(model, centre, 1.2, z0+1, z0+28, "vr_steel", 8)


def build_pedestal_into(model, centre, z0=0.0):
    lathe(model, centre, [(9,z0),(9,z0+.72),(8.88,z0+.94),(8.8,z0+1)],
          "vr_steel", sides=64, cap="vr_steel")
    cylinder(model, centre, 1.2, z0+1, z0+28, "vr_steel", 32)
    model.tile_overrides.setdefault("vr_steel", 64.0)


def legacy_top(model, centre, z0=0.0):
    cylinder(model, centre, RADIUS, z0 + BOTTOM, z0 + TOP, "vr_stone_light", 16,
             top="vr_stone_light", bottom="vr_steel")


def build_top_into(model, centre, z0=0.0):
    origin = v(centre[0], centre[1], z0)
    directions = [v(math.cos(2 * math.pi * k / SIDES), math.sin(2 * math.pi * k / SIDES), 0)
                  for k in range(SIDES)]
    # Each quarter circle meets the cap and straight side tangentially. No dome,
    # random dents, wobbly silhouette, or broad rounded furniture edge.
    profile = []
    for angle in np.linspace(-math.pi / 2, 0, 5):
        profile.append((RADIUS - EASE + EASE * math.cos(angle),
                        BOTTOM + EASE + EASE * math.sin(angle), math.cos(angle), math.sin(angle)))
    for angle in np.linspace(0, math.pi / 2, 5):
        profile.append((RADIUS - EASE + EASE * math.cos(angle),
                        TOP - EASE + EASE * math.sin(angle), math.cos(angle), math.sin(angle)))
    for j, (a, b) in enumerate(zip(profile, profile[1:])):
        for k in range(SIDES):
            q = (k + 1) % SIDES
            points = [origin + directions[k] * a[0] + UP * a[1],
                      origin + directions[q] * a[0] + UP * a[1],
                      origin + directions[q] * b[0] + UP * b[1],
                      origin + directions[k] * b[0] + UP * b[1]]
            normals = [directions[k] * a[2] + UP * a[3], directions[q] * a[2] + UP * a[3],
                       directions[q] * b[2] + UP * b[3], directions[k] * b[2] + UP * b[3]]
            # The narrow stone edge has its own continuous strip, inside one slab
            # of the existing texture. Never sample that texture's grout lines.
            u0, u1 = .30 + .40 * k / SIDES, .30 + .40 * (k + 1) / SIDES
            va, vb = .75 + (a[1] - BOTTOM) / 96, .75 + (b[1] - BOTTOM) / 96
            card(model, PAINT, points, sum(normals), normals=normals,
                 uv=[(u0, va), (u1, va), (u1, vb), (u0, vb)])
    ring = [origin + d * (RADIUS - EASE) + UP * TOP for d in directions]
    # 30 inches from one 48-inch limestone panel: continuous grain, true scale.
    # The OBJ importer flips V: source .75 becomes engine .25, the panel with
    # vertical joints at U=.25/.75 rather than the lower row's joint at U=.5.
    uv = [(.5 + (p[0] - origin[0]) / 96, .75 + (p[1] - origin[1]) / 96) for p in ring]
    card(model, PAINT, ring, UP, uv=uv)
    bottom = [origin + d * (RADIUS - EASE) + UP * BOTTOM for d in directions]
    card(model, "vr_steel", bottom, -UP)
    model.material_overrides[PAINT] = MATERIAL
    model.tile_overrides[PAINT] = 96.0
    model.tile_overrides.setdefault("vr_steel", 64.0)
