"""Formed steel lighter and exposed tidal-bank detail for Lowtide.

The standalone patch replaces only the barge's three material groups in the
existing Fleet OBJ. Its original collision, cargo and other map meshes survive.
"""
import json
import math
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage
import map_kit as K
from lowtide_brick import metadata

NAME = "lowtide_marine"
HULL_PAINTS = {"lt_hull_black", "lt_hull_red", "lt_hold_rust"}
SURFACE = K.ASSETS / "materials/lowtide/marine"
SOURCE = K.ROOT / "Sources/Lowtide/visual-target/marine-paint-source.png"


def bake_material():
    SURFACE.mkdir(parents=True,exist_ok=True)
    rgb = np.asarray(Image.open(SOURCE).convert("RGB").resize((2048,2048),Image.Resampling.LANCZOS),float)/255
    lum = rgb @ np.array([.2126,.7152,.0722])
    detail = lum-ndimage.gaussian_filter(lum,12,mode="wrap")
    height = ndimage.gaussian_filter(detail,.85,mode="wrap")*.6
    dx = (np.roll(height,-1,1)-np.roll(height,1,1))*.512
    dy = (np.roll(height,-1,0)-np.roll(height,1,0))*.512
    normal = np.stack([-dx,dy,np.ones_like(height)],-1)
    normal /= np.linalg.norm(normal,axis=-1,keepdims=True)
    rust = np.clip((rgb[...,0]-rgb[...,2]-.012)*9,0,1)
    maps = {"color":rgb,"normal":normal*.5+.5,"rough":np.clip(.48+rust*.34+detail*.3,.40,.9)}
    for suffix,data in maps.items():
        path = SURFACE/f"paint_{suffix}.png"
        Image.fromarray(np.rint(data*255).clip(0,255).astype(np.uint8)).save(path)
        metadata(path)
    write_materials()


def write_tidal_stone():
    path = SURFACE / "lt_tidal_granite.vmat"
    K.write_text(path, '''// Generated granite, damp at the tidal-bank waterline.
"Layer0"
{
    shader "shaders/complex.shader"
    F_SPECULAR "1"
    TextureColor "materials/lowtide/masonry/granite_color.png"
    TextureNormal "materials/lowtide/masonry/granite_normal.png"
    TextureRoughness "[0.39 0.39 0.39 0]"
    TextureMetalness "materials/default/default_black_mask.tga"
    TextureAmbientOcclusion "materials/default/default_ao.tga"
    g_vColorTint "[0.36 0.39 0.35 1]"
}
''')
    metadata(path)


def write_materials():
    SURFACE.mkdir(parents=True, exist_ok=True)
    write_tidal_stone()
    if not (SURFACE/"paint_color.png").exists():
        return
    for paint,tint in (("lt_hull_black","1 1 1"),("lt_hull_red",".85 .60 .43")):
        path = K.ASSETS/f"materials/lowtide/{paint}.vmat"
        K.write_text(path,f'''// Generated marine enamel; physical roughness and submillimetre pitting.
"Layer0"
{{
    shader "shaders/complex.shader"
    F_SPECULAR "1"
    TextureColor "materials/lowtide/marine/paint_color.png"
    TextureNormal "materials/lowtide/marine/paint_normal.png"
    TextureRoughness "materials/lowtide/marine/paint_rough.png"
    TextureMetalness "materials/default/default_black_mask.tga"
    TextureAmbientOcclusion "materials/default/default_ao.tga"
    g_vColorTint "[{tint} 1]"
}}
''')
        metadata(path)


def rounded_outline(e0, e1, n0, n1, radius):
    points = []
    for e, n, start in ((e1-radius, n1-radius, 0), (e0+radius, n1-radius, 90),
                         (e0+radius, n0+radius, 180), (e1-radius, n0+radius, 270)):
        for i in range(5):
            angle = math.radians(start + i*90/4)
            points.append(np.array((e+radius*math.cos(angle), n+radius*math.sin(angle))))
    return points


