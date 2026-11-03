"""Riverdale's notice board v2: real sheets of paper on real cork, in an aluminium frame. Builds the mesh, paints the maps and writes the model.

python board.py <project root> [preview]

Pure numpy and PIL, with no Blender: the board is nearly flat, so its bakes come from a height field worked out here. The sheets are grids that lift
and curl off the cork, each with its own page in the atlas at 100 px/in, so the print can be read up close. Everything printed is made up.
Engine X comes out of the wall, Y is the viewer's right, Z is up. The origin is on the wall at the board's bottom centre, as the old one's box was.
"""
import ctypes
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage as ndi
from scipy.spatial import cKDTree

try:
    ctypes.windll.kernel32.SetPriorityClass(ctypes.windll.kernel32.GetCurrentProcess(), 0x4000)  # Below normal: the editor is shared.
except AttributeError:
    pass

ROOT = sys.argv[1]
PREVIEW_ONLY = len(sys.argv) > 2 and sys.argv[2] == "preview"
MODEL = "models/maps/riverdale/notice_board_v2"
MATS = "materials/riverdale/notice_board_v2"
OUT = os.path.join(ROOT, "Assets", *MODEL.split("/"))
MAT_OUT = os.path.join(ROOT, "Assets", *MATS.split("/"))
REVIEW = os.path.join(ROOT, "output", "asset-improvement-20261030", "notice-board")
for folder in (OUT, MAT_OUT, REVIEW):
    os.makedirs(folder, exist_ok=True)

W, H = 36.0, 24.0  # The old board's footprint.
FRAME = 0.85
CORK_W, CORK_H = W - 2 * FRAME, H - 2 * FRAME
CORK_X = 0.55  # The cork's face, off the wall.
FRAME_X = 0.95
PPI = 100
PPI_CORK = 56
PPI_FRAME = 48
FAR_W, FAR_H = 1008, 672
ATLAS = 4096
rng = np.random.default_rng(44)

FONTS = {
    "sans": r"C:\Windows\Fonts\arial.ttf",
    "bold": r"C:\Windows\Fonts\arialbd.ttf",
    "cond": r"C:\Windows\Fonts\bahnschrift.ttf",
    "mono": r"C:\Windows\Fonts\consola.ttf",
    "impact": r"C:\Windows\Fonts\impact.ttf",
    "pen": r"C:\Windows\Fonts\Inkfree.ttf",
    "pen2": r"C:\Windows\Fonts\segoepr.ttf",
}
INK = (22, 22, 26)
BLUE_PEN = (24, 44, 130)
RED_PEN = (170, 26, 26)
NAVY = (18, 46, 92)


class Doc:
    """A page, drawn in inches from its top left."""

    def __init__(self, w, h, ground=(255, 255, 255)):
        self.w, self.h = w, h
        self.img = Image.new("RGB", (round(w * PPI), round(h * PPI)), ground)
        self.d = ImageDraw.Draw(self.img)

    def font(self, name, pt):
        return ImageFont.truetype(FONTS[name], max(4, round(pt / 72 * PPI)))

    def text(self, x, y, s, name="sans", pt=10, fill=INK, anchor="la"):
        self.d.text((x * PPI, y * PPI), s, font=self.font(name, pt), fill=fill, anchor=anchor)

    def rect(self, x0, y0, x1, y1, fill=None, outline=None, width=0.012):
        self.d.rectangle((x0 * PPI, y0 * PPI, x1 * PPI, y1 * PPI), fill=fill, outline=outline, width=max(1, round(width * PPI)))

    def line(self, x0, y0, x1, y1, fill=INK, width=0.012):
        self.d.line((x0 * PPI, y0 * PPI, x1 * PPI, y1 * PPI), fill=fill, width=max(1, round(width * PPI)))

    def para(self, x, y, w, words, name="sans", pt=9.5, lead=1.32, fill=INK):
        """Wrapped text. Returns the y it ended at."""
        font = self.font(name, pt)
        line = ""
        for word in words.split():
            trial = (line + " " + word).strip()
            if font.getlength(trial) > w * PPI and line:
                self.d.text((x * PPI, y * PPI), line, font=font, fill=fill)
                y += pt / 72 * lead
                line = word
            else:
                line = trial
        if line:
            self.d.text((x * PPI, y * PPI), line, font=font, fill=fill)
            y += pt / 72 * lead
        return y

    def scribble(self, x, y, w, h=0.16, fill=BLUE_PEN):
        """A signature: a pen line that wanders."""
        n = int(w * 14)
        xs = np.linspace(x, x + w, n) * PPI
        r = np.random.default_rng(int(x * 97 + y * 13))
        ys = (y + np.cumsum(r.normal(0, h * 0.34, n)) * 0.25 + np.sin(np.linspace(0, w * 11, n)) * h * 0.5) * PPI
        self.d.line(list(zip(xs.tolist(), ys.tolist())), fill=fill, width=2, joint="curve")

    def trefoil(self, cx, cy, r, fill=INK, ground=(250, 204, 30)):
        box = ((cx - r) * PPI, (cy - r) * PPI, (cx + r) * PPI, (cy + r) * PPI)
        for a in (-90, 30, 150):
            self.d.pieslice(box, a - 30, a + 30, fill=fill)
        inner = r * 0.3
        self.d.ellipse(((cx - inner) * PPI, (cy - inner) * PPI, (cx + inner) * PPI, (cy + inner) * PPI), fill=ground)
        hub = r * 0.2
        self.d.ellipse(((cx - hub) * PPI, (cy - hub) * PPI, (cx + hub) * PPI, (cy + hub) * PPI), fill=fill)

    def photo(self, x0, y0, x1, y1, crop, grey=False):
        art = Image.open(os.path.join(ROOT, "Assets", "ui", "maps", "riverdale.png")).convert("RGB").crop(crop)
        art = art.resize((round((x1 - x0) * PPI), round((y1 - y0) * PPI)), Image.LANCZOS)
        if grey:
            art = art.convert("L").convert("RGB")
        self.img.paste(art, (round(x0 * PPI), round(y0 * PPI)))


def header(p, title, sub=None, colour=NAVY):
    p.rect(0.45, 0.45, p.w - 0.45, 1.25, fill=colour)
    p.text(0.65, 0.57, "RIVERDALE NUCLEAR", "bold", 10, (225, 232, 240))
    p.text(0.65, 0.78, title, "bold", 17, (255, 255, 255))
    if sub:
        p.text(p.w - 0.65, 0.57, sub, "sans", 9, (225, 232, 240), "ra")


def art_radiation():
    y = (250, 204, 30)
    p = Doc(11.69, 8.27, y)
    p.rect(0.3, 0.3, 11.39, 7.97, outline=INK, width=0.14)
    p.trefoil(2.75, 3.9, 2.0, INK, y)
    p.text(5.25, 1.05, "CAUTION", "impact", 86, INK)
    p.text(5.25, 3.0, "RADIATION", "impact", 54, INK)
    p.text(5.25, 3.95, "AREA", "impact", 54, INK)
    p.rect(5.25, 5.15, 10.95, 5.2, fill=INK)
    p.text(5.25, 5.35, "EPD AND TLD MUST BE WORN", "bold", 19, INK)
    p.text(5.25, 5.75, "BEYOND THIS POINT", "bold", 19, INK)
    p.text(5.25, 6.4, "Check in with Radiation Protection before entry.", "sans", 12, INK)
    p.text(5.25, 6.65, "Form RP-12 rev. 6", "mono", 9, INK)
    return p


