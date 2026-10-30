"""Collider material source. Stage under output/collider/stage; install through the editor.
The signage follows the supplied laboratory reference. Shared Ares texture generators
provide the underlying steel/concrete finishes without modifying Ares assets.
"""
from pathlib import Path
import argparse
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import ares_materials as AM

RESOURCE_DIR = "materials/collider"
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output/collider/stage/materials/collider"
CELL = (1024, 512)
MARKINGS = ("c1","a1","c2","labs")
LABELS = {
    "sector": ("SECTOR B", "RESEARCH / LABS", "MAINTENANCE  >"),
    "control": ("CONTROL", "", ""),
    "science": ("SCIENCE", "DRIVES", "A BRIGHTER", "TOMORROW"),
    "accelerator": ("PARTICLE ACCELERATOR", "", ""),
    "observation": ("OBSERVATION  >", "", ""),
    "a1": ("A1", "OPERATIONS  >", ""),
    "b1": ("B1", "LABS  >", ""),
    "c2": ("C2", "OBSERVATION", "ACCESS  >"),
    "ring": ("RING", "SECTOR  >", ""),
    "cleaner": ("DEEPER", "CLEANER", "FARTHER"),
    "research": ("GLOBAL RESEARCH", "INITIATIVE", ""),
    "maintenance": ("SERVICE 03", "MAINTENANCE ACCESS", ""),
    "warning": ("BEAM ACTIVE", "RESTRICTED ACCESS", ""),
    "case": ("RESEARCH EQUIPMENT", "FRAGILE / INSTRUMENTS", "GRI  0427"),
    "red": ("RESEARCH", "WEST LABS", ""),
    "blue": ("OPERATIONS", "EAST LABS", ""),
}
SIGN_ASPECT = {"sector":280/300,"control":3.4,"science":72/245,"accelerator":900/70,
              "observation":610/70,"a1":140/180,"b1":170/180,"c2":170/200,
              "ring":330/240,"cleaner":66/190,"research":1.0,"maintenance":2.0,
              "warning":320/140,"case":2.5,"red":1.5,"blue":1.5}
TILES = {"co_floor": 192., "co_wall": 192., "co_concrete": 256., "co_steel": 64., "co_case":64., "co_grating":24.}