def shell(m, L):
    e0, e1, n0, n1 = L.BARGE
    rings = []
    for z in (-143, -132, -112, -84, -64):
        fraction = (z+143)/79
        taper, rake = (1-fraction)*5, (1-fraction)*40
        points = rounded_outline(e0+taper, e1-taper, n0+rake, n1-rake, 10)
        rings.append([np.array((e,n,z)) for e,n in points])
    for lower, upper in zip(rings, rings[1:]):
        paint = "lt_hull_red" if upper[0][2] <= -112 else "lt_hull_black"
        for i, a in enumerate(lower):
            j = (i+1)%len(lower)
            b = lower[j]
            edge = b-a
            outward = np.array((edge[1],-edge[0],0))
            L.card(m, paint, [a,b,upper[j],upper[i]], outward)
    # A real inboard coaming, turned-over top plate and stiffeners around the hold.
    top = rings[-1]
    inner_xy = rounded_outline(e0+6,e1-6,n0+6,n1-6,8)
    bottom_xy = rounded_outline(e0+8,e1-8,n0+42,n1-42,8)
    for i,a in enumerate(top):
        j = (i+1)%len(top)
        inner_a = np.array((*inner_xy[i],-64))
        inner_b = np.array((*inner_xy[j],-64))
        lower_a = np.array((*bottom_xy[i],-134))
        lower_b = np.array((*bottom_xy[j],-134))
        L.card(m,"lt_hull_black",[a,top[j],inner_b,inner_a],(0,0,1))
        edge = inner_b-inner_a
        L.card(m,"lt_hold_rust",[inner_a,inner_b,lower_b,lower_a],(-edge[1],edge[0],0))
        L.bar(m,a+(0,0,-1.2),top[j]+(0,0,-1.2),1.55,"lt_hull_black",sides=8)
    m.polygon("lt_hold_rust",[(*p,-134) for p in bottom_xy],normal=(0,0,1))
    for e,out in ((e0,-1),(e1,1)):
        # Narrow welded seams, longitudinal rubbing strake and internal frames.
        for n in np.arange(n0+64,n1-40,78):
            L.bar(m,(e+out*.15,n,-109),(e+out*.15,n,-66),.20,"lt_hold_rust",sides=5)
            m.beam((e-out*6.1,n,-131),(e-out*6.1,n,-69),(1.7,2.1),"lt_hold_rust")
            L.bar(m,(e+out*.3,n,-71),(e+out*1.1,n,-71),.55,"lt_hold_rust",sides=6)
        L.bar(m,(e+out*.7,n0+35,-94),(e+out*.7,n1-35,-94),1.7,"lt_hull_black",sides=10)
        for n in (n0+105,n1-108):
            # Salvaged tyres are genuinely hollow toruses, with a short rope loop.
            L.torus(m,(e+out*6,n,-91),(0,1,0),(0,0,1),9.2,3.6,"lt_rubber",segments=24,sides=8)
            L.bar(m,(e,n-2,-62),(e+out*6,n-2,-81),.48,"lt_rope_detail",sides=5)
            L.bar(m,(e,n+2,-62),(e+out*6,n+2,-81),.48,"lt_rope_detail",sides=5)
    # Low mooring cleats with caps and base plates, located on the end coamings.
    for n,sign in ((n0,-1),(n1,1)):
        for e in (e0+30,e1-30):
            m.box((e-6,n-sign*14-7,-64),(e+6,n-sign*14+7,-62.5),"lt_hull_black")
            L.bar(m,(e,n-sign*14,-63),(e,n-sign*14,-54),3.3,"lt_hull_black",sides=12)
            L.bar(m,(e-7,n-sign*14,-55),(e+7,n-sign*14,-55),2.0,"lt_hull_black",sides=10)