def art_rota():
    p = Doc(11.69, 8.27)
    header(p, "UNIT 1 OUTAGE: SHIFT ROTA, WEEK 44", "Issued by Ops Planning")
    days = ["CREW", "MON 26", "TUE 27", "WED 28", "THU 29", "FRI 30", "SAT 31", "SUN 1"]
    rows = [("A1", "E E E L L R R"), ("A2", "E E L L N N R"), ("B1", "L L N N R R E"), ("B2", "L N N R R E E"), ("C1", "N N R R E E L"),
            ("C2", "N R R E E L L"), ("D1", "R R E E L L N"), ("D2", "R E E L L N N"), ("RP", "E L N E L N R"), ("CHEM", "E E E E E R R"),
            ("CRANE", "D D D D D R R"), ("FUEL", "D D D D D D R")]
    x0, y0, cw, rh = 0.45, 1.45, (11.69 - 0.9) / 8, 0.41
    tint = {"E": (214, 234, 248), "L": (255, 236, 196), "N": (205, 205, 224), "R": (255, 255, 255), "D": (216, 240, 214)}
    p.rect(x0, y0, x0 + cw * 8, y0 + rh, fill=(226, 228, 232))
    for k, name in enumerate(days):
        p.text(x0 + cw * (k + 0.5), y0 + rh / 2, name, "bold", 9.5, INK, "mm")
    for j, (crew, codes) in enumerate(rows):
        yy = y0 + rh * (j + 1)
        p.text(x0 + cw / 2, yy + rh / 2, crew, "bold", 10, INK, "mm")
        for k, code in enumerate(codes.split()):
            p.rect(x0 + cw * (k + 1), yy, x0 + cw * (k + 2), yy + rh, fill=tint[code])
            p.text(x0 + cw * (k + 1.5), yy + rh / 2, code, "sans", 10.5, INK, "mm")
    for j in range(len(rows) + 2):
        p.line(x0, y0 + rh * j, x0 + cw * 8, y0 + rh * j, (90, 92, 98))
    for k in range(9):
        p.line(x0 + cw * k, y0, x0 + cw * k, y0 + rh * (len(rows) + 1), (90, 92, 98))
    p.text(0.45, 6.92, "E 06:00-14:00   L 14:00-22:00   N 22:00-06:00   D 08:00-16:30   R rest", "sans", 9.5, INK)
    p.text(0.45, 7.2, "Changes go through the shift manager. No swaps on crane or fuel crews without sign-off.", "sans", 9.5, INK)
    # A highlighter across one crew, and a note in pen over the top.
    high = Image.new("RGB", p.img.size, (255, 255, 255))
    ImageDraw.Draw(high).rectangle((int(x0 * PPI), int((y0 + rh * 4.08) * PPI), int((x0 + cw * 8) * PPI), int((y0 + rh * 4.92) * PPI)), fill=(250, 244, 90))
    p.img = Image.fromarray((np.asarray(p.img, np.float32) * np.asarray(high, np.float32) / 255).astype(np.uint8))
    p.d = ImageDraw.Draw(p.img)
    p.text(7.15, 7.42, "Thu swap with Dan - OK'd", "pen", 20, BLUE_PEN)
    p.d.ellipse((int((x0 + cw * 4) * PPI), int((y0 + rh * 4) * PPI), int((x0 + cw * 5) * PPI), int((y0 + rh * 5) * PPI)), outline=RED_PEN, width=3)
    return p


def art_muster():
    green = (0, 122, 72)
    p = Doc(8.27, 11.69)
    p.rect(0, 0, 8.27, 1.7, fill=green)
    p.text(4.13, 0.62, "EMERGENCY", "impact", 40, (255, 255, 255), "mm")
    p.text(4.13, 1.25, "MUSTER POINTS", "bold", 22, (255, 255, 255), "mm")
    p.rect(0.5, 2.0, 7.77, 7.9, fill=(238, 240, 236), outline=INK, width=0.03)
    # The site from above: halls, the pool, the road and the way out.
    grey, dark = (188, 192, 196), (120, 124, 130)
    p.rect(1.0, 2.5, 4.3, 5.9, fill=grey, outline=dark)
    p.d.ellipse((int(2.0 * PPI), int(3.5 * PPI), int(3.3 * PPI), int(4.8 * PPI)), fill=(120, 196, 214), outline=dark, width=2)
    p.text(2.65, 2.72, "REACTOR HALL", "bold", 9, INK, "mm")
    p.rect(4.7, 2.5, 7.2, 3.6, fill=grey, outline=dark)
    p.text(5.95, 3.05, "ANNEXE A1", "bold", 9, INK, "mm")
    p.rect(4.7, 4.0, 7.2, 5.1, fill=grey, outline=dark)
    p.text(5.95, 4.55, "CONTROL", "bold", 9, INK, "mm")
    p.rect(0.5, 6.25, 7.77, 6.85, fill=(214, 216, 212))
    p.text(4.13, 6.55, "PERIMETER ROAD", "sans", 9, (70, 72, 76), "mm")
    for (x0, y0, x1, y1) in ((2.6, 5.9, 2.6, 7.05), (5.9, 5.1, 5.9, 7.05), (2.6, 7.05, 5.9, 7.05)):
        p.line(x0, y0, x1, y1, green, 0.09)
    for cx, label in ((2.6, "M1"), (5.9, "M2")):
        p.d.ellipse((int((cx - 0.34) * PPI), int(7.05 * PPI), int((cx + 0.34) * PPI), int(7.73 * PPI)), fill=green)
        p.text(cx, 7.39, label, "bold", 15, (255, 255, 255), "mm")
    p.d.ellipse((int(3.7 * PPI), int(5.2 * PPI), int(4.0 * PPI), int(5.5 * PPI)), fill=(210, 20, 20))
    p.text(4.08, 5.25, "YOU ARE HERE", "bold", 8.5, (190, 10, 10))
    y = 8.2
    for line in ("1  Leave by the nearest exit. Do not stop to collect belongings.", "2  Go to your muster point and swipe your badge.", "3  Stay there until the Emergency Controller stands you down.", "4  Report anyone you know to be missing."):
        p.text(0.55, y, line, "sans", 11, INK)
        y += 0.32
    p.rect(0.5, 9.75, 7.77, 11.2, fill=(236, 240, 236), outline=green, width=0.03)
    p.text(0.7, 9.92, "SITE ALARM", "bold", 12, green)
    p.text(0.7, 10.25, "Rising tone: take cover indoors", "sans", 11, INK)
    p.text(0.7, 10.55, "Steady tone: evacuate to muster", "sans", 11, INK)
    p.text(0.7, 10.85, "Emergency control room: ext 2222", "bold", 11, INK)
    return p


TOOLBOX = ("Most dropped objects on this site are hand tools, and most of them fall less than two metres. From the refuelling floor that is enough to "
           "put a 19 mm socket through a hard hat or into the pool, where a recovery can stop fuel moves for a whole shift. Every tool above the "
           "toe boards is tethered, every tether is checked at the start of the task, and every tool is counted back in at the end of it.")


def art_toolbox():
    p = Doc(8.27, 11.69)
    header(p, "TOOLBOX TALK No. 37", "Read and sign")
    p.text(0.55, 1.45, "Dropped objects over the fuel pool", "bold", 16, INK)
    p.photo(4.5, 1.95, 7.75, 4.0, (620, 180, 1460, 700), grey=True)
    p.rect(4.5, 1.95, 7.75, 4.0, outline=INK)
    p.text(4.5, 4.05, "Refuelling floor, last outage.", "sans", 7.5, (70, 72, 76))
    p.para(0.55, 1.95, 3.7, TOOLBOX, "sans", 9.5, 1.34)
    y = 4.4
    p.text(0.55, y, "Before you start", "bold", 12, INK)
    y += 0.3
    for k, line in enumerate(("Tether every tool above the toe boards, and check the tethers.", "Tool count in, tool count out. Write both on the permit.", "Pockets empty: pens, keys and badges on a lanyard only.", "Anything dropped is reported straight away, even if you got it back.", "Stop the job if the crane is moving overhead.")):
        y = p.para(0.55, y, 7.1, f"{k + 1}.  {line}", "sans", 10.5, 1.36)
        y += 0.05
    y += 0.15
    p.text(0.55, y, "Crew sign-off", "bold", 12, INK)
    y += 0.28
    for row in range(8):
        p.line(0.55, y + 0.32 * (row + 1), 7.72, y + 0.32 * (row + 1), (120, 122, 128))
        if row < 5:
            p.scribble(1.0, y + 0.32 * row + 0.17, 1.2 + (row * 37 % 7) * 0.09, fill=BLUE_PEN if row % 3 else INK)
            p.text(4.6, y + 0.32 * row + 0.04, ("26 Oct", "26 Oct", "27 Oct", "27 Oct", "28 Oct")[row], "pen", 13, BLUE_PEN)
    return p


def art_openday():
    p = Doc(8.27, 11.69)
    p.photo(0, 0, 8.27, 5.6, (420, 90, 1500, 820))
    p.rect(0, 5.6, 8.27, 7.75, fill=(6, 92, 150))
    p.text(0.5, 5.85, "FAMILY", "impact", 46, (255, 255, 255))
    p.text(0.5, 6.7, "OPEN DAY", "impact", 46, (255, 212, 40))
    p.text(0.55, 8.05, "Saturday 14 November, 10:00 to 16:00", "bold", 17, INK)
    y = 8.55
    for line in ("Tours of the visitor centre and the turbine viewing gallery", "Face painting, food vans and the fire crew's engine", "Bring a partner, the kids or your mum. Photo ID for over-16s."):
        p.text(0.55, y, line, "sans", 12.5, INK)
        y += 0.34
    p.rect(0.55, 10.0, 7.72, 11.1, outline=(6, 92, 150), width=0.03)
    p.text(0.8, 10.17, "Sign up with HR by 6 November", "bold", 14, (6, 92, 150))
    p.text(0.8, 10.55, "ext 3310 or the sheet outside the canteen", "sans", 12, INK)
    return p


