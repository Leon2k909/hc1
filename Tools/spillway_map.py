"""Spillway: Riverdale Hydroelectric, built from the user's dam reference.

Run with Python; all generated files go to output/spillway, never directly to
the live Assets tree. Import and assemble with Sources/Spillway/editor scripts
through native s&box run_csharp. Plan coordinates are east, north, up (inches).
The independent scene uses the project's existing multiplayer components.
"""
import argparse
import json
import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy.ndimage import gaussian_filter, zoom

import map_kit as K
import riverdale_map as RV
import riverdale_parts as P
import riverdale_materials as RM
import riverdale_backdrop as RB
import spillway_landscape as LANDSCAPE
import spillway_waterfalls as WATERFALLS
from riverdale_parts import box, card, v, UP, STONE, METAL

ROOT = K.ROOT
OUT = ROOT / "output/spillway"
STAGE = OUT / "stage"
MAT = STAGE / "materials/spillway"
MODELS = STAGE / "models/maps/spillway"
SOURCE = ROOT / "Sources/Spillway"
PLAY = (-2400, 2400, -1800, 1950)
WATER_Z = -245
IDS = K.SceneIds("93bdfe49-6e09-4daa-bba9-8d142274bf3e")
ATLAS = {}
PROPS = []
CHECKS = []
TILES = {"sw_dam": 480, "sw_concrete": 128, "sw_yard": 192, "sw_rock": 220,
         "sw_moss": 170, "sw_river": 128, "sw_fall": 128, "sw_foam": 128,
         "sw_rust": 72, "sw_stain": 800}


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    K.write_text(path, text)


def texture_material(name, color, normal="materials/default/default_normal.tga", rough="[0.8 0.8 0.8 0]", tint=(1, 1, 1), alpha=None):
    write(MAT / (name + ".vmat"), RM.vmat(color, normal, rough, tint=tint, alpha=alpha))


def noise(rng, shape, cells):
    small = rng.random(cells)
    return zoom(small, (shape[0] / cells[0], shape[1] / cells[1]), order=3, mode="wrap")[:shape[0], :shape[1]]


def materials():
    MAT.mkdir(parents=True, exist_ok=True)
    tree=SOURCE/"source-assets/spruce-original.png"
    if tree.exists():
        # Technical engine conversion; preserves the generated original in Sources.
        bitmap=Image.open(tree).convert("RGBA").resize((1024,2048),Image.Resampling.LANCZOS)
        bitmap.save(MAT/"spruce.png");bitmap.getchannel("A").save(MAT/"spruce_alpha.png")
    rng = np.random.default_rng(3157)
    h, w = 2048, 1024
    yy, xx = np.mgrid[:h, :w]
    coarse = noise(rng, (h, w), (24, 16))
    streak = noise(rng, (h, w), (5, 160))
    fine = rng.normal(0, 1, (h, w))
    lines = ((xx % 256 < 2) | (yy % 256 < 2)).astype(float)
    stains = np.clip((streak - .46) * 2.1, 0, 1) * (.35 + .65 * (yy / h))
    c = 145 + (coarse - .5) * 42 + fine * 3 - stains * 72 - lines * 19
    rgb = np.stack((c * .98, c, c * .98), axis=-1)
    Image.fromarray(np.uint8(np.clip(rgb, 0, 255))).save(MAT / "dam_color.jpg", quality=94)
    scans="materials/spillway/scans/"
    texture_material("sw_dam", scans+"concrete_layers_02_diff_2k.jpg", scans+"concrete_layers_02_nor_dx_2k.jpg",
                     scans+"concrete_layers_02_rough_2k.jpg", (.82,.86,.88))
    texture_material("sw_concrete", scans+"concrete_wall_009_diff_2k.jpg", scans+"concrete_wall_009_nor_dx_2k.jpg",
                     scans+"concrete_wall_009_rough_2k.jpg", (.82,.85,.86))
    texture_material("sw_yard", scans+"concrete_layers_02_diff_2k.jpg", scans+"concrete_layers_02_nor_dx_2k.jpg",
                     "[0.52 0.52 0.52 0]", (.54,.57,.59))
    texture_material("sw_trim", scans+"concrete_layers_02_diff_2k.jpg", scans+"concrete_layers_02_nor_dx_2k.jpg",
                     scans+"concrete_layers_02_rough_2k.jpg", (.56,.59,.59))
    write(MAT/"sw_safety.vmat",RM.painted_vmat((148,116,42),.2,.67,0))
    write(MAT/"sw_window.vmat",RM.painted_vmat((10,18,22),0,.13,0))
    texture_material("sw_tarp","materials/buildings/canvas_green_color.png","materials/buildings/canvas_normal.png",
                     "materials/buildings/canvas_rough.png",(.78,.72,.56))
    texture_material("sw_spruce", "materials/spillway/spruce.png", rough="[0.85 0.85 0.85 0]",
                     alpha="materials/spillway/spruce_alpha.png")
    write(MAT / "sky/spillway_sky.vmat", '"Layer0"\n{\n shader "shaders/sky.shader"\n F_TEXTURE_FORMAT2 "6"\n g_flBrightnessExposureBias "-1.0"\n g_flRenderOnlyExposureBias "0"\n SkyTexture "materials/spillway/sky/clouds.exr"\n}\n')
    texture_material("sw_rust", "materials/lowtide/containers/lt_container_red_color.png",
                     "materials/riverdale/rv_steel_normal.jpg", "[0.65 0.65 0.65 0]")
    for name, tint in (("sw_rock", (.70, .71, .68)), ("sw_moss", (.40, .46, .28))):
        n = 1024
        a = noise(rng, (n, n), (50, 50)) + .6 * noise(rng, (n, n), (120, 120))
        a += .22 * rng.random((n, n))
        stone = (75 + a * 70)[..., None] * np.array(tint)[None, None, :]
        Image.fromarray(np.uint8(np.clip(stone, 0, 255))).save(MAT / (name + ".jpg"), quality=92)
        heights = gaussian_filter(a, .65)
        dy, dx = np.gradient(heights)
        norm = np.stack((-dx * 4, dy * 4, np.ones_like(dx)), -1)
        norm /= np.linalg.norm(norm, axis=-1)[..., None]
        Image.fromarray(np.uint8(np.clip((norm * .5 + .5) * 255, 0, 255))).save(MAT / (name + "_normal.png"))
        texture_material(name, f"materials/spillway/{name}.jpg", f"materials/spillway/{name}_normal.png")
    for name,tint in (("sw_rock",(.75,.78,.77)),("sw_moss",(.56,.64,.40)),("sw_mountain",(.57,.65,.68)),("sw_hill",(.40,.47,.38))):
        texture_material(name,scans+"seaside_rock_diff_2k.jpg",scans+"seaside_rock_nor_dx_2k.jpg",scans+"seaside_rock_rough_2k.jpg",tint)
    # Purpose-built graphic atlas: painted stencils, hydroelectric insignia and the reference's navy banner.
    atlas = Image.new("RGBA", (2048, 2048), (0, 0, 0, 0))
    d = ImageDraw.Draw(atlas)
    font = str(ROOT / "Assets/fonts/Dinish-Bold.ttf")
    regular = str(ROOT / "Assets/fonts/Dinish-Regular.ttf")
    def label(key, rect, lines, colors=(39, 43, 43, 255), background=None, fontsize=100, spacing=12, light=False):
        ATLAS[key] = rect
        x0, y0, x1, y1 = rect
        if background: d.rectangle(rect, fill=background)
        f = ImageFont.truetype(regular if light else font, fontsize)
        text = "\n".join(lines)
        bounds = d.multiline_textbbox((0, 0), text, font=f, spacing=spacing)
        while bounds[2] - bounds[0] > x1 - x0 - 20 or bounds[3] - bounds[1] > y1 - y0 - 16:
            fontsize -= 1
            f = ImageFont.truetype(regular if light else font, fontsize)
            bounds = d.multiline_textbbox((0, 0), text, font=f, spacing=spacing)
        d.multiline_text((x0 + 10, y0 + 8 - bounds[1]), text, fill=colors, font=f, spacing=spacing)
    label("hydro", (0, 0, 1220, 340), ["RIVERDALE", "HYDROELECTRIC", "UNIT 3"], fontsize=120, spacing=2)
    label("A1", (1250, 0, 1510, 320), ["A1"], fontsize=270)
    label("B2", (1530, 0, 1840, 320), ["B2"], colors=(221, 222, 213, 255), fontsize=260)
    label("C1", (0, 370, 260, 680), ["C1"], fontsize=250)
    label("turbine", (280, 370, 1240, 505), ["TURBINE HALL"], fontsize=100)
    label("control", (280, 530, 1240, 655), ["> CONTROL ROOM"], fontsize=90)
    label("02", (1260, 360, 1520, 635), ["02"], colors=(224, 217, 197, 255), fontsize=235)
    label("danger", (0, 730, 730, 970), ["DANGER", "FAST FLOWING WATER", "KEEP BEHIND GUARDRAILS"], colors=(32, 31, 26, 255), background=(201, 163, 48, 255), fontsize=76, spacing=2)
    label("restricted", (760, 730, 1480, 970), ["RESTRICTED AREA", "AUTHORISED PERSONNEL ONLY"], colors=(222, 221, 209, 255), background=(44, 59, 62, 255), fontsize=62, spacing=8)
    ATLAS["banner"]=(1536,700,2047,2047)
    d.rectangle(ATLAS["banner"],fill=(29,42,55,255))
    d.multiline_text((1600,1130),"CLEAN\nENERGY\nSECURE\nTOMORROW",font=ImageFont.truetype(regular,62),fill=(191,199,197,255),spacing=46)
    # Three pale wave ribbons, echoing the hydro graphic in the reference.
    for j in range(3):
        pts = []
        for i in range(121):
            x = 1638 + i * 2.45
            y = 963 + j * 36 - 43 * math.sin(i / 120 * math.pi * 1.75)
            pts.append((x, y))
        d.line(pts, fill=(185, 195, 196, 255), width=14)
    ATLAS["logo"] = (0, 1080, 430, 1530)
    for pts in (((205, 1100), (370, 1265), (295, 1335), (130, 1170)),
                ((120, 1180), (195, 1250), (115, 1330), (40, 1260)),
                ((220, 1270), (295, 1340), (130, 1505), (55, 1430))):
        d.polygon(pts, fill=(144, 53, 42, 255))
    label("03", (480, 1090, 700, 1380), ["03"], fontsize=230)
    label("outfall", (740, 1090, 1500, 1220), ["SPILLWAY / OUTFALL 3"], fontsize=70)
    label("pumps", (740, 1280, 1500, 1410), ["PUMP HOUSE"], fontsize=86)
    label("service", (0, 1580, 1480, 1750), ["RIVERDALE    •    GENERATING STATION"], colors=(212, 212, 200, 255), fontsize=75)
    atlas.convert("RGB").save(MAT / "graphics_color.png")
    atlas.getchannel("A").save(MAT / "graphics_alpha.png")
    texture_material("sw_graphics", "materials/spillway/graphics_color.png", alpha="materials/spillway/graphics_alpha.png")
    write(MAT / "sw_river.vmat", '"Layer0"\n{\n shader "shaders/hc1_spillway_river.shader"\n g_vWaterColor "[0.036 0.094 0.105]"\n g_vWaterFlow "[-62 3]"\n g_flRippleTile "83"\n g_flRippleStrength "1.35"\n g_flWaterRoughness "0.19"\n g_flAbsorptionDistance "48"\n g_flBankFade "0.3"\n}\n')
    for name, foam in (("sw_fall", 0), ("sw_foam", 1)):
        write(MAT / (name + ".vmat"), f'"Layer0"\n{{\n shader "shaders/hc1_spillway_falls.shader"\n g_flFoam "{foam}"\n}}\n')
    write(OUT / "graphics.json", json.dumps(ATLAS, indent=2))


