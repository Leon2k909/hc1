"""Orion launch complex: staged PBR surfaces and original facility graphics.

Generated sources stay in output/orion/stage until imported by the native editor.
Shared generators are read-only; no other map's materials are changed.
"""
from pathlib import Path
import math
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import ares_materials as AM
import boxyard_materials as BM

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output/orion/stage/materials/orion"
RESOURCE = "materials/orion"
FONT = ROOT / "Assets/fonts/Dinish-Bold.ttf"
TILES = {"or_concrete":192., "or_floor":384., "or_steel":64., "or_yellow":48.,
         "or_white":96., "or_red":64., "or_green":64., "or_silver":48., "or_tarp":96.}
SIGNS = {
    "launch": ("LAUNCH", "CONTROL", "01"),
    "fuel": ("B3", "FUEL", "PROCESSING", ">"),
    "ops": ("OPS", "SATELLITE", "CONTROL"),
    "orion": ("ORION", "A E R O S P A C E"),
    "rocket": ("O", "R", "I", "O", "N"),
    "warning": ("DANGER", "HIGH PRESSURE", "AUTHORIZED PERSONNEL ONLY"),
    "bay": ("04", "SERVICE BAY"),
    "a": ("A", "LAUNCH PAD"),
    "b": ("B", "CARGO YARD"),
    "case": ("ORION AEROSPACE", "FLIGHT HARDWARE", "OA / 00427"),
    "fuel2": ("LOX / LH2", "CRYOGENIC TRANSFER"),
    "access": ("SERVICE ACCESS", "KEEP CLEAR  >"),
    "red": ("LAUNCH CONTROL", "SECTOR 01"),
    "blue": ("OPERATIONS", "SECTOR 03"),
    "pad": ("PAD 07", "VEHICLE INTEGRATION"),
    "flag": (),
}
ASPECT = {"launch":.58,"fuel":.65,"ops":.8,"orion":1.3,"rocket":.2,
          "warning":2.4,"bay":1.,"a":1.,"b":1.,"case":3.,"fuel2":3.,
          "access":4.,"red":3.,"blue":3.,"pad":4.,"flag":1.6}

