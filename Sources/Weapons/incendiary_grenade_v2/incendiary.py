"""Incendiary grenade v2: build, bake and export, on the smoke grenade v2's pipeline. See adapt.py.

blender -b --factory-startup -t 4 --python incendiary.py -- <work dir> <project root> <build|bake|export> ...

A generic fictional incendiary can, the old one's size and shape on its origin and axes, with its three body groups in order
(grenade, spoon, pin), so the prefabs' mask of 11 still shows all three. It differs from the smoke can in having no vents: its top is
sealed but for a filler plug, and two rolled beads stiffen the wall. Outside only: there is nothing inside it. Inches, engine axes.
"""
import os
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import adapt  # noqa: E402

BODY = '''def body():
    b = piece("grenade", PAINT, 3, bevel=0.005, name="can")
    # The can's underside rolled up into its bottom chime, the wall with its two beads, the top chime and the plate the fuze stands on.
    profile = [(0.0, 0.17), (1.02, 0.17), (1.06, 0.13), (1.09, 0.035), (1.14, 0.0), (1.26, 0.0), (1.315, 0.03), (1.324, 0.11), (1.305, 0.175), (1.285, 0.205)]
    profile += [(1.285, 1.44), (1.297, 1.47), (1.302, 1.52), (1.297, 1.57), (1.285, 1.6)]
    profile += [(1.285, 3.34), (1.297, 3.37), (1.302, 3.42), (1.297, 3.47), (1.285, 3.5)]
    profile += [(1.285, 4.34), (1.305, 4.375), (1.324, 4.44), (1.315, 4.54), (1.26, 4.585), (1.16, 4.585), (1.1, 4.53), (1.065, 4.45), (1.0, 4.42), (0.66, 4.43), (0.58, 4.47), (0.5, 4.48)]
    lathe(b, profile, 60)
    # The filler plug, screwed in and painted over, and two pressed dimples balancing it.
    at = (0.82 * math.cos(math.radians(40)), 0.82 * math.sin(math.radians(40)), 4.415)
    lathe(piece("grenade", OXIDE, 1, bevel=0.004, name="filler plug"), [(0.17, 0.0), (0.17, 0.03), (0.14, 0.052), (0.0, 0.052)], 18, frame(at, (0, 0, 1)))
    for deg in (160, 280):
        at = (0.82 * math.cos(math.radians(deg)), 0.82 * math.sin(math.radians(deg)), 4.418)
        lathe(piece("grenade", PAINT, 1, name="dimple"), [(0.1, 0.0), (0.082, 0.012), (0.04, 0.02), (0.0, 0.022)], 14, frame(at, (0, 0, 1)))
'''

adapt.run(
    "smoke.py",
    [
        ('FOLDER = "weapons/throwable/m18_smoke_grenade/smoke_grenade_v2"', 'FOLDER = "weapons/throwable/molotov_cocktail/incendiary_grenade_v2"'),
        ('"M18_Smoke_Grenade", "smoke_grenade_v2"', '"Molotov_Cocktail", "incendiary_grenade_v2"'),
        ('NAME = "smoke_grenade"', 'NAME = "incendiary_grenade"'),
        ("Sources/Weapons/smoke_grenade_v2/smoke.py", "Sources/Weapons/incendiary_grenade_v2/incendiary.py"),
    ],
    os.path.abspath(__file__),
    patterns=[(r"def body\(\):.*?(?=\n\ndef fuze_body)", BODY.rstrip())],
)