def configure(m):
    for paint in m.polygons:
        if paint.startswith("sw_"):
            suffix="_v3" if paint=="sw_river" else "_v4" if paint in ("sw_fall","sw_foam","sw_mist") else "_v2" if paint in ("sw_dam","sw_concrete","sw_yard","sw_trim") else ""
            m.material_overrides[paint] = f"materials/spillway/{paint}{suffix}.vmat"
            m.tile_overrides[paint] = TILES.get(paint, 128)
        elif paint.startswith("rv_"):
            m.material_overrides[paint] = f"materials/riverdale/{paint}.vmat"
            m.tile_overrides[paint] = RM.TILES.get(paint, 64)
            replacements={"rv_yellow":"sw_safety", "rv_plinth":"sw_trim", "rv_wall":"sw_concrete", "rv_yard":"sw_yard", "rv_window_dark":"sw_window",
                          "rv_snow":"sw_mountain","rv_rock":"sw_mountain","rv_rock_far":"sw_mountain","rv_pine_far":"sw_mountain","rv_forest":"sw_hill"}
            if paint in replacements:
                target=replacements[paint]
                suffix="_v4" if target in ("sw_mountain","sw_hill") else "_v2" if target in ("sw_concrete","sw_trim","sw_yard") else ""
                m.material_overrides[paint]=f"materials/spillway/{target}{suffix}.vmat"
                m.tile_overrides[paint]=640 if target in ("sw_mountain","sw_hill") else TILES.get(target,128)
        elif paint.startswith("rw_"):
            m.material_overrides[paint] = RV.R.RM.material_path(paint)
            m.tile_overrides[paint] = 64
    return m


def graphic(m, key, centre, right, h, off=.6):
    x0, y0, x1, y1 = ATLAS[key]
    w = h * (x1 - x0) / (y1 - y0)
    uv = [(x0/2048, 1-y1/2048), (x1/2048, 1-y1/2048), (x1/2048, 1-y0/2048), (x0/2048, 1-y0/2048)]
    P.quad(m, "sw_graphics", centre, right, UP, w, h, uv=uv, off=off)


def slab(m, e0, e1, n0, n1, z=0, bottom=-440, floor="sw_yard"):
    box(m, e0, e1, n0, n1, bottom, z, {"default":"sw_concrete", "+z":floor}, STONE)
    # Weathered coping and the poured concrete joints on retaining faces.
    for n in (n0, n1):
        box(m, e0, e1, n-2, n+2, z-18, z-8, "rv_plinth")
    for e in np.arange(e0 + 240, e1, 240):
        box(m, e-1, e+1, n0-.3, n0+.3, bottom, z-20, "rv_plinth")


def rail(m, pts, z=0, height=42, clip=True, name="waterside"):
    P.railing(m, pts, z, height=height, post_every=78, clip_to=200 if clip else None, name=name)


def pipe(m, pts, radius, paint="rv_pipe", **kwargs):
    kwargs["sides"] = max(kwargs.get("sides", 10), 32 if radius >= 15 else 20)
    P.pipe(m, pts, radius, paint, **kwargs)


def case(m,c,size,along=(1,0),paint="rv_olive",z0=0,**kwargs):
    P.case(m,c,size,along,paint,z0,**kwargs)
    L,W,H=size
    if L<100:return
    right=P.unit(v(along[0],along[1],0));side=np.cross(UP,right)
    origin=v(c[0],c[1],z0)
    for sign in (-1,1):
        for x in (-L*.32,0,L*.32):
            centre=origin+right*x+side*(sign*(W/2+.45))+UP*(H*.35)
            P.bevel_box(m,centre,(right,side,UP),(2.2,1.6,H*.56),paint,.45)
    for x in (-L*.35,L*.35):
        P.bevel_box(m,origin+right*x+UP*2,(right,side,UP),(L*.13,W*.88,4),"rv_black",.65)


