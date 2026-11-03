"""Riverdale ARM-04: dedicated instrument graphics and serviceable wall enclosure, in inches."""
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import riverdale_parts as P

FOLDER = "materials/riverdale/radiation_monitor_v2"
SHELL, SEAL, STEEL, PANEL, LCD, SIGN, AMBER, GREEN = (
    "rv_arm_" + s for s in ("shell", "seal", "steel", "panel", "lcd", "sign", "amber", "green"))
MATERIALS = (SHELL, SEAL, STEEL, PANEL, LCD, SIGN, AMBER, GREEN)
UV = [(0, 0), (1, 0), (1, 1), (0, 1)]


def artwork():
    """Graphics follow physical panel coordinates; no shared low-resolution atlas."""
    def font(size, mono=False, bold=True):
        name = "consolab.ttf" if mono else ("arialbd.ttf" if bold else "arial.ttf")
        return ImageFont.truetype(str(Path("C:/Windows/Fonts") / name), size)

    panel = Image.new("RGB", (1536, 1024), (43, 56, 60))
    d = ImageDraw.Draw(panel)
    def at(x, z):
        return ((x + 6.225) / 12.45 * 1536, (9.275 - z) / 8.35 * 1024)
    def text(x, z, words, size, fill=(206, 214, 207), anchor="lm", mono=False):
        d.text(at(x, z), words, font=font(size, mono), fill=fill, anchor=anchor)
    text(-5.45, 8.55, "AREA RADIATION MONITOR", 47)
    text(5.45, 8.03, "ARM-04", 30, (145, 165, 163), "rm", True)
    d.line((*at(-5.45, 7.98), *at(2.5, 7.98)), fill=(99, 118, 120), width=2)
    text(4.28, 7.35, "SYSTEM", 24, anchor="mm")
    text(4.28, 5.92, "NORMAL", 25, (169, 199, 174), "mm")
    text(4.28, 3.82, "ALARM", 25, anchor="mm")
    text(-4.2, 2.68, "LAMP TEST", 24, anchor="mm")
    text(-1.6, 2.68, "ACK / RESET", 24, anchor="mm")
    d.rectangle((*at(.6, 2.62), *at(5.4, 1.25)), fill=(166, 176, 167))
    text(.82, 2.30, "RIVERDALE NUCLEAR", 25, (33, 49, 49))
    text(.82, 1.85, "24V DC   /   IP65", 23, (41, 57, 55), mono=True)
    text(.82, 1.45, "S/N 004-0716", 19, (56, 69, 64), mono=True)

    lcd = Image.new("RGB", (1536, 704), (24, 43, 40))
    d = ImageDraw.Draw(lcd)
    d.text((66, 49), "FUEL HANDLING  /  AREA 04", font=font(39, True), fill=(132, 175, 151))
    d.line((66, 123, 1470, 123), fill=(64, 96, 79), width=3)
    d.text((62, 178), "0.12", font=font(227, True), fill=(184, 214, 164), anchor="lt")
    d.text((960, 304), "µSv/h", font=font(91, True), fill=(150, 188, 149), anchor="lm")
    d.text((69, 459), "DOSE RATE", font=font(37, True), fill=(127, 166, 140))
    for i in range(45):
        x = 70 + i * 31
        d.rectangle((x, 537, x + 20, 570), fill=(131, 173, 130) if i < 5 else (43, 68, 56))
    d.text((70, 620), "BACKGROUND", font=font(34, True), fill=(139, 181, 148))
    d.text((1460, 620), "DETECTOR OK", font=font(34, True), fill=(139, 181, 148), anchor="rt")

    sign = Image.new("RGB", (2048, 410), (197, 156, 47))
    d = ImageDraw.Draw(sign)
    d.rounded_rectangle((22, 22, 2026, 388), radius=28, outline=(50, 48, 32), width=5)
    # Standard trefoil, in the plant's existing magenta/yellow convention.
    cx, cy, r = 228, 205, 139
    for angle in (-90, 30, 150):
        d.pieslice((cx-r, cy-r, cx+r, cy+r), angle-27, angle+27, fill=(74, 38, 58))
    d.ellipse((cx-50, cy-50, cx+50, cy+50), fill=(197, 156, 47))
    d.ellipse((cx-28, cy-28, cx+28, cy+28), fill=(74, 38, 58))
    d.text((441, 107), "AREA RADIATION MONITOR", font=font(86), fill=(33, 36, 31), anchor="lt")
    d.text((445, 249), "ARM-04  /  CONTINUOUS AREA MONITORING", font=font(43, True), fill=(48, 47, 33), anchor="lt")

    rng = np.random.default_rng(704)
    result = {}
    for name, picture in ((PANEL, panel), (LCD, lcd), (SIGN, sign)):
        a = np.asarray(picture, float).copy()
        h, w = a.shape[:2]
        yy, xx = np.mgrid[:h, :w]
        edge = np.minimum.reduce((xx, w-1-xx, yy, h-1-yy))
        a *= (1 - .055 * np.exp(-edge / 10))[..., None]
        a += rng.normal(0, .48, (h, w, 1))
        result[name] = Image.fromarray(np.uint8(np.clip(a, 0, 255)))
    return result


