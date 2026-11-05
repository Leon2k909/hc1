"""Compact weathered ice merchandiser for Riverside's Lucky Stop, as a review candidate.

python build.py <project-root>
Engine +X faces the door, +Y is its left. Origin is the ground under its centre.
"""
from pathlib import Path
import ctypes
import json
import math
import sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage as ndi

ROOT = Path(sys.argv[1]).resolve()
sys.path.insert(0, str(ROOT / "Tools"))
import map_kit as K
import riverdale_parts as G
K.obj_vector = lambda p: f"{p[1]:.5f} {p[2]:.5f} {p[0]:.5f}"
try:
    ctypes.windll.kernel32.SetPriorityClass(ctypes.windll.kernel32.GetCurrentProcess(), 0x4000)
except AttributeError:
    pass

MODEL = "models/props/riverside/ice_freezer_v2"
MAT = "materials/riverside/ice_freezer_v2"
OUT, TEX = ROOT / "Assets" / MODEL, ROOT / "Assets" / MAT
REPORT = ROOT / "output/asset-improvement-20261030/riverside-ice-freezer"
for p in (OUT, TEX, REPORT): p.mkdir(parents=True, exist_ok=True)
SIZE = 2048
PPI = 28


def field(shape, sigma, seed):
    a = ndi.gaussian_filter(np.random.default_rng(seed).normal(size=shape), sigma, mode="wrap")
    return a / (3 * a.std() + 1e-8)