def roof_fan(m,centre,radius=40):
    e,n,z=centre
    P.lathe(m,(e,n),[(radius+4,z),(radius+4,z+3),(radius,z+6),(radius-2,z+6)],"rv_steel",32)
    P.cylinder(m,(e,n),radius-2,z+.2,z+1,"rv_dark",32)
    for j in range(5):
        a=j*2*math.pi/5
        points=[v(e+math.cos(a+off)*r,n+math.sin(a+off)*r,z+2+dz) for r,off,dz in ((7,-.12,0),(radius-4,.15,1),(radius-5,.52,1),(10,.24,0))]
        card(m,"rv_steel",points,UP)
    P.cylinder(m,(e,n),8,z+1,z+6,"rv_steel",24)
    for rr in (radius*.35,radius*.65,radius*.90):
        points=[v(e+math.cos(a)*rr,n+math.sin(a)*rr,z+7) for a in np.linspace(0,2*math.pi,33)]
        for p,q in zip(points[:-1],points[1:]):P.rod(m,p,q,.45,"rv_frame",5)
    for j in range(8):
        a=j*math.pi/4
        P.rod(m,(e,n,z+7),(e+math.cos(a)*(radius-2),n+math.sin(a)*(radius-2),z+7),.5,"rv_frame",5)


def equipment_cover(m, bounds):
    """A draped canvas shell, with sagging sides and rounded equipment underneath."""
    e0,e1,n0,n1,z0,z1=bounds
    # Retain the cover's previous solid gameplay envelope.
    box(m,e0,e1,n0,n1,z0,z1,{"default":None},STONE)
    rows,cols=24,48
    for face in ("top","front","back","left","right"):
        expected=UP if face=="top" else v(0,-1,0) if face=="front" else v(0,1,0) if face=="back" else v(-1,0,0) if face=="left" else v(1,0,0)
        def sample(u,vv):
            fold=math.sin(u*37+math.sin(vv*9)*.6)*1.15+math.sin(u*73+vv*13)*.35
            if face=="top":
                x=e0+(e1-e0)*u;y=n0+(n1-n0)*vv
                edge=min(u,1-u,vv,1-vv)
                z=z1-5*(1-min(1,edge*8))+fold*.35+math.sin(u*math.pi)*math.sin(vv*math.pi)*1.8
            elif face in ("front","back"):
                x=e0+(e1-e0)*u;y=(n0 if face=="front" else n1)+fold*(1-vv)*(.5 if face=="front" else -.5)
                z=z0+(z1-z0-4)*vv
            else:
                x=(e0 if face=="left" else e1)+fold*(1-vv)*(.5 if face=="left" else -.5)
                y=n0+(n1-n0)*u;z=z0+(z1-z0-4)*vv
            return v(x,y,z)
        def smooth(u,vv):
            du=sample(u+.0001,vv)-sample(u-.0001,vv)
            dv=sample(u,vv+.0001)-sample(u,vv-.0001)
            normal=P.unit(np.cross(du,dv))
            return normal if np.dot(normal,expected)>0 else -normal
        width=(e1-e0) if face in ("top","front","back") else n1-n0
        height=(n1-n0) if face=="top" else z1-z0
        for j in range(rows):
            for k in range(cols):
                coords=[(k/cols,j/rows),((k+1)/cols,j/rows),((k+1)/cols,(j+1)/rows),(k/cols,(j+1)/rows)]
                points=[sample(u,vv) for u,vv in coords]
                normals=[smooth(u,vv) for u,vv in coords]
                uv=[(u*width/96,vv*height/96) for u,vv in coords]
                normal=P.unit(np.cross(points[1]-points[0],points[3]-points[0]))
                if np.dot(normal,expected)<0:points.reverse();normals.reverse();uv.reverse();normal=-normal
                card(m,"sw_tarp",points,normal,uv=uv,normals=normals)


def window(m, centre, right, width, height, light=False):
    p, r = v(*centre), P.unit(v(*right))
    P.quad(m, "rv_window_lit" if light else "rv_window_dark", p, r, UP, width, height, off=.4)
    out = P.unit(np.cross(r, UP))
    for z in (-height/2, height/2):
        P.i_beam(m, p-r*width/2+UP*z+out, p+r*width/2+UP*z+out, 3, 4, "rv_frame")
    count = max(1, round(width/65))
    for i in range(count+1):
        a = p + r * (width*(i/count-.5)) + out
        P.i_beam(m, a-UP*height/2, a+UP*height/2, 3, 3, "rv_frame")


def building(m, bounds, floor=0, top=420, doors=(), windows=True, roof=True):
    e0,e1,n0,n1 = bounds
    walls = {
        "south": K.Wall("e", (e0,e1), (n0,n0+18), (floor,top), "-n"),
        "north": K.Wall("e", (e0,e1), (n1-18,n1), (floor,top), "+n"),
        "west": K.Wall("n", (n0+18,n1-18), (e0,e0+18), (floor,top), "-e"),
        "east": K.Wall("n", (n0+18,n1-18), (e1-18,e1), (floor,top), "+e"),
    }
    for face, at, width, height in doors:
        walls[face].add(at,width,floor,floor+height,"door")
    for wall in walls.values(): wall.build(m,"sw_concrete","rv_wall","rv_plinth",surface=STONE)
    if roof:
        box(m,e0-10,e1+10,n0-10,n1+10,top,top+18,"rv_plinth",STONE)
        rail(m,[(e0-5,n0-5),(e1+5,n0-5),(e1+5,n1+5),(e0-5,n1+5),(e0-5,n0-5)],top+18,clip=False)
    if windows:
        window(m,((e0+e1)/2,n0-.6,top-84),(1,0,0),e1-e0-100,100)
    for e in np.arange(e0+80,e1,240):
        box(m,e-10,e+10,n0-10,n0,0,top,"rv_plinth")
    for e in (e0+42,e1-42):
        pipe(m,[(e,n0-14,10),(e,n0-14,top+10),(e,n0+25,top+36)],3,"rv_pipe",sides=8)


def container(m, c, z=0, paint="sw_rust", num="02", length=420):
    e,n = c; w=110; h=112
    box(m,e-length/2,e+length/2,n-w/2,n+w/2,z,z+h,paint,METAL)
    for j in np.arange(-length/2+12,length/2,12):
        for side in (-1,1): box(m,e+j-2,e+j+2,n+side*w/2-1.5,n+side*w/2+1.5,z+8,z+h-8,paint)
    for a in (-1,1):
        for b in (-1,1): box(m,e+a*length/2-3,e+a*length/2+3,n+b*w/2-3,n+b*w/2+3,z,z+h,"rv_dark")
    for dz in (4,h-4):
        for side in (-1,1): box(m,e-length/2,e+length/2,n+side*w/2-3,n+side*w/2+3,z+dz-3,z+dz+3,"rv_dark")
    for j in (-.28,.28):
        P.rod(m,(e+length/2+2,n+j*w,z+8),(e+length/2+2,n+j*w,z+h-8),1.3,"rv_pipe",8)
    graphic(m,num,(e-length*.26,n-w/2-.8,z+h*.5),(1,0,0),56)


