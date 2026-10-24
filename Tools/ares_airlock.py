"""Ares' sealed pressure doors: drawn detail inside the existing hatch footprint and collision envelope."""
import math

import numpy as np

import ares_materials as AM
from boxyard_map import Frame, lathe

SHELL, METAL, DARK = "ar_ext_shell", "ar_ext_metal", "ar_ext_dark"
SEAL, ACCENT, HARDWARE = "ar_rubber", "ar_ext_ochre", "ar_rover_white"


def octagon(half, bottom, top, corner):
    return [(-half + corner, bottom), (half - corner, bottom), (half, bottom + corner),
            (half, top - corner), (half - corner, top), (-half + corner, top),
            (-half, top - corner), (-half, bottom + corner)]


def rectangle(x0, x1, z0, z1, corner=2):
    mid = (x0 + x1) / 2
    return [(x + mid, z) for x, z in octagon((x1 - x0) / 2, z0, z1, corner)]


def face(model, frame, points, depth, paint):
    frame.quad(model, paint, [(x, depth, z) for x, z in points], (0, -1, 0))


def rim(model, frame, outer, inner, outside_depth, inside_depth, paint):
    if len(outer) != len(inner):
        raise ValueError("A pressure-door bevel needs matching profiles")
    for i, (a, c) in enumerate(zip(outer, inner)):
        b, d = outer[(i + 1) % len(outer)], inner[(i + 1) % len(inner)]
        frame.quad(model, paint, [(a[0], outside_depth, a[1]), (b[0], outside_depth, b[1]),
                                 (d[0], inside_depth, d[1]), (c[0], inside_depth, c[1])], (0, -1, 0))


def edges(model, frame, points, back, front, paint):
    centre = np.array(points).mean(axis=0)
    for i, a in enumerate(points):
        b = points[(i + 1) % len(points)]
        outward = ((a[0] + b[0]) / 2 - centre[0], 0, (a[1] + b[1]) / 2 - centre[1])
        frame.quad(model, paint, [(a[0], back, a[1]), (b[0], back, b[1]),
                                 (b[0], front, b[1]), (a[0], front, a[1])], outward)


def plate(model, frame, x0, x1, z0, z1, back, front, paint=METAL, corner=2):
    profile = rectangle(x0, x1, z0, z1, corner)
    edges(model, frame, profile, back, front, paint)
    face(model, frame, profile, front, paint)


def bolt(model, frame, x, z, back=-9.5, front=-11.1, radius=1.2):
    frame.rod(model, (x, back, z), (x, front, z), radius, HARDWARE, sides=6)
    frame.rod(model, (x, front - .03, z), (x, front - .15, z), radius * .38, DARK, sides=6)


