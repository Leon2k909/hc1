"""Orion's whiteboard v2, for the satellite control room: a glossy board in an aluminium frame, written on in marker, with a tray of markers and an eraser, and
printouts held by magnets. Builds the mesh, paints the maps and writes the model, with numpy and PIL and no Blender, as Sources/Riverdale/notice-board-v2/board.py does.

python whiteboard.py <project root> [preview]

Engine X comes out of the wall, Y is the viewer's right, Z is up. The origin is on the wall at the board's bottom centre. Everything written on it is made up.
"""
import ctypes
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from scipy import ndimage as ndi

try:
    ctypes.windll.kernel32.SetPriorityClass(ctypes.windll.kernel32.GetCurrentProcess(), 0x4000)  # Below normal: the editor is shared.
except AttributeError:
    pass

ROOT = sys.argv[1]
PREVIEW_ONLY = len(sys.argv) > 2 and sys.argv[2] == "preview"
MODEL = "models/maps/orion/whiteboard_v2"
MATS = "materials/orion/whiteboard_v2"
OUT = os.path.join(ROOT, "Assets", *MODEL.split("/"))
MAT_OUT = os.path.join(ROOT, "Assets", *MATS.split("/"))
REVIEW = os.path.join(ROOT, "output", "asset-improvement-20261030", "whiteboard")
for folder in (OUT, MAT_OUT, REVIEW):
    os.makedirs(folder, exist_ok=True)

W, H = 104.0, 58.0  # Within the old picture's 105 x 60.
FRAME = 1.0
FACE_W, FACE_H = W - 2 * FRAME, H - 2 * FRAME
FACE_X = 0.62  # The board's face off the wall: in front of the old quad at 0.5.
FRAME_X = 0.92
PPI_FACE = 32
PPI = 80  # Printouts.
PPI_FRAME = 24
FAR_W, FAR_H = 1040, 580
ATLAS = 4096
FONTS = {
    "sans": r"C:\Windows\Fonts\arial.ttf",
    "bold": r"C:\Windows\Fonts\arialbd.ttf",
    "mono": r"C:\Windows\Fonts\consola.ttf",
    "pen": r"C:\Windows\Fonts\Inkfree.ttf",
    "pen2": r"C:\Windows\Fonts\segoepr.ttf",
    "pen3": r"C:\Windows\Fonts\segoeprb.ttf",
}
BLACK_INK = (24, 26, 30)
BLUE_INK = (18, 52, 150)
RED_INK = (186, 26, 30)
GREEN_INK = (16, 120, 58)