def deck_ground():
    m=K.Model()
    slab(m,-2400,-850,-1800,1950)
    slab(m,1100,2400,-1800,1950)
    slab(m,-500,750,-1150,1550)
    slab(m,-850,1100,1550,1950)
    # Bridges: each channel crossing remains wide enough for two players.
    for lo,hi in ((-850,-500),(750,1100)):
        for a,b in ((-900,-690),(130,350),(1110,1340)):
            slab(m,lo,hi,a,b,bottom=-36)
            for n in (a+4,b-4): rail(m,[(lo,n),(hi,n)])
            P.i_beam(m,(lo,a+10,-30),(hi,a+10,-30),25,14,"rv_steel")
            P.i_beam(m,(lo,b-10,-30),(hi,b-10,-30),25,14,"rv_steel")
    # Right foreground terrace, split from the lower road by two traversable stairs.
    slab(m,1440,2400,-1800,-810,z=128)
    P.stairs(m,(1515,-510),(1515,-810),150,0,128,tread="rv_yard",side="rv_plinth",solid_under=True,name="B2 north")
    P.stairs(m,(1140,-1320),(1440,-1320),156,0,128,tread="rv_yard",side="rv_plinth",solid_under=True,name="B2 west")
    # All exposed channel edges are guarded; intentionally leave the three bridge mouths open.
    runs=[(-1800,-900),(-690,130),(350,1110),(1340,1550)]
    for e in (-850,1100):
        for a,b in runs: rail(m,[(e,a),(e,b)])
    for e in (-500,750):
        for a,b in [(-1150,-900),(-690,130),(350,1110),(1340,1550)]: rail(m,[(e,a),(e,b)])
    rail(m,[(-500,-1150),(750,-1150)])
    rail(m,[(-2400,-1800),(-850,-1800)])
    rail(m,[(1100,-1800),(1440,-1800)])
    rail(m,[(1440,-1800),(2400,-1800)],128)
    rail(m,[(1440,-1800),(1440,-1400)],128)
    rail(m,[(1440,-1240),(1440,-810)],128)
    rail(m,[(1595,-810),(2400,-810)],128)
    for e in (-2400,2400):
        box(m,e-18,e+18,-1800,1950,0,180,"sw_concrete",STONE)
    # Rear parapet catches the playable boundary below the dam basin.
    box(m,-2400,2400,1940,1970,0,90,"sw_concrete",STONE)
    rail(m,[(-2400,1940),(2400,1940)],90,clip=False)
    for e in (-2375,2375): P.clip("perimeter",(e,-1800),(e,1950),0,1800,8)
    P.clip("rear perimeter",(-2400,1938),(2400,1938),90,1800,8)
    return m


def west_works():
    m=K.Model()
    building(m,(-2380,-1330,130,1250),top=620,doors=[("south",-1750,210,170),("north",-1750,210,170),("east",720,200,170)])
    graphic(m,"hydro",(-1720,117,355),(1,0,0),160)
    graphic(m,"logo",(-2225,116,355),(1,0,0),175)
    graphic(m,"turbine",(-1750,126,196),(1,0,0),44)
    for n in (350,700,1030):
        P.tank(m,(-2200,n),70,180,z0=0,paint="rv_steel",ladder=False)
        pipe(m,[(-2200,n,185),(-2070,n,185),(-2070,n,30)],15)
    for n in (360,850):
        P.ceiling_light(m,f"Turbine interior {n}",(-1770,n,245),radius=430,shadows=True)
    for n in (300,600,900,1200):
        P.wall_light(m,f"Turbine east {n}",(-1327,n,185),(1,0,0),radius=220)
    for z in (320,500):
        window(m,(-1328,690,z),(0,1,0),930,84)
    for n in (220,1150):
        box(m,-1328,-1310,n-50,n+50,25,118,"rv_steel",METAL)
        P.louvre(m,(-1308,n,75),(0,1,0),86,64)
    # A narrow maintenance gallery across the facade, behind the main circulation.
    box(m,-2390,-1325,78,130,228,237,"rv_steel")
    rail(m,[(-2380,80),(-1330,80)],237,clip=False)
    for e in (-2310,-2050,-1790,-1530):
        P.i_beam(m,(e,100,233),(e,130,190),6,7,"rv_steel")
    # Roof monitor and ventilators.
    building(m,(-2300,-1480,850,1190),floor=638,top=790,windows=True,roof=False)
    for e in (-2190,-1940,-1690):
        box(m,e-72,e+72,350,530,638,710,"rv_steel")
        P.louvre(m,(e,348,675),(1,0,0),130,65)
        roof_fan(m,(e,440,711),43)
    # Covered red deployment court, with a screening wall between spawn and mid.
    building(m,(-2380,-1850,-1660,-880),top=220,doors=[("south",-2110,240,150),("north",-2110,240,150),("east",-1150,220,150)],windows=False)
    box(m,-1790,-1750,-1480,-1000,0,132,"sw_concrete",STONE)
    P.wall_light(m,"Red shelter",(-2110,-1300,180),(0,-1,0),radius=300)
    container(m,(-1380,-1560),length=350,paint="rv_steel",num="03")
    P.case_stack(m,(-1190,-1070),(0,1),seed=81)
    P.case_stack(m,(-1120,-270),(1,0),seed=82)
    P.jersey(m,(-1100,840),(0,1),180)
    graphic(m,"danger",(-900,-20,42),(0,-1,0),50)
    # Pipe run along the exposed west retaining wall, with large flange rings.
    for z,r in ((-74,15),(-160,11)):
        pipe(m,[(-830,-1750,z),(-830,-850,z),(-830,250,z),(-830,1700,z)],r,"rv_pipe",sides=12,flanges=[0,1,2,3])
    return m


def east_works():
    m=K.Model()
    building(m,(1710,2380,-160,750),top=970,doors=[("west",270,220,180),("north",2030,220,180)],windows=False)
    # The right side of the reference is a very tall concrete service tower and a full-height blue banner.
    graphic(m,"banner",(2035,-174,535),(1,0,0),760)
    for e in (1750,1790): pipe(m,[(e,-182,12),(e,-182,990),(e,80,990)],8,"rv_pipe",sides=10)
    for e in (1820,2150):
        box(m,e-105,e+105,80,320,990,1080,"rv_steel")
        P.louvre(m,(e,76,1035),(1,0,0),190,76)
        for n in (145,255):roof_fan(m,(e,n,1081),42)
    P.beacon(m,"Tower beacon",(2220,300,1125),light=False)
    for n in (20,430):
        P.wall_light(m,f"Tower west {n}",(1708,n,190),(-1,0,0),radius=300)
    for z in (330,570,805):
        window(m,(1708,290,z),(0,-1,0),720,92)
        box(m,1704,1710,-155,745,z-62,z-55,"rv_plinth")
    building(m,(1640,2380,1000,1650),top=350,doors=[("south",2010,220,170),("west",1330,220,170),("north",2010,220,170)])
    graphic(m,"pumps",(2010,998,205),(1,0,0),54)
    P.ceiling_light(m,"Pumps interior",(2020,1300,220),radius=440,shadows=True)
    for n in (1140,1490):
        P.tank(m,(2260,n),50,170,paint="rv_white",ladder=False)
    # Blue deployment shed on the elevated B2 deck.
    building(m,(1860,2370,-1660,-1060),floor=128,top=350,doors=[("west",-1440,200,160),("north",2080,220,160)],windows=False)
    graphic(m,"B2",(1720,-1801,8),(1,0,0),170)
    P.wall_light(m,"B2 shelter",(2110,-1330,310),(0,-1,0),radius=310)
    case(m,(1750,-1010),(170,94,86),(1,0),z0=128)
    case(m,(1750,-1010),(130,85,65),(1,0),z0=214)
    case(m,(2290,-920),(120,90,100),(1,0),z0=128)
    # Canvas-covered equipment and its retaining straps on the B2 loading deck.
    equipment_cover(m,(1480,1620,-1770,-1640,128,218))
    for e in (1500,1600):
        box(m,e-2,e+2,-1771,-1639,218,220,"rv_dark")
        box(m,e-2,e+2,-1772,-1770,128,220,"rv_dark")
    P.case_stack(m,(1300,650),(0,1),seed=88)
    P.jersey(m,(1300,1520),(1,0),180)
    container(m,(2070,1830),length=370,paint="rv_steel",num="03")
    pipe(m,[(1080,-1740,-75),(1080,1720,-75)],17,"rv_pipe",sides=12)
    for n in (-400,750):
        pipe(m,[(1670,n,0),(1670,n,300),(900,n,300),(900,n,200)],12,"rv_pipe",sides=12)
    return m