def smooth(a, b, x):
    t = np.clip((x - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)


def paint():
    yy, xx = np.mgrid[0:SIZE, 0:SIZE].astype(np.float32)
    cloud = field((SIZE, SIZE), (18, 45), 11).astype(np.float32)
    speck = field((SIZE, SIZE), .6, 12).astype(np.float32)
    streak = field((SIZE, SIZE), (70, 2.5), 13).astype(np.float32)
    base = np.array((.72, .73, .70), np.float32)
    colour = np.broadcast_to(base, (SIZE, SIZE, 3)).copy()
    colour *= (1 + .025 * cloud[:, :, None] + .008 * speck[:, :, None])
    height = .001 * speck
    rough = np.clip(.60 + .08 * cloud, .4, .8)
    metal = np.zeros((SIZE, SIZE), np.float32)
    glow = np.zeros((SIZE, SIZE), np.float32)
    ao = np.ones((SIZE, SIZE), np.float32)
    # Surface dirt is anchored in inches so rain falls down the cabinet and mud stays low.
    for x0, width in ((28, 1064), (1120, 840)):
        y0, h = 28, 1680
        sl = (slice(y0, y0 + h), slice(x0, x0 + width))
        y, x = np.mgrid[0:h, 0:width].astype(np.float32)
        z = 60 - y / PPI
        film = np.clip(.09 + .06 * cloud[sl] + .10 * streak[sl], 0, .35)
        low = smooth(12, 1, z)
        dirt = np.clip(film + low * (.25 + .2 * cloud[sl]), 0, .7)
        colour[sl] = colour[sl] * (1 - dirt[:, :, None]) + np.array((.26, .25, .20)) * dirt[:, :, None]
        green = low * smooth(.3, .8, .5 + cloud[sl]) * .18
        colour[sl] = colour[sl] * (1 - green[:, :, None]) + np.array((.20, .25, .16)) * green[:, :, None]
        # Worn perimeter and service-door edges expose steel and old rust, with small drips.
        edge = np.minimum(x, width - 1 - x) / PPI
        edge_wear = smooth(.6, .03, edge) * smooth(.35, .72, .5 + speck[sl] * .4 + cloud[sl] * .3)
        foot_wear = low * smooth(.62, .9, .5 + cloud[sl] * .25 + speck[sl] * .2)
        chip = np.clip(edge_wear * .65 + foot_wear * .35, 0, .9)
        rust_colour = np.array((.24, .12, .055))
        colour[sl] = colour[sl] * (1 - chip[:, :, None]) + rust_colour * chip[:, :, None]
        rough[sl] = np.clip(.62 + .14 * dirt + .18 * chip, .4, .96)
        metal[sl] = chip * .18
        height[sl] -= chip * .006
    # Original, generic light-box lettering. The self-illumination is restricted to its face.
    overlay = Image.new("RGBA", (SIZE, SIZE))
    d = ImageDraw.Draw(overlay)
    front_centre = 28 + 19 * PPI
    header_y = 28 + 5.0 * PPI
    big = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", 170)
    d.rectangle((62, 60, 1058, 270), fill=(218, 225, 219, 255), outline=(110, 130, 135, 255), width=5)
    d.text((front_centre, header_y), "ICE", font=big, fill=(37, 83, 111, 255), anchor="mm", stroke_width=1)
    small = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", 23)
    d.text((front_centre, 28 + (60 - 23) * PPI), "KEEP DOOR CLOSED", font=small, fill=(105, 115, 111, 205), anchor="mm")
    d.text((front_centre, 28 + (60 - 20.8) * PPI), "BAGGED ICE", font=ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 20), fill=(105, 115, 111, 170), anchor="mm")
    # A faded ICE stencil on the side panel, with no real manufacturer's branding.
    d.text((1540, 480), "ICE", font=ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", 160), fill=(121, 50, 37, 150), anchor="mm")
    rgba = np.asarray(overlay, np.float32) / 255
    ink = rgba[:, :, 3] * np.clip(.90 + .12 * speck + .10 * cloud, .25, 1)
    colour = colour * (1 - ink[:, :, None]) + rgba[:, :, :3] * ink[:, :, None]
    glow[62:268, 64:1056] = .60
    glow *= np.clip(colour.mean(-1) * 1.15, 0, 1)
    # Metal, rubber and grille patches. UVs are geometric projections, not constant points.
    for (x0, y0, w, h), c, r, m in (
        ((0,1740,320,256), (.36,.38,.38), .40, .85),
        ((820,1740,280,256), (.045,.047,.043), .86, 0),
        ((1120,1740,280,256), (.07,.08,.075), .77, .3)):
        sl = (slice(y0,y0+h),slice(x0,x0+w))
        brushed = field((h,w),(8,.5),31 + x0)
        colour[sl] = np.array(c) * (1 + .09 * brushed[:, :, None])
        rough[sl], metal[sl], height[sl], glow[sl] = r, m, .0006 * brushed, 0
    # A small top-skin patch, kept separate from the signage and hardware.
    colour[1740:2040,400:800] = np.array((.60,.62,.59)) * (1 + .045 * cloud[1740:2040,400:800,None])
    rough[1740:2040,400:800] = .72
    dy, dx = np.gradient(height)
    normal = np.stack((-dx * PPI, dy * PPI, np.ones_like(height)), -1)
    normal /= np.linalg.norm(normal,axis=-1,keepdims=True)
    for name, data in (("color",colour), ("normal",normal*.5+.5), ("rough",rough), ("metal",metal), ("ao",ao), ("glow",glow)):
        Image.fromarray(np.uint8(np.clip(data,0,1)*255+.5)).save(TEX/("ice_"+name+".png"))


def plan(p): return np.array((-p[1],p[0],p[2]),float)
X,Y,Z = plan((1,0,0)),plan((0,1,0)),plan((0,0,1))


def uv(p, n, paint):
    if paint in ("ic_body","ic_header"):
        if abs(n[2]) > .8:
            return 400 + (19 - p[1]) * 10, 1740 + (15 - p[0]) * 10
        if abs(n[0]) >= abs(n[1]):
            return 28 + (19 + p[1]) * PPI, 28 + (60 - p[2]) * PPI
        return 1120 + (15 + (p[0] if n[1] > 0 else -p[0])) * PPI, 28 + (60 - p[2]) * PPI
    ox,oy = {"ic_steel":(8,1750),"ic_rubber":(828,1750),"ic_vent":(1128,1750)}[paint]
    axis=int(np.argmax(abs(n)))
    a,b={0:(1,2),1:(0,2),2:(0,1)}[axis]
    return ox+(p[a]+32)*4,oy+(p[b]+32)*2


def build(lod):
    m=K.Model()
    def box(c,size,paint="ic_body",bevel=.1,angles=0):
        axes=(X,Y,Z)
        if angles:
            a=math.radians(angles)
            axes=(X*math.cos(a)+Z*math.sin(a),Y,-X*math.sin(a)+Z*math.cos(a))
        if lod==2: m.oriented_box(plan(c),axes,size,paint)
        else: G.bevel_box(m,plan(c),axes,size,paint,bevel=bevel)
    def cylinder(c,axis,length,radius,paint="ic_steel",sides=None):
        G.lathe_axis(m,plan(c),plan(axis),[(0,0),(radius,0),(radius,length),(0,length)],paint,sides=sides or (16,10,6)[lod])
    def tube(points,radius,paint="ic_steel"):
        G.tube(m,[plan(p) for p in points],radius,paint,sides=(12,8,4)[lod])
    # Painted insulated body, standing on four rubber-covered adjustable feet.
    box((0,0,31.5),(30,38,57),bevel=.35)
    for x in (-10,10):
        for y in (-14,14):
            box((x,y,1.5),(3,3,3),"ic_rubber",.25)
    # A separate door, gasket and raised light-box make the front's construction visible.
    box((15.16,0,29.2),(.34,35.8,42.8),"ic_rubber",.10)
    box((15.75,0,29.2),(1.0,34.0,41.0),bevel=.16)
    box((15.5,0,55.0),(1.3,35.7,8.4),"ic_header",.22)
    # Recessed compressor bay with individual angled louvres and a service-panel rim.
    box((15.45,0,5.7),(.6,35.5,6.8),bevel=.10)
    box((15.82,0,5.7),(.12,33.1,5.1),"ic_vent",.03)
    for z in np.linspace(3.7,7.6,(10,7,4)[lod]):
        box((16.0,0,float(z)),(.58,31.8,.15),"ic_body",.025,angles=25)
    # Hinge leaves, barrels and their fixing screws.
    for z in (15.,29.,43.):
        box((16.28,15.4,z),(.16,2.6,3.5),"ic_steel",.035)
        cylinder((16.28,16.7,z-1.4),(0,0,1),2.8,.32)
        if lod==0:
            for y in (14.65,16.1):
                for zz in (z-1.1,z+1.1):
                    cylinder((16.38,y,zz),(1,0,0),.07,.11,sides=10)
    # Latch and a curved vertical pull stand proud of the insulated skin.
    box((16.36,-12.2,30.0),(.25,3.1,8.3),"ic_steel",.08)
    for z in (27.,33.):
        cylinder((16.50,-12.2,z),(1,0,0),.55,.35)
    tube([(16.8,-12.2,27),(17.4,-12.2,27),(17.8,-12.2,27.6),(17.8,-12.2,32.4),(17.4,-12.2,33),(16.8,-12.2,33)],.31)
    if lod<2:
        box((16.55,-12.2,35.3),(.15,1.2,1.4),"ic_steel",.04)
        box((16.65,-12.2,35.3),(.04,.24,.54),"ic_rubber",.005)
    if lod==0:
        for y in (-15.8,15.8):
            for z in (3.2,8.0):
                cylinder((16.02,y,z),(1,0,0),.06,.12,sides=10)
        # Folded side/rear seams and a rear service panel, without expensive hidden internals.
        for y in (-19.03,19.03):
            box((-11.5,y,31.5),(.12,.08,54.0),"ic_rubber",.02)
        box((-15.1,0,17),(.15,27,24),bevel=.08)
    for paint, polygons in m.polygons.items():
        m.material_overrides[paint]=MAT+"/ice_freezer.vmat"
        m.tile_overrides[paint]=16
        for i,(points,normal) in enumerate(polygons):
            engine_points=[K.to_world(p) for p in points]
            n=K.to_world(normal)
            m.polygon_uvs[(paint,i)]=[(u/SIZE,1-v/SIZE) for u,v in (uv(p,n,paint) for p in engine_points)]
    return m


def modeldoc(paints):
    remaps=','.join('{ from = "%s.vmat" to = "%s/ice_freezer.vmat" }'%(p,MAT) for p in paints)
    tail='import_translation = [0.0,0.0,0.0] import_rotation = [0.0,0.0,0.0] import_scale = 1.0 align_origin_x_type = "None" align_origin_y_type = "None" align_origin_z_type = "None" parent_bone = "" import_filter = { exclude_by_default = false exception_list = [] }'
    meshes=','.join('{ _class = "RenderMeshFile" name = "lod%d" filename = "%s/ice_freezer_lod%d.obj" %s }'%(k,MODEL,k,tail) for k in range(3))
    (OUT/'ice_freezer.vmdl').write_text('''<!-- kv3 encoding:text:version{e21c7f3c-8a33-41c5-9977-a76d3a32aa0d} format:modeldoc29:version{3cec427c-1b0e-4d48-a90a-0436f33a6041} -->
{ rootNode = { _class = "RootNode" children = [
 { _class = "MaterialGroupList" children = [ { _class = "DefaultMaterialGroup" remaps = [ %REMAPS% ] use_global_default = false global_default_material = "" } ] },
 { _class = "RenderMeshList" children = [ %MESHES% ] },
 { _class = "LODGroupList" children = [
 { _class = "LODGroup" switch_threshold = 0.0 meshes = ["lod0"] },
 { _class = "LODGroup" switch_threshold = 25.0 meshes = ["lod1"] },
 { _class = "LODGroup" switch_threshold = 70.0 meshes = ["lod2"] }
 ] }
] } }
'''.replace('%REMAPS%',remaps).replace('%MESHES%',meshes))


if __name__=='__main__':
    paint()
    counts=[]
    for k in range(3):
        model=build(k)
        counts.append(K.write_obj(OUT/f'ice_freezer_lod{k}.obj',model,'ice_freezer'))
    modeldoc(sorted(model.polygons))
    (TEX/'ice_freezer.vmat').write_text('''Layer0
{
 shader "shaders/complex.shader"
 F_SPECULAR 1
 F_METALNESS_TEXTURE 1
 F_SELF_ILLUM 1
 TextureColor "%MAT%/ice_color.png"
 TextureNormal "%MAT%/ice_normal.png"
 TextureRoughness "%MAT%/ice_rough.png"
 TextureMetalness "%MAT%/ice_metal.png"
 TextureAmbientOcclusion "%MAT%/ice_ao.png"
 TextureSelfIllumMask "%MAT%/ice_glow.png"
 g_flSelfIllumBrightness "0.65"
 g_flSelfIllumAlbedoFactor "1.0"
 g_vSelfIllumTint "[0.8 0.9 1.0 0]"
 g_flRoughnessScaleFactor "1"
 g_flModelTintAmount "1"
 g_vColorTint "[1 1 1 0]"
 g_bFogEnabled "1"
}
'''.replace('%MAT%',MAT))
    (REPORT/'mesh-report.json').write_text(json.dumps(dict(triangles=counts,atlas=[SIZE,SIZE],installed=False),indent=2))
    print('LOD triangles:',counts,flush=True)