def uv(name,s,t):
    i=list(SIGNS).index(name)
    return ((i%4+s)/4,1-(i//4+1-t)/4)

def vmat(name,color,**kwargs):
    return AM.vmat(name,color,**kwargs).replace("Tools/ares_materials.py","Tools/orion_materials.py")

def write_surface(name,c,r,n,metal=0):
    BM.save_rgb(OUT/f"{name}_color.jpg",np.clip(c,0,255))
    BM.save_grey(OUT/f"{name}_rough.png",np.clip(r,.03,1))
    BM.save_normal(OUT/f"{name}_normal.png",n)
    # Preserve the selected image-generated concrete across future source rebuilds.
    color_path=f"{RESOURCE}/{name}_color.jpg"
    if name=="or_concrete":
        enhanced=OUT/"or_concrete_color_v2.png"
        imported=ROOT/"Assets/materials/orion/or_concrete_color_v2.png"
        if not enhanced.exists() and imported.exists():
            enhanced.write_bytes(imported.read_bytes())
        if enhanced.exists(): color_path=f"{RESOURCE}/{enhanced.name}"
    (OUT/f"{name}.vmat").write_text(vmat(name,color_path,
        normal=f"{RESOURCE}/{name}_normal.png",rough=f"{RESOURCE}/{name}_rough.png",metalness=metal))

def logo(draw,cx,cy,size,color):
    draw.ellipse((cx-size*.28,cy-size*.28,cx+size*.28,cy+size*.28),outline=color,width=max(2,int(size*.035)))
    # Tilted orbital ellipse, cut through the planetary disc.
    pts=[]
    for a in np.linspace(0,math.tau,100):
        x,y=math.cos(a)*size*.54,math.sin(a)*size*.16
        pts.append((cx+x*.83+y*.56,cy-x*.56+y*.83))
    draw.line(pts,fill=color,width=max(2,int(size*.035)))

def signs():
    atlas=Image.new("RGBA",(4096,4096))
    for i,(name,lines) in enumerate(SIGNS.items()):
        ratio=ASPECT[name]; h=1024; w=max(160,round(h*ratio))
        p=Image.new("RGBA",(w,h)); d=ImageDraw.Draw(p)
        ink=(23,27,28,245)
        if name in ("warning","red","blue","access","fuel2","pad","case"):
            d.rectangle((0,0,w,h),fill=(25,32,35,255)); ink=(215,220,210,255)
            d.rectangle((0,0,w,h*.035),fill=(195,146,42,255))
        if name=="flag":
            d.rectangle((0,0,w,h),fill=(15,21,27,255)); logo(d,w/2,h/2,min(w,h)*.82,(192,198,203,255))
        elif name=="orion":
            logo(d,w/2,h*.31,h*.55,ink)
            for j,(txt,factor) in enumerate(zip(lines,(.175,.052))):
                font=ImageFont.truetype(str(FONT),int(h*factor))
                d.text((w/2,h*(.64+j*.22)),txt,font=font,fill=ink,anchor="mm")
        else:
            top=.05 if name not in ("launch","fuel") else .03
            total=.90*h; row=total/max(1,len(lines))
            for j,txt in enumerate(lines):
                large=txt in ("01","B3","04","OPS","A","B")
                size=int(row*(1.20 if large else .76))
                font=ImageFont.truetype(str(FONT),size)
                while d.textbbox((0,0),txt,font=font)[2]>w*.88:
                    size-=2; font=ImageFont.truetype(str(FONT),max(8,size))
                d.text((w*.50,h*top+row*(j+.5)),txt,font=font,fill=ink,anchor="mm")
        # Fine erosion in the paint, not rectangular black borders on wall stencils.
        arr=np.array(p); rng=np.random.default_rng(710+i)
        erode=rng.random(arr.shape[:2])<.025
        arr[erode,3]=0
        p=Image.fromarray(arr).resize((1024,1024),Image.Resampling.LANCZOS)
        atlas.paste(p,((i%4)*1024,(i//4)*1024))
    atlas.save(OUT/"or_signs_color.png")
    atlas.getchannel("A").save(OUT/"or_signs_alpha.png")
    t=vmat("or_signs",f"{RESOURCE}/or_signs_color.png",rough_value=.7)
    t=t.replace('    F_SPECULAR "1"',f'    F_SPECULAR "1"\n    F_ALPHA_TEST "1"\n    TextureTranslucency "{RESOURCE}/or_signs_alpha.png"\n    g_flAlphaTestReference "0.25"')
    (OUT/"or_signs.vmat").write_text(t)

def floor():
    n=2048; rng=np.random.default_rng(817)
    x,y=np.meshgrid(np.arange(n)/n,np.arange(n)/n)
    noise=BM.noise(rng,(n,n),(n/384,n/384),2.0,120,1)
    fine=rng.normal(0,1,(n,n))
    joint=(np.minimum(x% .5,.5-x%.5)<.0015)|(np.minimum(y%.5,.5-y%.5)<.0015)
    wet=AM.smoothstep(.25,1.2,BM.noise(rng,(n,n),(n/384,n/384),2.8,250,15))
    color=np.array((110,113,111))[None,None,:]*(.91+.085*noise+.025*fine)[...,None]
    color*= (1-.26*wet-.42*joint)[...,None]
    # Wandering cracks and worn concrete patches, periodic across the tile.
    crack=np.abs(np.sin(x*math.tau*2+.18*np.sin(y*45)))<.006
    color[crack]*=.55
    height=.009*fine+.025*noise-.08*joint-.035*crack
    rough=.78*(1-wet)+.15*wet
    normal=BM.normals(height*(1-.96*wet),(n/384,n/384))
    write_surface("or_floor",color,rough,normal)
    write_surface("or_dryfloor",color/(1-.26*wet)[...,None],np.clip(.76+.05*noise,.55,.95),BM.normals(height,(n/384,n/384)))

def telemetry_atlas():
    """Original launch-control displays; four panels match the monitor mesh UVs."""
    atlas=Image.new("RGB",(2048,1024),(19,31,39))
    titles=("FLIGHT TRAJECTORY","PROPELLANT SYSTEMS","LAUNCH SEQUENCE","RANGE TELEMETRY")
    values=(("ALTITUDE","000.0 KM","VELOCITY","0000 M/S"),
            ("LOX TANK","98.4 %","LH2 TANK","97.8 %"),
            ("COUNTDOWN","T - 02:17","VEHICLE","READY"),
            ("SIGNAL","99.7 %","TRACKING","NOMINAL"))
    for index,title in enumerate(titles):
        panel=Image.new("RGB",(1024,512),(19,31,39));d=ImageDraw.Draw(panel)
        bold=ImageFont.truetype(str(FONT),28);small=ImageFont.truetype(str(FONT),18)
        d.rectangle((12,12,1011,499),outline=(85,135,150),width=2)
        d.rectangle((14,14,1009,61),fill=(35,71,85))
        d.text((30,20),title,font=bold,fill=(206,241,244))
        d.text((820,25),"ORION / 01",font=small,fill=(128,218,227))
        for x in range(30,673,40):d.line((x,90,x,320),fill=(36,65,77))
        for y in range(90,321,32):d.line((30,y,672,y),fill=(36,65,77))
        for trace,color in enumerate(((100,221,232),(192,237,202),(225,185,99))):
            xs=np.arange(31,671,2)
            ys=204+np.sin(xs/(46+index*17)+trace*.8)*(66-trace*18)+trace*12
            d.line(list(zip(xs.tolist(),ys.tolist())),fill=color,width=3)
        for row in range(2):
            label,value=values[index][row*2:row*2+2];y=94+row*96
            d.text((714,y),label,font=small,fill=(129,186,201))
            d.text((714,y+28),value,font=bold,fill=(209,241,240))
        d.text((714,292),"SYSTEMS ONLINE",font=small,fill=(147,228,173))
        # Launch vehicle silhouette and subsystem status strip.
        d.polygon(((100,365),(117,341),(134,365),(134,455),(100,455)),outline=(156,220,227),width=3)
        d.line((117,355,117,455),fill=(83,166,188),width=2)
        d.polygon(((100,430),(88,460),(100,452)),fill=(115,191,209))
        d.polygon(((134,430),(146,460),(134,452)),fill=(115,191,209))
        d.text((220,351),"FLIGHT SYSTEMS / STATUS",font=small,fill=(153,210,219))
        for k in range(16):
            x=220+k*45;height=30+int(43*(.5+.5*np.sin(k*.8+index)))
            d.rectangle((x,465-height,x+27,465),fill=(78,169+2*k,185+k))
        atlas.paste(panel,((index%2)*1024,(index//2)*512))
    atlas.save(OUT/"or_screens_color.png")
    (OUT/"or_screens.vmat").write_text(vmat("or_screens",f"{RESOURCE}/or_screens_color.png",
        rough_value=.32,metalness=.05,illum="[1 1 1 1]",brightness=3.2))

def build():
    OUT.mkdir(parents=True,exist_ok=True)
    c,r,n=AM.concrete(2048)
    write_surface("or_concrete",c*np.array((.94,.98,1.00)),r,n)
    floor()
    for name,color,seed in (("or_steel",(65,72,73),9),("or_yellow",(196,142,32),12),
          ("or_white",(217,216,205),14),("or_red",(125,43,31),15),("or_green",(48,62,57),17)):
        c,r,n=BM.region_maps(BM.painted_steel(color,seed,n=1024,tile=TILES.get(name,64.)))
        write_surface(name,c,r,n,.12)
    c,r,n=BM.region_maps(BM.galvanised(n=1024,tile=48.))
    write_surface("or_silver",c,r*.80,n,.85)
    c,r,n=BM.region_maps(BM.painted_steel((53,60,39),23,n=512,tile=96.))
    write_surface("or_tarp",c,np.clip(r+.28,0,1),n)
    flats={"or_rubber":((.026,.031,.032),.82,0,0),"or_light":((.92,.78,.52),.2,0,3.5),
           "or_redlight":((.82,.018,.009),.2,0,6),"or_blueglass":((.12,.24,.29),.16,.35,0),
           "or_dark":((.065,.073,.078),.45,.25,0),"or_earth":((.20,.23,.18),.95,0,0),
           "or_radome":((.64,.66,.65),.68,0,0),"or_pine":((.11,.145,.10),.92,0,0)}
    for name,(color,rough,metal,glow) in flats.items():
        c="["+" ".join(map(str,color))+" 1]"
        (OUT/f"{name}.vmat").write_text(vmat(name,c,rough_value=rough,metalness=metal,
            illum="[1 1 1 1]" if glow else None,brightness=glow))
    signs();telemetry_atlas()
    print(f"Staged {len(list(OUT.glob('*.vmat')))} Orion materials")

if __name__=="__main__": build()