def control_house():
    m=K.Model()
    # Passage under the front control room: three portals make a small, defensible interior.
    building(m,(-400,690,650,1450),top=218,doors=[("south",330,220,166),("west",920,200,166),("east",920,200,166),("north",250,200,166)],windows=False,roof=False)
    box(m,-420,710,630,1470,218,236,"rv_plinth",STONE)
    # An upper room with glazed front, and doors onto the two exterior landings.
    for e0,e1,n0,n1 in ((-370,660,1330,1450),(-370,-350,800,1330),(640,660,800,1330)):
        box(m,e0,e1,n0,n1,236,486,"sw_concrete",STONE)
    # Two full-height doorways align with the exterior stairs. The window sill
    # is split at both entrances, so bots and standing players can enter.
    for a,b in ((-370,-345),(-205,490),(630,660)):
        box(m,a,b,800,818,236,274,"sw_concrete",STONE)
    box(m,-370,660,800,818,402,486,"sw_concrete",STONE)
    for e in (-365,-345,-205,-35,135,305,475,490,630,655):
        box(m,e-5,e+5,795,821,274,402,"rv_frame",METAL)
    box(m,-390,680,780,1470,486,510,"rv_plinth",STONE)
    # Doorways from side landings into the control room are in its short front side walls.
    for e in (-370,640):
        box(m,e,e+20,650,690,236,486,"sw_concrete",STONE)
        box(m,e,e+20,690,800,420,486,"sw_concrete",STONE)
    # Open south balcony connects both stairs, so the upper floor has two exits.
    for a,b in ((-410,-343),(-207,492),(628,700)):
        rail(m,[(a,640),(b,640)],236)
    for e in (-420,710):
        rail(m,[(e,630),(e,1470)],236)
    P.stairs(m,(-275,180),(-275,630),136,0,236,name="Control west")
    P.stairs(m,(560,180),(560,630),136,0,236,name="Control east")
    # Landings occupy the ends of the balcony, not the stair mouth.
    graphic(m,"A1",(-401,1190,325),(0,-1,0),180)
    graphic(m,"control",(180,629,198),(1,0,0),50)
    for e in (-110,180,480):
        P.wall_light(m,f"A1 porch {e}",(e,648,155),(0,-1,0),radius=230)
    for n in (900,1230):
        P.ceiling_light(m,f"A1 lower {n}",(100,n,190),radius=390,shadows=True)
        P.ceiling_light(m,f"Control upper {n}",(150,n,462),radius=480,shadows=True)
    for e in (-190,60,310,500):
        box(m,e-60,e+60,1240,1310,236,270,"rv_desk",METAL)
        P.screen(m,"schematic",(e,1237,301),(1,0,0),45)
    # Taller stair/service core and rooftop communications.
    box(m,-400,-190,1150,1450,510,660,"sw_concrete")
    window(m,(-295,1148,590),(1,0,0),140,65)
    P.rod(m,(-300,1330,660),(-300,1330,900),3,"rv_pipe",8)
    for z in (720,790,850): P.rod(m,(-355,1330,z),(-245,1330,z),1,"rv_dark",6)
    # Roof clerestory, ventilation, cable trays and an A1 service facade.
    building(m,(-170,590,1110,1430),floor=510,top=660,windows=True,roof=False)
    for e in (-95,210,510):
        box(m,e-34,e+34,860,1000,510,567,"rv_steel")
        P.louvre(m,(e,858,543),(1,0,0),60,48)
    for e in (-380,674):
        pipe(m,[(e,825,10),(e,825,474),(e,1170,474)],4,"rv_pipe",sides=8)
    for z in (90,310):
        P.louvre(m,(-401,1060,z),(0,-1,0),90,70)
    return m


def cargo_yard():
    m=K.Model()
    container(m,(-170,-590),length=390)
    P.case_stack(m,(225,-770),(1,0),seed=91)
    P.case_stack(m,(560,-1030),(0,1),seed=92)
    P.case_stack(m,(-340,-1000),(1,0),seed=93)
    for e,n,L,W,H in ((-280,-400,160,80,70),(325,-1050,170,90,90),(610,-655,110,140,78),(-400,-215,92,150,65),(90,-350,140,85,56)):
        case(m,(e,n),(L,W,H),(1,0),z0=0)
        if H>75:case(m,(e+4,n),(L*.76,W*.9,48),(1,0),z0=H)
    # A pallet, hose loops and cabinets make the shipping yard read at player scale.
    for e in range(-285,-105,26):box(m,e,e+20,-712,-663,2,7,"rv_desk")
    for e in (-325,-280):
        box(m,e-18,e+18,332,358,0,79,"rv_steel",METAL)
    for j in range(3):
        pts=[(90+math.cos(t)*(44+j*4),-1080+math.sin(t)*(22+j*2),3+j) for t in np.linspace(0,2*math.pi,32)]
        for a,b in zip(pts[:-1],pts[1:]):P.rod(m,a,b,1.2,"rv_dark",5)
    P.jersey(m,(300,-120),(0,1),160)
    P.jersey(m,(-310,-100),(1,0),160)
    # A1 stair core wraps the west stairs without crossing their walking volume.
    building(m,(-430,-110,60,650),top=510,doors=[("south",-275,190,170),("north",-275,190,460)],windows=False)
    graphic(m,"A1",(-270,58,310),(1,0,0),190)
    window(m,(-109,365,418),(0,1,0),430,90)
    box(m,-440,-100,42,68,183,192,"rv_plinth")
    P.wall_light(m,"Stair core entrance",(-155,53,176),(0,-1,0),radius=240)
    # Enclosed high service gallery, visually joining the central works and tower.
    box(m,710,1710,690,835,302,318,"rv_plinth")
    box(m,710,1710,680,845,424,439,"rv_plinth")
    for e in np.arange(735,1710,140):
        box(m,e-5,e+5,686,694,318,424,"rv_frame")
    window(m,(1210,687,370),(1,0,0),970,92)
    pipe(m,[(715,855,350),(1705,855,350)],9,"rv_pipe",sides=10)
    # Damp grates and cable trenches, useful reference-scale detail.
    for e,n,w,h in ((330,-460,150,55),(-50,-930,190,60),(980,-470,90,140),(-1130,50,140,60),(1730,-960,140,65)):
        P.quad(m,"rv_grating",(e,n,.35),(1,0,0),(0,1,0),w,h)
    # Big pipe wraps around the island retaining wall, with visible elbows and discharge spouts.
    pipe(m,[(-480,-1090,-125),(680,-1090,-125),(680,-900,-125)],23,"rv_pipe",sides=16)
    for e in (-380,570):
        pipe(m,[(e,-1050,-70),(e,-1190,-70),(e,-1240,-145)],19,"rv_pipe",sides=12)
    for e,n,z in ((570,-400,0),(-1110,-600,0),(1290,-250,0),(1630,-1600,128)):
        box(m,e-9,e+9,n-9,n+9,z,z+13,"rv_plinth")
        P.rod(m,(e,n,z+8),(e,n,z+310),3,"rv_steel",10)
        for off in (-35,35): P.wall_light(m,f"Yard mast {e} {off}",(e+off,n,z+310),(0,-1,0),radius=430)
        P.rod(m,(e-42,n,z+302),(e+42,n,z+302),2,"rv_steel",8)
    # Marked loading bay with broken, worn paint rather than a solid bright decal.
    for e in range(-440,700,80):
        box(m,e,e+37,-1140,-1137,.3,.5,"rv_line_yellow")
    return m


def dam_front(e,z):
    t = max(0,min(1,(z+350)/3650))
    return 3520 + 1150*(t**.72) + .000010*e*e


