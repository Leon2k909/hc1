"""Railhead's glazed mechanical signal cabin, authored against the supplied reference.

Plan coordinates and the playable footprint come from railhead_station. The lower
relay storey stays closed to players; its recessed windows contain small furnished
alcoves. Upper glazing is visual only, preserving the original shooting openings.
Scanned CC0 brick and slate channels are cached outside Assets and recorded with
their source and checksum in railhead_signal_box_sources.json.
"""
import hashlib
import json
import math
import urllib.request
from functools import lru_cache
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage

import map_kit as K

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "Assets/materials/railhead"
RESOURCE = "materials/railhead"
CACHE = ROOT / "output/railhead/source-cache"
MANIFEST = Path(__file__).with_name("railhead_signal_box_sources.json")
SOURCES = {"red_brick": ("4k", 55.11811), "roof_slates_03": ("2k", 145.0)}
BRICK = "rw_signal_box_brick"
SLATE = "rw_signal_box_slate"
STONE = "rw_signal_box_stone"
CREAM = "rw_signal_box_cream"
GREEN = "rw_signal_box_green"
CLAY = "rw_signal_box_clay"
WOOD = "rw_signal_box_wood"
GRATE = "rw_signal_box_grate"
GLASS = "rw_signal_box_glass"
DETAIL = "rw_signal_box_details"
PAINTS = {BRICK: SOURCES["red_brick"][1], SLATE: SOURCES["roof_slates_03"][1],
          STONE: 36.0, CREAM: 32.0, GREEN: 32.0, CLAY: 16.0, WOOD: 64.0,
          GRATE: 8.0, GLASS: 64.0, DETAIL: 1.0}


def request(url):
    headers = {"User-Agent": "Railhead-asset-import/1.0"}
    with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=40) as response:
        return response.read()


@lru_cache(maxsize=2)
def scan(asset):
    resolution, _ = SOURCES[asset]
    records = json.loads(MANIFEST.read_text()) if MANIFEST.exists() else {}
    if asset not in records:
        files = json.loads(request("https://api.polyhaven.com/files/" + asset))
        info = json.loads(request("https://api.polyhaven.com/info/" + asset))
        records[asset] = {"source": "https://polyhaven.com/a/" + asset,
                          "license": "CC0-1.0", "license_url": "https://polyhaven.com/license",
                          "authors": info["authors"], "resolution": resolution,
                          "channels": {k: files[k][resolution]["png"] for k in ("Diffuse", "nor_gl", "arm")}}
        MANIFEST.write_text(json.dumps(records, indent=2) + "\n", encoding="utf-8")
    folder = CACHE / asset
    folder.mkdir(parents=True, exist_ok=True)
    for channel, info in records[asset]["channels"].items():
        path = folder / (channel + ".png")
        if not path.exists():
            data = request(info["url"])
            if hashlib.md5(data).hexdigest() != info["md5"]:
                raise ValueError("Source checksum mismatch: " + asset + "/" + channel)
            path.write_bytes(data)
            print("Imported " + asset + "/" + channel, flush=True)
    return tuple(np.asarray(Image.open(folder / (k + ".png")).convert("RGB"), dtype=np.float32) / 255
                 for k in ("Diffuse", "nor_gl", "arm"))


def save(path, data):
    Image.fromarray(np.clip(np.rint(np.asarray(data) * 255), 0, 255).astype(np.uint8)).save(path, optimize=True)


def vmat(paint, metal=0.0, alpha=False):
    lines = ['// Tools/railhead_signal_box.py', '"Layer0"', '{', '    shader "shaders/complex.shader"',
             '    F_SPECULAR "1"', f'    g_flMetalness "{metal}"', '    g_flRoughnessScaleFactor "1"',
             '    g_vColorTint "[1 1 1 1]"', '    g_flModelTintAmount "1"']
    if alpha:
        lines += ['    F_ALPHA_TEST "1"', '    F_RENDER_BACKFACES "1"',
                  f'    TextureTranslucency "{RESOURCE}/{paint}_alpha.png"',
                  '    g_flAlphaTestReference "0.5"', '    g_flAntiAliasedEdgeStrength "1"']
    for channel, parameter in (("color", "Color"), ("normal", "Normal"), ("rough", "Roughness"), ("ao", "AmbientOcclusion")):
        lines.append(f'    Texture{parameter} "{RESOURCE}/{paint}_{channel}.png"')
    return "\n".join(lines + ['}', ''])


def surface(paint, colour, normal, rough, ao, metal=0.0, alpha=None):
    for channel, data in (("color", colour), ("normal", normal), ("rough", rough), ("ao", ao)):
        save(OUT / f"{paint}_{channel}.png", data)
    if alpha is not None:
        save(OUT / f"{paint}_alpha.png", alpha)
    (OUT / f"{paint}.vmat").write_text(vmat(paint, metal, alpha is not None), encoding="utf-8")