def art_dosimetry():
    p = Doc(8.27, 11.69)
    header(p, "TLD BADGE RETURN LOG", "Period 10")
    p.para(0.55, 1.42, 7.1, "Return your badge to the RP office within 5 working days of the end of the period. Late badges are chased through your line manager.", "sans", 9.5)
    y0, rh = 2.05, 0.42
    cols = (0.55, 1.75, 4.25, 5.55, 7.72)
    p.rect(cols[0], y0, cols[-1], y0 + rh, fill=(226, 228, 232))
    for x, name in zip(cols, ("Badge", "Name", "Date", "Initials")):
        p.text(x + 0.08, y0 + 0.12, name, "bold", 10, INK)
    entries = (("4471", "D. Marsh", "2/10"), ("4475", "A. Okafor", "2/10"), ("4482", "S. Lindqvist", "3/10"), ("4490", "P. Wren", "3/10"), ("4493", "R. Haddad", "3/10"),
               ("4501", "J. Teague", "5/10"), ("4507", "M. Sato", "5/10"), ("4512", "L. Brandt", "5/10"), ("4518", "K. Nowak", "6/10"), ("4520", "T. Harlow", "9/10"), ("4533", "E. Vance", "9/10"))
    for j in range(20):
        y = y0 + rh * (j + 1)
        if j < len(entries):
            badge, name, date = entries[j]
            p.text(cols[0] + 0.1, y + 0.05, badge, "pen", 15, BLUE_PEN if j % 4 else INK)
            p.text(cols[1] + 0.1, y + 0.05, name, "pen", 15, BLUE_PEN if j % 4 else INK)
            p.text(cols[2] + 0.1, y + 0.05, date, "pen", 15, BLUE_PEN if j % 4 else INK)
            p.scribble(cols[3] + 0.25, y + 0.22, 0.75 + j % 3 * 0.18, 0.1, BLUE_PEN if j % 4 else INK)
    for j in range(22):
        p.line(cols[0], y0 + rh * j, cols[-1], y0 + rh * j, (120, 122, 128))
    for x in cols:
        p.line(x, y0, x, y0 + rh * 21, (120, 122, 128))
    return p


CAR_TABS = 8
CAR_BODY = 3.7