def spillway_dam():
    m=K.Model()
    edges=np.linspace(-7600,7600,23)
    zs=[-350,0,400,1000,1750,2400,2900,3300]
    for k,(e0,e1) in enumerate(zip(edges[:-1],edges[1:])):
        for z0,z1 in zip(zs[:-1],zs[1:]):
            pts=[(e0,dam_front(e0,z0),z0),(e1,dam_front(e1,z0),z0),(e1,dam_front(e1,z1),z1),(e0,dam_front(e0,z1),z1)]
            normal=P.unit(np.cross(v(*pts[1])-v(*pts[0]),v(*pts[3])-v(*pts[0])))
            card(m,"sw_dam",pts,normal)
        # Expansion buttresses remain large enough to register from the yard.
        if k%2==0:
            for z0,z1 in zip(zs[:-1],zs[1:]):
                pts=[(e0-24,dam_front(e0,z0)-26,z0),(e0+24,dam_front(e0,z0)-26,z0),
                     (e0+24,dam_front(e0,z1)-26,z1),(e0-24,dam_front(e0,z1)-26,z1)]
                card(m,"rv_plinth",pts,(0,-1,.3))
        crest=dam_front((e0+e1)/2,3300)
        box(m,e0,e1,crest-80,crest+300,3300,3400,"sw_concrete")
        rail(m,[(e0,crest-80),(e1,crest-80)],3400,clip=False,height=54)
        rail(m,[(e0,crest+290),(e1,crest+290)],3400,clip=False,height=54)
    # Four broad torrents, each in a deep coffer below the crest road.
    for k,e in enumerate((-4300,-3200,-2100,-1000)):
        top=dam_front(e,2980)
        box(m,e-420,e+420,top-95,top+80,2970,3270,"rv_dark")
        for side in (-1,1):
            box(m,e+side*455-45,e+side*455+45,top-160,top+210,2810,3410,"sw_concrete")
        P.i_beam(m,(e-420,top-120,3130),(e+420,top-120,3130),80,55,"rv_steel")
    for j,e in enumerate((-5600,-2700,700,4700)):
        n=dam_front(e,3300)
        box(m,e-185,e+185,n-100,n+310,3400,3930,"sw_concrete")
        window(m,(e,n-101,3760),(1,0,0),210,130)
        box(m,e-210,e+210,n-120,n+330,3920,3950,"rv_plinth")
        P.rod(m,(e,n+60,3950),(e,n+60,4510),6,"rv_steel",10)
        for a in (-1,1): P.rod(m,(e+a*130,n,3950),(e,n+60,4350),1.5,"rv_dark",6)
        for z in (4120,4240,4360): P.rod(m,(e-60,n+60,z),(e+60,n+60,z),2,"rv_pipe",6)
        P.beacon(m,f"Crest beacon {j}",(e,n+60,4508),light=False)
    # Compress the backdrop's vertical scale so the crest sits above the plant,
    # with the entire four-bay spillway visible from the reference riverbank.
    for model in (m,):
        for paint,faces in model.polygons.items():
            for index,(pts,normal) in enumerate(faces):
                faces[index]=([v(p[0],p[1]+400,(p[2]+245)*.78-245) for p in pts],P.unit(normal/v(1,1,.78)))
                if (paint,index) in model.polygon_normals:
                    model.polygon_normals[paint,index]=[P.unit(n/v(1,1,.78)) for n in model.polygon_normals[paint,index]]
    return m,WATERFALLS.build()


def pylon(m,e,n,h=1700):
    # Tapering four-chord lattice with three crossarms and catenary conductors.
    for z0,z1 in zip([0,350,750,1150],[350,750,1150,h]):
        a=145*(1-z0/h)+28; b=145*(1-z1/h)+28
        for s in (-1,1):
            for t in (-1,1):
                P.rod(m,(e+s*a,n+t*a,z0),(e+s*b,n+t*b,z1),4,"rv_steel",6)
            P.rod(m,(e-a,n+s*a,z0),(e+b,n+s*b,z1),2,"rv_steel",5)
            P.rod(m,(e+a,n+s*a,z0),(e-b,n+s*b,z1),2,"rv_steel",5)
            P.rod(m,(e+s*a,n-a,z0),(e+s*b,n+b,z1),2,"rv_steel",5)
    for z,w in ((h*.68,400),(h*.83,300),(h,220)):
        P.truss(m,(e-w,n,z),(e+w,n,z),55,chord=3,web=1.5)
        for s in (-1,1):
            P.rod(m,(e+s*w,n,z),(e+s*w,n,z-90),5,"rv_dark",8)
    return h


def backdrop():
    m=K.Model(); trees=K.Model(); near=K.Model()
    rng=np.random.default_rng(6459)
    radii,angles,heights=LANDSCAPE.terrain(m,rng)
    # The dam occupies the north side; trees frame its right flank and distant ridges.
    for k in range(4800):
        a=rng.uniform(0,2*math.pi); r=rng.uniform(5000,27000)
        e,n=r*math.sin(a),r*math.cos(a)
        if n>2200 and abs(e)<7800: continue
        z=RB.height_at(radii,angles,heights,e,n)-30
        if z < 5300: spruce(trees,(e,n,z),rng.uniform(340,680),rng)
    # Near riverbanks, visibly rough and moss covered, outside the playable enclosure.
    for k in range(130):
        side=-1 if k<78 else 1
        e=side*rng.uniform(2500,4800); n=rng.uniform(-3400,3800)
        z=-160+max(0,abs(e)-2650)*.22
        rock(near,(e,n,z),(rng.uniform(160,480),rng.uniform(180,450),rng.uniform(150,400)),rng)
    # Nearer trees on the high banks have textured, irregular silhouettes.
    for k in range(160):
        e=rng.uniform(3100,7200); n=rng.uniform(2400,6800)
        z=RB.height_at(radii,angles,heights,e,n)-30
        spruce(trees,(e,n,z),rng.uniform(450,850),rng)
    # Reference foreground: rough mossy rocks on the left bank below the viewpoint.
    for k in range(14):
        rock(near,(-1550-rng.uniform(0,600),-2100-rng.uniform(0,650),-70),
             (rng.uniform(180,340),rng.uniform(160,330),rng.uniform(130,260)),rng)
    # The terrain supplies slope normals; preserve them across the ridgelines.
    for e,n,h in ((3300,2600,2050),(4900,3900,1810),(-6600,1900,1900)):
        pylon(near,e,n,h)
    for offset,z in ((-300,1630),(300,1630),(-220,1930),(220,1930)):
        pts=[]
        for t in np.linspace(0,1,24):
            pts.append((3300+offset+1600*t,2600+1300*t,z-200*t-180*math.sin(t*math.pi)))
        for a,b in zip(pts[:-1],pts[1:]): P.rod(near,a,b,1.5,"rv_dark",4)
    # Gated service structures beyond the rear railing, and massive intake penstocks.
    for e in (-2200,2050):
        box(near,e-230,e+230,2400,2780,-100,290,"sw_concrete")
        window(near,(e,2398,210),(1,0,0),340,80)
        for off in (-150,150): P.pipe(near,[(e+off,2600,260),(e+off,2600,600),(e+off,3500,600)],35,"rv_pipe",sides=12)
    return m,trees,near


def smooth_normals(m):
    sums={}
    for paint,faces in m.polygons.items():
        for pts,normal in faces:
            for p in pts:
                key=tuple(np.round(p,3));sums[key]=sums.get(key,np.zeros(3))+normal
    for paint,faces in m.polygons.items():
        for i,(pts,normal) in enumerate(faces):
            m.polygon_normals[paint,i]=[P.unit(sums[tuple(np.round(p,3))]) for p in pts]


def spruce(m,base,h,rng):
    centre=v(*base)+UP*h*.5
    angle=rng.uniform(0,math.pi)
    for j in range(2):
        a=angle+j*math.pi/2
        r=v(math.cos(a),math.sin(a),0)
        pts=[centre-r*h*.32-UP*h*.5,centre+r*h*.32-UP*h*.5,
             centre+r*h*.32+UP*h*.5,centre-r*h*.32+UP*h*.5]
        m.polygon("sw_spruce",pts,uv=[(0,0),(1,0),(1,1),(0,1)],both_sides=True)