def smooth(a, b, x):
    t = np.clip((x - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)


def blobs(shape, sigma, seed):
    r = np.random.default_rng(seed).normal(size=(max(4, shape[0] // 4), max(4, shape[1] // 4)))
    r = ndi.gaussian_filter(r, sigma / 4, mode="wrap")
    r = ndi.zoom(r, (shape[0] / r.shape[0], shape[1] / r.shape[1]), order=1)[: shape[0], : shape[1]]
    return r / (r.std() * 2.5 + 1e-6)


def to_normal(height, ppi):
    dr, dc = np.gradient(height)
    n = np.stack((-dc * ppi, dr * ppi, np.ones_like(height)), -1)
    return n / np.linalg.norm(n, axis=-1, keepdims=True)


# ---------------------------------------------------------------------------------------------------------------------
# The writing: marker on the board's face, drawn as coverage per ink so it can be laid on as marker is, never quite solid
# ---------------------------------------------------------------------------------------------------------------------


class Marker:
    """Ink layers in inches from the face's top left, supersampled for clean strokes."""

    SS = 2

    def __init__(self):
        self.size = (round(FACE_W * PPI_FACE * self.SS), round(FACE_H * PPI_FACE * self.SS))
        self.layers = {}
        self.rng = np.random.default_rng(5)

    def layer(self, ink):
        if ink not in self.layers:
            self.layers[ink] = Image.new("L", self.size, 0)
        return ImageDraw.Draw(self.layers[ink])

    def px(self, x):
        return x * PPI_FACE * self.SS

    def write(self, x, y, text, ink, size=1.6, face="pen", tilt=0.0, alpha=230):
        """Handwriting about size inches tall, its baseline wandering a little."""
        font = ImageFont.truetype(FONTS[face], max(8, round(self.px(size))))
        box = font.getbbox(text)
        tile = Image.new("L", (box[2] + 40, box[3] + 40), 0)
        ImageDraw.Draw(tile).text((20, 20), text, font=font, fill=alpha)
        if tilt:
            tile = tile.rotate(tilt, resample=Image.BICUBIC, expand=True)
        base = self.layers.setdefault(ink, Image.new("L", self.size, 0))
        base.paste(Image.fromarray(np.maximum(np.asarray(base.crop((round(self.px(x)), round(self.px(y)), round(self.px(x)) + tile.width, round(self.px(y)) + tile.height)), np.uint8), np.asarray(tile))), (round(self.px(x)), round(self.px(y))))

    def line(self, points, ink, width=0.14, wobble=0.03, alpha=230):
        d = self.layer(ink)
        pts = []
        for a, b in zip(points, points[1:]):
            n = max(2, int(np.hypot(b[0] - a[0], b[1] - a[1]) / 0.6))
            for t in np.linspace(0, 1, n, endpoint=False):
                pts.append((a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t))
        pts.append(points[-1])
        pts = np.array(pts)
        pts = pts + self.rng.normal(0, wobble, pts.shape) * np.array((0.3, 1.0))
        d.line([(self.px(x), self.px(y)) for x, y in pts], fill=alpha, width=max(1, round(self.px(width))), joint="curve")

    def ellipse(self, cx, cy, rx, ry, ink, width=0.14, start=0, end=360, alpha=230, gap=0.0):
        a = np.radians(np.linspace(start, end - gap, 90))
        self.line([(cx + rx * np.cos(t), cy + ry * np.sin(t)) for t in a], ink, width, 0.015, alpha)

    def arrow(self, a, b, ink, width=0.12):
        self.line([a, b], ink, width)
        d = np.array(b, float) - np.array(a, float)
        d = d / (np.linalg.norm(d) + 1e-9)
        n = np.array((-d[1], d[0]))
        tip = np.array(b, float)
        for side in (1, -1):
            self.line([tuple(tip), tuple(tip - d * 0.9 + n * side * 0.45)], ink, width)

    def coverage(self, ink):
        arr = np.asarray(self.layers[ink].resize((round(FACE_W * PPI_FACE), round(FACE_H * PPI_FACE)), Image.LANCZOS), np.float32) / 255
        return arr


def write_board(m):
    # What was there before, wiped: faint ghosts.
    ghost = Marker()
    ghost.rng = np.random.default_rng(9)
    for k, (x, y, text) in enumerate(((8, 31, "PASS 4417  AOS 03:12  LOS 03:21"), (54, 40, "battery 3 temp??"), (12, 44, "call Dana re: telemetry gap"), (60, 6, "SAFE MODE 12/10"), (36, 49, "X-band 8.2 GHz"))):
        ghost.write(x, y, text, "ghost", 1.4, "pen", tilt=ghost.rng.uniform(-2, 2), alpha=255)
    ghost.ellipse(84, 30, 8, 6, "ghost", 0.16, alpha=170)
    ghost.line([(4, 22), (40, 23.5)], "ghost", 0.18, alpha=255)

    m.write(3.0, 2.2, "MISSION 07  -  LAUNCH WINDOW", BLACK_INK, 2.3, "pen3", tilt=0.6)
    m.line([(3.4, 5.0), (47.0, 5.25)], BLACK_INK, 0.11)
    m.write(3.2, 6.2, "Window opens 04:12:30 UTC, 11 min long", BLUE_INK, 1.65, "pen")
    m.write(3.2, 8.9, "Backup: +24h, same pad, same orbit", BLUE_INK, 1.65, "pen")
    # The countdown, as a line of ticks.
    y = 21.5
    m.line([(4.0, y), (70.0, y + 0.4)], BLUE_INK, 0.16)
    ticks = (("T-6h", "fuel load"), ("T-3h", "poll 1"), ("T-90m", "LOX top"), ("T-30m", "poll 2"), ("T-10", "terminal"), ("T-0", "LIFTOFF"), ("+3m", "MECO"), ("+9m", "SECO"), ("+52m", "DEPLOY"))
    for k, (label, note) in enumerate(ticks):
        x = 5.0 + k * 8.0
        ink = RED_INK if label == "T-0" else BLUE_INK
        m.line([(x, y - 1.1 + k * 0.045), (x, y + 1.1 + k * 0.045)], ink, 0.15)
        m.write(x - 1.6, y - 3.6 + k * 0.045, label, ink, 1.35, "pen3")
        m.write(x - 2.1, y + 1.6 + k * 0.045, note, BLACK_INK if label != "T-0" else RED_INK, 1.3, "pen")
    m.ellipse(45.0, y + 0.25, 3.6, 2.5, RED_INK, 0.13, gap=20)
    m.arrow((45.0, 27.6), (45.0, y + 3.2), RED_INK)
    m.write(38.0, 28.0, "HOLD HERE if WX NO-GO", RED_INK, 1.5, "pen")
    # Go / no-go poll.
    x0, y0 = 77.0, 3.0
    m.write(x0, y0, "GO / NO-GO", BLACK_INK, 1.9, "pen3")
    m.line([(x0, y0 + 2.6), (x0 + 20.0, y0 + 2.75)], BLACK_INK, 0.1)
    for k, (name, state) in enumerate((("RANGE", "go"), ("WEATHER", "40%"), ("PROPULSION", "go"), ("GNC", "go"), ("COMMS", "go"), ("RECOVERY", "?"))):
        yy = y0 + 4.0 + k * 2.6
        m.write(x0 + 0.4, yy, name, BLACK_INK, 1.5, "pen")
        if state == "go":
            m.line([(x0 + 15.2, yy + 1.0), (x0 + 15.9, yy + 1.7), (x0 + 17.6, yy + 0.1)], GREEN_INK, 0.17)
        else:
            m.write(x0 + 14.6, yy, state, RED_INK, 1.3, "pen3")
    # The orbit, sketched.
    cx, cy = 86.0, 36.0
    m.ellipse(cx, cy, 5.2, 5.2, BLUE_INK, 0.14)
    m.ellipse(cx, cy, 12.0, 7.0, BLACK_INK, 0.1, start=-200, end=150, gap=6)
    m.arrow((cx + 11.4, cy - 2.4), (cx + 12.0, cy + 0.6), BLACK_INK, 0.1)
    m.write(cx - 10.0, cy + 8.4, "LEO 520 km   i = 97.6 deg", BLUE_INK, 1.5, "pen")
    m.write(cx - 10.0, cy + 10.9, "sun-sync, 10:30 LTDN", BLUE_INK, 1.35, "pen")
    # Notes along the bottom.
    m.write(3.4, 32.6, "Telemetry handover: Ops 2 -> Ops 1 at T-30m", BLACK_INK, 1.6, "pen")
    m.write(3.4, 35.6, "Ground stations: Svalbard, Inuvik, Awarua", BLACK_INK, 1.6, "pen")
    m.write(3.4, 40.8, "Next sat window - THU", GREEN_INK, 1.6, "pen3", tilt=-1.0)
    m.line([(3.4, 43.6), (26.0, 43.4)], GREEN_INK, 0.1)
    m.write(52.2, 5.3, "DO NOT ERASE", RED_INK, 1.9, "pen3", tilt=1.2)
    m.line([(51.4, 4.7), (68.6, 4.3), (68.8, 8.5), (51.6, 8.7), (51.4, 4.5)], RED_INK, 0.11)
    return ghost


# ---------------------------------------------------------------------------------------------------------------------
# Printouts held by magnets
# ---------------------------------------------------------------------------------------------------------------------


class Doc:
    def __init__(self, w, h, ground=(255, 255, 255)):
        self.w, self.h = w, h
        self.img = Image.new("RGB", (round(w * PPI), round(h * PPI)), ground)
        self.d = ImageDraw.Draw(self.img)

    def font(self, name, pt):
        return ImageFont.truetype(FONTS[name], max(4, round(pt / 72 * PPI)))

    def text(self, x, y, s, name="sans", pt=10, fill=BLACK_INK, anchor="la"):
        self.d.text((x * PPI, y * PPI), s, font=self.font(name, pt), fill=fill, anchor=anchor)

    def rect(self, x0, y0, x1, y1, fill=None, outline=None, width=0.012):
        self.d.rectangle((x0 * PPI, y0 * PPI, x1 * PPI, y1 * PPI), fill=fill, outline=outline, width=max(1, round(width * PPI)))

    def line(self, x0, y0, x1, y1, fill=BLACK_INK, width=0.012):
        self.d.line((x0 * PPI, y0 * PPI, x1 * PPI, y1 * PPI), fill=fill, width=max(1, round(width * PPI)))


def art_ground_track():
    p = Doc(11.69, 8.27)
    p.rect(0.45, 0.45, 11.24, 1.1, fill=(16, 34, 66))
    p.text(0.65, 0.58, "GROUND TRACK  |  REV 1-3  |  MISSION 07", "bold", 15, (240, 240, 240))
    x0, y0, x1, y1 = 0.6, 1.35, 11.1, 7.4
    p.rect(x0, y0, x1, y1, fill=(214, 226, 236), outline=(90, 100, 110))
    r = np.random.default_rng(3)
    # Made-up land masses, and the grid.
    for k in range(11):
        cx, cy = r.uniform(x0 + 0.6, x1 - 0.6), r.uniform(y0 + 0.5, y1 - 0.5)
        pts = [(cx + np.cos(a) * r.uniform(0.3, 1.1), cy + np.sin(a) * r.uniform(0.2, 0.7)) for a in np.linspace(0, 2 * np.pi, 14, endpoint=False)]
        p.d.polygon([(x * PPI, y * PPI) for x, y in pts], fill=(178, 196, 160))
    for k in range(1, 12):
        p.line(x0 + (x1 - x0) * k / 12, y0, x0 + (x1 - x0) * k / 12, y1, (160, 172, 184), 0.008)
    for k in range(1, 6):
        p.line(x0, y0 + (y1 - y0) * k / 6, x1, y0 + (y1 - y0) * k / 6, (160, 172, 184), 0.008)
    for rev, colour in ((0, (200, 30, 30)), (1, (230, 130, 20)), (2, (30, 90, 190))):
        xs = np.linspace(x0, x1, 120)
        ys = (y0 + y1) / 2 + np.sin((xs - x0) / (x1 - x0) * 2 * np.pi + rev * 1.6) * (y1 - y0) * 0.38
        p.d.line(list(zip((xs * PPI).tolist(), (ys * PPI).tolist())), fill=colour, width=3)
    for name, (x, y) in (("SVALBARD", (6.2, 1.9)), ("INUVIK", (2.1, 2.4)), ("AWARUA", (9.7, 6.8))):
        p.d.ellipse(((x - 0.08) * PPI, (y - 0.08) * PPI, (x + 0.08) * PPI, (y + 0.08) * PPI), fill=(20, 20, 20))
        p.text(x + 0.12, y - 0.1, name, "bold", 8, (20, 20, 20))
    p.text(0.6, 7.6, "Printed 02/11 06:40  Flight Dynamics", "sans", 8.5, (80, 80, 84))
    return p


def art_checklist():
    p = Doc(8.27, 11.69)
    p.rect(0.5, 0.5, 7.77, 1.15, fill=(16, 34, 66))
    p.text(0.7, 0.62, "TERMINAL COUNT CHECKLIST", "bold", 15, (240, 240, 240))
    y = 1.5
    items = ("Range clear and safety officer on loop", "Weather officer go, upper winds in limits", "Vehicle on internal power", "Flight termination armed",
             "Tracking stations in lock", "Payload on internal power", "Recovery vessel on station", "Launch director poll complete")
    for k, item in enumerate(items):
        p.rect(0.6, y + 0.05, 0.85, y + 0.3, outline=BLACK_INK, width=0.015)
        p.text(1.05, y, f"{k + 1:02d}  {item}", "sans", 11, BLACK_INK)
        if k < 5:
            p.d.line(((0.62 * PPI, (y + 0.17) * PPI), (0.72 * PPI, (y + 0.28) * PPI), (0.92 * PPI, (y - 0.02) * PPI)), fill=BLUE_INK, width=3)
        y += 0.52
    y += 0.3
    p.text(0.6, y, "Sign-off", "bold", 12, BLACK_INK)
    for k in range(4):
        p.line(0.6, y + 0.6 + k * 0.48, 7.6, y + 0.6 + k * 0.48, (120, 122, 128))
    p.text(1.0, y + 0.2, "R. Ines  - LD", "pen", 18, BLUE_INK)
    p.text(1.0, y + 0.68, "T. Obi  - FD", "pen", 18, BLUE_INK)
    p.text(0.6, 10.9, "Form OPS-C-14 rev 3", "mono", 8.5, (80, 80, 84))
    return p


def art_photo():
    p = Doc(6.0, 4.5)
    art = Image.open(os.path.join(ROOT, "Assets", "ui", "maps", "orion.png")).convert("RGB") if os.path.exists(os.path.join(ROOT, "Assets", "ui", "maps", "orion.png")) else Image.new("RGB", (600, 450), (60, 70, 90))
    art = art.resize((round(5.6 * PPI), round(3.7 * PPI)), Image.LANCZOS)
    p.img.paste(art, (round(0.2 * PPI), round(0.2 * PPI)))
    p.text(0.25, 4.0, "Pad 2 rollout, 28/10", "pen", 15, BLUE_INK)
    return p


PAPER = (0.95, 0.945, 0.915)
# c: the middle on the face, inches from its bottom left. curl: bottom left, bottom right, top left, top right. magnets: (s, t, colour) as fractions.
SHEETS = [
    dict(name="ground_track", art=art_ground_track, c=(59.5, 41.5), rot=-0.8, curl=(0.25, 0.12, 0.02, 0.02), magnets=[(0.06, 0.94, "red"), (0.94, 0.94, "red")]),
    dict(name="checklist", art=art_checklist, c=(48.0, 8.4), rot=1.1, curl=(0.3, 0.22, 0.0, 0.0), magnets=[(0.5, 0.95, "blue")]),
    dict(name="photo", art=art_photo, c=(35.5, 7.2), rot=-2.6, curl=(0.08, 0.14, 0.0, 0.0), magnets=[(0.5, 0.9, "yellow")], kind="photo"),
]


class Page:
    def __init__(self, info, layer):
        self.info = info
        self.name = info["name"]
        self.doc = info["art"]()
        self.w, self.h = self.doc.w, self.doc.h
        self.kind = info.get("kind", "paper")
        self.c = np.array(info["c"], float)
        a = np.radians(info["rot"])
        self.ax = np.array((np.cos(a), np.sin(a)))
        self.ay = np.array((-np.sin(a), np.cos(a)))
        self.base = 0.012 + layer * 0.02
        self.magnets = [(s * self.w, t * self.h, colour) for s, t, colour in info.get("magnets", [])]
        self.wave = np.random.default_rng(700 + layer).uniform(0, 6.28, 4)

    def board(self, s, t):
        ds, dt = s - self.w / 2, t - self.h / 2
        return self.c[0] + ds * self.ax[0] + dt * self.ay[0], self.c[1] + ds * self.ax[1] + dt * self.ay[1]

    def local(self, u, v):
        du, dv = u - self.c[0], v - self.c[1]
        return du * self.ax[0] + dv * self.ax[1] + self.w / 2, du * self.ay[0] + dv * self.ay[1] + self.h / 2

    def lift(self, s, t):
        s, t = np.asarray(s, float), np.asarray(t, float)
        bl, br, tl, tr = self.info.get("curl", (0, 0, 0, 0))
        reach = 0.62 * min(self.w, self.h)
        total = np.zeros_like(s)
        for value, cs, ct in ((bl, 0, 0), (br, self.w, 0), (tl, 0, self.h), (tr, self.w, self.h)):
            if value:
                d = np.hypot(s - cs, t - ct) / reach
                total += value * (1 - smooth(0, 1, d)) ** 1.6
        stiff = 0.02 if self.kind == "photo" else 0.04
        total += (np.sin(s * 0.8 + self.wave[0]) * np.sin(t * 0.6 + self.wave[1]) + 1.0) * stiff
        for ps, pt, _ in self.magnets:
            total *= smooth(0.3, 1.8, np.hypot(s - ps, t - pt))
        return total + self.base


PAGES = [Page(info, k) for k, info in enumerate(SHEETS)]

# ---------------------------------------------------------------------------------------------------------------------
# Atlas
# ---------------------------------------------------------------------------------------------------------------------

GUTTER = 8
TRAY_LEN = 70.0
rects = {"face": (round(FACE_W * PPI_FACE), round(FACE_H * PPI_FACE)), "far": (FAR_W, FAR_H), "back": (64, 64), "swatch": (320, 48),
         "frame_top": (round(W * PPI_FRAME), 48), "frame_bottom": (round(W * PPI_FRAME), 48), "frame_left": (round(H * PPI_FRAME), 48), "frame_right": (round(H * PPI_FRAME), 48),
         "tray": (round(TRAY_LEN * PPI_FRAME), 128)}
for page in PAGES:
    rects[page.name] = page.doc.img.size
place = {}
_x, _y, _shelf = 0, 0, 0
for name, (rw, rh) in sorted(rects.items(), key=lambda kv: -kv[1][1]):
    if _x + rw + GUTTER > ATLAS:
        _x, _y, _shelf = 0, _y + _shelf + GUTTER, 0
    place[name] = (_x, _y, rw, rh)
    _x += rw + GUTTER
    _shelf = max(_shelf, rh)
print("atlas used to row", _y + _shelf, flush=True)
if _y + _shelf > ATLAS:
    raise SystemExit("The atlas is full.")
COLOUR = np.zeros((ATLAS, ATLAS, 3), np.float32)
NORMAL = np.zeros((ATLAS, ATLAS, 3), np.float32)
NORMAL[..., 2] = 1
ROUGH = np.full((ATLAS, ATLAS), 0.6, np.float32)
METAL = np.zeros((ATLAS, ATLAS), np.float32)
AO = np.ones((ATLAS, ATLAS), np.float32)
COVER = np.zeros((ATLAS, ATLAS), bool)


def put(name, colour=None, normal=None, rough=None, metal=None, ao=None):
    x, y, w, h = place[name]
    for arr, value in ((COLOUR, colour), (NORMAL, normal), (ROUGH, rough), (METAL, metal), (AO, ao)):
        if value is not None:
            arr[y : y + h, x : x + w] = value
    COVER[y : y + h, x : x + w] = True


# Shadows over the face from the papers, magnets, frame lip and tray.
PPI_SHADE = 16
sh, sw = round(FACE_H * PPI_SHADE), round(FACE_W * PPI_SHADE)
gv, gu = np.mgrid[0:sh, 0:sw].astype(np.float32)
gu, gv = (gu + 0.5) / PPI_SHADE, (gv + 0.5) / PPI_SHADE  # From the face's bottom left.


def cast_of(page):
    s, t = page.local(gu, gv)
    inside = ((s >= 0) & (s <= page.w) & (t >= 0) & (t <= page.h)).astype(np.float32)
    tight = ndi.gaussian_filter(np.roll(inside, -1, 0), 0.06 * PPI_SHADE)
    wide = ndi.gaussian_filter(np.roll(inside, -3, 0), 0.3 * PPI_SHADE)
    return 1 - 0.4 * tight - 0.14 * wide


def magnet_cast(page):
    cast = np.ones((sh, sw), np.float32)
    for ps, pt, _ in page.magnets:
        u, v = page.board(ps, pt)
        d = np.hypot(gu - u - 0.04, gv - v + 0.14)
        cast *= 1 - 0.7 * (1 - smooth(0.4, 0.95, d))
    return cast


shade_of = {}
above = np.ones((sh, sw), np.float32)
for page in reversed(PAGES):
    above = above * magnet_cast(page)
    shade_of[page.name] = above.copy()
    above = above * cast_of(page)
edge = np.minimum.reduce((gu, gv, FACE_W - gu, FACE_H - gv))
lip = 0.6 + 0.4 * smooth(0.0, 0.5, edge)
# The tray stands out under the board and shades its lowest inches a little.
tray_shade = 1 - 0.18 * (1 - smooth(0.0, 2.5, gv)) * (np.abs(gu - FACE_W / 2) < TRAY_LEN / 2 + 1)
shade_of["face"] = above * lip * tray_shade
for page in PAGES:
    shade_of[page.name] = shade_of[page.name] * lip


def sample_shade(key, u, v):
    return ndi.map_coordinates(shade_of[key], (v * PPI_SHADE - 0.5, u * PPI_SHADE - 0.5), order=1, mode="nearest")


def paint_face():
    x, y, w, h = place["face"]
    marker = Marker()
    ghost = write_board(marker)
    colour = np.empty((h, w, 3), np.float32)
    base = np.array((0.925, 0.932, 0.94), np.float32)
    haze = blobs((h, w), 120, 41)
    colour[:] = base
    colour *= (1 + 0.012 * haze)[..., None]
    rows, cols = np.mgrid[0:h, 0:w].astype(np.float32)
    # Ghosts of wiped writing, and the eraser's swirls through them.
    g = ndi.gaussian_filter(ghost.coverage("ghost"), 1.6)
    swirl = np.clip(blobs((h, w), 60, 42) + 0.3, 0, 1)
    colour = colour * (1 - (0.06 * g + 0.025 * swirl * smooth(0.2, 0.6, ndi.gaussian_filter(g, 12) * 8))[..., None] * np.array((1.0, 1.0, 0.96), np.float32))
    # Hand smudges low on the board.
    hand = np.clip(blobs((h, w), 30, 43) - 0.5, 0, 1) * smooth(30, 8, (h - rows) / PPI_FACE)
    colour = colour * (1 - 0.03 * hand)[..., None]
    rough = 0.09 + 0.06 * np.clip(haze, 0, 1) + 0.18 * swirl * 0.4 + 0.22 * hand + 0.08 * g
    height = 0.0012 * blobs((h, w), 200, 44) + 0.0004 * blobs((h, w), 6, 45)
    inks = {BLACK_INK: 0.92, BLUE_INK: 0.9, RED_INK: 0.88, GREEN_INK: 0.9}
    streak = 1 - 0.12 * np.clip(ndi.gaussian_filter(np.random.default_rng(46).normal(size=(h, w)), (0.6, 3.5)) * 2.5, -1, 1)
    for ink, strength in inks.items():
        if ink not in marker.layers:
            continue
        a = marker.coverage(ink) * strength * streak
        ink_lin = np.array(ink, np.float32) / 255
        colour = colour * (1 - a[..., None]) + ink_lin * a[..., None] * (0.92 + 0.08 * colour)
        rough = rough * (1 - a) + 0.34 * a
        height = height + 0.0008 * a
    uu, vv = (cols + 0.5) / PPI_FACE, (h - rows - 0.5) / PPI_FACE
    shade = sample_shade("face", uu, vv)
    put("face", np.clip(colour * (0.55 + 0.45 * shade)[..., None], 0, 1), to_normal(height, PPI_FACE), np.clip(rough, 0.04, 1), 0.0, np.clip(0.45 + 0.55 * shade, 0, 1))
    return colour


RENDERED = {}


def paint_page(page):
    x, y, w, h = place[page.name]
    art = np.asarray(page.doc.img, np.float32) / 255
    art = ndi.gaussian_filter(art, (0.4, 0.4, 0))
    ground = np.array(PAPER, np.float32) if page.kind != "photo" else np.array((0.98, 0.98, 0.97), np.float32)
    colour = art * ground
    colour = colour * (1 + 0.02 * blobs((h, w), 50, 800 + len(page.name)))[..., None]
    rows, cols = np.mgrid[0:h, 0:w].astype(np.float32)
    uu, vv = page.board((cols + 0.5) / PPI, (h - rows - 0.5) / PPI)
    shade = sample_shade(page.name, uu, vv)
    RENDERED[page.name] = np.clip(colour * (0.5 + 0.5 * shade)[..., None], 0, 1)
    height = 0.002 * blobs((h, w), 24, 801) + 0.006 * smooth(0.1, 0.0, np.abs(blobs((h, w), 40, 802))) * (page.kind != "photo")
    rough = np.full((h, w), 0.3 if page.kind == "photo" else 0.8, np.float32)
    put(page.name, RENDERED[page.name], to_normal(height, PPI), rough, 0.0, np.clip(0.5 + 0.5 * shade, 0, 1))


def paint_metal():
    for name, seed in (("frame_top", 1), ("frame_bottom", 2), ("frame_left", 3), ("frame_right", 4), ("tray", 5)):
        x, y, w, h = place[name]
        r = np.random.default_rng(900 + seed)
        streak = ndi.gaussian_filter(r.normal(size=(h, w)), (0.5, 12))
        streak = streak / streak.std()
        scuff = np.clip(blobs((h, w), 18, 910 + seed) - 0.5, 0, 1) * 2.0
        tone = 0.72 + 0.02 * streak - 0.08 * scuff
        colour = np.stack((tone, tone * 1.004, tone * 1.018), -1)
        rough = 0.38 + 0.03 * streak + 0.2 * scuff
        if name == "tray":
            # Marker dust and ink rubbings collect in the tray.
            dust = np.clip(blobs((h, w), 14, 920) + 0.4, 0, 1) * smooth(0.25, 0.55, np.linspace(0, 1, h))[:, None]
            colour = colour * (1 - 0.25 * dust)[..., None]
            rough = rough + 0.3 * dust
        put(name, np.clip(colour, 0, 1), to_normal(0.0012 * streak - 0.0015 * scuff, PPI_FRAME), np.clip(rough, 0.1, 1), 0.68 * (1 - 0.3 * np.clip(scuff, 0, 1)), 1.0)


SWATCH = {"black": (0.03, 0.03, 0.035), "blue": (0.04, 0.16, 0.6), "red": (0.72, 0.05, 0.05), "green": (0.03, 0.45, 0.18), "cap_white": (0.86, 0.86, 0.84), "plastic": (0.16, 0.165, 0.17),
          "felt": (0.32, 0.31, 0.3), "yellow": (0.95, 0.75, 0.06), "grey": (0.55, 0.56, 0.57), "tip": (0.12, 0.12, 0.13)}


def paint_small():
    x, y, w, h = place["swatch"]
    colour = np.zeros((h, w, 3), np.float32)
    rough = np.full((h, w), 0.32, np.float32)
    step = w / len(SWATCH)
    for k, (name, c) in enumerate(SWATCH.items()):
        c0, c1 = round(k * step), round((k + 1) * step)
        colour[:, c0:c1] = c
        if name in ("felt", "tip"):
            rough[:, c0:c1] = 0.95
    put("swatch", colour, None, rough, 0.0, 1.0)
    x, y, w, h = place["back"]
    put("back", np.full((h, w, 3), (0.82, 0.81, 0.78), np.float32), None, 0.85, 0.0, 0.8)


def swatch_uv(name):
    x, y, w, h = place["swatch"]
    k = list(SWATCH).index(name)
    return np.array((x + (k + 0.5) * w / len(SWATCH), y + h / 2), np.float32)


def composite_far(face_colour):
    scale = 2
    pw, ph = FAR_W * scale, FAR_H * scale
    ppi = pw / W
    out = Image.new("RGB", (pw, ph), (176, 178, 182))
    x, y, w, h = place["face"]
    face = Image.fromarray((np.clip(COLOUR[y : y + h, x : x + w], 0, 1) * 255).astype(np.uint8)).resize((round(FACE_W * ppi), round(FACE_H * ppi)), Image.LANCZOS)
    out.paste(face, (round(FRAME * ppi), round(FRAME * ppi)))
    for page in PAGES:
        art = RENDERED[page.name]
        hh, ww = art.shape[:2]
        rgba = Image.fromarray(np.dstack(((art * 255).astype(np.uint8), np.full((hh, ww), 255, np.uint8))))
        small = rgba.resize((max(2, round(page.w * ppi)), max(2, round(page.h * ppi))), Image.LANCZOS).rotate(page.info["rot"], expand=True, resample=Image.BICUBIC)
        cx, cy = (FRAME + page.c[0]) * ppi, ph - (FRAME + page.c[1]) * ppi
        out.paste(small, (round(cx - small.width / 2), round(cy - small.height / 2)), small)
    d = ImageDraw.Draw(out)
    for page in PAGES:
        for ps, pt, colour in page.magnets:
            u, v = page.board(ps, pt)
            px, py, r = (FRAME + u) * ppi, ph - (FRAME + v) * ppi, 0.55 * ppi
            d.ellipse((px - r, py - r, px + r, py + r), fill=tuple(int(a * 255) for a in SWATCH[colour]))
    far = out.resize((FAR_W, FAR_H), Image.LANCZOS)
    far.save(os.path.join(REVIEW, "layout.png"))
    put("far", np.asarray(far, np.float32) / 255, None, 0.2, 0.0, 1.0)


# ---------------------------------------------------------------------------------------------------------------------
# Mesh
# ---------------------------------------------------------------------------------------------------------------------


class Mesh:
    def __init__(self):
        self.p, self.t, self.n = [], [], []

    def tri(self, p, t, n):
        self.p.append(p)
        self.t.append(t)
        self.n.append(n)

    def quad(self, a, b, c, d, ta, tb, tc, td, normal=None):
        a, b, c, d = (np.asarray(v_, np.float64) for v_ in (a, b, c, d))
        if normal is None:
            normal = np.cross(c - a, d - b)
            normal = normal / (np.linalg.norm(normal) + 1e-12)
        nn = np.broadcast_to(np.asarray(normal, np.float64), (3, 3))
        self.tri((a, b, c), (ta, tb, tc), nn)
        self.tri((a, c, d), (ta, tc, td), nn)

    def grid(self, pos, uv, flip=False):
        rows, cols = pos.shape[:2]
        nor = np.cross(np.gradient(pos, axis=1), np.gradient(pos, axis=0))
        nor = nor / (np.linalg.norm(nor, axis=-1, keepdims=True) + 1e-12)
        if flip:
            nor = -nor
        for j in range(rows - 1):
            for k in range(cols - 1):
                idx = ((j, k), (j, k + 1), (j + 1, k + 1), (j + 1, k))
                if flip:
                    idx = idx[::-1]
                a, b, c, d = idx
                self.tri((pos[a], pos[b], pos[c]), (uv[a], uv[b], uv[c]), (nor[a], nor[b], nor[c]))
                self.tri((pos[a], pos[c], pos[d]), (uv[a], uv[c], uv[d]), (nor[a], nor[c], nor[d]))

    def lathe(self, start, axis, profile, colour, seg=10, cap=True):
        """profile: (radius, along) from the start along axis. Normals out from the axis, approximately."""
        axis = np.asarray(axis, float) / np.linalg.norm(axis)
        ref = np.array((0.0, 0.0, 1.0)) if abs(axis[2]) < 0.9 else np.array((1.0, 0.0, 0.0))
        e1 = np.cross(axis, ref)
        e1 /= np.linalg.norm(e1)
        e2 = np.cross(axis, e1)
        uv = swatch_uv(colour)
        rings = []
        for r, h in profile:
            rings.append([np.asarray(start) + axis * h + (e1 * np.cos(a) + e2 * np.sin(a)) * r for a in np.linspace(0, 2 * np.pi, seg + 1)])
        rings = np.array(rings)
        for j in range(len(rings) - 1):
            for k in range(seg):
                a, b, c, d = rings[j, k], rings[j, k + 1], rings[j + 1, k + 1], rings[j + 1, k]
                ang = [2 * np.pi * k / seg, 2 * np.pi * (k + 1) / seg]
                na = e1 * np.cos(ang[0]) + e2 * np.sin(ang[0])
                nb = e1 * np.cos(ang[1]) + e2 * np.sin(ang[1])
                slope = (profile[j][0] - profile[j + 1][0]) / max(1e-6, abs(profile[j + 1][1] - profile[j][1]))
                na, nb = na + axis * slope, nb + axis * slope
                na, nb = na / np.linalg.norm(na), nb / np.linalg.norm(nb)
                if np.linalg.norm(np.cross(b - a, c - a)) > 1e-9:
                    self.tri((a, b, c), (uv, uv, uv), (na, nb, nb))
                if np.linalg.norm(np.cross(c - a, d - a)) > 1e-9:
                    self.tri((a, c, d), (uv, uv, uv), (na, nb, na))
        if cap:
            for j, sign in ((0, -1), (len(rings) - 1, 1)):
                if profile[j][0] < 1e-6:
                    continue
                centre = np.asarray(start) + axis * profile[j][1]
                for k in range(seg):
                    self.tri((centre, rings[j, k], rings[j, k + 1]), (uv, uv, uv), (axis * sign,) * 3)

    def arrays(self):
        return np.array(self.p, np.float64), np.array(self.t, np.float64), np.array(self.n, np.float64)


def face_world(u, v, x):
    return np.stack((FACE_X + x, u - FACE_W / 2, FRAME + v), -1)


def page_grid(mesh, page, step=1.3):
    ns, nt = max(2, int(round(page.w / step)) + 1), max(2, int(round(page.h / step)) + 1)
    tt, ss = np.meshgrid(np.linspace(0, page.h, nt), np.linspace(0, page.w, ns), indexing="ij")
    uu, vv = page.board(ss, tt)
    pos = face_world(uu, vv, page.lift(ss, tt))
    x, y, w, h = place[page.name]
    mesh.grid(pos, np.stack((x + ss / page.w * w, y + (1 - tt / page.h) * h), -1))
    bx, by, bw, bh = place["back"]
    mesh.grid(pos - np.array((0.004, 0, 0)), np.stack((bx + 4 + ss / page.w * (bw - 8), by + 4 + tt / page.h * (bh - 8)), -1), flip=True)
    for ps, pt, colour in page.magnets:
        u, v = page.board(ps, pt)
        start = face_world(np.array(u), np.array(v), np.array(page.lift(np.array([ps]), np.array([pt]))[0]))
        mesh.lathe(start, (1, 0, 0), [(0.55, 0.0), (0.56, 0.18), (0.5, 0.3), (0.0, 0.33)], colour, seg=14)


def frame_profile():
    pts = [(0.0, 0.0), (0.0, 0.7), (0.1, 0.86), (0.22, FRAME_X), (0.74, FRAME_X), (0.86, 0.86), (0.94, 0.74), (FRAME, FACE_X - 0.04)]
    lengths = [0.0]
    for a, b in zip(pts, pts[1:]):
        lengths.append(lengths[-1] + np.hypot(b[0] - a[0], b[1] - a[1]))
    return pts, np.array(lengths) / lengths[-1]


def add_frame(mesh):
    pts, along = frame_profile()
    for name, side in (("frame_top", "top"), ("frame_bottom", "bottom"), ("frame_left", "left"), ("frame_right", "right")):
        x, y, w, h = place[name]
        for k in range(len(pts) - 1):
            (d0, x0), (d1, x1) = pts[k], pts[k + 1]
            if side in ("top", "bottom"):
                zc, sign = (H, -1) if side == "top" else (0.0, 1)
                a, b = np.array((x0, -W / 2 + d0, zc + sign * d0)), np.array((x0, W / 2 - d0, zc + sign * d0))
                c, e = np.array((x1, W / 2 - d1, zc + sign * d1)), np.array((x1, -W / 2 + d1, zc + sign * d1))
                L = W
            else:
                yc, sign = (-W / 2, 1) if side == "left" else (W / 2, -1)
                a, b = np.array((x0, yc + sign * d0, d0)), np.array((x0, yc + sign * d0, H - d0))
                c, e = np.array((x1, yc + sign * d1, H - d1)), np.array((x1, yc + sign * d1, d1))
                L = H
            ta, tb = (x + w * d0 / L, y + h * along[k]), (x + w * (1 - d0 / L), y + h * along[k])
            tc, te = (x + w * (1 - d1 / L), y + h * along[k + 1]), (x + w * d1 / L, y + h * along[k + 1])
            normal = np.cross(b - a, e - a)
            normal /= np.linalg.norm(normal) + 1e-12
            middle = (a + b + c + e) / 4
            want = np.array((middle[0] - 0.3, 0.0, 0.0))
            if side in ("top", "bottom"):
                want[2] = -(zc + sign * 0.5 - middle[2])
            else:
                want[1] = -(yc + sign * 0.5 - middle[1])
            if normal @ want < 0:
                normal = -normal
            mesh.tri((a, b, c), (ta, tb, tc), (normal,) * 3)
            mesh.tri((a, c, e), (ta, tc, te), (normal,) * 3)


def add_corners(mesh, top=1.0, size=1.5, cut=0.3):
    uv = swatch_uv("grey")
    for sy, sz in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
        y0, z0 = sy * W / 2, 0 if sz < 0 else H
        dy, dz = -sy, -sz
        outline = [(cut, 0), (size, 0), (size, 0.95), (0.95, 0.95), (0.95, size), (0, size), (0, cut)]
        pts = [np.array((y0 + dy * a, z0 + dz * b)) for a, b in outline]
        n = len(pts)
        centre = np.mean(pts, 0)
        for k in range(n):
            a, b = pts[k], pts[(k + 1) % n]
            mesh.tri((np.array((top, *centre)), np.array((top, *a)), np.array((top, *b))), (uv, uv, uv), (np.array((1.0, 0, 0)),) * 3)
            edge = b - a
            out = np.array((0.0, edge[1], -edge[0]))
            out /= np.linalg.norm(out) + 1e-12
            if out @ np.array((0.0, *(((a + b) / 2) - centre))) < 0:
                out = -out
            mesh.tri((np.array((top, *a)), np.array((0.0, *a)), np.array((0.0, *b))), (uv, uv, uv), (out,) * 3)
            mesh.tri((np.array((top, *a)), np.array((0.0, *b)), np.array((top, *b))), (uv, uv, uv), (out,) * 3)


TRAY = [(0.0, 0.25), (0.0, -0.55), (3.1, -0.55), (3.35, -0.35), (3.35, 0.55), (3.15, 0.62), (3.0, 0.05), (0.9, 0.05), (0.9, 0.25)]  # (out, up) about the board's bottom.


def add_tray(mesh):
    x, y, w, h = place["tray"]
    lengths = [0.0]
    for a, b in zip(TRAY, TRAY[1:]):
        lengths.append(lengths[-1] + np.hypot(b[0] - a[0], b[1] - a[1]))
    along = np.array(lengths) / lengths[-1]
    y0, y1 = -TRAY_LEN / 2, TRAY_LEN / 2
    for k in range(len(TRAY) - 1):
        (o0, z0), (o1, z1) = TRAY[k], TRAY[k + 1]
        a, b = np.array((o0, y0, z0)), np.array((o0, y1, z0))
        c, e = np.array((o1, y1, z1)), np.array((o1, y0, z1))
        normal = np.array((z1 - z0, 0.0, -(o1 - o0)))
        normal /= np.linalg.norm(normal) + 1e-12
        # The profile runs round the outside first, so its normals point away from the U's inside.
        if k >= 5:
            normal = -normal
        mesh.tri((a, b, c), ((x, y + h * along[k]), (x + w, y + h * along[k]), (x + w, y + h * along[k + 1])), (normal,) * 3)
        mesh.tri((a, c, e), ((x, y + h * along[k]), (x + w, y + h * along[k + 1]), (x, y + h * along[k + 1])), (normal,) * 3)
    uv = swatch_uv("plastic")
    # End caps, in moulded plastic: the base and the lip as plain shapes.
    for ye, sign in ((y0, -1), (y1, 1)):
        n = np.array((0.0, float(sign), 0.0))
        for poly in ([(0.0, 0.25), (0.0, -0.55), (3.1, -0.55), (3.35, -0.35), (3.35, 0.05), (0.0, 0.05)], [(3.0, 0.05), (3.35, 0.05), (3.35, 0.55), (3.15, 0.62)]):
            pts = [np.array((o, ye + sign * 0.06, z)) for o, z in poly]
            for j in range(1, len(pts) - 1):
                mesh.tri((pts[0], pts[j], pts[j + 1]), (uv, uv, uv), (n,) * 3)
    # Markers and an eraser lying in it.
    for yy, colour, out in ((-22.0, "black", 1.75), (-15.5, "blue", 2.45), (-9.0, "red", 1.8), (13.5, "green", 2.3)):
        start = np.array((out, yy, 0.05 + 0.36))
        mesh.lathe(start, (0, 1, 0), [(0.0, 0.0), (0.36, 0.02), (0.36, 3.9), (0.33, 4.0), (0.33, 4.15)], colour if colour != "black" else "black", seg=10)
        mesh.lathe(start + np.array((0, 4.15, 0)), (0, 1, 0), [(0.39, 0.0), (0.39, 1.4), (0.3, 1.55), (0.0, 1.6)], colour, seg=10)
        mesh.lathe(start, (0, -1, 0), [(0.36, 0.0), (0.2, 0.35), (0.12, 0.7), (0.0, 0.74)], "cap_white", seg=8)
    ex, ey = 2.0, 22.0
    corners = [(-2.6, -0.95), (2.6, -0.95), (2.6, 0.95), (-2.6, 0.95)]
    top, bottom = 1.25, 0.05
    uvp, uvf = swatch_uv("plastic"), swatch_uv("felt")
    for zz, uvx, up in ((top, uvp, 1), (bottom + 0.25, uvf, 1)):
        pts = [np.array((ex + dx, ey + dy, zz)) for dy, dx in corners]
        mesh.tri((pts[0], pts[1], pts[2]), (uvx,) * 3, (np.array((0, 0, 1.0)),) * 3)
        mesh.tri((pts[0], pts[2], pts[3]), (uvx,) * 3, (np.array((0, 0, 1.0)),) * 3)
    for k in range(4):
        (ya, xa), (yb, xb) = corners[k], corners[(k + 1) % 4]
        a, b = np.array((ex + xa, ey + ya, top)), np.array((ex + xb, ey + yb, top))
        c, d = np.array((ex + xb, ey + yb, bottom)), np.array((ex + xa, ey + ya, bottom))
        out = np.cross(b - a, d - a)
        out /= np.linalg.norm(out) + 1e-12
        if out @ (((a + b) / 2) - np.array((ex, ey, (top + bottom) / 2))) < 0:
            out = -out
        mesh.tri((a, b, c), (uvp,) * 3, (out,) * 3)
        mesh.tri((a, c, d), (uvp,) * 3, (out,) * 3)


def build_lod0():
    mesh = Mesh()
    x, y, w, h = place["face"]
    mesh.quad((FACE_X, -FACE_W / 2, FRAME), (FACE_X, FACE_W / 2, FRAME), (FACE_X, FACE_W / 2, FRAME + FACE_H), (FACE_X, -FACE_W / 2, FRAME + FACE_H), (x, y + h), (x + w, y + h), (x + w, y), (x, y))
    for page in PAGES:
        page_grid(mesh, page)
    add_frame(mesh)
    add_corners(mesh)
    add_tray(mesh)
    return mesh


def far_front(mesh, x_face):
    x, y, w, h = place["far"]
    mesh.quad((x_face, -W / 2, 0), (x_face, W / 2, 0), (x_face, W / 2, H), (x_face, -W / 2, H), (x + 1.5, y + h - 1.5), (x + w - 1.5, y + h - 1.5), (x + w - 1.5, y + 1.5), (x + 1.5, y + 1.5))


def fix_winding(p, t, n):
    face = np.cross(p[:, 1] - p[:, 0], p[:, 2] - p[:, 0])
    flip = (face * n.mean(1)).sum(-1) < 0
    p[flip], t[flip], n[flip] = p[flip][:, [0, 2, 1]], t[flip][:, [0, 2, 1]], n[flip][:, [0, 2, 1]]
    return int(flip.sum())


def write_obj(path, mesh):
    p, t, n = mesh.arrays()
    turned = fix_winding(p, t, n)
    uv = np.stack((t[..., 0] / ATLAS, 1 - t[..., 1] / ATLAS), -1)
    tables = ({}, {}, {})
    lines = ([], [], [])
    faces = []

    def index(k, prefix, values):
        key = tuple(np.round(values, 5))
        got = tables[k].get(key)
        if got is None:
            got = len(tables[k]) + 1
            tables[k][key] = got
            lines[k].append(prefix + " ".join(f"{v_:.5f}" for v_ in key) + "\n")
        return got

    po, no = p[..., [1, 2, 0]], n[..., [1, 2, 0]]  # Engine X, Y, Z become OBJ Z, X, Y: a rotation, so the winding holds.
    for k in range(len(po)):
        faces.append("f " + " ".join("%d/%d/%d" % (index(0, "v ", po[k, c]), index(1, "vt ", uv[k, c]), index(2, "vn ", no[k, c])) for c in range(3)) + "\n")
    with open(path, "w", newline="\n") as h:
        h.write("# Generated by Sources/Orion/whiteboard-v2/whiteboard.py\nmtllib whiteboard.mtl\n")
        for block in lines:
            h.writelines(block)
        h.write("usemtl whiteboard\n")
        h.writelines(faces)
    print(os.path.basename(path), "triangles", len(po), "turned", turned, "bounds", p.reshape(-1, 3).min(0).round(2), p.reshape(-1, 3).max(0).round(2), flush=True)
    return len(po)


def write_model():
    lod0 = build_lod0()
    lod1 = Mesh()
    far_front(lod1, 0.7)
    add_frame(lod1)
    add_tray(lod1)
    lod2 = Mesh()
    far_front(lod2, 0.95)
    counts = [write_obj(os.path.join(OUT, f"whiteboard_lod{k}.obj"), m) for k, m in enumerate((lod0, lod1, lod2))]
    with open(os.path.join(OUT, "whiteboard.mtl"), "w", newline="\n") as h:
        h.write("newmtl whiteboard\n")
    tail = 'import_translation = [ 0.0, 0.0, 0.0 ] import_rotation = [ 0.0, 0.0, 0.0 ] import_scale = 1.0 align_origin_x_type = "None" align_origin_y_type = "None" align_origin_z_type = "None" parent_bone = "" import_filter = { exclude_by_default = false exception_list = [ ] }'
    meshes = "\n".join(f'\t\t\t\t\t{{ _class = "RenderMeshFile" name = "lod{k}" filename = "{MODEL}/whiteboard_lod{k}.obj" {tail} }},' for k in range(3))
    with open(os.path.join(OUT, "whiteboard.vmdl"), "w", newline="\n") as h:
        h.write(f"""<!-- kv3 encoding:text:version{{e21c7f3c-8a33-41c5-9977-a76d3a32aa0d}} format:modeldoc29:version{{3cec427c-1b0e-4d48-a90a-0436f33a6041}} -->
// Generated by Sources/Orion/whiteboard-v2/whiteboard.py
{{
	rootNode =
	{{
		_class = "RootNode"
		children =
		[
			{{
				_class = "MaterialGroupList"
				children =
				[
					{{
						_class = "DefaultMaterialGroup"
						remaps =
						[
							{{ from = "whiteboard.vmat" to = "{MATS}/whiteboard.vmat" }}
						]
						use_global_default = false
						global_default_material = ""
					}},
				]
			}},
			{{
				_class = "RenderMeshList"
				children =
				[
{meshes}
				]
			}},
			{{
				_class = "LODGroupList"
				children =
				[
					{{ _class = "LODGroup" switch_threshold = 0.0 meshes = [ "lod0" ] }},
					{{ _class = "LODGroup" switch_threshold = 36.0 meshes = [ "lod1" ] }},
					{{ _class = "LODGroup" switch_threshold = 100.0 meshes = [ "lod2" ] }}
				]
			}},
		]
		model_archetype = ""
		primary_associated_entity = ""
		anim_graph_name = ""
		base_model_name = ""
	}}
}}
""")
    with open(os.path.join(MAT_OUT, "whiteboard.vmat"), "w", newline="\n") as h:
        h.write(f"""// Generated by Sources/Orion/whiteboard-v2/whiteboard.py

Layer0
{{
	shader "shaders/complex.shader"

	//---- PBR ----
	F_METALNESS_TEXTURE 1
	F_SPECULAR 1

	//---- Ambient Occlusion ----
	g_flAmbientOcclusionDirectDiffuse "0.300"
	g_flAmbientOcclusionDirectSpecular "0.500"
	TextureAmbientOcclusion "{MATS}/whiteboard_ao.png"

	//---- Color ----
	g_flModelTintAmount "1.000"
	g_vColorTint "[1.000000 1.000000 1.000000 0.000000]"
	TextureColor "{MATS}/whiteboard_color.png"

	//---- Fog ----
	g_bFogEnabled "1"

	//---- Metalness ----
	TextureMetalness "{MATS}/whiteboard_metal.png"

	//---- Normal ----
	TextureNormal "{MATS}/whiteboard_normal.png"

	//---- Roughness ----
	g_flRoughnessScaleFactor "1.000"
	TextureRoughness "{MATS}/whiteboard_rough.png"
}}
""")
    return counts


face_colour = paint_face()
print("face done", flush=True)
for _page in PAGES:
    paint_page(_page)
paint_metal()
paint_small()
composite_far(face_colour)
print("layout written", flush=True)
if PREVIEW_ONLY:
    sys.exit(0)
fill = tuple(ndi.distance_transform_edt(~COVER, return_distances=False, return_indices=True))
COLOUR, NORMAL, ROUGH, METAL, AO = COLOUR[fill], NORMAL[fill], ROUGH[fill], METAL[fill], AO[fill]
del fill
Image.fromarray((np.clip(COLOUR, 0, 1) * 255 + 0.5).astype(np.uint8)).save(os.path.join(MAT_OUT, "whiteboard_color.png"), compress_level=6)
Image.fromarray((np.clip(NORMAL * 0.5 + 0.5, 0, 1) * 255 + 0.5).astype(np.uint8)).save(os.path.join(MAT_OUT, "whiteboard_normal.png"), compress_level=6)
for array, name in ((ROUGH, "rough"), (METAL, "metal"), (AO, "ao")):
    Image.fromarray((np.clip(array, 0, 1) * 255 + 0.5).astype(np.uint8)).resize((2048, 2048), Image.BOX).save(os.path.join(MAT_OUT, f"whiteboard_{name}.png"), compress_level=6)
print("maps written", flush=True)
print("triangles", write_model(), flush=True)