def write_materials():
    import railhead_materials as RM
    import railhead_scanned as SC
    OUT.mkdir(parents=True, exist_ok=True)
    for asset, paint in (("red_brick", BRICK), ("roof_slates_03", SLATE)):
        colour, normal, arm = scan(asset)
        if paint == SLATE:
            colour = colour * .78
        else:
            luminance = colour @ np.array((.2126, .7152, .0722))
            colour = (luminance[..., None] + (colour-luminance[..., None])*1.12) * (1.035, 1.0, .94)
        surface(paint, colour, normal, np.clip(arm[..., 1], .64, 1), arm[..., 0])
    # Fine mineral grain for individual sandstone quoins, without mortar joints
    # crossing the arch stones and window sills.
    concrete, mineral, packed = SC.scan("rough_concrete")
    concrete, mineral, packed = (SC.resize(a, (1024, 1024)) for a in (concrete, mineral, packed))
    grain = np.clip(concrete.mean(axis=-1) / concrete.mean(), .55, 1.5)
    surface(STONE, np.array((.76, .69, .56)) * (.72 + grain[..., None] * .28), mineral,
            np.clip(packed[..., 1], .78, 1), packed[..., 0])
    rng = np.random.default_rng(7512)
    size = 512
    coarse = ndimage.gaussian_filter(rng.normal(0, 1, (size, size)), 18, mode="wrap")
    coarse /= coarse.std()
    fine = rng.normal(0, 1, (size, size))
    woodgrain = ndimage.gaussian_filter(fine, (9, .8), mode="wrap")
    woodgrain /= woodgrain.std()
    relief = .035 * woodgrain + .008 * fine
    normal = RM.gl_normals(relief, .35) * .5 + .5
    for paint, base, metallic in ((CREAM, (.80, .765, .665), 0), (GREEN, (.115, .165, .145), .05),
                                   (CLAY, (.38, .215, .135), 0)):
        scale = 1 + .022 * coarse + .018 * woodgrain + .009 * fine
        colour = np.array(base) * scale[..., None]
        surface(paint, colour, normal, np.clip(.63 + .045 * coarse, .52, .8), np.ones((size, size)), metallic)
    wood, normal, packed = SC.scan("brown_planks_03")
    wood, normal, packed = (SC.resize(a, (1024, 1024)) for a in (wood, normal, packed))
    surface(WOOD, np.clip(wood * (.92, .76, .56), 0, 1), normal,
            np.clip(packed[..., 1] * .76, .45, .8), packed[..., 0])
    # A real open grate on the tread tops: long slots between the bearing bars.
    yy, xx = np.indices((512, 512))
    bar = ((xx % 64) < 8) | ((yy % 256) < 8)
    steel = np.stack([np.full((512, 512), c) for c in (.24, .265, .25)], axis=-1)
    steel *= (1 + rng.normal(0, .025, (512, 512, 1)))
    surface(GRATE, steel, np.broadcast_to((.5, .5, 1), steel.shape), np.full((512, 512), .57),
            np.ones((512, 512)), .72, bar.astype(float))
    (OUT / f"{GLASS}.vmat").write_text(RM.glass_vmat(GLASS, (.93, .955, .94), .16)
        .replace('g_flBlurAmount "0.02"', 'g_flBlurAmount "0.005"')
        .replace('g_flRefractionStrength "1.006"', 'g_flRefractionStrength "1.002"'), encoding="utf-8")
    # Small, legible enamel number plates and brass instrument dials, authored
    # as an atlas so all thirty levers share one draw call.
    art = Image.new("RGB", (2048, 512), (22, 25, 22))
    d = ImageDraw.Draw(art)
    font = ImageFont.truetype(str(ROOT / "Assets/fonts/Dinish.ttf"), 58) if (ROOT / "Assets/fonts/Dinish.ttf").exists() \
        else ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 58)
    for k in range(30):
        x, y = (k % 16) * 128, (k // 16) * 128
        d.rounded_rectangle((x+8, y+8, x+120, y+120), radius=6, fill=(194, 183, 151), outline=(87, 81, 62), width=3)
        d.text((x+64, y+64), str(k+1), font=font, fill=(31, 33, 29), anchor="mm")
        for sx in (x+17, x+111):
            d.ellipse((sx-3, y+20, sx+3, y+26), fill=(70, 73, 65))
    for k in range(8):
        x, y = k * 128, 256
        d.ellipse((x+8, y+8, x+120, y+120), fill=(179, 154, 100), outline=(12, 14, 12), width=8)
        d.ellipse((x+18, y+18, x+110, y+110), fill=(207, 201, 174))
        for a in range(12):
            angle = math.radians(a*30)
            d.line((x+64+38*math.cos(angle), y+64+38*math.sin(angle),
                    x+64+44*math.cos(angle), y+64+44*math.sin(angle)), fill=(30, 32, 28), width=3)
        a = math.radians(36+k*43)
        d.line((x+64, y+64, x+64+35*math.cos(a), y+64+35*math.sin(a)), fill=(36, 36, 31), width=3)
    # The operating room's framed track diagram and pinned timetable.
    d.rectangle((1032,264,2040,504),fill=(195,186,158),outline=(74,77,63),width=5)
    small=ImageFont.truetype("C:/Windows/Fonts/arial.ttf",24)
    d.text((1052,275),"STELLWERK HF  /  GLEISPLAN",font=small,fill=(44,48,39))
    for y in (333,366,399,432):
        d.line((1060,y,2008,y),fill=(60,65,53),width=4)
    for x,y,side in ((1145,333,1),(1310,366,-1),(1475,399,-1),(1630,399,1),(1850,366,-1)):
        d.line((x,y,x+72,y+side*33,x+155,y+side*33),fill=(60,65,53),width=4)
        d.ellipse((x-6,y-6,x+6,y+6),fill=(134,45,34))
    d.text((1775,468),"14:03   HF",font=small,fill=(70,72,60))
    colour = np.asarray(art, dtype=float) / 255
    surface(DETAIL, colour, np.broadcast_to((.5, .5, 1), colour.shape),
            np.full(colour.shape[:2], .59), np.ones(colour.shape[:2]))
    print("Wrote " + ", ".join(PAINTS), flush=True)


class Facade:
    """Local r along the wall, d outwards from its masonry face, z up."""
    def __init__(self, axis, at, outward):
        self.axis, self.at, self.out = axis, at, outward
        self.normal = (outward, 0, 0) if axis == "n" else (0, outward, 0)

    def p(self, r, d, z):
        return (self.at + self.out*d, r, z) if self.axis == "n" else (r, self.at + self.out*d, z)

    def box(self, model, r0, r1, d0, d1, z0, z1, paint, surface=None):
        model.box(self.p(r0, d0, z0), self.p(r1, d1, z1), paint, surface)

    def face(self, model, paint, points, d=0, reverse=False, uv=None):
        import railhead_station as S
        S.facing(model, paint, [self.p(r, d, z) for r, z in points],
                 -np.asarray(self.normal) if reverse else self.normal, uv=uv)

    def rect(self, model, paint, r0, r1, z0, z1, d=0, uv=None):
        self.face(model, paint, [(r0,z0), (r1,z0), (r1,z1), (r0,z1)], d, uv=uv)


def arch_top(r, centre, radius, cz):
    return cz + math.sqrt(max(0, radius*radius-(r-centre)**2))


def arch_outline(centre, half=18, bottom=30, spring=94, rise=5, count=16):
    radius = (half*half+rise*rise)/(2*rise)
    cz = spring+rise-radius
    angle = math.asin(half/radius)
    arc = [(centre+radius*math.sin(a), cz+radius*math.cos(a)) for a in np.linspace(angle, -angle, count+1)]
    return [(centre-half,bottom), (centre+half,bottom)] + arc, radius, cz, angle


def leaves(model, root, height=22, seed=1, pot=False):
    """Small bowed leaves on separate stems; no collision on decorative plants."""
    import railhead_station as S
    import railhead_props as P
    rng = np.random.default_rng(seed)
    root = np.asarray(root, float)
    if pot:
        P._frustum(model, root, root+(0,0,7), 3.5, 5.2, "rw_pot", sides=14)
        P.disc(model, "rw_soil", root+(0,0,7.03), (0,0,1), 4.75, sides=14)
        root = root+(0,0,7)
    for k in range(2 if height < 8 else 9):
        direction = rng.uniform(0, 2*math.pi)
        spread = rng.uniform(1, 3) if height < 8 else rng.uniform(3, 11)
        end = root + (math.cos(direction)*spread, math.sin(direction)*spread, rng.uniform(.5,1)*height)
        S.tube(model, root, end, .17, "rw_leaf", sides=5)
        for t in ((.55,.98) if height < 8 else (.32,.55,.78,.98)):
            start = root+(end-root)*t
            turn = direction + (1 if k%2 else -1)*rng.uniform(.5,1.4)
            length, width = (rng.uniform(2.1,3.1),rng.uniform(1.4,2.1)) if height < 8 \
                else (rng.uniform(4,6.5),rng.uniform(3,4.7))
            a = np.array((math.cos(turn),math.sin(turn),.35))
            b = K.normalise(np.cross(a,(0,0,1)))
            tip = start+a*length
            mid = start+a*length*.45+(0,0,.55)
            pts = [start, mid+b*width/2, tip, mid-b*width/2]
            paint = "rw_leaf_light" if (k+int(t*10))%4 == 0 else "rw_leaf"
            model.polygon(paint, pts, both_sides=True)


def lower_window(model, glass, F, centre, blinds=False):
    import railhead_station as S
    outline, radius, cz, angle = arch_outline(centre)
    # Stone jambs are jointed into separate blocks. Slight mortar reveals make
    # the shape readable in raking sunlight rather than a flat cream rectangle.
    for side in (-1,1):
        a, b = sorted((centre+side*18, centre+side*25))
        for low in np.arange(26, 94, 17):
            F.box(model, a, b, -.3, 3.0, low+.12, min(low+16.8, 94.5), STONE)
        # Shoulder blocks connect the curved head continuously to the jambs.
        shoulder=[(centre+side*18,94),(centre+side*25,94),
                  (centre+side*25,97),(centre+side*(radius+7)*math.sin(angle),cz+(radius+7)*math.cos(angle))]
        F.face(model,STONE,shoulder,3)
    for a0,a1 in zip(np.linspace(-angle,angle,10)[:-1], np.linspace(-angle,angle,10)[1:]):
        gap = .0035
        pts = [(centre+radius*math.sin(a0+gap), cz+radius*math.cos(a0+gap)),
               (centre+radius*math.sin(a1-gap), cz+radius*math.cos(a1-gap)),
               (centre+(radius+7)*math.sin(a1-gap), cz+(radius+7)*math.cos(a1-gap)),
               (centre+(radius+7)*math.sin(a0+gap), cz+(radius+7)*math.cos(a0+gap))]
        F.face(model, STONE, pts, 3)
        for i in range(4):
            j=(i+1)%4
            S.facing(model, STONE, [F.p(pts[i][0],-.2,pts[i][1]),F.p(pts[j][0],-.2,pts[j][1]),
                                    F.p(pts[j][0],3,pts[j][1]),F.p(pts[i][0],3,pts[i][1])],
                     np.array(F.normal)*.1 + (0,0,1))
    F.box(model, centre-27, centre+27, -.5, 6.0, 23, 30, STONE)
    F.box(model, centre-25.5, centre+25.5, -.3, 4.2, 21.2, 23, STONE)
    # Recessed dark-green sash, two three-light leaves with a substantial
    # meeting rail and finer horizontal muntins.
    for r in (centre-17.2,centre+17.2):
        F.box(model,r-.85,r+.85,-4,-1,30,94,GREEN)
    F.box(model,centre-17.2,centre+17.2,-4,-1,30,32,GREEN)
    for r in (centre-5.6,centre+5.6):
        F.box(model,r-.35,r+.35,-3.8,-2,32,arch_top(r,centre,radius,cz)-1,GREEN)
    for z, thick in ((42,.85),(61,1.5),(82,.65)):
        F.box(model,centre-17,centre+17,-4,-1.8,z-thick/2,z+thick/2,GREEN)
    # Curved top rail and the masonry reveals follow the aperture.
    for (r0,z0),(r1,z1) in zip(outline[2:-1],outline[3:]):
        S.tube(model,F.p(r0,-2.2,z0),F.p(r1,-2.2,z1),.9,GREEN,sides=8)
        S.facing(model,STONE,[F.p(r0,0,z0),F.p(r1,0,z1),F.p(r1,-8,z1),F.p(r0,-8,z0)],(0,0,-1))
    for r, sign in ((centre-18,1),(centre+18,-1)):
        S.facing(model,STONE,[F.p(r,0,30),F.p(r,-8,30),F.p(r,-8,94),F.p(r,0,94)],
                 (0,sign,0) if F.axis=="n" else (sign,0,0))
    # Glass is separate from the collision model. The lower storey's retained
    # solid collider keeps these non-playable alcoves inaccessible.
    F.face(glass,GLASS,outline,-4.3)
    F.face(glass,GLASS,outline,-4.3,reverse=True)
    F.box(model,centre-22,centre+22,-36,-34,11,106,WOOD)
    F.box(model,centre-23,centre-21,-34,-7,11,106,BRICK)
    F.box(model,centre+21,centre+23,-34,-7,11,106,BRICK)
    F.box(model,centre-22,centre+22,-34,-6,10,12,WOOD)
    F.box(model,centre-22,centre+22,-34,-6,105,107,WOOD)
    if blinds:
        for z in np.arange(66,96,2.1):
            F.box(model,centre-16.5,centre+16.5,-8.6,-7.8,z,z+.9,WOOD)
        for r in (centre-11,centre+11):
            S.tube(model,F.p(r,-7.65,64),F.p(r,-7.65,97),.12,GREEN,sides=4)
    # A shelf and a few plant pots are visible through the glazing.
    F.box(model,centre-20,centre+20,-27,-10,26,28,WOOD)
    leaves(model,F.p(centre-7,-16,28),height=24,seed=int(abs(centre)),pot=True)
    if not blinds:
        for r in (centre-8,centre+8):
            F.box(model,r-3,r+3,-32,-28,32,87,WOOD)
        for z in (35,62,87):
            F.box(model,centre-14,centre+14,-31,-25,z,z+1.8,WOOD)


def relay_storey(model,glass):
    import railhead_station as S
    e0,e1,n0,n1=S.BOX
    # Retain the original closed lower-storey collider independently of its
    # newly recessed visual faces. Bullet/player navigation stays consistent.
    model.collision_box((e0,n0,S.BED_Z),(e1,n1,S.BOX_FLOOR),S.STONE)
    for at,out in ((e0,-1),(e1,1)):
        F=Facade("n",at,out)
        windows=(-2120.,-2040.,-1960.)
        F.rect(model,BRICK,n0,n1,S.BED_Z,30)
        F.rect(model,BRICK,n0,n1,102,S.BOX_FLOOR)
        left=n0
        for centre in windows:
            F.rect(model,BRICK,left,centre-18,30,102)
            _,radius,cz,_=arch_outline(centre)
            for r0,r1 in zip(np.linspace(centre-18,centre+18,19)[:-1],np.linspace(centre-18,centre+18,19)[1:]):
                F.face(model,BRICK,[(r0,arch_top(r0,centre,radius,cz)),(r1,arch_top(r1,centre,radius,cz)),
                                   (r1,102),(r0,102)])
            lower_window(model,glass,F,centre,blinds=centre==-1960)
            left=centre+18
        F.rect(model,BRICK,left,n1,30,102)
    for at,out in ((n0,-1),(n1,1)):
        F=Facade("e",at,out)
        F.rect(model,BRICK,e0,e1,S.BED_Z,S.BOX_FLOOR)
    # Block-jointed sandstone plinth and weathered continuous string course.
    for F,r0,r1 in ((Facade("n",e0,-1),n0,n1),(Facade("n",e1,1),n0,n1),
                    (Facade("e",n0,-1),e0,e1),(Facade("e",n1,1),e0,e1)):
        for r in np.arange(r0,r1,28):
            F.box(model,r+.15,min(r+27.85,r1),0,2.2,S.BED_Z,S.BED_Z+19.8,STONE)
        F.box(model,r0-2,r1+2,0,4,S.BOX_FLOOR-8,S.BOX_FLOOR,STONE)
        F.box(model,r0-2,r1+2,0,3,S.BOX_FLOOR-9.5,S.BOX_FLOOR-8,STONE)
    # Original service door, detailed as a boarded door rather than an empty
    # black decal; it remains a closed relay-room door.
    F=Facade("e",n0,-1)
    F.box(model,-22,22,.15,1.6,S.BED_Z+20,66,WOOD)
    for e in np.arange(-20,23,7):
        F.box(model,e-.18,e+.18,1.61,1.75,S.BED_Z+21,65,GREEN)
    for r in (-24,24):
        F.box(model,r-2,r+2,.2,3,S.BED_Z+20,71,GREEN)
    F.box(model,-28,28,.2,3,66,72,GREEN)
    F.box(model,-27,27,.1,7,S.BED_Z+19,S.BED_Z+21,STONE)
    S.tube(model,F.p(17,2,30),F.p(17,3.2,30),.7,"rw_steel",sides=12,cap=True)


def window_band(model,glass):
    import railhead_station as S
    e0,e1,n0,n1=S.BOX
    zf, sill, head, top = S.BOX_FLOOR,166.,233.,242.
    # Brick parapets and a deep green sill, backed by light plaster inside.
    door=(82.,124.)
    for F,r0,r1 in ((Facade("n",e0,-1),n0,n1),(Facade("n",e1,1),n0,n1),
                    (Facade("e",n0,-1),e0,e1),(Facade("e",n1,1),e0,e1)):
        intervals=[(r0,r1)] if not (F.axis=="e" and F.out==1) else [(r0,door[0]),(door[1],r1)]
        for a,b in intervals:
            F.box(model,a,b,-8,0,zf,sill-2,{"default":BRICK},S.STONE)
            F.rect(model,CREAM,a+.2,b-.2,zf+2,sill-2,-8.05)
            F.box(model,a,b,-8.2,2.2,sill-2,sill,GREEN)
            F.box(model,a,b,-6.5,1.2,sill,sill+1.3,CREAM)
        F.box(model,r0,r1,-8,0,head,top,GREEN,S.WOOD)
        F.box(model,r0+4,r1-4,-6.5,-1,head-2.2,head,CREAM)
        # Narrow cream stiles set into green corner posts, opening sections
        # and fine horizontal muntins in each of the eight/nine main bays.
        count=9 if F.axis=="n" else 8
        cuts=np.linspace(r0+6,r1-6,count+1)
        if F.axis=="e" and F.out==1:
            cuts=np.linspace(r0+6,door[0]-1.2,7)
        for k,(a,b) in enumerate(zip(cuts[:-1],cuts[1:])):
            F.box(model,a-1.15,a+1.15,-6.5,-1.2,sill,head,CREAM)
            if k==len(cuts)-2:
                F.box(model,b-1.15,b+1.15,-6.5,-1.2,sill,head,CREAM)
            for z in (sill+26,head-22):
                F.box(model,a+1.2,b-1.2,-5.5,-2,z-.45,z+.45,CREAM)
            F.rect(glass,GLASS,a+1.2,b-1.2,sill+1.3,head-2.2,-4.4)
            F.face(glass,GLASS,[(a+1.2,sill+1.3),(b-1.2,sill+1.3),(b-1.2,head-2.2),(a+1.2,head-2.2)],-4.4,reverse=True)
            # Small sash latches, glazing beads and hinge plates.
            F.box(model,(a+b)/2-.7,(a+b)/2+.7,-1.7,-1.1,sill+25.6,sill+26.3,GREEN)
            for z in (sill+8,head-9):
                F.box(model,b-.8,b+.8,-1.05,-.65,z,z+1.4,GREEN)
    for ce,cn in ((e0,n0),(e1-6,n0),(e0,n1-6),(e1-6,n1-6)):
        model.box((ce,cn,sill-3),(ce+6,cn+6,top),GREEN,S.WOOD)
    F=Facade("e",n1,1)
    for r in (door[0]-1.5,door[1]+1.5):
        F.box(model,r-1.5,r+1.5,-8,0,zf,head,CREAM,S.WOOD)
    F.box(model,door[0],door[1],-8,0,zf+80,head,CREAM,S.WOOD)
    # Upper doorway is open with a fixed glazed transom. Neither the new
    # glass nor any prop intersects the original 42-inch door aperture.
    F.rect(glass,GLASS,door[0]+2,door[1]-2,zf+82,head-2,-4)
    F.face(glass,GLASS,[(door[0]+2,zf+82),(door[1]-2,zf+82),(door[1]-2,head-2),(door[0]+2,head-2)],-4,reverse=True)
    F.box(model,door[0],door[1],-10,2,zf-1,zf+.1,WOOD)
    model.box((e0+8,n0+8,zf-10),(e1-8,n1-8,zf),WOOD,S.WOOD,skip=("-z",))
    model.box((e0+7,n0+7,top-4),(e1-7,n1-7,top-2),CREAM)
    return top


def label(model,F,index,r,z,width=2.8,height=2.8,depth=.2):
    x,y=(index%16)*128,(index//16)*128
    uv=[((x+8)/2048,1-(y+120)/512),((x+120)/2048,1-(y+120)/512),
        ((x+120)/2048,1-(y+8)/512),((x+8)/2048,1-(y+8)/512)]
    F.rect(model,DETAIL,r-width/2,r+width/2,z-height/2,z+height/2,depth,uv=uv)


def interior(model):
    import railhead_station as S
    import railhead_props as P
    zf=S.BOX_FLOOR
    e0,e1,n0,n1=S.BOX
    # Cabinets along the rear windows, kept clear of the door and the lever
    # frame. Recessed drawers, handles and countertop equipment catch light.
    for n in (-2140,-2102,-2064,-2026,-1988,-1950):
        model.box((88,n-17,zf+3),(118,n+17,zf+36),WOOD)
        model.box((85,n-18.5,zf+36),(120,n+18.5,zf+38),WOOD)
        F=Facade("n",87.9,-1)
        for a,b,handle in ((n-15,n-.7,n-3),(n+.7,n+15,n+3)):
            F.box(model,a,b,0,.6,zf+6,zf+29,WOOD)
            F.box(model,a+1,b-1,.61,.8,zf+7.2,zf+27.8,WOOD)
            F.box(model,handle-.3,handle+.3,.9,1.6,zf+17,zf+21,GREEN)
        F.box(model,n-15,n+15,0,.6,zf+30,zf+35,WOOD)
        F.box(model,n-3,n+3,.7,1.6,zf+32.1,zf+32.7,GREEN)
        for zz in (zf+4,zf+33):
            F.box(model,n-17,n+17,0,.7,zz,zz+1,GREEN)
    # Timber piers and a light plaster infill carry the clock behind the
    # glazed front. The neighboring back windows still admit daylight.
    model.box((117,-2076,166),(121,-2052,236),CREAM)
    for n in (-2077,-2051):
        model.box((116,n-1,166),(121,n+1,237),WOOD)
    S.tube(model,(116,-2064,209),(114.4,-2064,209),5.8,GREEN,sides=40,cap=True)
    S.clock_dial(model,(114.3,-2064,209),(-1,0,0),5.35)
    # A framed, non-emissive railway diagram on a narrow timber back panel.
    model.box((117,-2016,180),(121,-1982,226),WOOD)
    F=Facade("n",116.8,-1)
    F.box(model,-2014,-1984,0,1,200.5,209.5,GREEN)
    diagram_uv=[(1032/2048,1-504/512),(2040/2048,1-504/512),
                (2040/2048,1-264/512),(1032/2048,1-264/512)]
    F.rect(model,DETAIL,-2013,-1985,201.65,208.35,1.02,uv=diagram_uv)
    # Telephone, logbook, framed diagram and small brass block instruments.
    model.box((89,-2046,zf+38),(103,-2037,zf+42),GREEN)
    for n in (-2045,-2038):
        S.tube(model,(89,n,zf+42),(101,n,zf+42),1.15,"rw_satin_black",sides=12,cap=True)
    model.box((86,-1990,zf+38),(100,-1979,zf+38.8),CREAM)
    model.box((88,-2152,zf+38),(109,-2139,zf+56),GREEN)
    F=Facade("n",87.9,-1)
    for j in range(3):
        r=-2150+4.5+j*4.5
        x=j*128
        uv=[((x+8)/2048,1-376/512),((x+120)/2048,1-376/512),
            ((x+120)/2048,1-264/512),((x+8)/2048,1-264/512)]
        F.rect(model,DETAIL,r-2,r+2,zf+45,zf+49,.1,uv=uv)
    for n in (-2087,-1938):
        leaves(model,(103,n,zf+38),height=17,seed=abs(n),pot=True)
    # A padded swivel chair at the operating desk, with a five-spoke base.
    ce,cn=65,-2030
    S.tube(model,(ce,cn,zf+3),(ce,cn,zf+21),1.25,"rw_steel_grey",sides=12,cap=True)
    for a in np.linspace(0,2*math.pi,6)[:-1]:
        end=(ce+12*math.cos(a),cn+12*math.sin(a),zf+3)
        S.tube(model,(ce,cn,zf+4),end,.65,GREEN,sides=6)
        model.box((end[0]-1,end[1]-1,zf+1),(end[0]+1,end[1]+1,zf+3),"rw_satin_black")
    model.box((ce-10,cn-10,zf+20),(ce+10,cn+10,zf+23),"rw_satin_black")
    chair_back=[(cn-10,zf+25),(cn+10,zf+25),(cn+10,zf+43),
                (cn+8,zf+46),(cn-8,zf+46),(cn-10,zf+43)]
    F=Facade("n",ce-10,-1)
    F.face(model,"rw_satin_black",chair_back,1)
    F.face(model,"rw_satin_black",chair_back,-1,reverse=True)
    for (r0,z0),(r1,z1) in zip(chair_back,chair_back[1:]+chair_back[:1]):
        S.tube(model,F.p(r0,0,z0),F.p(r1,0,z1),.95,"rw_satin_black",sides=8)
    for n in (cn-10.3,cn+10.3):
        S.tube(model,(ce-8,n,zf+22),(ce-8,n,zf+34),.5,GREEN,sides=6)
        model.box((ce-10,n-1,zf+33),(ce+7,n+1,zf+35),"rw_satin_black")
    # The detailed lever frame, annunciators and pendants are a shared prop.
    # railhead_map.write_scene places railhead_signal_frame.scene_group().
    model.grain_paints.add(WOOD)


def roof(model,eaves):
    import railhead_station as S
    import railhead_props as P
    e0,e1,n0,n1=S.BOX
    overhang=16.
    r0,r1,s0,s1=e0-overhang,e1+overhang,n0-overhang,n1+overhang
    ridge0,ridge1=n0+130,n1-130
    high=320.
    faces=[([(r0,s0,eaves),(r1,s0,eaves),(0,ridge0,high)],(0,-1,1)),
           ([(r1,s1,eaves),(r0,s1,eaves),(0,ridge1,high)],(0,1,1)),
           ([(r1,s0,eaves),(r1,s1,eaves),(0,ridge1,high),(0,ridge0,high)],(1,0,1)),
           ([(r0,s1,eaves),(r0,s0,eaves),(0,ridge0,high),(0,ridge1,high)],(-1,0,1))]
    for points,toward in faces:
        # Authored roof UVs keep every slate course level around all four
        # slopes. World projection otherwise makes the hips' tiles diagonal.
        normal=K.normalise(np.cross(np.asarray(points[1])-points[0],np.asarray(points[2])-points[0]))
        if np.dot(normal,toward)<0:
            normal=-normal
        along=K.normalise(np.cross((0,0,1),normal))
        up=K.normalise(np.cross(normal,along))
        uv=[(np.dot(p,along)/PAINTS[SLATE],np.dot(p,up)/PAINTS[SLATE]) for p in points]
        S.facing(model,SLATE,points,toward,uv=uv)
    S.facing(model,WOOD,[(r0,s0,eaves-1.2),(r1,s0,eaves-1.2),(r1,s1,eaves-1.2),(r0,s1,eaves-1.2)],(0,0,-1))
    model.hull([(r0,s0,eaves),(r1,s0,eaves),(r1,s1,eaves),(r0,s1,eaves),
                (0,ridge0,high),(0,ridge1,high)],S.TILE)
    for F,a,b in ((Facade("n",r0,-1),s0,s1),(Facade("n",r1,1),s0,s1),
                  (Facade("e",s0,-1),r0,r1),(Facade("e",s1,1),r0,r1)):
        F.box(model,a,b,-1.8,1,eaves-6,eaves,GREEN)
        F.box(model,a,b,-1.8,2,eaves-6.7,eaves-5.7,GREEN)
        # Smooth half-round rainwater gutters with lips, end caps and straps.
        P._frustum(model,F.p(a,3.0,eaves-2),F.p(b,3.0,eaves-2),1.7,1.7,GREEN,sides=16,inside=GREEN)
        for r in np.arange(a+10,b,28):
            S.tube(model,F.p(r,3.0,eaves-2.1),F.p(r+.5,3.0,eaves-2.1),1.92,"rw_steel_dark",sides=16)
    # Overlapping barrel hip caps, oriented to each hip rather than a green
    # square ridge block. Only the exposed half of each clay shell is drawn.
    segments=[((r0,s0,eaves),(0,ridge0,high)),((r1,s0,eaves),(0,ridge0,high)),
              ((r0,s1,eaves),(0,ridge1,high)),((r1,s1,eaves),(0,ridge1,high)),
              ((0,ridge0,high),(0,ridge1,high))]
    for start,end in segments:
        start,end=np.asarray(start,float),np.asarray(end,float)
        axis=K.normalise(end-start)
        side=K.normalise(np.cross(axis,(0,0,1))) if abs(axis[2])<.95 else np.array((1.,0,0))
        up=K.normalise(np.cross(side,axis))
        length=np.linalg.norm(end-start)
        count=max(1,math.ceil(length/9))
        for k in range(count):
            a=start+axis*(k*length/count-.2)+up*.65
            b=start+axis*((k+1)*length/count+.35)+up*.65
            for t0,t1 in zip(np.linspace(0,math.pi,13)[:-1],np.linspace(0,math.pi,13)[1:]):
                d0=math.cos(t0)*side+math.sin(t0)*up
                d1=math.cos(t1)*side+math.sin(t1)*up
                model.polygon(CLAY,[a+d0*2.1,a+d1*2.1,b+d1*1.95,b+d0*1.95],normals=[d0,d1,d1,d0])
            S.tube(model,a,b,.3,CLAY,sides=6)
    # Dark downpipes with two offset bends, collars and masonry brackets.
    for e,n,sign in ((e0-5,n1-8,-1),(e1+5,n0+8,1)):
        points=[(e-sign*6,n,eaves-2),(e,n,eaves-10),(e,n,eaves-26),(e,n,S.BED_Z+7),
                (e+sign*3,n,S.BED_Z+2)]
        for a,b in zip(points[:-1],points[1:]):
            S.tube(model,a,b,1.5,GREEN,sides=16,cap=True)
        for z in (S.BED_Z+28,95,175,215):
            S.tube(model,(e,n,z-.6),(e,n,z+.6),1.85,GREEN,sides=16)
            model.box((min(e,e-sign*6),n-.65,z-.5),(max(e,e-sign*6),n+.65,z+.5),GREEN)
    # Small rafter tails on the shadowed soffit.
    for n in np.arange(n0+8,n1,28):
        for e,sign in ((e0,-1),(e1,1)):
            model.box((min(e,e+sign*13),n-1.2,eaves-7),(max(e,e+sign*13),n+1.2,eaves-2),GREEN)


def bulb(model,top,scale=1.):
    """A pear-shaped opal bulb with a rounded base instead of a white prism."""
    import railhead_props as P
    top=np.asarray(top,float)
    profile=((0,.65),(1.0,1.35),(2.0,2.35),(3.4,2.55),(4.8,1.85),(5.7,.8),(6.0,.04))
    for (z0,r0),(z1,r1) in zip(profile[:-1],profile[1:]):
        P._frustum(model,top+(0,0,-z0*scale),top+(0,0,-z1*scale),r0*scale,r1*scale,"rw_lamp_warm",sides=20)


def wall_lamps(model):
    import railhead_station as S
    import railhead_props as P
    for e,sign in ((S.BOX[0],-1),(S.BOX[1],1)):
        F=Facade("n",e,sign)
        for n in (-2150.,-1944.):
            F.box(model,n-2,n+2,.6,1.8,228,241,GREEN)
            a,b,c=F.p(n,1.5,238),F.p(n,6.5,241),F.p(n,11.5,238)
            S.tube(model,a,b,.5,GREEN,sides=10)
            S.tube(model,b,c,.5,GREEN,sides=10)
            S.tube(model,c,F.p(n,11.5,233),.6,GREEN,sides=12)
            P._frustum(model,F.p(n,11.5,233),F.p(n,11.5,229),1.8,7.0,GREEN,sides=24,inside=CREAM)
            P.disc(model,GREEN,F.p(n,11.5,233),(0,0,1),1.8,sides=20)
            bulb(model,F.p(n,11.5,232.2))


def stairs(model):
    import railhead_station as S
    a0,a1,w0,w1=S.BOX_STAIR
    zb,zf=S.BED_Z,S.BOX_FLOOR
    end=S.BOX[1]
    count=24
    rise,tread=(zf-zb)/count,(a1-a0)/count
    for k in range(count):
        a=a0+k*tread
        top=zb+(k+1)*rise
        model.collision_box((a,w0,zb),(a+tread,w1,top),S.METAL)
        model.box((a,w0+2,top-1.1),(a+tread+1,w1-2,top),GREEN,skip=("+z",))
        S.facing(model,GRATE,[(a,w0+2,top),(a+tread+1,w0+2,top),(a+tread+1,w1-2,top),(a,w1-2,top)],(0,0,1))
        model.box((a-.2,w0+1.9,top-.25),(a+.75,w1-1.9,top+.12),"rw_steel_grey")
        for w in (w0+1.9,w1-1.9):
            # Visible fixing bolts and the side support angle on every tread.
            model.box((a,w-.55,top-3),(a+tread+.8,w+.55,top-1.1),GREEN)
            S.tube(model,(a+tread*.55,w-1,top-2),(a+tread*.55,w+1,top-2),.35,"rw_steel_grey",sides=6,cap=True)
    for w in (w0+1,w1-1):
        model.beam((a0,w,zb+2),(a1,w,zf-4),(2.,8.),GREEN)
        for k in (0,5,10,15,20,24):
            a=a0+k*tread
            floor=zb+min(k+1,count)*rise
            S.tube(model,(a,w,floor-5),(a,w,floor+39),.65,GREEN,sides=10,cap=True)
        S.tube(model,(a0,w,zb+rise+39),(a1,w,zf+39),.85,GREEN,sides=12,cap=True)
        S.tube(model,(a0,w,zb+rise+19),(a1,w,zf+19),.48,GREEN,sides=8,cap=True)
        model.hull([(e,n,z) for e,zz in ((a0,zb+rise),(a1,zf)) for n in (w-1,w+1)
                    for z in (zz,zz+40)],S.METAL)
    model.box((a1,w0,zf-3),(end,w1,zf),GREEN,S.METAL,skip=("+z",))
    model.collision_box((a1,w0,zb),(end,w1,zf),S.METAL)
    S.facing(model,GRATE,[(a1,w0,zf+.03),(end,w0,zf+.03),(end,w1,zf+.03),(a1,w1,zf+.03)],(0,0,1))
    for e in (a1+4,end-4):
        model.box((e-1.6,w1-3,zb),(e+1.6,w1,zf-3),GREEN)
        for de in (-2,2):
            model.box((e+de-1,w1-6,zb),(e+de+1,w1+2,zb+1.3),"rw_steel_dark")
    for a,b in (((a1,w1-1,zf),(end+1,w1-1,zf)),((end+1,w0,zf),(end+1,w1-1,zf))):
        for z in (19,39):
            S.tube(model,np.array(a)+(0,0,z),np.array(b)+(0,0,z),.85 if z==39 else .48,GREEN,sides=12)
        length=np.linalg.norm(np.asarray(b)-a)
        for t in np.linspace(0,1,max(2,math.ceil(length/24)+1)):
            p=np.asarray(a)+(np.asarray(b)-a)*t
            S.tube(model,p,p+(0,0,39),.65,GREEN,sides=10)
    model.collision_box((a1,w1-2,zf),(end+3,w1+.5,zf+40),S.METAL)
    model.collision_box((end,w0,zf),(end+3,w1,zf+40),S.METAL)
    # A concrete pad at the stair foot, wholly outside the rail running gauge.
    model.box((a0-10,w0-5,zb-2),(a0+14,w1+5,zb),"rw_concrete",S.STONE)


def vegetation(model):
    import railhead_station as S
    rng=np.random.default_rng(816)
    e0,e1,n0,n1=S.BOX
    for sign,e in ((-1,e0),(1,e1)):
        for i,n in enumerate((-2157,-2132,-2050,-1950,-1923)):
            leaves(model,(e+sign*rng.uniform(5,14),n,S.BED_Z),height=rng.uniform(13,29),seed=30+i)
        # Sparse climbing sprigs below the right-hand window; leaves stay
        # below the sill, preserving the facade and its window proportions.
        for j in range(4):
            n=-2125+j*4
            base=np.array((e+sign*3,n,S.BED_Z+2))
            end=base+(sign*1,(-1 if j%2 else 1)*6,45+j*4)
            S.tube(model,base,end,.2,WOOD,sides=5)
            for t in np.linspace(.15,1,7):
                p=base+(end-base)*t
                leaves(model,p,height=4,seed=140+j+int(t*10))


def lights():
    """Fixture positions and local light radii, used by the saved scene too."""
    out=[]
    for e,side in ((-141.5,"West"),(141.5,"East")):
        for k,n in enumerate((-2150.,-1944.)):
            out.append((f"Signal Box {side} wall {k+1}",(e,n,226.4),"1.05,0.79,0.45,1",70,True))
    for k,(e,n) in enumerate(((30,-1960),(35,-2040),(20,-2120))):
        out.append((f"Signal Box pendant {k+1}",(e,n,212.3),"1.05,0.80,0.47,1",155,True))
    return out


def build(model,glass):
    relay_storey(model,glass)
    eaves=window_band(model,glass)
    interior(model)
    roof(model,eaves)
    wall_lamps(model)
    stairs(model)
    vegetation(model)


def missing():
    return any(not (OUT / f"{paint}.vmat").exists() for paint in PAINTS)


if __name__ == "__main__":
    write_materials()