def rock(m, centre, scale, rng):
    rows,cols=8,12
    e,n,z=centre; se,sn,sz=scale
    jitter=rng.uniform(.83,1.17,(rows+1,cols))
    for j in range(rows):
        for k in range(cols):
            pts=[]; ns=[]
            for jj,kk in ((j,k),(j,(k+1)%cols),(j+1,(k+1)%cols),(j+1,k)):
                a=2*math.pi*kk/cols; b=math.pi*jj/rows
                normal=v(math.sin(b)*math.cos(a),math.sin(b)*math.sin(a),math.cos(b))
                pts.append(v(e,n,z)+normal*v(se,sn,sz)*jitter[jj,kk]); ns.append(P.unit(normal/v(se,sn,sz)))
            card(m,"sw_rock",pts,np.mean(ns,axis=0),normals=ns)


def water():
    m=K.Model()
    # One continuous sheet under the whole map. Opaque ground hides it where there is land;
    # the old separate tiles left open sky between the west/east rocks and the platforms.
    e0,e1,n0,n1=-7400,7400,-7000,WATERFALLS.BASIN_END
    P.quad(m,"sw_river",((e0+e1)/2,(n0+n1)/2,WATER_Z),(1,0,0),(0,1,0),e1-e0,n1-n0)
    # Smaller outfalls on the island, just as in the foreground of the reference.
    for e in (-380,570):
        pts=[(e-32,-1240,-143),(e+32,-1240,-143),(e+47,-1265,WATER_Z),(e-47,-1265,WATER_Z)]
        card(m,"sw_fall",pts,(0,-1,0),uv=[(0,0),(1,0),(1,1),(0,1)])
        P.quad(m,"sw_foam",(e,-1330,WATER_Z+2),(1,0,0),(0,1,0),160,280,uv=[(0,0),(1,0),(1,1),(0,1)])
    return m


RED=[(-2220,-1450,0),(-2070,-1450,0),(-1920,-1450,0),(-2220,-1260,0),(-2070,-1260,0),(-1920,-1260,0),
     (-2220,-1060,0),(-2070,-1060,0),(-1920,-1060,0),(-2260,-1700,0),(-2080,-1700,0),(-1900,-1700,0)]
BLUE=[(1980,-1500,128),(2140,-1500,128),(2290,-1500,128),(1980,-1310,128),(2140,-1310,128),(2290,-1310,128),
      (1960,-1160,128),(2140,-1160,128),(2300,-1160,128),(1700,-1540,128),(1650,-1420,128),(1650,-1230,128)]
DM=[(-1130,-730,0),(-1130,400,0),(-1760,490,0),(-1760,1390,0),(-970,1800,0),(50,1800,0),(1300,1780,0),
    (2000,1250,0),(1290,1000,0),(1300,-450,0),(1250,-1100,0),(1730,-1650,128),(20,-900,0),
    (540,-460,0),(-320,20,0),(100,480,0),(200,1030,0),(100,1000,236)]
DOM=[("A",(-1100,600,0)),("B",(100,-160,0)),("C",(1320,850,0))]
HOT=[("Cargo",(80,-890,0)),("Control",(100,1050,236)),("Turbine",(-1750,720,0)),("Tailrace",(1240,-1000,0)),("Service",(30,1770,0))]
SITES=[("bombsite_a","A · Control",-90,450,850,1200,0),("bombsite_b","B · Cargo",-360,530,-1000,-350,0)]


def minimap():
    # Radar is a top-down drawing of the authored walkable platforms and rooms.
    size=1024; span=5200; cy=75
    img=Image.new("RGB",(size,size),(20,36,43)); d=ImageDraw.Draw(img)
    def point(e,n): return ((e+span/2)/span*size,(cy+span/2-n)/span*size)
    def rect(b,fill,outline=None):
        e0,e1,n0,n1=b; d.rectangle((*point(e0,n1),*point(e1,n0)),fill=fill,outline=outline,width=3)
    for b in ((-2400,-850,-1800,1950),(1100,2400,-1800,1950),(-500,750,-1150,1550),(-850,1100,1550,1950)):
        rect(b,(115,127,128),(172,177,166))
    for a,b in ((-850,-500),(750,1100)):
        for c,f in ((-900,-690),(130,350),(1110,1340)):rect((a,b,c,f),(159,166,154))
    for b in ((-2380,-1330,130,1250),(1710,2380,-160,750),(1640,2380,1000,1650),(-400,690,650,1450),(-430,-110,60,650),(-2380,-1850,-1660,-880),(1860,2370,-1660,-1060)):
        rect(b,(69,81,85),(188,191,177))
    for p,color in ((RED[4],(187,91,76)),(BLUE[4],(68,137,190))):
        x,y=point(*p[:2]);d.ellipse((x-10,y-10,x+10,y+10),fill=color)
    dest=STAGE/"ui/minimaps/minimap_spillway.png";dest.parent.mkdir(parents=True,exist_ok=True);img.save(dest)