def banks(m,L):
    # Broken clay masonry, stone and tide-deposited pebbles disturb the sterile
    # bank silhouette. Clearance is kept around every stair/ladder landing.
    rng = np.random.default_rng(84203)
    landings = (-1450,-1280,-870,-560,-315,205,465,725,1020)
    for side in (-1,1):
        for i in range(250):
            n = rng.uniform(-1570,1130)
            if min(abs(n-x) for x in landings) < 45:
                continue
            e = side*rng.uniform(108,233)
            z = float(L.mud_z(e,n))
            radius = rng.uniform(1.0,4.8)
            height = rng.uniform(.45,2.0)
            # Irregular faceted river stones, partly buried below the bank.
            outline = []
            for k in range(6):
                angle = k*math.tau/6
                rr = radius*rng.uniform(.75,1.2)
                outline.append((e+math.cos(angle)*rr,n+math.sin(angle)*rr))
            centre = (e+rng.uniform(-.4,.4),n+rng.uniform(-.4,.4),z+height)
            paint = "lt_bank_stone" if i%5 else "lt_hold_rust"
            for k,a in enumerate(outline):
                b = outline[(k+1)%6]
                L.card(m,paint,[(*a,z-.35),(*b,z-.35),centre],(0,0,1))
    # Irregular clusters sit along the changing waterline, with a second sparse
    # band against the quay. Keep the middle of each bank and landings clear.
    for side in (-1, 1):
        for index in range(92):
            n0 = rng.uniform(-1490, 1120)
            if min(abs(n0-x) for x in landings) < 42:
                continue
            samples = np.linspace(50, 175, 100)
            shore = samples[np.argmin(np.abs(L.mud_z(side*samples, n0) - (L.WATER_Z+1)))]
            for k in range(int(rng.integers(3, 8))):
                n = n0 + rng.normal(0, 14)
                e = side * (rng.uniform(216, 231) if index % 4 == 0 else shore + rng.uniform(1, 24))
                z = float(L.mud_z(e, n))
                radius = rng.uniform(2.2, 8.5)
                height = rng.uniform(.65, 3.1)
                centre = np.array((e, n, z+.7))
                angles = np.arange(7)*math.tau/7 + rng.uniform(0, math.tau)
                radii = radius*rng.uniform(.70, 1.15, 7)
                lower = [np.array((e+math.cos(a)*r, n+math.sin(a)*r*.8, z-.7)) for a, r in zip(angles, radii)]
                rim = [np.array((p[0], p[1], z+height*.45)) for p in lower]
                top = [np.array((e+(p[0]-e)*.58, n+(p[1]-n)*.58, z+height*rng.uniform(.75, 1))) for p in lower]
                def face(points):
                    uv = [(.19+(p[0]-e)/160, .89+(p[1]-n+p[2]-z)/160) for p in points]
                    L.card(m, "lt_tidal_granite", points, np.mean(points,axis=0)-centre, uv=uv)
                for j in range(7):
                    b = (j+1)%7
                    face([lower[j], lower[b], rim[b], rim[j]])
                    face([rim[j], rim[b], top[b], top[j]])
                face(top)


def build(L):
    m = K.Model()
    shell(m,L)
    banks(m,L)
    L.configure(m)
    configure(m)
    assert not m.boxes and not m.hulls
    return m


def configure(m):
    if "lt_tidal_granite" in m.polygons:
        m.material_overrides["lt_tidal_granite"] = "materials/lowtide/marine/lt_tidal_granite.vmat"
    for paint in HULL_PAINTS:
        if paint in m.polygons:
            m.tile_overrides[paint] = 78.74


def strip_model(m):
    for paint in HULL_PAINTS:
        m.polygons.pop(paint, None)
    m.polygon_uvs = {k:v for k,v in m.polygon_uvs.items() if k[0] not in HULL_PAINTS}
    m.polygon_normals = {k:v for k,v in m.polygon_normals.items() if k[0] not in HULL_PAINTS}


def strip_original_hull(path):
    lines = path.read_text().splitlines()
    result = []
    current = None
    removed = 0
    for line in lines:
        if line.startswith("usemtl "):
            current = line.split(maxsplit=1)[1]
        if current in HULL_PAINTS and (line.startswith("f ") or line.startswith("usemtl ")):
            removed += line.startswith("f ")
            continue
        result.append(line)
    if removed:
        K.write_text(path,"\n".join(result)+"\n")
    return removed


def apply_scene(scene,L):
    world = next(o for o in scene["GameObjects"] if o.get("Name")=="Lowtide")
    children = world["Children"]
    index = next((i for i, o in enumerate(children) if o.get("Name") == "Tidal Details"), len(children))
    children[:] = [o for o in children if o.get("Name")!="Tidal Details"]
    children.insert(index, L.model_object("Tidal Details","world/lowtide_marine",NAME,False,True))


def main():
    import lowtide_map as L
    write_materials()
    count = K.write_model(L.OUT_DIR,L.RESOURCE_DIR,NAME,build(L))
    removed = strip_original_hull(L.OUT_DIR/"lowtide_fleet.obj")
    scene = json.loads(L.SCENE_FILE.read_text())
    apply_scene(scene,L)
    K.write_text(L.SCENE_FILE,json.dumps(scene,indent=2)+"\n",newline=None)
    print(f"Marine pass: {count} visual triangles; {removed} original hull triangles replaced; collision retained")


if __name__ == "__main__":
    main()