def monitor(detail, fine, face, s, z):
    """Same anchors and silhouette as the original; all geometry is decorative."""
    for model in (detail, fine):
        for material in MATERIALS:
            model.material_overrides[material] = f"{FOLDER}/{material}.vmat"
            model.tile_overrides[material] = 6.0
    def point(x, zz, depth):
        return face.p(s + x, z + zz, depth)
    axes = (face.out, face.a, P.UP)
    def box(x, zz, depth, width, height, thick, mat, bevel=.10):
        P.bevel_box(detail, point(x, zz, depth), axes, (thick, width, height), mat, bevel)
    def quad(mat, x, zz, depth, width, height):
        P.quad(fine, mat, point(x, zz, depth), face.a, P.UP, width, height, UV)
    def turned(x, zz, depth, profile, mat, sides=16, axis=None):
        P.lathe_axis(detail, point(x, zz, depth), face.out if axis is None else axis, profile, mat, sides, cap=mat)
    def screw(x, zz, depth, radius=.19):
        turned(x, zz, depth, [(radius, 0), (radius, .065), (radius*.72, .11), (0, .11)], STEEL, 12)
        P.quad(fine, SEAL, point(x, zz, depth+.113), face.a, P.UP, radius*1.35, .045)

    # Wall standoffs, cast back enclosure and a continuous lid gasket.
    for x in (-5.65, 5.65):
        box(x, 5, .43, 1.2, 9.1, .75, STEEL, .13)
    box(0, 5, 2.35, 14, 10, 3.45, SHELL, .33)
    box(0, 5, 4.10, 13.94, 9.94, .16, SEAL, .07)
    box(0, 5, 4.52, 14.0, 10.0, .74, SHELL, .28)
    # Dark laminated face with a thin bright metal reveal.
    box(0, 5.1, 4.91, 12.68, 8.58, .12, STEEL, .055)
    quad(PANEL, 0, 5.1, 4.978, 12.45, 8.35)
    for x in (-6.48, 6.48):
        for zz in (.57, 9.43):
            screw(x, zz, 4.91, .19)

    # The LCD sits behind a raised four-sided moulded bezel.
    box(-1.47, 5.70, 5.04, 8.40, 4.26, .13, SEAL, .055)
    quad(LCD, -1.47, 5.70, 5.116, 7.65, 3.51)
    for x in (-5.49, 2.55):
        box(x, 5.7, 5.18, .36, 4.12, .38, SEAL, .11)
    for zz in (3.77, 7.63):
        box(-1.47, zz, 5.18, 7.88, .32, .38, SEAL, .10)
    # Round pilot lights in machined collars: only NORMAL is illuminated.
    for zz, mat in ((6.65, GREEN), (4.58, AMBER)):
        turned(4.28, zz, 5.0, [(.49, 0), (.49, .14), (.39, .21)], STEEL, 24)
        turned(4.28, zz, 5.08, [(.34, 0), (.34, .13), (.25, .19), (0, .21)], mat, 24)
    # Two tactile buttons with dished caps and a quiet serial plate.
    for x in (-4.2, -1.6):
        turned(x, 1.8, 5.0, [(.52, 0), (.52, .11), (.43, .18)], STEEL, 24)
        turned(x, 1.8, 5.12, [(.40, 0), (.40, .17), (.32, .22), (0, .18)], SEAL, 24)
    # Beacon: black base, amber Fresnel bands and a domed weather cap.
    beacon = point(4, 10, 2.5)
    P.lathe_axis(detail, beacon, P.UP, [(1.36, 0), (1.36, .24), (1.16, .42), (1.16, .52)], SEAL, 32, cap=SEAL)
    P.lathe_axis(detail, beacon, P.UP, [(1.04, .47), (1.11, .65), (1.11, 2.10), (1.0, 2.35), (.65, 2.57), (0, 2.64)], AMBER, 32, cap=AMBER)
    for zz in (.84, 1.12, 1.40, 1.68, 1.96):
        P.lathe_axis(detail, beacon, P.UP, [(1.11, zz), (1.145, zz+.035), (1.11, zz+.09)], AMBER, 32)
    # Underside cable glands sit within the original five-inch wall projection.
    for x in (-4.3, 3.6):
        turned(x, .18, 2.35, [(.44, 0), (.44, .55), (.33, .72), (.28, .9)], SEAL, 8, axis=-P.UP)
    # Folded enamel identification plate, separate from the shared atlas.
    for x in (-7.7, 7.7):
        for zz in (-4.2, -2.2):
            turned(x, zz, .02, [(.27, 0), (.27, .28)], STEEL, 12)
    box(0, -3.2, .35, 17.0, 3.4, .19, STEEL, .07)
    quad(SIGN, 0, -3.2, .453, 16.83, 3.24)
    for x in (-7.7, 7.7):
        for zz in (-4.2, -2.2):
            screw(x, zz, .46, .16)