def pressure_door(model, centre, facing, width=180, height=180, border=16):
    """Front is local -Y, controls stay at human height, and no detail projects beyond the existing 12-inch collider."""
    frame = Frame(centre[0], centre[1], math.degrees(math.atan2(facing[1], facing[0])) + 90, centre[2])
    half = width / 2
    outer = octagon(half + border, 0, height + border, 15)
    lip = octagon(half + border - 2.5, 2.5, height + border - 2.5, 13)
    opening = octagon(half - 2, 6, height + 1, 14)
    gasket = octagon(half - 5, 9, height - 2, 12)
    edges(model, frame, outer, -.1, -6.5, DARK)
    rim(model, frame, outer, lip, -6.5, -9.4, METAL)
    rim(model, frame, lip, opening, -9.4, -9.4, METAL)
    rim(model, frame, opening, gasket, -9.4, -4.5, HARDWARE)
    face(model, frame, gasket, -4.3, SEAL)

    # Each pressure leaf has clipped outside corners, a raised welded rim and a genuinely recessed face.
    x0, x1, z0, z1, cut = -half + 8, -.9, 12, height - 7, 11
    left = [(x0 + cut, z0), (x1, z0), (x1, z1), (x0 + cut, z1), (x0, z1 - cut), (x0, z0 + cut)]
    inner = [(x0 + cut + 1, z0 + 3), (x1 - 3, z0 + 3), (x1 - 3, z1 - 3),
             (x0 + cut + 1, z1 - 3), (x0 + 3, z1 - cut - 1), (x0 + 3, z0 + cut + 1)]
    for side in (-1, 1):
        # The base polygon is the left leaf; mirror it for the right while retaining matching bevel vertices.
        sign = -side
        boundary = [(x * sign, z) for x, z in left]
        inset = [(x * sign, z) for x, z in inner]
        edges(model, frame, boundary, -4.6, -8.0, METAL)
        rim(model, frame, boundary, inset, -8.0, -6.8, METAL)
        face(model, frame, inset, -6.8, SHELL)
        lo, hi = sorted((side * (half - 17), side * 9))
        plate(model, frame, lo, hi, 17, 36, -7.1, -8.4, METAL, 3)
        for x in (lo + 4, hi - 4):
            bolt(model, frame, x, 22, -8.45, -9.1, .7)
        # A narrow ochre reinforcement edge gives each leaf a readable identity without a striped wallpaper frame.
        edge_x = side * (half - 13)
        plate(model, frame, edge_x - 1.5, edge_x + 1.5, 44, height - 28, -7.2, -8.3, ACCENT, .6)
        # Stamped upper panel breaks up the large shell while leaving the lower controls at human scale.
        patch = rectangle(lo + 4, hi - 4, 111, height - 22, 5)
        smaller = rectangle(lo + 6.5, hi - 6.5, 113.5, height - 24.5, 4)
        rim(model, frame, patch, smaller, -7.75, -7.0, METAL)
        face(model, frame, smaller, -7.0, SHELL)

    # Six locking dogs visibly clamp the leaves into the jamb; hex pivots are separate from the painted shell.
    for side in (-1, 1):
        for z in (43, height * .52, height - 28):
            pivot = side * (half + 5)
            end = side * (half - 13)
            lo, hi = sorted((pivot, end))
            plate(model, frame, lo - 2, hi + 2, z - 3, z + 3, -9.5, -10.7, HARDWARE, 1.8)
            bolt(model, frame, pivot, z, -10.75, -11.5, 2.1)
        for z in (17, height + 7):
            bolt(model, frame, side * (half + border * .45), z, -9.5, -10.5, 1.3)
        plate(model, frame, side * (half + 7) - 3.5, side * (half + 7) + 3.5,
              22, 35, -9.5, -9.9, ACCENT, 1)

    # Manual release wheel, on the left leaf at chest height; shallow hardware stays within the old collision box.
    wheel_x, wheel_z = -min(half * .45, 38), 58
    plate(model, frame, wheel_x - 12, wheel_x + 12, wheel_z - 13, wheel_z + 13, -7.0, -8.5, DARK, 4)
    frame.rod(model, (wheel_x, -8.6, wheel_z), (wheel_x, -11.2, wheel_z), 2.5, HARDWARE, sides=12)
    lathe(model, frame.p(wheel_x, -10.6, wheel_z), frame.v(0, -1, 0),
          [(7.7, -.65), (9, -.65), (9, .65), (7.7, .65), (7.7, -.65)], HARDWARE, sides=24)
    for i in range(3):
        angle = i * math.tau / 3
        frame.rod(model, (wheel_x, -10.6, wheel_z),
                  (wheel_x + 7.8 * math.cos(angle), -10.6, wheel_z + 7.8 * math.sin(angle)), .65, HARDWARE)
    frame.rod(model, (wheel_x, -11.25, wheel_z), (wheel_x, -11.6, wheel_z), 1.5, ACCENT, sides=12)

    # Armoured inspection port on the other leaf and a compact pressure/control unit on its jamb.
    window_x = min(half * .65, 90)
    plate(model, frame, window_x - 15, window_x + 15, 57, 82, -7, -8.6, DARK, 4)
    plate(model, frame, window_x - 11, window_x + 11, 61, 78, -8.65, -8.9, "ar_ext_glazing", 2)
    for x in (window_x - 12, window_x + 12):
        for z in (60, 79):
            bolt(model, frame, x, z, -8.9, -9.4, .7)
    panel_x = max(16, half * .25)
    plate(model, frame, panel_x - 8, panel_x + 8, 39, 80, -8, -11.1, DARK, 2)
    uv = [AM.region_uv(AM.SCREEN, AM.SCREEN_ATLAS, "screen3", s, t)
          for s, t in ((0, 0), (1, 0), (1, 1), (0, 1))]
    frame.quad(model, "ar_screens", [(panel_x - 6.5, -11.25, 57), (panel_x + 6.5, -11.25, 57),
                                     (panel_x + 6.5, -11.25, 70), (panel_x - 6.5, -11.25, 70)],
               (0, -1, 0), uv=uv)
    for i in range(3):
        x = panel_x - 4.5 + i * 4.5
        frame.rod(model, (x, -11.15, 47), (x, -11.7, 47), 1.1,
                  ACCENT if i == 2 else HARDWARE, sides=10)
    frame.box(model, panel_x - 4, panel_x + 4, -11.45, -11.3, 75, 76.5, "ar_ext_lamp")

    # A metal threshold with one restrained warning strip replaces the old all-over hazard rectangle.
    frame.box(model, -half - 7, half + 7, -11.7, -8.2, 0, 5.5, METAL)
    frame.quad(model, "ar_hazard", [(-half + 12, -11.8, 1), (half - 12, -11.8, 1),
                                     (half - 12, -11.8, 3.5), (-half + 12, -11.8, 3.5)], (0, -1, 0))