def uv(name, s, t):
    i = list(LABELS).index(name)
    return ((i % 4 + s) / 4, 1 - (i // 4 + 1 - t) / 4)

def vmat(name, color, **kwargs):
    return AM.vmat(name, color, **kwargs).replace("// Tools/ares_materials.py", "// Tools/collider_materials.py")

def floor_markings(out):
    """Worn navigation stencils, separate from the rectangular wall sign atlas."""
    size=1024;alpha=Image.new("L",(size*2,size*2));rng=np.random.default_rng(231)
    for i,(number,title) in enumerate((("C1","CONTROL"),("A1","OPERATIONS"),("C2","OBSERVATION"),("B1","LABS"))):
        tile=Image.new("L",(size,size));draw=ImageDraw.Draw(tile)
        draw.text((60,95),number,font=ImageFont.truetype(str(AM.FONT_BOLD),360),fill=240)
        font=ImageFont.truetype(str(AM.FONT_BOLD),108 if len(title)<10 else 94)
        draw.text((65,500),title,font=font,fill=230)
        draw.line((80,760,650,760),fill=230,width=45)
        draw.polygon(((650,665),(805,760),(650,855)),fill=230)
        # Narrow stencil bridges and localized wear expose the floor underneath.
        for x in (155,365):draw.rectangle((x,80,x+12,445),fill=0)
        pixels=np.asarray(tile).copy()
        wear=AM.noise(rng,(size,size),(size/140,size/100),1.8,8,.15)
        pixels[wear>1.7]=0
        pixels=np.clip(pixels.astype(float)*(1-.12*np.maximum(wear,0)),0,255).astype(np.uint8)
        alpha.paste(Image.fromarray(pixels),((i%2)*size,(i//2)*size))
    alpha.save(out/"co_markings_alpha.png")
    text=vmat("co_markings","[0.52 0.55 0.55 1]",rough_value=.58,metalness=0,alpha="co_markings_alpha.png")
    text=text.replace("materials/ares/co_markings_alpha.png",f"{RESOURCE_DIR}/co_markings_alpha.png")
    (out/"co_markings.vmat").write_text(text)

def equipment_surfaces(out):
    """Fine powder-coat wear and galvanized tread mesh at physical texture scales."""
    n=1024;ppi=n/TILES["co_case"];rng=np.random.default_rng(217)
    grain=AM.noise(rng,(n,n),(ppi,ppi),1.1,.4,.06)
    scuff=AM.noise(rng,(n,n),(ppi*.12,ppi),1.7,8,.3)
    broad=AM.noise(rng,(n,n),(ppi,ppi),2.3,32,5)
    c=np.array((57.,63.,68.))[None,None,:]*(1+.025*grain+.012*broad)[...,None]
    worn=AM.smoothstep(1.8,3.2,scuff)
    c=c*(1-worn[...,None]*.35)+np.array((111.,117.,121.))*worn[...,None]*.35
    rough=np.clip(.48+.025*grain-.13*worn,.32,.60)
    normal=AM.normals(.0025*grain-.001*worn,(ppi,ppi))
    AM.BX.save_rgb(out/"co_case_color.png",np.clip(c,0,255))
    AM.BX.save_normal(out/"co_case_normal.png",normal)
    AM.BX.save_grey(out/"co_case_rough.png",rough)
    (out/"co_case.vmat").write_text(vmat("co_case",f"{RESOURCE_DIR}/co_case_color.png",
        normal=f"{RESOURCE_DIR}/co_case_normal.png",rough=f"{RESOURCE_DIR}/co_case_rough.png",metalness=.12))
    import riverdale_materials as RM
    c,r,h,ppi,alpha=RM.grating(seed=218,n=1024)
    AM.BX.save_rgb(out/"co_grating_color.png",AM.T.linear_to_srgb(c)*1.25)
    AM.BX.save_normal(out/"co_grating_normal.png",AM.normals(h*.35,(ppi,ppi)))
    AM.BX.save_grey(out/"co_grating_rough.png",r*.8)
    AM.BX.save_grey(out/"co_grating_trans.png",alpha)
    text=vmat("co_grating",f"{RESOURCE_DIR}/co_grating_color.png",normal=f"{RESOURCE_DIR}/co_grating_normal.png",
        rough=f"{RESOURCE_DIR}/co_grating_rough.png",metalness=.6,alpha="co_grating_trans.png")
    text=text.replace("materials/ares/co_grating_trans.png",f"{RESOURCE_DIR}/co_grating_trans.png")
    (out/"co_grating.vmat").write_text(text)

def telemetry_atlas(out):
    """Four readable instrument displays, laid out as a 2x2 monitor atlas."""
    atlas=Image.new("RGB",(2048,1024),(7,16,23))
    for index,title in enumerate(("BEAM DIAGNOSTICS", "MAGNET ARRAY", "VACUUM SYSTEM", "COLLISION MONITOR")):
        panel=Image.new("RGB",CELL,(7,16,23)); d=ImageDraw.Draw(panel)
        bold=ImageFont.truetype(str(AM.FONT_BOLD),27)
        small=ImageFont.truetype(str(AM.FONT_BOLD),18)
        d.rectangle((12,12,1011,499),outline=(56,100,122),width=2)
        d.rectangle((14,14,1009,61),fill=(20,48,65))
        d.text((30,20),title,font=bold,fill=(172,223,239))
        d.text((795,25),"GRI / LIVE",font=small,fill=(89,189,207))
        # Main plot: a different stable, authored trace for each instrument.
        plot=(30,90,672,320)
        for x in range(plot[0],plot[2],40): d.line((x,plot[1],x,plot[3]),fill=(20,43,55))
        for y in range(plot[1],plot[3],32): d.line((plot[0],y,plot[2],y),fill=(20,43,55))
        for trace in range(3):
            xs=np.arange(31,671,2)
            wave=np.sin(xs/(31+index*11)+trace*.8)*np.exp(-((xs-330)/270)**2)
            ys=204+wave*(72-trace*17)+np.sin(xs/7+index)*5+trace*9
            d.line(list(zip(xs.tolist(),ys.tolist())),fill=((68,175,217),(151,218,233),(55,103,132))[trace],width=2)
        for row,(name,value) in enumerate((("ENERGY","06.50 TeV"),("CURRENT","0.584 A"),("VACUUM","2.1 E-10"),("STATUS","STABLE"))):
            y=91+row*57
            d.text((714,y),name,font=small,fill=(94,150,174))
            d.text((714,y+22),value,font=bold,fill=(184,229,241))
        # Ring schematic and channel bars make the layout legible at a distance.
        for radius in (45,62):
            d.ellipse((117-radius,410-radius,117+radius,410+radius),outline=(97,183,216),width=3)
        d.line((37,410,197,410),fill=(164,222,242),width=2)
        for k in range(16):
            x=230+k*43; height=25+int(48*(.5+.5*np.sin(k*.8+index)))
            d.rectangle((x,462-height,x+24,462),fill=(42,111+3*k,151+3*k))
        d.text((230,343),"CHANNEL RESPONSE / NORMALIZED",font=small,fill=(112,175,199))
        atlas.paste(panel,((index%2)*1024,(index//2)*512))
    atlas.save(out/"co_screens_color.png")
    text=vmat("co_screens",f"{RESOURCE_DIR}/co_screens_color.png",rough_value=.32,metalness=.1,
              illum="[1 1 1 1]",brightness=1.1)
    (out/"co_screens.vmat").write_text(text,encoding="utf-8")

def build(out=OUT):
    out.mkdir(parents=True, exist_ok=True)
    # Shared generators return sRGB colour in 0..255, roughness and tangent-space normals.
    for name, fn, metal in (
        ("co_floor", AM.floor_plates, .5), ("co_wall", AM.wall_panels, .25),
        ("co_concrete", AM.concrete, 0.), ("co_steel", AM.painted_dark_steel, .2)):
        c, r, n = fn(1024)
        if name == "co_floor":
            c *= np.array((1.0, 1.03, 1.05)); r = np.clip(r * .88, .30, .72)
        if name == "co_concrete":
            c *= np.array((1.13, 1.16, 1.18))
        if name == "co_steel":
            # Painted equipment reflects as a dielectric coating, not dark bare metal.
            c *= np.array((1.85, 1.90, 1.95)); r = np.clip(r, .36, .65)
        AM.BX.save_rgb(out / f"{name}_color.jpg", np.clip(c, 0, 255))
        AM.BX.save_normal(out / f"{name}_normal.png", n)
        AM.BX.save_grey(out / f"{name}_rough.png", r)
        (out / f"{name}.vmat").write_text(vmat(name, f"{RESOURCE_DIR}/{name}_color.jpg",
            normal=f"{RESOURCE_DIR}/{name}_normal.png", rough=f"{RESOURCE_DIR}/{name}_rough.png", metalness=metal), encoding="utf-8")
    atlas = Image.new("RGB", (4096, 2048), (49, 53, 56))
    for i, (label, lines) in enumerate(LABELS.items()):
        x, y = (i % 4) * 1024, (i // 4) * 512
        # Draw at the final sign's proportions before packing; narrow column signs
        # and long headers must not stretch their letters when sampled from the atlas.
        ratio=SIGN_ASPECT[label]
        w,h=min(4096,round(768*ratio)),768
        h=round(w/ratio)
        light_header=label in ("accelerator","observation")
        panel=Image.new("RGB",(w,h),(140,145,146) if light_header else (49,53,56))
        draw=ImageDraw.Draw(panel)
        lines=[line for line in lines if line]
        margin=max(12,round(w*.08))
        row_h=h*.72/max(1,len(lines))
        for row, text in enumerate(lines):
            size = round(row_h*(.80 if row==0 else .58))
            while True:
                font = ImageFont.truetype(str(AM.FONT_BOLD), size)
                if draw.textbbox((0,0), text, font=font)[2] < w-2*margin: break
                size -= 2
            draw.text((margin,h*.12+row*row_h),text,fill=(37,44,49) if light_header else (205,212,215),font=font)
        if len(lines)>1:
            draw.line((margin,h*.91,margin+w*.15,h*.91),fill=(164,55,41),width=max(2,round(h*.009)))
        atlas.paste(panel.resize(CELL,Image.Resampling.LANCZOS),(x,y))
    atlas.save(out / "co_signs_color.png")
    (out / "co_signs.vmat").write_text(vmat("co_signs", f"{RESOURCE_DIR}/co_signs_color.png", rough_value=.65), encoding="utf-8")
    telemetry_atlas(out)
    flats = {
        "co_beam": ((.35,.65,1.), .16, .1, 6.0), "co_white": ((.85,.89,.96), .28, .4, 2.2),
        "co_red": ((.80,.07,.035), .3, .35, 2.), "co_amber": ((.65,.39,.08), .4, .5, 0),
        "co_rubber": ((.025,.03,.032), .8, 0., 0), "co_trim": ((.26,.29,.32), .36, .35, 0),
        "co_silver": ((.56,.60,.65), .36, .8, 0),
        "co_copper": ((.46,.23,.105), .32, .75, 0),
        "co_enamel": ((.44,.49,.51), .39, .12, 0),
    }
    for name, (color, rough, metal, glow) in flats.items():
        c = "[" + " ".join(str(v) for v in color) + " 1]"
        text = vmat(name,c,rough_value=rough,metalness=metal,
            illum="materials/default/default_white.tga" if glow else None,brightness=glow)
        # Existing self-illuminating materials use a constant mask; it has no texture dependency.
        text = text.replace('TextureSelfIllumMask "materials/default/default_white.tga"', 'TextureSelfIllumMask "[1 1 1 1]"')
        (out / f"{name}.vmat").write_text(text, encoding="utf-8")
    (out / "co_glass.vmat").write_text(AM.glass_vmat((225,238,245), .09, .006), encoding="utf-8")
    equipment_surfaces(out)
    floor_markings(out)
    import collider_finish
    collider_finish.materials(out / "finish-v1")
    import collider_craft
    collider_craft.materials(out / "craft-v1")
    import collider_ceiling
    collider_ceiling.materials(out / "ceiling-v1")
    import collider_gallery_trench
    collider_gallery_trench.materials(out)
    print(f"Staged {len(list(out.glob('*.vmat')))} Collider materials in {out}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=OUT)
    build(parser.parse_args().out)

