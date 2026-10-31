"""Paint the incendiary grenade's maps, on the smoke grenade v2's recipe: python paint_incendiary.py <work dir> <output dir>

Brick red enamel, so it's still the red can players know, with black lettering and a black band, a charcoal lever, and no vents or
soot since it's sealed. All lettering is invented: the old can said "AN-M14" and "TH3", real designations, and those are gone.
"""
import os
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import adapt  # noqa: E402

adapt.run(
    "paint_smoke.py",
    [
        ('NAME = "smoke_grenade"', 'NAME = "incendiary_grenade"'),
        ('stencil_image(["SMOKE", "SCREENING  K-44"]', 'stencil_image(["INCENDIARY", "THERMITE  K-52"]'),
        ('stencil_image(["WHITE  HC", "LOT RZD 26-0418"]', 'stencil_image(["KEEP CLEAR WHEN LIT", "LOT RZD 26-0421"]'),
        ('stencil_image(["RZD K-44", "26-0418"]', 'stencil_image(["RZD K-52", "26-0421"]'),
        # Plain letters: the bridge through the middle of a stencil makes small words hard to read on a curve.
        ("(1600, 760), bridge=True", "(1600, 760), bridge=False"),
        # Pale dust on red goes pink, so there's less of it, and fewer bright dashes along the lever's edge.
        ("dust = np.clip(settled * 0.2 + gathered * 0.42, 0, 0.7)", "dust = np.clip(settled * 0.08 + gathered * 0.3, 0, 0.5)"),
        ("edge * (0.3 + 0.8 * smooth(0.3, 0.72, mid * 0.5 + fine * 0.5))", "edge * (0.2 + 0.72 * smooth(0.3, 0.72, mid * 0.5 + fine * 0.5))"),
        # Sealed: no white top, no vents, no soot round them.
        ("white_top = top_plate.astype(np.float32)", "white_top = top_plate.astype(np.float32) * 0"),
        ("for k in range(4):\n    a = math.radians(45 + 90 * k)\n    vent_d =", "for k in range(0):\n    a = math.radians(45 + 90 * k)\n    vent_d ="),
        # Brick red, as the old can was. Lettering and the band in black.
        ("olive = mix(rgb(82, 78, 50), rgb(100, 94, 60), smooth(0.25, 0.75, big))", "olive = mix(rgb(100, 38, 28), rgb(122, 50, 36), smooth(0.25, 0.75, big))"),
        (
            "olive = np.where(lever[..., None], olive * np.array((1.05, 1.0, 0.9), np.float32) * 0.94, olive)",
            "olive = np.where(lever[..., None], rgb(50, 50, 47) * (0.86 + 0.28 * mid[..., None]), olive)",
        ),
        ("white = mix(rgb(198, 196, 180), rgb(182, 180, 164), smooth(0.3, 0.7, big * 0.6 + mid * 0.4))", "white = mix(rgb(24, 23, 21), rgb(36, 33, 30), smooth(0.3, 0.7, big * 0.6 + mid * 0.4))"),
        ("yellow = mix(rgb(168, 146, 66), rgb(140, 122, 60), smooth(0.3, 0.7, mid))", "yellow = mix(rgb(20, 19, 18), rgb(32, 29, 26), smooth(0.3, 0.7, mid))"),
        ('print("smoke grenade painted", flush=True)', 'print("incendiary grenade painted", flush=True)'),
    ],
    os.path.abspath(__file__),
)