def art_carshare():
    p = Doc(6.2, CAR_BODY + 1.5, (255, 255, 255))
    p.text(3.1, 0.62, "CAR SHARE", "impact", 44, INK, "mm")
    p.text(3.1, 1.32, "Shift C, from the Harbour Road side", "bold", 15, INK, "mm")
    p.text(3.1, 1.76, "Two seats free, Mon to Fri, back by 23:00", "sans", 12, INK, "mm")
    p.text(3.1, 2.2, "You chip in for fuel. I bring the coffee.", "sans", 12, INK, "mm")
    p.text(3.1, 2.8, "Sam, ext 4471", "bold", 21, INK, "mm")
    tab = 6.2 / CAR_TABS
    tall = Image.new("RGB", (round(1.42 * PPI), round(tab * PPI)), (255, 255, 255))
    d = ImageDraw.Draw(tall)
    d.text((6, tall.height // 2), "Sam ext 4471", font=ImageFont.truetype(FONTS["bold"], 19), fill=INK, anchor="lm")
    d.text((6, tall.height // 2 + 22), "car share", font=ImageFont.truetype(FONTS["sans"], 14), fill=INK, anchor="lm")
    tall = tall.rotate(90, expand=True)
    for k in range(CAR_TABS):
        p.img.paste(tall, (round((k * tab) * PPI), round((CAR_BODY + 0.08) * PPI)))
    return p


def art_canteen():
    p = Doc(5.83, 8.27, (255, 255, 255))
    p.text(2.91, 0.7, "CANTEEN", "impact", 46, (150, 40, 10), "mm")
    p.text(2.91, 1.3, "Lunch this week, 11:30 to 14:00", "bold", 12, INK, "mm")
    y = 1.75
    for day, a, b in (("MON", "Cottage pie", "Lentil dhal"), ("TUE", "Chicken curry", "Veg chilli"), ("WED", "Fish and chips", "Halloumi wrap"), ("THU", "Sausage and mash", "Mushroom stroganoff"), ("FRI", "Pizza day", "Pizza day")):
        p.text(0.5, y, day, "bold", 13, (150, 40, 10))
        p.text(1.3, y, a, "sans", 12, INK)
        p.text(1.3, y + 0.26, b, "sans", 11, (70, 60, 56))
        p.line(0.5, y + 0.62, 5.33, y + 0.62, (150, 120, 100))
        y += 0.82
    p.text(2.91, 6.25, "Night shift hot food 01:00 to 02:00", "bold", 11, INK, "mm")
    p.text(2.91, 6.65, "No cash on site. Badge or card only.", "sans", 11, INK, "mm")
    p.text(0.5, 7.25, "bring back the chips!!", "pen", 25, BLUE_PEN)
    return p


def art_note(lines, size=3.0, pen="pen", ink=BLUE_PEN, pt=26):
    p = Doc(size, size)
    y = 0.42
    for line in lines:
        p.text(0.22, y, line, pen, pt, ink)
        y += pt / 72 * 1.12
    return p


def art_card():
    p = Doc(3.6, 2.15)
    p.rect(0, 0, 3.6, 0.42, fill=(190, 30, 30))
    p.text(1.8, 0.21, "ON-CALL ELECTRICIAN", "bold", 12, (255, 255, 255), "mm")
    p.text(1.8, 0.85, "ext 2290", "impact", 30, INK, "mm")
    p.text(1.8, 1.32, "After hours, via the gatehouse", "sans", 9.5, INK, "mm")
    p.text(1.8, 1.65, "Do not reset breakers yourself", "bold", 9.5, (190, 30, 30), "mm")
    return p


PAPER = (0.945, 0.935, 0.895)
# In order from the cork up. c is the middle on the cork (inches from its bottom left), rot in degrees. curl: bottom left, bottom right, top left, top
# right, in inches off the cork. pins: (s, t, colour) as fractions of the sheet, t from its bottom.
SHEETS = [
    dict(name="dosimetry", art=art_dosimetry, c=(15.0, 6.25), rot=-0.8, curl=(0.28, 0.1, 0.0, 0.0), pins=[(0.5, 0.965, "white")], fade=0.1, fold=True),
    dict(name="radiation", art=art_radiation, c=(6.65, 16.95), rot=-0.6, curl=(0.06, 0.1, 0.02, 0.02), pins=[(0.03, 0.96, "red"), (0.97, 0.96, "red"), (0.03, 0.04, "red"), (0.97, 0.04, "red")], kind="laminate", fade=0.05),
    dict(name="rota", art=art_rota, c=(27.6, 17.2), rot=0.9, curl=(0.16, 0.18, 0.0, 0.0), pins=[(0.04, 0.955, "blue"), (0.96, 0.955, "blue")], fade=0.03),
    dict(name="muster", art=art_muster, c=(17.1, 15.9), rot=0.25, curl=(0.05, 0.04, 0.03, 0.03), pins=[(0.04, 0.97, "brass"), (0.96, 0.97, "brass"), (0.04, 0.03, "brass"), (0.96, 0.03, "brass")], kind="laminate", fade=0.0),
    dict(name="toolbox", art=art_toolbox, c=(5.6, 6.25), rot=-1.3, curl=(0.42, 0.16, 0.0, 0.0), pins=[(0.5, 0.97, "yellow")], fade=0.2),
    dict(name="openday", art=art_openday, c=(29.5, 6.55), rot=1.5, curl=(0.12, 0.5, 0.0, 0.02), pins=[(0.5, 0.975, "red")], fade=0.08),
    dict(name="canteen", art=art_canteen, c=(22.5, 9.65), rot=2.4, curl=(0.2, 0.26, 0.0, 0.05), pins=[(0.5, 0.96, "green")], paper=(0.98, 0.72, 0.42), fade=0.12),
    dict(name="carshare", art=art_carshare, c=(21.9, 2.92), rot=-1.8, curl=(0.0, 0.0, 0.0, 0.0), pins=[(0.08, 0.95, "white"), (0.92, 0.95, "white")], paper=(0.72, 0.95, 0.24), kind="carshare", fade=0.05),
    dict(name="card", art=art_card, c=(11.95, 11.75), rot=-3.2, curl=(0.06, 0.1, 0.0, 0.03), pins=[(0.5, 0.88, "blue")], fade=0.0),
    dict(name="note_a", art=lambda: art_note(["Locker 12", "cleared by", "Fri or RP", "bin it!"], ink=INK), c=(12.4, 7.4), rot=2.5, curl=(0.2, 0.34, 0.0, 0.0), paper=(0.99, 0.91, 0.36), kind="note"),
    dict(name="note_b", art=lambda: art_note(["WHO HAS", "the 19mm", "socket??", "- Dan"], pen="pen2", ink=(150, 20, 40), pt=20), c=(32.5, 13.2), rot=-6.0, curl=(0.38, 0.18, 0.0, 0.0), paper=(0.98, 0.56, 0.68), kind="note"),
    dict(name="note_c", art=lambda: art_note(["Crane PM", "moved to", "THURSDAY"], pt=27), c=(26.6, 11.4), rot=4.2, curl=(0.14, 0.26, 0.0, 0.0), paper=(0.58, 0.92, 0.62), kind="note"),
]


# ---------------------------------------------------------------------------------------------------------------------
# Where things are, and how the paper lies
# ---------------------------------------------------------------------------------------------------------------------


def smooth(a, b, x):
    t = np.clip((x - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)


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
        self.base = 0.012 + layer * 0.022
        self.layer = layer
        self.pins = [(s * self.w, t * self.h, colour) for s, t, colour in info.get("pins", [])]
        self.seed = 1000 + layer * 7
        self.wave = np.random.default_rng(self.seed).uniform(0, 6.28, 4)
        self.under = None

    def stand(self, s, t):
        """Height off the cork at (s, t): its base and lift, always clear of the sheets beneath it."""
        height = self.base + self.lift(s, t)
        if self.under is None:
            return height
        u, v = self.board(np.asarray(s, float), np.asarray(t, float))
        floor = ndi.map_coordinates(self.under, (np.asarray(v) * PPI_STACK - 0.5, np.asarray(u) * PPI_STACK - 0.5), order=1, mode="nearest")
        return np.maximum(height, floor + 0.014)

    def board(self, s, t):
        """Cork coordinates of a sheet point, s and t in inches from the sheet's bottom left."""
        ds, dt = s - self.w / 2, t - self.h / 2
        return self.c[0] + ds * self.ax[0] + dt * self.ay[0], self.c[1] + ds * self.ax[1] + dt * self.ay[1]

    def local(self, u, v):
        du, dv = u - self.c[0], v - self.c[1]
        return du * self.ax[0] + dv * self.ax[1] + self.w / 2, du * self.ay[0] + dv * self.ay[1] + self.h / 2

    def lift(self, s, t):
        """How far the sheet stands off its base at (s, t), inches."""
        s, t = np.asarray(s, float), np.asarray(t, float)
        bl, br, tl, tr = self.info.get("curl", (0, 0, 0, 0))
        reach = 0.62 * min(self.w, self.h)
        total = np.zeros_like(s)
        for value, cs, ct in ((bl, 0, 0), (br, self.w, 0), (tl, 0, self.h), (tr, self.w, self.h)):
            if value:
                d = np.hypot(s - cs, t - ct) / reach
                total += value * (1 - smooth(0, 1, d)) ** 1.6
        stiff = 0.012 if self.kind == "laminate" else 0.05
        ripple = (np.sin(s * 0.9 + self.wave[0]) * np.sin(t * 0.7 + self.wave[1]) + 0.5 * np.sin(s * 0.33 + t * 0.41 + self.wave[2]) + 1.5) * stiff
        total += ripple
        if self.kind == "note":
            # Its glue holds the top strip flat, and the rest bows away.
            total = total * smooth(0.8, 0.45, t / self.h) + 0.42 * self.info["curl"][0] * (1 - np.clip(t / (0.78 * self.h), 0, 1)) ** 2
        for ps, pt, _ in self.pins:
            total *= smooth(0.12, 1.5, np.hypot(s - ps, t - pt))
        if self.info.get("fold"):
            total += 0.05 * np.clip(1 - np.abs(t - self.h / 2) / 0.55, 0, 1)
        return total


PPI_STACK = 20
LAYERS = []
_layer = 0
for _info in SHEETS:
    LAYERS.append(Page(_info, _layer))
    _layer += 1
print("pages", [(p.name, p.w, p.h) for p in LAYERS], flush=True)

# Each sheet learns how high the ones below it stand, and pins that a later sheet covers come out.
_rows, _cols = round(CORK_H * PPI_STACK), round(CORK_W * PPI_STACK)
_gv, _gu = np.mgrid[0:_rows, 0:_cols].astype(np.float32)
_gu, _gv = (_gu + 0.5) / PPI_STACK, (_gv + 0.5) / PPI_STACK
_stack = np.zeros((_rows, _cols), np.float32)
for _page in LAYERS:
    _page.under = ndi.maximum_filter(_stack, size=int(1.9 * PPI_STACK) | 1)
    _s, _t = _page.local(_gu, _gv)
    _inside = (_s >= 0) & (_s <= _page.w) & (_t >= 0) & (_t <= _page.h)
    _height = _page.stand(np.clip(_s, 0, _page.w), np.clip(_t, 0, _page.h))
    _stack = np.where(_inside, np.maximum(_stack, _height), _stack)
for _k, _page in enumerate(LAYERS):
    _kept = []
    for _pin in _page.pins:
        _u, _v = _page.board(_pin[0], _pin[1])
        _covered = False
        for _other in LAYERS[_k + 1 :]:
            _s, _t = _other.local(_u, _v)
            if -0.25 <= _s <= _other.w + 0.25 and -0.25 <= _t <= _other.h + 0.25:
                _covered = True
        if _covered:
            print("pin under another sheet, left out:", _page.name, _pin[2], flush=True)
        else:
            _kept.append(_pin)
    _page.pins = _kept


# ---------------------------------------------------------------------------------------------------------------------
# The atlas
# ---------------------------------------------------------------------------------------------------------------------

GUTTER = 8
rects = {"cork": (round(CORK_W * PPI_CORK), round(CORK_H * PPI_CORK)), "far": (FAR_W, FAR_H), "back": (96, 96), "swatch": (240, 48)}
FRAME_T = 64  # Strip height in texels for the frame's profile.
rects.update({"frame_top": (round(W * PPI_FRAME), FRAME_T), "frame_bottom": (round(W * PPI_FRAME), FRAME_T), "frame_left": (round(H * PPI_FRAME), FRAME_T), "frame_right": (round(H * PPI_FRAME), FRAME_T)})
for page in LAYERS:
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
ROUGH = np.full((ATLAS, ATLAS), 0.8, np.float32)
METAL = np.zeros((ATLAS, ATLAS), np.float32)
AO = np.ones((ATLAS, ATLAS), np.float32)
COVER = np.zeros((ATLAS, ATLAS), bool)


def to_normal(height, ppi):
    """Tangent-space OpenGL normal of a height in inches, rows top-down as images are."""
    dr, dc = np.gradient(height)
    n = np.stack((-dc * ppi, dr * ppi, np.ones_like(height)), -1)
    return n / np.linalg.norm(n, axis=-1, keepdims=True)


def blobs(shape, sigma, seed):
    """Smooth noise about 0, roughly -1 to 1."""
    r = np.random.default_rng(seed).normal(size=(max(4, shape[0] // 4), max(4, shape[1] // 4)))
    r = ndi.gaussian_filter(r, sigma / 4, mode="wrap")
    r = ndi.zoom(r, (shape[0] / r.shape[0], shape[1] / r.shape[1]), order=1)[: shape[0], : shape[1]]
    return r / (r.std() * 2.5 + 1e-6)


def put(name, colour=None, normal=None, rough=None, metal=None, ao=None):
    x, y, w, h = place[name]
    if colour is not None:
        COLOUR[y : y + h, x : x + w] = colour
    if normal is not None:
        NORMAL[y : y + h, x : x + w] = normal
    if rough is not None:
        ROUGH[y : y + h, x : x + w] = rough
    if metal is not None:
        METAL[y : y + h, x : x + w] = metal
    if ao is not None:
        AO[y : y + h, x : x + w] = ao
    COVER[y : y + h, x : x + w] = True


# ---------------------------------------------------------------------------------------------------------------------
# Shadows: what each layer gets from those above it, on a grid over the cork
# ---------------------------------------------------------------------------------------------------------------------

PPI_SHADE = 40
sh, sw = round(CORK_H * PPI_SHADE), round(CORK_W * PPI_SHADE)
grid_v, grid_u = np.mgrid[0:sh, 0:sw].astype(np.float32)
grid_u = (grid_u + 0.5) / PPI_SHADE
grid_v = (grid_v + 0.5) / PPI_SHADE  # Rows here run from the cork's bottom.


def cast_of(page):
    s, t = page.local(grid_u, grid_v)
    inside = (s >= 0) & (s <= page.w) & (t >= 0) & (t <= page.h)
    lift = np.where(inside, page.lift(np.clip(s, 0, page.w), np.clip(t, 0, page.h)), 0.0)
    mask = inside.astype(np.float32)
    tight = ndi.gaussian_filter(np.roll(mask, -2, 0), 0.05 * PPI_SHADE)
    wide = ndi.gaussian_filter(np.roll(mask, -6, 0), 0.26 * PPI_SHADE)
    # Standing proud of the cork spreads the shadow.
    away = ndi.gaussian_filter(lift, 0.4 * PPI_SHADE)
    return 1 - 0.46 * tight * (1 - smooth(0.0, 0.5, away) * 0.5) - 0.3 * wide * smooth(0.02, 0.5, away)


def pin_cast_of(page):
    cast = np.ones((sh, sw), np.float32)
    for ps, pt, _ in page.pins:
        pu, pv = page.board(ps, pt)
        d = np.hypot(grid_u - pu - 0.03, grid_v - pv + 0.09)
        cast *= 1 - 0.72 * (1 - smooth(0.09, 0.3, d))
    return cast


shade_of = {}
above = np.ones((sh, sw), np.float32)
for page in reversed(LAYERS):
    above = above * pin_cast_of(page)
    shade_of[page.name] = above.copy()
    above = above * cast_of(page)
shade_of["cork"] = above
# The frame's lip shades the cork round its edge.
edge = np.minimum.reduce((grid_u, grid_v, CORK_W - grid_u, CORK_H - grid_v))
frame_shade = 0.55 + 0.45 * smooth(0.0, 0.42, edge)
for key in shade_of:
    shade_of[key] = shade_of[key] * frame_shade
print("shadows done", flush=True)


# ---------------------------------------------------------------------------------------------------------------------
# Cork: agglomerated grains, dark bark flecks, pin holes, and the pale ghosts of sheets long gone
# ---------------------------------------------------------------------------------------------------------------------


def paint_cork():
    x, y, w, h = place["cork"]
    r = np.random.default_rng(7)
    rows, cols = np.mgrid[0:h, 0:w].astype(np.float32)
    pts = np.c_[((cols + 0.5) / PPI_CORK).ravel(), ((rows + 0.5) / PPI_CORK).ravel()]

    def cells(size, seed):
        q = np.random.default_rng(seed)
        n = int(CORK_W * CORK_H / size**2)
        seeds = q.random((n, 2)) * (CORK_W, CORK_H)
        dist, index = cKDTree(seeds).query(pts, k=2, workers=4)
        return dist[:, 0].reshape(h, w), dist[:, 1].reshape(h, w), index[:, 0].reshape(h, w), n

    f1, f2, index, n = cells(0.105, 1)
    print("cork cells", n, flush=True)
    tone = r.normal(1.0, 0.12, n)
    kind = r.random(n)
    base = np.array((0.735, 0.555, 0.355), np.float32)  # sRGB, a warm mid tan.
    colour = np.empty((n, 3), np.float32)
    colour[:] = base
    colour *= tone[:, None]
    dark = kind < 0.045
    colour[dark] = np.array((0.33, 0.21, 0.12), np.float32) * r.uniform(0.75, 1.25, dark.sum())[:, None]
    mid = (kind >= 0.045) & (kind < 0.17)
    colour[mid] = np.array((0.56, 0.39, 0.23), np.float32) * r.uniform(0.85, 1.15, mid.sum())[:, None]
    light = (kind > 0.87)
    colour[light] = np.array((0.85, 0.69, 0.48), np.float32) * r.uniform(0.9, 1.08, light.sum())[:, None]
    art = colour[index]
    crevice = smooth(0.0, 0.03, f2 - f1)
    art = art * (0.66 + 0.34 * crevice)[..., None]
    # Fine grains inside the big ones.
    g1, g2, gi, gn = cells(0.042, 2)
    fine = np.random.default_rng(3).normal(1.0, 0.09, gn)[gi]
    art = art * (fine * (0.82 + 0.18 * smooth(0.0, 0.016, g2 - g1)))[..., None]
    # Broad stains and handling.
    art = art * (1 + 0.075 * blobs((h, w), 90, 11) + 0.04 * blobs((h, w), 24, 12))[..., None]
    height = 0.016 * crevice + 0.008 * (tone[index] - 1) * 4 + 0.006 * smooth(0.0, 0.016, g2 - g1)
    # Pale ghosts where sheets hung for years and kept the sun off.
    ghost = np.zeros((h, w), np.float32)
    for gu, gv, gw, gh, ga in ((12.2, 18.0, 8.3, 11.7, 3), (31.2, 11.5, 8.3, 11.7, -2), (19.0, 2.6, 11.7, 8.3, 1), (3.0, 12.0, 5.8, 8.3, -4)):
        a = np.radians(ga)
        du, dv = pts[:, 0].reshape(h, w) - gu, (CORK_H - pts[:, 1].reshape(h, w)) - gv
        s, t = du * np.cos(a) + dv * np.sin(a), -du * np.sin(a) + dv * np.cos(a)
        ghost = np.maximum(ghost, (1 - smooth(gw / 2 - 0.1, gw / 2 + 0.1, np.abs(s))) * (1 - smooth(gh / 2 - 0.1, gh / 2 + 0.1, np.abs(t))))
    art = art * (1 + 0.11 * ghost)[..., None]
    # Holes from every pin the board has seen, and the tearing round them.
    holes = np.random.default_rng(23)
    xs, ys = holes.uniform(0, CORK_W, 340), holes.uniform(0, CORK_H, 340)
    mask = np.zeros((h, w), np.float32)
    mask[np.clip((ys * PPI_CORK).astype(int), 0, h - 1), np.clip((xs * PPI_CORK).astype(int), 0, w - 1)] = 1
    hole = np.clip(ndi.gaussian_filter(mask, 1.05) * 7.0, 0, 1)
    art = art * (1 - 0.82 * hole)[..., None]
    height = height - 0.03 * hole
    # Baked shadows, then grime gathering along the bottom rail.
    shade = ndi.zoom(shade_of["cork"], (h / sh, w / sw), order=1)[::-1]
    art = art * (0.5 + 0.5 * shade)[..., None]
    low = 1 - smooth(0, 2.0, (h - rows) / PPI_CORK)
    art = art * (1 - 0.1 * low)[..., None]
    put("cork", np.clip(art, 0, 1), to_normal(ndi.gaussian_filter(height, 0.5), PPI_CORK), np.clip(0.86 + 0.07 * (crevice - 0.5) + 0.05 * hole, 0, 1), 0.0, np.clip(0.55 + 0.45 * shade, 0, 1) * (0.72 + 0.28 * crevice))


# ---------------------------------------------------------------------------------------------------------------------
# Paper, one page at a time
# ---------------------------------------------------------------------------------------------------------------------

RENDERED = {}


def paint_page(page):
    x, y, w, h = place[page.name]
    seed = page.seed
    art = np.asarray(page.doc.img, np.float32) / 255
    # Toner: a slight softness, and ink that isn't quite solid.
    art = ndi.gaussian_filter(art, (0.45, 0.45, 0))
    ink = 1 - art.mean(-1)
    speck = np.random.default_rng(seed).normal(size=(h, w))
    speck = ndi.gaussian_filter(speck, 0.8)
    speck = speck / speck.std()
    art = np.clip(art + (ink * np.clip(speck, -2, 2) * 0.05)[..., None], 0, 1)
    fade = page.info.get("fade", 0)
    art = art + (1 - art) * (fade + 0.05)
    ground = np.array(page.info.get("paper", PAPER), np.float32)
    colour = art * ground
    laminate = page.kind == "laminate"
    note = page.kind == "note"
    fibre = ndi.gaussian_filter(np.random.default_rng(seed + 1).normal(size=(h, w)), (0.6, 1.6))
    fibre = fibre / fibre.std()
    colour = colour * (1 + (0.012 if laminate else 0.022) * fibre)[..., None]
    # Old paper yellows and picks up dirt from the edge in, and from hands low down.
    d_edge = ndi.distance_transform_edt(np.pad(np.ones((h, w), bool), 1, constant_values=False))[1:-1, 1:-1] / PPI
    yellow = (1 - smooth(0.0, 0.7, d_edge)) * (0.03 + fade * 0.6) + np.clip(blobs((h, w), 70, seed + 2), 0, 1) * 0.05
    colour = colour * (1 - yellow[..., None] * np.array((0.0, 0.05, 0.28), np.float32))
    colour = colour * (1 + 0.022 * blobs((h, w), 60, seed + 3))[..., None]
    rows, cols = np.mgrid[0:h, 0:w].astype(np.float32)
    # Heights: fibre, soft wrinkles, the fold, the print's slight relief.
    height = 0.0009 * fibre + 0.0035 * blobs((h, w), 30, seed + 4)
    if not laminate and not note:
        wrinkle = np.abs(blobs((h, w), 40, seed + 5))
        height += 0.012 * smooth(0.12, 0.0, wrinkle) * np.clip(blobs((h, w), 90, seed + 6) + 0.2, 0, 1)
    if laminate:
        height = 0.0002 * fibre + 0.01 * blobs((h, w), 80, seed + 7)
    if page.info.get("fold"):
        band = np.abs(rows - h / 2) / PPI
        height += 0.03 * np.clip(1 - band / 0.5, 0, 1)
        crease = smooth(0.025, 0.0, band)
        colour = colour * (1 - 0.10 * crease)[..., None]
        colour = colour + (np.array((1, 1, 1), np.float32) - colour) * (crease * ink * 0.6)[..., None]
    if page.kind == "carshare":
        # The scissor cuts between the tabs show as lines only on the body's edge; the tabs themselves are their own strips.
        pass
    # A pin dimple, and a coffee ring on the log.
    for ps, pt, _ in page.pins:
        d = np.hypot((cols + 0.5) / PPI - ps, (h - rows - 0.5) / PPI - pt)
        height -= 0.02 * (1 - smooth(0.02, 0.2, d))
    if page.name == "dosimetry":
        d = np.hypot((cols + 0.5) / PPI - 6.1, (rows + 0.5) / PPI - 9.7)
        ring = np.exp(-(((d - 1.32) / 0.05) ** 2)) * 0.5 + np.exp(-(((d - 1.26) / 0.2) ** 2)) * 0.1 + (d < 1.3) * 0.05
        ring = ring * (0.6 + 0.4 * blobs((h, w), 24, seed + 8))
        colour = colour * (1 - np.clip(ring, 0, 1)[..., None] * np.array((0.28, 0.42, 0.62), np.float32))
    # Shadows from whatever lies on top, at this page's own place on the board.
    uu, vv = page.board((cols + 0.5) / PPI, (h - rows - 0.5) / PPI)
    shade = ndi.map_coordinates(shade_of[page.name], (vv * PPI_SHADE - 0.5, uu * PPI_SHADE - 0.5), order=1, mode="nearest")
    outside = (uu < 0) | (uu > CORK_W) | (vv < 0) | (vv > CORK_H)
    shade = np.where(outside, 1.0, shade)
    RENDERED[page.name] = np.clip(colour * (0.45 + 0.55 * shade)[..., None], 0, 1)
    rough = np.full((h, w), 0.27 if laminate else (0.62 if note else 0.8), np.float32)
    rough = rough + (0.02 if laminate else 0.05) * blobs((h, w), 40, seed + 9)
    if not laminate:
        rough = rough - 0.1 * ink  # Toner has a slight sheen.
    put(page.name, RENDERED[page.name], to_normal(height, PPI), np.clip(rough, 0.05, 1), 0.0, np.clip(0.5 + 0.5 * shade, 0, 1))


# ---------------------------------------------------------------------------------------------------------------------
# The frame, pins and plastic
# ---------------------------------------------------------------------------------------------------------------------


def paint_frame():
    for name, seed in (("frame_top", 31), ("frame_bottom", 32), ("frame_left", 33), ("frame_right", 34)):
        x, y, w, h = place[name]
        r = np.random.default_rng(seed)
        streak = ndi.gaussian_filter(r.normal(size=(h, w)), (0.5, 14))
        streak = streak / streak.std()
        scuff = np.clip(blobs((h, w), 22, seed + 10) - 0.45, 0, 1) * 2.2
        tone = 0.70 + 0.022 * streak - 0.1 * scuff + 0.03 * blobs((h, w), 50, seed + 11)
        colour = np.stack((tone, tone * 1.005, tone * 1.02), -1)
        height = 0.0014 * streak - 0.002 * scuff
        rough = 0.42 + 0.03 * streak + 0.22 * scuff
        # Dust lies along the top bars and in the lip.
        if name == "frame_bottom":
            dust = np.clip(blobs((h, w), 30, seed + 12) + 0.35, 0, 1)
            colour = colour * (1 - dust * 0.2)[..., None]
            rough = rough + dust * 0.25
        put(name, np.clip(colour, 0, 1), to_normal(height, PPI_FRAME), np.clip(rough, 0.1, 1), 0.68 * (1 - np.clip(scuff * 0.3, 0, 1)), 1.0)


SWATCH = {"red": (0.76, 0.05, 0.05), "blue": (0.05, 0.19, 0.62), "yellow": (0.95, 0.74, 0.05), "green": (0.04, 0.5, 0.2), "white": (0.86, 0.86, 0.83), "brass": (0.80, 0.62, 0.28), "plastic": (0.11, 0.115, 0.125), "needle": (0.6, 0.6, 0.62)}


def paint_small():
    x, y, w, h = place["swatch"]
    colour = np.zeros((h, w, 3), np.float32)
    rough = np.full((h, w), 0.28, np.float32)
    metal = np.zeros((h, w), np.float32)
    names = list(SWATCH)
    step = w / len(names)
    for k, name in enumerate(names):
        c0, c1 = round(k * step), round((k + 1) * step)
        colour[:, c0:c1] = SWATCH[name]
        if name == "brass":
            rough[:, c0:c1], metal[:, c0:c1] = 0.38, 0.92
        if name == "plastic":
            rough[:, c0:c1] = 0.58
    put("swatch", colour, None, rough, metal, 1.0)
    # The backs of sheets: plain paper.
    x, y, w, h = place["back"]
    put("back", np.full((h, w, 3), (0.8, 0.79, 0.75), np.float32), None, 0.82, 0.0, 0.8)


def swatch_uv(name):
    x, y, w, h = place["swatch"]
    k = list(SWATCH).index(name)
    return np.array((x + (k + 0.5) * w / len(SWATCH), y + h / 2), np.float32)


def composite_far():
    """The whole board as one picture, for the far LODs and for checking the layout."""
    scale = 2
    pw, ph = FAR_W * scale, FAR_H * scale
    ppi = pw / W
    out = Image.new("RGB", (pw, ph), (150, 152, 156))
    x, y, w, h = place["cork"]
    cork = Image.fromarray((COLOUR[y : y + h, x : x + w] * 255).astype(np.uint8)).resize((round(CORK_W * ppi), round(CORK_H * ppi)), Image.LANCZOS)
    out.paste(cork, (round(FRAME * ppi), round(FRAME * ppi)))
    draw = ImageDraw.Draw(out)
    f = round(FRAME * ppi)
    draw.rectangle((0, 0, pw, ph), outline=(186, 188, 192), width=round(f * 0.72))
    draw.rectangle((f - 3, f - 3, pw - f + 3, ph - f + 3), outline=(98, 100, 104), width=3)
    for page in LAYERS:
        art = RENDERED[page.name]
        hh, ww = art.shape[:2]
        rgba = Image.fromarray(np.dstack(((art * 255).astype(np.uint8), np.full((hh, ww), 255, np.uint8))))
        small = rgba.resize((max(2, round(page.w * ppi)), max(2, round(page.h * ppi))), Image.LANCZOS)
        turned = small.rotate(page.info["rot"], expand=True, resample=Image.BICUBIC)
        cx = (FRAME + page.c[0]) * ppi
        cy = ph - (FRAME + page.c[1]) * ppi
        out.paste(turned, (round(cx - turned.width / 2), round(cy - turned.height / 2)), turned)
    draw = ImageDraw.Draw(out)
    for page in LAYERS:
        for ps, pt, colour in page.pins:
            u, v = page.board(ps, pt)
            px, py = (FRAME + u) * ppi, ph - (FRAME + v) * ppi
            r = 0.17 * ppi
            c = tuple(int(a * 255) for a in SWATCH[colour])
            draw.ellipse((px - r, py - r, px + r, py + r), fill=c)
    far = out.resize((FAR_W, FAR_H), Image.LANCZOS)
    far.save(os.path.join(REVIEW, "layout.png"))
    arr = np.asarray(far, np.float32) / 255
    put("far", arr, None, 0.72, 0.0, 1.0)


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
        """a b c d counter-clockwise from outside."""
        a, b, c, d = (np.asarray(v, np.float64) for v in (a, b, c, d))
        if normal is None:
            normal = np.cross(c - a, d - b)
            normal = normal / (np.linalg.norm(normal) + 1e-12)
        na = np.broadcast_to(normal, (3, 3)) if np.ndim(normal) == 1 else None
        self.tri((a, b, c), (ta, tb, tc), na)
        self.tri((a, c, d), (ta, tc, td), na)

    def grid(self, pos, uv, flip=False):
        """A grid of positions (rows, cols, 3) with UVs in texels, smooth normals from its own shape. Faces towards +X unless flipped."""
        rows, cols = pos.shape[:2]
        dr = np.gradient(pos, axis=0)
        dc = np.gradient(pos, axis=1)
        nor = np.cross(dc, dr)
        nor = nor / (np.linalg.norm(nor, axis=-1, keepdims=True) + 1e-12)
        if flip:
            nor = -nor
        for j in range(rows - 1):
            for k in range(cols - 1):
                # rows run with t (up), cols with s (viewer's right). From the +X side that is counter-clockwise.
                idx = ((j, k), (j, k + 1), (j + 1, k + 1), (j + 1, k))
                if flip:
                    idx = idx[::-1]
                a, b, c, d = idx
                self.tri((pos[a], pos[b], pos[c]), (uv[a], uv[b], uv[c]), (nor[a], nor[b], nor[c]))
                self.tri((pos[a], pos[c], pos[d]), (uv[a], uv[c], uv[d]), (nor[a], nor[c], nor[d]))

    def arrays(self):
        return np.array(self.p, np.float64), np.array(self.t, np.float64), np.array(self.n, np.float64)


def world(u, v, x):
    """Cork coordinates and height off the cork to engine position."""
    return np.stack((CORK_X + x, u - CORK_W / 2, FRAME + v), -1)


def uv_box(name):
    x, y, w, h = place[name]
    return x, y, w, h


def page_grid(mesh, page, s0=0.0, s1=None, t0=0.0, t1=None, step=1.3, extra=None, back=True):
    s1 = page.w if s1 is None else s1
    t1 = page.h if t1 is None else t1
    ns = max(2, int(round((s1 - s0) / step)) + 1)
    nt = max(2, int(round((t1 - t0) / step)) + 1)
    if page.info.get("fold") and nt % 2 == 0:
        nt += 1
    tt, ss = np.meshgrid(np.linspace(t0, t1, nt), np.linspace(s0, s1, ns), indexing="ij")
    lift = page.stand(ss, tt)
    if extra is not None:
        lift = lift + extra(ss, tt)
    uu, vv = page.board(ss, tt)
    pos = world(uu, vv, lift)
    x, y, w, h = uv_box(page.name)
    uv = np.stack((x + ss / page.w * w, y + (1 - tt / page.h) * h), -1)
    mesh.grid(pos, uv)
    if back:
        bx, by, bw, bh = uv_box("back")
        buv = np.stack((bx + bw * (ss - s0) / max(s1 - s0, 1e-6) * 0.9 + 4, by + bh * (tt - t0) / max(t1 - t0, 1e-6) * 0.9 + 4), -1)
        mesh.grid(pos - np.array((0.004, 0, 0)), buv, flip=True)


def add_pin(mesh, page, ps, pt, colour):
    u, v = page.board(ps, pt)
    rr = np.random.default_rng(int(u * 31 + v * 17))
    x0 = float(page.stand(np.array([ps]), np.array([pt]))[0]) + 0.005
    if colour == "brass":
        profile = [(0.0, 0.07), (0.1, 0.07), (0.2, 0.05), (0.215, 0.02), (0.2, 0.0)]
    else:
        # Dome, grip, waist, flange.
        profile = [(0.0, 0.5), (0.1, 0.49), (0.165, 0.45), (0.16, 0.39), (0.095, 0.3), (0.085, 0.17), (0.14, 0.09), (0.205, 0.05), (0.205, 0.0)]
    tilt = rr.uniform(-0.1, 0.1, 2)
    seg = 10 if colour != "brass" else 8
    uv = swatch_uv(colour)
    rings = []
    for r, h in profile:
        ring = []
        for k in range(seg):
            a = 2 * np.pi * k / seg
            dy, dz = r * np.cos(a), r * np.sin(a)
            ring.append((x0 + h, u + dy + tilt[0] * h, v + dz + tilt[1] * h))
        rings.append(ring)
    rings = np.array(rings)
    pos = world(rings[..., 1], rings[..., 2], rings[..., 0])
    # Rings run from the top down, and round the axis: closing the loop by repeating the first column.
    pos = np.concatenate((pos, pos[:, :1]), 1)
    # Normals from the shape, outward from the axis.
    rows, cols = pos.shape[:2]
    dr, dc = np.gradient(pos, axis=0), np.gradient(pos, axis=1)
    dc[:, 0] = dc[:, -1] = (pos[:, 1] - pos[:, -2]) / 2
    nor = np.cross(dr, dc)
    nor = nor / (np.linalg.norm(nor, axis=-1, keepdims=True) + 1e-12)
    centre = world(np.array(u), np.array(v), np.array(x0 + 0.2))
    for j in range(rows - 1):
        for k in range(cols - 1):
            a, b, c, d = pos[j, k], pos[j, k + 1], pos[j + 1, k + 1], pos[j + 1, k]
            na, nb, nc, nd = nor[j, k], nor[j, k + 1], nor[j + 1, k + 1], nor[j + 1, k]
            for tri, ns in (((a, b, c), (na, nb, nc)), ((a, c, d), (na, nc, nd))):
                if np.linalg.norm(np.cross(tri[1] - tri[0], tri[2] - tri[0])) < 1e-7:
                    continue
                mesh.tri(tri, (uv, uv, uv), ns)


def frame_profile():
    """Across the bar from the outer edge in: (distance in, height off the wall), and how far along the strip's height each point is."""
    pts = [(0.0, 0.0), (0.0, 0.74), (0.09, 0.9), (0.2, FRAME_X), (0.6, FRAME_X), (0.71, 0.9), (0.79, 0.74), (FRAME, CORK_X - 0.05)]
    lengths = [0.0]
    for a, b in zip(pts, pts[1:]):
        lengths.append(lengths[-1] + np.hypot(b[0] - a[0], b[1] - a[1]))
    return pts, np.array(lengths) / lengths[-1]


def add_frame(mesh):
    pts, along = frame_profile()
    for name, y0, y1, z0, z1, side in (("frame_top", -W / 2, W / 2, H, H, "top"), ("frame_bottom", -W / 2, W / 2, 0, 0, "bottom"), ("frame_left", 0, H, -W / 2, -W / 2, "left"), ("frame_right", 0, H, W / 2, W / 2, "right")):
        x, y, w, h = uv_box(name)
        for k in range(len(pts) - 1):
            (d0, x0), (d1, x1) = pts[k], pts[k + 1]
            if side in ("top", "bottom"):
                sign = -1 if side == "top" else 1
                a = np.array((x0, -W / 2 + d0, z0 + sign * d0))
                b = np.array((x0, W / 2 - d0, z0 + sign * d0))
                c = np.array((x1, W / 2 - d1, z0 + sign * d1))
                e = np.array((x1, -W / 2 + d1, z0 + sign * d1))
                ta = (x + w * d0 / W, y + h * along[k])
                tb = (x + w * (1 - d0 / W), y + h * along[k])
                tc = (x + w * (1 - d1 / W), y + h * along[k + 1])
                te = (x + w * d1 / W, y + h * along[k + 1])
            else:
                sign = 1 if side == "left" else -1
                a = np.array((x0, z0 + sign * d0, d0))
                b = np.array((x0, z0 + sign * d0, H - d0))
                c = np.array((x1, z0 + sign * d1, H - d1))
                e = np.array((x1, z0 + sign * d1, d1))
                ta = (x + w * d0 / H, y + h * along[k])
                tb = (x + w * (1 - d0 / H), y + h * along[k])
                tc = (x + w * (1 - d1 / H), y + h * along[k + 1])
                te = (x + w * d1 / H, y + h * along[k + 1])
            normal = np.cross(b - a, e - a)
            normal = normal / (np.linalg.norm(normal) + 1e-12)
            # Out from the bar: towards the viewer or the bar's outside for the first faces, into the cork's side for the last.
            middle = (a + b + c + e) / 4
            want = np.array((middle[0] - 0.3, 0.0, 0.0))
            if side in ("top", "bottom"):
                want[2] = (z0 + sign * 0.42 - middle[2]) * -1
            else:
                want[1] = (z0 + sign * 0.42 - middle[1]) * -1
            if normal @ want < 0:
                a, b, c, e, ta, tb, tc, te = b, a, e, c, tb, ta, te, tc
                normal = -normal
            mesh.tri((a, b, c), (ta, tb, tc), (normal, normal, normal)) if np.cross(b - a, c - a) @ normal > 0 else mesh.tri((a, c, b), (ta, tc, tb), (normal, normal, normal))
            mesh.tri((a, c, e), (ta, tc, te), (normal, normal, normal)) if np.cross(c - a, e - a) @ normal > 0 else mesh.tri((a, e, c), (ta, te, tc), (normal, normal, normal))


def add_corners(mesh, top=1.06, size=1.22, cut=0.22):
    """Moulded plastic corner keys over the mitres."""
    uv = swatch_uv("plastic")
    for sy, sz in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
        y0, z0 = sy * W / 2, 0 if sz < 0 else H
        dy, dz = -sy, -sz
        # Round the outline: the corner itself is chamfered, the inner end is square with a slanted cut.
        outline = [(cut, 0), (size, 0), (size, 0.78), (0.78, 0.78), (0.78, size), (0, size), (0, cut)]
        pts = [np.array((y0 + dy * a, z0 + dz * b)) for a, b in outline]
        n = len(pts)
        area = sum(pts[k][0] * pts[(k + 1) % n][1] - pts[(k + 1) % n][0] * pts[k][1] for k in range(n))
        if area < 0:
            pts = pts[::-1]
        centre = np.mean(pts, 0)
        up = np.array((1.0, 0, 0))
        for k in range(n):
            a, b = pts[k], pts[(k + 1) % n]
            p0 = np.array((top, centre[0], centre[1]))
            p1 = np.array((top, a[0], a[1]))
            p2 = np.array((top, b[0], b[1]))
            mesh.tri((p0, p1, p2), (uv, uv, uv), (up, up, up))
            # Sides down to the wall.
            q1, q2 = np.array((0.0, a[0], a[1])), np.array((0.0, b[0], b[1]))
            edge = b - a
            out = np.array((0.0, edge[1], -edge[0]))
            out = out / (np.linalg.norm(out) + 1e-12)
            mesh.tri((p1, q1, q2), (uv, uv, uv), (out, out, out))
            mesh.tri((p1, q2, p2), (uv, uv, uv), (out, out, out))


def build_lod0():
    mesh = Mesh()
    x, y, w, h = uv_box("cork")
    a = (CORK_X, -CORK_W / 2, FRAME)
    b = (CORK_X, CORK_W / 2, FRAME)
    c = (CORK_X, CORK_W / 2, FRAME + CORK_H)
    d = (CORK_X, -CORK_W / 2, FRAME + CORK_H)
    mesh.quad(a, b, c, d, (x, y + h), (x + w, y + h), (x + w, y), (x, y))
    for page in LAYERS:
        if page.kind == "carshare":
            # The body, then each tab as its own strip that lifts, with two already torn off.
            tab_top = page.h - CAR_BODY - 0.08
            page_grid(mesh, page, t0=tab_top)
            tab = page.w / CAR_TABS
            for k in range(CAR_TABS):
                if k in (2, 5):
                    continue
                gap = 0.022
                bend = 0.12 + 0.2 * ((k * 37) % 5) / 4

                def extra(ss, tt, bend=bend, top=tab_top):
                    return bend * np.clip((top - tt) / top, 0, 1) ** 1.8

                page_grid(mesh, page, s0=k * tab + gap, s1=(k + 1) * tab - gap, t0=0.0, t1=tab_top, step=0.5, extra=extra)
        else:
            page_grid(mesh, page, step=0.85 if page.kind == "note" else 1.3)
        for ps, pt, colour in page.pins:
            add_pin(mesh, page, ps, pt, colour)
    add_frame(mesh)
    add_corners(mesh)
    return mesh


def far_front(mesh, x_face):
    x, y, w, h = uv_box("far")
    inset = 1.5
    u0, u1, v0, v1 = x + inset, x + w - inset, y + inset, y + h - inset
    mesh.quad((x_face, -W / 2, 0), (x_face, W / 2, 0), (x_face, W / 2, H), (x_face, -W / 2, H), (u0, v1), (u1, v1), (u1, v0), (u0, v0))


def add_sides(mesh, x_face):
    uv = swatch_uv("needle")
    for (y0, z0), (y1, z1), out in (((-W / 2, 0), (W / 2, 0), (0, 0, -1)), ((W / 2, 0), (W / 2, H), (0, 1, 0)), ((W / 2, H), (-W / 2, H), (0, 0, 1)), ((-W / 2, H), (-W / 2, 0), (0, -1, 0))):
        normal = np.array(out, np.float64)
        mesh.quad((0, y0, z0), (0, y1, z1), (x_face, y1, z1), (x_face, y0, z0), uv, uv, uv, uv, normal)


def fix_winding(p, t, n):
    """Every triangle's winding agrees with its own normals. Rows where it doesn't are swapped."""
    face = np.cross(p[:, 1] - p[:, 0], p[:, 2] - p[:, 0])
    flip = (face * n.mean(1)).sum(-1) < 0
    p[flip] = p[flip][:, [0, 2, 1]]
    t[flip] = t[flip][:, [0, 2, 1]]
    n[flip] = n[flip][:, [0, 2, 1]]
    return int(flip.sum())


def write_obj(path, mesh, mtl="notice_board.mtl"):
    p, t, n = mesh.arrays()
    flipped = fix_winding(p, t, n)
    uv = np.stack((t[..., 0] / ATLAS, 1 - t[..., 1] / ATLAS), -1)
    p_index, t_index, n_index = {}, {}, {}
    p_lines, t_lines, n_lines, faces = [], [], [], []

    def key_index(table, lines, prefix, values):
        key = tuple(np.round(values, 5))
        got = table.get(key)
        if got is None:
            got = len(table) + 1
            table[key] = got
            lines.append(prefix + " ".join(f"{v:.5f}" for v in key) + "\n")
        return got

    # Engine X, Y, Z become OBJ Z, X, Y: a rotation, so the winding holds.
    po, no = p[..., [1, 2, 0]], n[..., [1, 2, 0]]
    for k in range(len(po)):
        a = ["%d/%d/%d" % (key_index(p_index, p_lines, "v ", po[k, c]), key_index(t_index, t_lines, "vt ", uv[k, c]), key_index(n_index, n_lines, "vn ", no[k, c])) for c in range(3)]
        faces.append("f " + " ".join(a) + "\n")
    with open(path, "w", newline="\n") as h:
        h.write(f"# Generated by Sources/Riverdale/notice-board-v2/board.py\nmtllib {mtl}\n")
        h.writelines(p_lines)
        h.writelines(t_lines)
        h.writelines(n_lines)
        h.write("usemtl notice_board\n")
        h.writelines(faces)
    print(os.path.basename(path), "triangles", len(po), "turned", flipped, "bounds", p.reshape(-1, 3).min(0).round(2), p.reshape(-1, 3).max(0).round(2), flush=True)
    return len(po)


def write_model():
    lod0 = build_lod0()
    lod1 = Mesh()
    far_front(lod1, 0.72)
    add_frame(lod1)
    add_corners(lod1)
    lod2 = Mesh()
    far_front(lod2, 0.95)
    add_sides(lod2, 0.95)
    counts = [write_obj(os.path.join(OUT, f"notice_board_lod{k}.obj"), m) for k, m in enumerate((lod0, lod1, lod2))]
    with open(os.path.join(OUT, "notice_board.mtl"), "w", newline="\n") as h:
        h.write("newmtl notice_board\n")
    tail = 'import_translation = [ 0.0, 0.0, 0.0 ] import_rotation = [ 0.0, 0.0, 0.0 ] import_scale = 1.0 align_origin_x_type = "None" align_origin_y_type = "None" align_origin_z_type = "None" parent_bone = "" import_filter = { exclude_by_default = false exception_list = [ ] }'
    meshes = "\n".join(f'\t\t\t\t\t{{ _class = "RenderMeshFile" name = "lod{k}" filename = "{MODEL}/notice_board_lod{k}.obj" {tail} }},' for k in range(3))
    with open(os.path.join(OUT, "notice_board.vmdl"), "w", newline="\n") as h:
        h.write(f"""<!-- kv3 encoding:text:version{{e21c7f3c-8a33-41c5-9977-a76d3a32aa0d}} format:modeldoc29:version{{3cec427c-1b0e-4d48-a90a-0436f33a6041}} -->
// Generated by Sources/Riverdale/notice-board-v2/board.py
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
							{{ from = "notice_board.vmat" to = "{MATS}/notice_board.vmat" }}
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
					{{ _class = "LODGroup" switch_threshold = 30.0 meshes = [ "lod1" ] }},
					{{ _class = "LODGroup" switch_threshold = 90.0 meshes = [ "lod2" ] }}
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
    with open(os.path.join(MAT_OUT, "notice_board.vmat"), "w", newline="\n") as h:
        h.write(f"""// Generated by Sources/Riverdale/notice-board-v2/board.py

Layer0
{{
	shader "shaders/complex.shader"

	//---- PBR ----
	F_METALNESS_TEXTURE 1
	F_SPECULAR 1

	//---- Ambient Occlusion ----
	g_flAmbientOcclusionDirectDiffuse "0.300"
	g_flAmbientOcclusionDirectSpecular "0.500"
	TextureAmbientOcclusion "{MATS}/notice_board_ao.png"

	//---- Color ----
	g_flModelTintAmount "1.000"
	g_vColorTint "[1.000000 1.000000 1.000000 0.000000]"
	TextureColor "{MATS}/notice_board_color.png"

	//---- Fog ----
	g_bFogEnabled "1"

	//---- Metalness ----
	TextureMetalness "{MATS}/notice_board_metal.png"

	//---- Normal ----
	TextureNormal "{MATS}/notice_board_normal.png"

	//---- Roughness ----
	g_flRoughnessScaleFactor "1.000"
	TextureRoughness "{MATS}/notice_board_rough.png"
}}
""")
    return counts


# ---------------------------------------------------------------------------------------------------------------------

paint_cork()
print("cork done", flush=True)
for _page in LAYERS:
    paint_page(_page)
print("pages done", flush=True)
paint_frame()
paint_small()
composite_far()
print("layout written", flush=True)
if PREVIEW_ONLY:
    sys.exit(0)

index = ndi.distance_transform_edt(~COVER, return_distances=False, return_indices=True)
fill = tuple(index)
COLOUR, NORMAL, ROUGH, METAL, AO = COLOUR[fill], NORMAL[fill], ROUGH[fill], METAL[fill], AO[fill]
del index, fill


def save_rgb(array, name):
    Image.fromarray((np.clip(array, 0, 1) * 255 + 0.5).astype(np.uint8)).save(os.path.join(MAT_OUT, name), optimize=False, compress_level=6)


def save_grey(array, name, size=2048):
    im = Image.fromarray((np.clip(array, 0, 1) * 255 + 0.5).astype(np.uint8))
    if size != array.shape[0]:
        im = im.resize((size, size), Image.BOX)
    im.save(os.path.join(MAT_OUT, name), compress_level=6)


save_rgb(COLOUR, "notice_board_color.png")
save_rgb(NORMAL * 0.5 + 0.5, "notice_board_normal.png")
save_grey(ROUGH, "notice_board_rough.png")
save_grey(METAL, "notice_board_metal.png")
save_grey(AO, "notice_board_ao.png")
print("maps written", flush=True)
print("triangles", write_model(), flush=True)