def scene(written):
    RV.ids=IDS;RV.TITLE="Spillway";RV.RESOURCE_DIR="models/maps/spillway"
    RV.SCENE_FILE=OUT/"scene-import.json";RV.MAP_ART_PATH="ui/maps/spillway.png"
    RV.MINIMAP_PATH="ui/minimaps/minimap_spillway.png";RV.MINIMAP_CENTRE=(0,75);RV.MINIMAP_SIZE=5200
    RV.PLAY=PLAY;RV.NAV_TOP=560;RV.CATCH_FLOOR_Z=-1100
    RV.SUN_PITCH=28;RV.SUN_YAW=135;RV.SUN_COLOUR="2.80,2.43,2.04,1"
    RV.SKY_MATERIAL="materials/spillway/sky/spillway_overcast.vmat";RV.FOG_COLOUR="0.47,0.55,0.64"
    RV.RED_SPAWNS=RED;RV.BLUE_SPAWNS=BLUE;RV.DM_SPAWNS=DM
    RV.DOMINATION=DOM;RV.HOT_ZONES=HOT;RV.BOMB_SITES=SITES
    RV.BUY_ZONE=(1820,2390,-1770,-900,110,420)
    RV.RETAKES={
        "bombsite_a":{"planter":[(100,1010,0),(390,1100,0)],"defender":[(450,1360,0),(100,1040,236),(550,720,236)],"attacker":[(-1100,1100,0),(-1100,1450,0),(1320,1280,0),(1340,700,0),(-50,1770,0),(160,370,0)]},
        "bombsite_b":{"planter":[(250,-720,0),(200,-480,0)],"defender":[(540,-480,0),(500,-900,0),(-260,-1020,0)],"attacker":[(-1100,-780,0),(-1100,-450,0),(-1150,-1300,0),(1300,-980,0),(1250,-580,0),(100,30,0)]}}
    RV.CASH_POINTS=[("Cargo",(180,-900,0),(1250,-1100,0)),("Control",(100,1000,236),(-1750,700,0)),("Service",(60,1770,0),(2000,1270,0))]
    RV.HAZE=[("Dam spray",(-6400,-800,2750,4400,-320,750),.23,"0.69,0.76,0.80,1"),
             ("Tailrace mist",(-900,1120,-2400,2000,-310,-110),.10,"0.56,0.66,0.72,1")]
    RV.ROOF_CLIPS=[]
    # Prevent out-of-bounds routes along the visual rooftop railings.
    for name,b in (("Turbine roof",(-2400,-1310,110,1270,638,1750)),("Tower roof",(1690,2400,-180,770,990,1750)),
                   ("Pump roof",(1620,2400,980,1670,370,1750)),("Control roof",(-410,700,780,1470,510,1750)),
                   ("Red shelter roof",(-2380,-1840,-1660,-880,240,1750)),("Blue shelter roof",(1850,2380,-1670,-1050,370,1750))):
        RV.ROOF_CLIPS.append((name,b))
    RV.SCENE_MODELS=[(name,title,collide,shadow) for name,title,collide,shadow in written]
    RV.callouts=lambda:[("RED / GENERATORS",-2400,-1800,-1800,120,-10,300),("TURBINE HALL",-2400,-1300,120,1300,-10,650),
       ("WEST RACE",-1330,-850,-1800,1550,-10,600),("CARGO YARD",-500,750,-1150,650,-10,230),
       ("A1 / CONTROL",-420,710,630,1470,230,510),("A1 / SERVICE",-420,710,630,1470,-10,230),
       ("B2 / LOADING",1440,2400,-1800,-810,110,600),("EAST RACE",1100,1710,-810,1000,-10,600),
       ("PUMP HOUSE",1640,2400,1000,1660,-10,500),("DAM ACCESS",-2400,2400,1550,1950,-10,700)]
    RV.write_scene([x[0] for x in written],P.LIGHTS,[
        ("Yard",(20,-350,180),(-2400,2400,-1800,1950,-400,1100)),
        ("Turbine",(-1750,690,140),(-2370,-1340,150,1240,0,600)),
        ("Control lower",(130,1040,100),(-390,680,660,1440,0,218)),
        ("Control upper",(130,1050,340),(-360,650,810,1440,236,480)),
        ("Pump room",(2000,1320,160),(1660,2370,1020,1640,0,340))])
    data=json.loads(RV.SCENE_FILE.read_text())
    data["Title"]="Spillway"
    data["GameObjects"].append(K.game_object(IDS,"Sky Fill","ambient",components=[
        K.component(IDS,"Sandbox.AmbientLight","ambient/light",Color="0.095,0.120,0.160,1")]))
    for root in data["GameObjects"]:
        name=root.get("Name","")
        if name=="Sun":root["Components"][0]["SkyColor"]="0.20,0.25,0.33,1"
        if name=="Reflection Probes":
            for index,probe in enumerate(root["Children"]):
                for comp in probe["Components"]:
                    if comp["__type"]=="Sandbox.EnvmapProbe":
                        cache=SOURCE/"lighting/reflections.json"
                        texture=json.loads(cache.read_text())[index]["Path"] if cache.exists() else f"lighting/spillway/reflection_{index}.vtex"
                        comp.update(Mode="CustomTexture",Texture=texture)
                        comp.pop("RenderDynamically",None)
        if name=="Player Clips":
            # P.clip's yaw already maps its long plan axis to world X. Its local
            # collider therefore has length on X, not Y (the old helper swaps it).
            for go,spec in zip(root["Children"],P.CLIPS):
                for comp in go["Components"]:
                    if comp["__type"]=="Sandbox.BoxCollider":comp["Scale"]=K.vec(spec[3])
        if name=="Riverdale":
            root["Name"]="Spillway"
            for child in root["Children"]:
                if child["Name"]=="Dam":
                    for comp in child["Components"]:
                        if comp["__type"]=="Sandbox.ModelRenderer":comp["RenderType"]="On"
                if child["Name"]=="River":
                    child["Tags"]="water"
                    child["Components"].append(K.component(IDS,"Facepunch.LowtideWaterReflections","world/water/reflection",
                        WaterHeight=WATER_Z,MaximumWidth=960,ChannelMinimum="-7000,-7400",ChannelMaximum="4000,7400"))
        if name=="Scene Information":
            for comp in root["Components"]:
                if comp["__type"]=="Sandbox.SceneInformation": comp["Description"]="Fight across the rain-soaked terraces, control rooms and bridges of Riverdale Hydroelectric beneath a monumental alpine spillway."
        if name=="Look":
            for comp in root["Components"]:
                if comp["__type"]=="Sandbox.Tonemapping": comp.update(AutoExposureEnabled=True,MinimumExposure=1.0,MaximumExposure=1.0,ExposureCompensation=0)
                if comp["__type"]=="Sandbox.ColorGrading":comp.update(ColorTempK=6900,BlendFactor=.18)
                if comp["__type"]=="Sandbox.Bloom":comp.update(Strength=.10,Threshold=1.8)
                if comp["__type"]=="Sandbox.Vignette":comp.update(Intensity=.14)
        if name=="Fog":root["Components"][0].update(StartDistance=7500,EndDistance=68000,Color="0.42,0.49,0.57,0.85",FalloffExponent=1.2)
        if name=="Buy Zones":
            red=root["Children"][0]
            centre,scale=RV.plan_box(-2390,-1810,-1770,-880,-10,240)
            red["Position"]=K.vec(centre)
            for comp in red["Components"]:
                if comp["__type"]=="Sandbox.BoxCollider":comp["Scale"]=K.vec(scale)
    # Adjust navigation to the lower water surface and usable upper deck only.
    data["SceneProperties"]["NavMesh"]["Bounds"]={"Mins":K.vec(K.to_world((2400,-1800,-40))),"Maxs":K.vec(K.to_world((-2400,1950,510)))}
    lighting=SOURCE/"lighting/indirect-light.json"
    if lighting.exists(): data["GameObjects"].append(json.loads(lighting.read_text()))
    write(OUT/"scene-import.json",json.dumps(data,indent=2))
    checks=[]
    for kind,pts in (("Red",RED),("Blue",BLUE),("DM",DM)):
        checks += [{"name":f"{kind} {i+1}","position":K.to_world(p).tolist()} for i,p in enumerate(pts)]
    checks += [{"name":f"Domination {label}","position":K.to_world(p).tolist()} for label,p in DOM]
    checks += [{"name":f"Hot zone {label}","position":K.to_world(p).tolist()} for label,p in HOT]
    for site,roles in RV.RETAKES.items():
        for role,pts in roles.items():checks += [{"name":f"{site} {role} {i}","position":K.to_world(p).tolist()} for i,p in enumerate(pts)]
    for label,p,x in RV.CASH_POINTS:
        for suffix,pos in (("Cash",p),("Extract",x)):checks.append({"name":f"{label} {suffix}","position":K.to_world(pos).tolist()})
    for label,p in (("West lower bridge",(-675,-790,0)),("East lower bridge",(920,-790,0)),("West middle bridge",(-675,240,0)),("East middle bridge",(920,240,0)),("West rear bridge",(-675,1220,0)),("East rear bridge",(920,1220,0)),("Control west landing",(-275,720,236)),("Control east landing",(560,720,236))):
        checks.append({"name":label,"position":K.to_world(p).tolist()})
    write(OUT/"check-points.json",json.dumps(checks,indent=2))


def build():
    P.reset();OUT.mkdir(parents=True,exist_ok=True)
    materials()
    models={"ground":deck_ground(),"west":west_works(),"east":east_works(),"control":control_house(),"cargo":cargo_yard()}
    models["dam"],models["falls"]=spillway_dam()
    models["mountains"],models["forest"],models["backdrop"]=backdrop()
    models["river"]=water()
    metadata=[];counts={}
    for name,m in models.items():
        asset="spillway_"+name
        counts[name]=K.write_model(MODELS,"models/maps/spillway",asset,configure(m))
        collide=name in ("ground","west","east","control","cargo")
        shadows=name not in ("mountains","forest","river","falls")
        metadata.append((asset,name.replace("_"," ").title(),collide,shadows))
    write(OUT/"build-state.json",json.dumps({"models":metadata,"lights":P.LIGHTS,"clips":P.CLIPS},indent=2))
    scene(metadata);minimap()
    write(OUT/"build-summary.json",json.dumps({"triangles":counts,"total_triangles":sum(counts.values()),"lights":len(P.LIGHTS),"clips":len(P.CLIPS)},indent=2))
    print(json.dumps({"triangles":counts,"total":sum(counts.values()),"lights":len(P.LIGHTS),"clips":len(P.CLIPS)},indent=2))


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--materials-only",action="store_true")
    parser.add_argument("--scene-only",action="store_true")
    args=parser.parse_args()
    if args.materials_only:materials()
    elif args.scene_only:
        state=json.loads((OUT/"build-state.json").read_text())
        P.LIGHTS[:]=state["lights"];P.CLIPS[:]=state["clips"]
        scene(state["models"])
    else:build()
