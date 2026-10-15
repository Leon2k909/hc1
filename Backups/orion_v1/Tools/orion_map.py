"""Orion: a two-level multiplayer launch complex matching the supplied reference.

Plan coordinates (east,north,up) in inches, world=(north,-east,up).
Stages source geometry and an editor import description; never overwrites a live scene.
"""
from pathlib import Path
import argparse, json, math
import numpy as np
from PIL import Image, ImageDraw
import map_kit as K
import boxyard_map as B
import boxyard_materials as BM
import ares_map as A
import ares_materials as AM
import railhead_map as R
import collider_detail_geometry as D
import orion_materials as M

ROOT=Path(__file__).resolve().parents[1]
STAGE=ROOT/"output/orion/stage"
RESOURCE="models/maps/orion"
IDS=K.SceneIds("24009a7f-9871-4651-acaa-37871a2748ef")
UP=np.array((0.,0.,1.))
G=240.
PLAY=(-1800.,1800.,-1400.,1700.)
LIGHTS=[]
ART={"name":"art","eye":[-760,-1720,620],"target":[-200,650,420],"fov":100}
MODELS=(("orion_west","Launch control",True),("orion_east","Fuel processing and operations",True),
        ("orion_yard","Cargo yard and launch deck",True),("orion_detail","Equipment and circulation",True),
        ("orion_rocket","Orion launch vehicle and gantry",True),("orion_backdrop","Mountain launch range",False))

def box(m,e0,e1,n0,n1,z0,z1,p="or_concrete",solid=True):
    surface=("concrete" if p in ("or_concrete","or_floor") else "metal") if solid else None
    m.box((e0,n0,z0),(e1,n1,z1),p,surface)

def wall(m,axis,run,across,z,openings=(),paint="or_concrete"):
    return A.wall(m,axis,run,across,z,openings,outside=paint,inside=paint,reveal="or_steel",surface="concrete")

def pipe(m,a,b,r=6,p="or_silver",solid=False,sides=12):
    a,b=np.asarray(a,float),np.asarray(b,float)
    if np.linalg.norm(b-a)<.0001:return
    B.lathe(m,a,b-a,[(r,0),(r,float(np.linalg.norm(b-a)))],p,sides=sides,cap=p,surface="metal" if solid else None)

def ring(m,c,axis,r,width,p="or_silver",sides=24):
    B.lathe(m,c,axis,[(r,-width/2),(r,width/2)],p,sides=sides,cap=p)

def rail(m,a,b,z,solid=True):
    a,b=np.array((*a,z)),np.array((*b,z)); length=np.linalg.norm(b-a)
    for h,r in ((43,1.65),(23,1.1)):
        pipe(m,a+UP*h,b+UP*h,r,"or_yellow",sides=8)
    for t in np.linspace(0,1,max(2,round(length/76)+1)):
        at=a+(b-a)*t
        pipe(m,at,at+UP*43,1.5,"or_yellow",sides=8)
        m.box(at+(-4,-4,0),at+(4,4,2),"or_steel")
    m.beam(a+UP*3,b+UP*3,(1.4,6),"or_steel")
    if solid:m.beam(a+UP*42,b+UP*42,(3.5,8),{"default":None},"metal")

def sign(m,label,c,f,w,h):
    c=np.asarray(c,float); f=K.normalise((*f,0)); r=np.cross(UP,f)
    pts=[c-r*w/2-UP*h/2,c+r*w/2-UP*h/2,c+r*w/2+UP*h/2,c-r*w/2+UP*h/2]
    B.card(m,"or_signs",pts,f,uv=[M.uv(label,s,t) for s,t in ((0,0),(1,0),(1,1),(0,1))])

def lamp(m,c,axis="e",length=50,power=2.8,radius=290,shadow=False,color=None):
    c=np.asarray(c,float); ext=np.array((length/2,3,2) if axis=="e" else (3,length/2,2))
    m.box(c-ext-1,c+ext+1,"or_steel")
    m.box(c-ext+np.array((0,0,-1.2)),c+ext-np.array((0,0,2.2)),"or_light")
    color=color or (power,power*.77,power*.47,1)
    LIGHTS.append((f"Work light {len(LIGHTS)+1}",tuple(c-UP*5),K.vec(color),radius,shadow))

def stairs(m,axis,c0,c1,s0,s1,z0=0,z1=G):
    temp=K.Model(); A.stair(temp,axis,c0,c1,s0,s1,z0,z1)
    recolor(temp,{"ar_grating":"ar_grating","ar_steel":"or_steel","ar_hazard":"or_yellow","ar_gunmetal":"or_yellow","ar_brass":"or_yellow"})
    m.extend(temp)

def recolor(m,mapping):
    out=K.Model()
    for old,items in m.polygons.items():
        target=mapping.get(old,old)
        for i,(pts,normal) in enumerate(items):
            out.polygon(target,pts,normal,uv=m.polygon_uvs.get((old,i)),normals=m.polygon_normals.get((old,i)))
    m.polygons=out.polygons;m.polygon_uvs=out.polygon_uvs;m.polygon_normals=out.polygon_normals

def case(m,e,n,z=0,w=104,d=66,h=58,heading=0):
    tmp=K.Model();D.hardcase(tmp,e,n,z,w,d,h,heading,lambda *args:None)
    recolor(tmp,{"co_case":"or_green","co_trim":"or_steel","co_rubber":"or_rubber","co_silver":"or_silver","co_amber":"or_yellow"})
    m.extend(tmp)
    f=B.Frame(e,n,heading,z);sign(m,"case",f.p(0,-d/2-2,h*.5),-f.y[:2],w*.60,h*.30)

def tarped_pallet(m,e,n,w=150,d=100,h=75):
    box(m,e-w/2,e+w/2,n-d/2,n+d/2,0,9,"or_steel")
    box(m,e-w*.44,e+w*.44,n-d*.42,n+d*.42,9,h-4,"or_dark")
    # A draped triangulated cloth: raised cargo shoulders, sagging edges and creases.
    xs=np.linspace(-w/2,w/2,15);ys=np.linspace(-d/2,d/2,11)
    def p(x,y):
        edge=max(abs(x)/(w/2),abs(y)/(d/2))
        z=h-13*edge**4+2.5*math.sin(x*.24+y*.11)+2*math.sin(x*.08-y*.29)
        return np.array((e+x,n+y,z))
    for ix in range(len(xs)-1):
        for iy in range(len(ys)-1):
            pts=[p(xs[ix],ys[iy]),p(xs[ix+1],ys[iy]),p(xs[ix+1],ys[iy+1]),p(xs[ix],ys[iy+1])]
            m.polygon("or_tarp",pts[:3]);m.polygon("or_tarp",[pts[0],pts[2],pts[3]])
    for side in (-1,1):
        for ix in range(len(xs)-1):
            a,b=p(xs[ix],side*d/2),p(xs[ix+1],side*d/2)
            B.card(m,"or_tarp",[a,b,(b[0]+math.sin(ix)*3,b[1],12),(a[0]+math.sin(ix)*3,a[1],12)],(0,side,0))
        for iy in range(len(ys)-1):
            a,b=p(side*w/2,ys[iy]),p(side*w/2,ys[iy+1])
            B.card(m,"or_tarp",[a,b,(b[0],b[1],12),(a[0],a[1],12)],(side,0,0))
    for x in (-w*.28,w*.28):
        pipe(m,(e+x,n-d/2-2,8),(e+x,n-d/2-2,h-10),.6,"or_yellow",sides=5)
        m.beam((e+x,n-d/2,h),(e+x,n+d/2,h),(2.5,.6),"or_steel")

def monitor(m,c,f,w=42,h=26,index=0):
    c=np.asarray(c,float);f=K.normalise((*f,0));r=np.cross(UP,f)
    m.oriented_box(c-f*3,(-r,f,UP),(w+5,6,h+5),"or_dark")
    u=index%2*.5;v=(1-index//2)*.5
    B.card(m,"or_screens",[c-r*w/2-UP*h/2,c+r*w/2-UP*h/2,c+r*w/2+UP*h/2,c-r*w/2+UP*h/2],f,
        uv=[(u,v),(u+.5,v),(u+.5,v+.5),(u,v+.5)])

def console(m,e,n,z,side):
    f=B.Frame(e,n,90 if side<0 else -90,z)
    f.box(m,-60,60,-22,22,0,33,"or_steel","metal")
    f.box(m,-63,63,-24,25,33,36,"or_green")
    for x in (-38,10):monitor(m,f.p(x,10,53),-f.y[:2],42,28,int(abs(x))%4)
    for x in np.linspace(-48,48,13):f.box(m,x,x+2,-18,-13,36,37,"or_yellow" if x<0 else "or_rubber")
    for dx in (-32,32):
        f.box(m,dx-12,dx+12,-63,-40,23,28,"or_rubber")
        f.box(m,dx-12,dx+12,-66,-62,25,51,"or_rubber")
        pipe(m,f.p(dx,-52,2),f.p(dx,-52,24),2,"or_silver")
        pipe(m,f.p(dx-15,-52,3),f.p(dx+15,-52,3),1.5,"or_dark")

def building(m,side):
    # Both wings have open ground service rooms and an accessible upper control room.
    e0,e1=(-1800,-1100) if side<0 else (1100,1800)
    inner=-1100 if side<0 else 1100;outer=-1800 if side<0 else 1800
    box(m,e0,e1,-1400,1700,-30,0,"or_floor")
    wall(m,"n",(-1400,1700),(outer-12,outer+12),(0,720))
    wall(m,"e",(e0,e1),(-1418,-1398),(0,600))
    wall(m,"e",(e0,e1),(1680,1700),(0,600))
    # Slab split leaves a generous stairwell along the outside edge.
    if side<0:box(m,-1530,-1100,-1000,1700,G-22,G,"or_floor")
    else:box(m,1100,1530,-1000,1700,G-22,G,"or_floor")
    box(m,e0,e1,50,1700,G-22,G,"or_floor")
    box(m,e0,e1,-80,160,G-22,G,"or_floor")
    box(m,e0,e1,-1400,-1000,G-22,G,"or_floor")
    stairs(m,"n",min(side*1740,side*1550),max(side*1740,side*1550),-740,-60)
    # Broken interior face: tall open bays, solid sign piers and upper openings.
    wall(m,"n",(-1400,1700),(inner-12,inner+12),(0,G-22),
         [(-1050,180,0,185),(-360,260,0,190),(1050,280,0,195)])
    wall(m,"n",(-1400,1700),(inner-12,inner+12),(G,560),
         [(-700,360,G,450),(-80,420,G,455),(1060,700,G,465)])
    # Roofs, caps and reinforced concrete grid.
    box(m,e0-12,e1+12,-1400,550,560,586,"or_concrete")
    box(m,e0-12,e1+12,550,1700,510,536,"or_concrete")
    for n in (-1390,-950,-470,430,650,1470,1690):
        box(m,inner-19,inner+19,n-18,n+18,0,560,"or_concrete")
    for z in (G,480):
        box(m,inner-20,inner+20,-1400,1700,z-9,z+6,"or_steel",False)
    # Prominent launch-control sign and fuel processing stencils facing the court.
    f=(-side,0);face=inner-side*20
    sign(m,"ops" if side>0 else "red",(face,560,384),f,150,170 if side>0 else 50)
    # Upper openings framed in black mullions; open entry gaps remain traversable.
    for n in (-780,-120,1060):
        for nn in (n-150,n+150):
            box(m,inner-18,inner+18,nn-3,nn+3,G+20,455,"or_dark",False)
    # Control stations, wall screens and warm ceiling strips.
    for n in (-730,-320,700,1300):
        console(m,side*1365,n,G,side)
        lamp(m,(side*1390,n,475),"n",100,power=9.0,radius=560,shadow=n==-320)
        lamp(m,(side*1390,n,188),"n",65,power=6.0,radius=450)
    for n in (-800,-680,-560): monitor(m,(side*1778,n,G+105),(-side,0),90,54,(n//120)%4)
    # Ground electrical cabinets and overhead service pipes.
    for n in (-1240,260,1480):
        box(m,side*1720-40,side*1720+40,n-65,n+65,0,148,"or_green")
        sign(m,"warning",(side*1678,n,90),(-side,0),62,26)
    # Spawn exits turn around solid blast screens before entering the shared court.
    if side<0:box(m,-1240,-1218,-1340,-830,0,177,"or_concrete")
    else:box(m,1218,1240,930,1570,0,177,"or_concrete")
    for z in (78,122,176):
        pipe(m,(face,-1380,z),(face,1680,z),10 if z!=176 else 6,"or_silver")
        for n in np.arange(-1320,1680,240):ring(m,(face,n,z),(0,1,0),12,7,"or_steel",12)
    # Right-hand fuel risers are a key foreground silhouette in the reference.
    if side>0:
        for n in (-1320,-1250,-1180):
            pipe(m,(1058,n,30),(1058,n,450),22,"or_silver")
            pipe(m,(1058,n,450),(970,n,480),22,"or_silver")
            for z in (80,310,410):ring(m,(1058,n,z),UP,24,15,"or_yellow")
    # Roof vent banks, parapets, small aerials.
    for n in (-1000,-400,950):
        box(m,side*1510-85,side*1510+85,n-60,n+60,586,640,"or_steel",False)
        for j in range(8):box(m,side*1510-80,side*1510+80,n-55+j*14,n-49+j*14,640,643,"or_dark",False)
    rail(m,(e0,-1400),(e1,-1400),586,False)
    # Foreground control tower and fuel block give the reference's uneven skyline.
    if side<0:
        wall(m,"n",(-1400,-920),(-1118,-1098),(586,1010),[(-1190,230,670,905)])
        wall(m,"e",(e0,e1),(-1410,-1390),(586,1010),[(-1420,500,670,905)])
        box(m,e0-14,e1+24,-1410,-900,1000,1030,"or_steel",False)
        box(m,e0,e1,-1400,-900,586,610,"or_concrete")
        for n in (-1330,-1250,-1170,-1090):
            box(m,-1124,-1094,n-3,n+3,670,905,"or_steel",False)
        sign(m,"launch",(-1080,-1190,410),(1,0),180,310)
        for z in (600,640,975):box(m,-1125,-1090,-1400,-900,z,z+13,"or_steel",False)
        for n in (-1250,-1050):lamp(m,(-1270,n,950),"n",65,9.0,540)
    else:
        box(m,e0,e1,-1400,-950,560,670,"or_concrete")
        sign(m,"fuel",(1080,-1190,365),(-1,0),190,320)
    # Ribbed utility soffits, conduits and fuse banks lend the interiors human scale.
    for n in np.arange(-1300,1600,180):
        box(m,e0+12,e1-12,n-7,n+7,194,211,"or_steel",False)
        box(m,e0+12,e1-12,n-7,n+7,484,501,"or_steel",False)
    for z in (205,504):
        for e in (side*1180,side*1220):pipe(m,(e,-1390,z),(e,1660,z),3.5,"or_steel")
    for n in (-900,-500,600,1280):
        for j in range(3):
            ee=side*(1745-j*38)
            box(m,ee-16,ee+16,n-9,n+9,G+70,G+142,"or_green",False)
            for zz in (G+85,G+110,G+135):box(m,ee-10,ee+10,n-11,n-9,zz,zz+4,"or_dark",False)
    # Dry control-room floors and slab undersides, retaining wet exterior balconies.
    recolor(m,{"or_floor":"or_dryfloor"})

def yard(m):
    box(m,-1800,1800,-1400,1700,-40,0,"or_floor")
    # Foreground perimeter closes the playable area without blocking the architectural view.
    box(m,-1800,1800,-1420,-1400,0,110,"or_concrete")
    box(m,-1100,1100,1680,1710,0,G+100,"or_concrete")
    # Broad upper deck over a three-entrance maintenance undercroft.
    box(m,-1100,1100,600,1700,G-24,G,"or_floor")
    wall(m,"e",(-1100,1100),(580,610),(0,G-24),[(-730,250,0,185),(160,530,0,185),(870,180,0,185)])
    sign(m,"orion",(-230,579,116),(0,-1),210,176)
    for e in (-1070,-495,505,1090):
        for n in (650,1110,1620):box(m,e-16,e+16,n-16,n+16,0,G-24,"or_concrete")
    # Underpass service divider with doors at either side, so the lower loop stays connected.
    wall(m,"e",(-1100,1100),(1180,1202),(0,G-24),[(-750,210,0,190),(180,280,0,190),(840,180,0,190)])
    for e in (-740,160,860):
        for n in (760,1400):lamp(m,(e,n,211),"e",70,power=7.0,radius=460,shadow=e==160 and n==760)
    sign(m,"bay",(510,579,110),(0,-1),72,100)
    sign(m,"access",(150,578,204),(0,-1),380,34)
    # Long balconies and two outdoor stairs, joined to the rear deck.
    for s in (-1,1):
        e0,e1=sorted((s*1100,s*850))
        box(m,e0,e1,-1000,1700,G-20,G,"or_floor")
        rail(m,(s*850,-1000),(s*850,-510),G)
        rail(m,(s*850,380),(s*850,580),G)
        box(m,min(s*1100,s*655),max(s*1100,s*655),180,380,G-20,G,"or_floor")
        stairs(m,"n",min(s*840,s*660),max(s*840,s*660),-500,180)
        rail(m,(s*655,180),(s*655,380),G)
        rail(m,(s*655,380),(s*850,380),G)
        for n in (-850,0,560):box(m,s*980-15,s*980+15,n-15,n+15,0,G-20,"or_concrete")
    rail(m,(-1100,580),(-320,580),G)
    rail(m,(-320,580),(470,580),G)
    rail(m,(470,580),(1100,580),G)
    # Four lane-marking runs, parking bays and drains, raised only a fraction of an inch.
    for e in (-570,570):
        box(m,e-2,e+2,-1390,550,.10,.14,"or_yellow",False)
    for n in range(-1300,480,240):
        box(m,-560,560,n-2,n+2,.10,.14,"or_yellow",False)
    for e in (-1070,1070):
        box(m,e-12,e+12,-1380,560,.1,.2,"ar_grating",False)
    for n in (-1000,-400,170):
        # Painted chevrons down the main aisle.
        for s in (-1,1):m.beam((0,n,.2),(s*28,n-45,.2),(7,.1),"or_white")

def tower(m,e,n,z,height,width=100,paint="or_steel"):
    for dx in (-1,1):
        for dy in (-1,1):
            a=(e+dx*width/2,n+dy*width/2,z);b=(e+dx*width*.21,n+dy*width*.21,z+height)
            m.beam(a,b,(7,7),paint)
    levels=max(3,round(height/110))
    def at(side,h):return e+side[0]*width*(.5-.29*h/height),n+side[1]*width*(.5-.29*h/height),z+h
    sides=((-1,-1),(1,-1),(1,1),(-1,1))
    for i in range(levels):
        h0=height*i/levels;h1=height*(i+1)/levels
        for j in range(4):
            a=sides[j];b=sides[(j+1)%4]
            m.beam(at(a,h0),at(b,h0),(3,3),paint)
            m.beam(at(a,h0),at(b,h1),(2.2,2.2),paint)
            m.beam(at(b,h0),at(a,h1),(2.2,2.2),paint)
    box(m,e-40,e+40,n-40,n+40,z+height,z+height+8,"or_steel",False)
    pipe(m,(e,n,z+height),(e,n,z+height+90),2,"or_silver")
    ring(m,(e,n,z+height+64),UP,5,8,"or_redlight")

def rocket(m):
    e,n=400,1200
    # Flame trench, angled support shoes and circular service base.
    box(m,e-245,e+245,n-270,n+270,G,G+52,"or_steel")
    B.lathe(m,(e,n,G+52),UP,[(190,0),(178,24),(155,30)],"or_steel",sides=48,cap="or_steel",surface="metal")
    for a in np.linspace(0,math.tau,8,endpoint=False):
        d=np.array((math.cos(a),math.sin(a),0))
        m.beam(np.array((e,n,G+70))+d*160,np.array((e,n,G+250))+d*105,(18,22),"or_silver")
    base=G+208
    profile=[(100,0),(110,45),(110,450),(110,465),(108,480),(108,1150),(104,1170),(104,1610),(96,1650),(70,1750),(34,1875),(0,2030)]
    paints=["or_white","or_white","or_dark","or_yellow","or_white","or_dark","or_white","or_steel","or_white","or_white","or_white"]
    B.lathe(m,(e,n,base),UP,profile,paints,sides=64,cap="or_white",surface="metal")
    for h in (75,420,505,800,1120,1200,1450,1590):ring(m,(e,n,base+h),UP,111 if h<480 else 109,3,"or_silver",64)
    # Four black engine bells, individual service lines and external raceways.
    for dx,dy in ((-48,-48),(48,-48),(-48,48),(48,48)):
        B.lathe(m,(e+dx,n+dy,base-100),UP,[(33,0),(30,12),(17,73),(20,100)],"or_dark",sides=24)
    for a in (0,math.pi/2,math.pi,math.pi*1.5):
        dx,dy=math.cos(a)*111,math.sin(a)*111
        pipe(m,(e+dx,n+dy,base+60),(e+dx,n+dy,base+1600),2.2,"or_silver")
    sign(m,"rocket",(e,n-111.2,base+765),(0,-1),61,360)
    sign(m,"orion",(e,n-111.4,base+1070),(0,-1),83,66)
    # Dense offset gantry: I-beams, cross-braces, platforms, handrails and umbilicals.
    x0,x1=e+135,e+460;y0,y1=n+55,n+425;top=base+1940
    for x in (x0,x1):
        for y in (y0,y1):
            box(m,x-10,x+10,y-14,y+14,G,top,"or_steel",False)
            box(m,x-17,x+17,y-15,y-10,G,top,"or_red",False)
    for z in np.arange(G+65,top,210):
        box(m,x0-35,x1+40,y0-35,y1+45,z-8,z,"ar_grating",False)
        for x in (x0,x1):
            m.beam((x,y0,z),(x,y1,z+210),(7,7),"or_steel")
            m.beam((x,y1,z),(x,y0,z+210),(7,7),"or_steel")
        for y in (y0,y1):
            m.beam((x0,y,z),(x1,y,z+210),(8,8),"or_steel")
            m.beam((x1,y,z),(x0,y,z+210),(8,8),"or_steel")
        # Equipment lift, cable trunks and small service enclosures behind the open lattice.
        box(m,x1-92,x1-48,y0+45,y1-40,z,z+190,"or_steel",False)
        for yy in (y0+50,y1-50):pipe(m,(x0+40,yy,z),(x0+40,yy,z+210),9,"or_silver")
        box(m,x0+60,x0+135,y1-70,y1-30,z+20,z+138,"or_green",False)
        rail(m,(x0-35,y0-35),(x1+40,y0-35),z,False)
        rail(m,(x1+40,y0-35),(x1+40,y1+45),z,False)
        pipe(m,(e+108,n,z+65),(x0+50,y0+60,z+65),10,"or_silver")
        lamp(m,(x1-30,y0+20,z+174),"n",38,1.6,220)
    for x in (x1-42,x1-16):pipe(m,(x,y0+15,G),(x,y0+15,top),2.5,"or_silver")
    for z in np.arange(G,top,16):pipe(m,(x1-42,y0+15,z),(x1-16,y0+15,z),1,"or_silver",sides=6)
    # Keep players out of dense gantry feet while leaving the deck's ring route clear.
    m.collision_box((x0-30,y0-30,G),(x1+40,y1+45,G+190),"metal")
    for x in (x0,x1):ring(m,(x,y1,top+12),UP,8,12,"or_redlight")

def detail(m):
    # Strong, deliberately placed cover rather than random clutter.
    for i,(e,n,z,heading,color) in enumerate(((-610,-1140,0,5,"red"),(620,40,0,90,"grey"),
            (-560,360,0,0,"red"),(840,1390,G,90,"blue"),(-720,1160,G,0,"grey"))):
        B.closed_container(m,B.Frame(e,n,heading,z),B.paint_for(color,e,n))
    for i,(e,n,z,w,d,h,heading) in enumerate(((-230,-780,0,180,95,70,7),(330,-1080,0,120,78,65,-10),
          (300,-650,0,120,70,58,0),(-300,-190,0,155,85,64,4),(370,280,0,130,76,60,-3),
          (30,480,0,90,65,52,2),(-740,790,G,120,70,66,0),(750,680,G,140,80,62,2),
          (-980,-700,G,95,70,56,0),(980,50,G,95,65,57,0),(-700,1500,0,125,75,60,0),
          (800,1510,0,130,70,60,0),(-1620,-1300,0,120,70,58,0),(1570,1500,0,120,70,58,0))):
        case(m,e,n,z,w,d,h,heading)
        if i in (1,4,6,7,10,11):case(m,e+3,n-2,z+h+2,w*.87,d*.9,h*.8,heading+3)
    for e,n in ((540,-1230),(-950,-1290),(900,280)):tarped_pallet(m,e,n)
    for i,(e,n,z) in enumerate(((-1020,-450,0),(1010,-300,0),(950,450,0),(-900,1450,G),
         (710,1580,G),(-1500,1550,G),(-1500,-1250,G),(1520,-1180,G),(-300,1470,0),
         (600,1050,0),(-600,1020,0),(-900,500,0))):
        case(m,e,n,z,70,52,46,i*11)
        if i%3==0:case(m,e+3,n,z+47,65,48,40,i*11+7)
    # Service drums with raised seams and hazard bands.
    for e,n,z in ((-1020,1530,G),(980,-1170,0),(-970,-80,0),(890,850,0),(-1420,1530,0)):
        for j in range(3):
            at=(e+(j%2)*30,n+(j//2)*32,z)
            B.lathe(m,at,UP,[(12,0),(13,3),(13,37),(12,40)],"or_green",sides=16,cap="or_steel",surface="metal")
            for h in (6,20,34):ring(m,np.array(at)+UP*h,UP,13.7,2,"or_yellow",16)
    # Long utility bundles, flange collars, valves and suspended cable trays.
    for s in (-1,1):
        for z,r in ((145,12),(183,8)):
            pipe(m,(s*1040,-1380,z),(s*1040,1670,z),r,"or_silver")
            for n in np.arange(-1200,1600,180):ring(m,(s*1040,n,z),(0,1,0),r+3,5,"or_steel")
        for n in (-600,400,1200):
            pipe(m,(s*1040,n,145),(s*990,n,145),5,"or_silver")
            B.lathe(m,(s*984,n,145),(1,0,0),[(20,-1),(20,1)],"or_red",sides=20)
            for a in np.linspace(0,math.tau,6,endpoint=False):pipe(m,(s*984,n,145),(s*984,n+math.cos(a)*20,145+math.sin(a)*20),1.5,"or_red",sides=5)
    for e in (-1060,1070):
        for n in (-1260,-630,80,750,1460):lamp(m,(e,n,202),"n",50,5.0,380)
    # Floodlight towers and safety masts.
    for e,n,h in ((-1260,1320,1870),(1040,1550,1480),(-880,450,720),(960,-980,680)):
        z=G if n>600 else 0;tower(m,e,n,z,h,80)
        box(m,e-64,e+64,n-12,n+12,z+h-10,z+h+28,"or_steel",False)
        for dx in (-43,0,43):
            box(m,e+dx-16,e+dx+16,n-16,n-13,z+h-4,z+h+22,"or_light",False)
        if h<800:LIGHTS.append((f"Flood {e}",(e,n,z+h-40),"3.4,3.1,2.5,1",850,False))
    # Launch-pad cabinets, ducts and hazard guards.
    for e,n in ((-420,1430),(900,1040),(-380,720)):
        box(m,e-50,e+50,n-40,n+40,G,G+104,"or_green")
        sign(m,"warning",(e,n-40.3,G+70),(0,-1),80,34)
    sign(m,"pad",(0,579,G+75),(0,-1),320,65)
    # Flag at Operations; mesh has a restrained wave and reads from both directions.
    pipe(m,(1140,700,530),(1140,700,910),3.2,"or_silver")
    for i in range(18):
        x0=i/18;x1=(i+1)/18
        def point(x,z):return (1140+x*220,700+math.sin(x*8+z)*15,880-z*126-x*12)
        pts=[point(x0,1),point(x1,1),point(x1,0),point(x0,0)]
        B.card(m,"or_signs",pts,(0,-1,0),uv=[M.uv("flag",x0,0),M.uv("flag",x1,0),M.uv("flag",x1,1),M.uv("flag",x0,1)],both=True)

def backdrop(m):
    rng=np.random.default_rng(71)
    def height(e,n):
        r=np.hypot(e,n);a=np.arctan2(n,e)
        fade=np.clip((r-2400)/4500,0,1)
        broad=1100+450*np.sin(e/2100+n/3300)+350*np.sin(n/1900-e/4200)+180*np.sin(e/700)*np.cos(n/900)
        ridge=np.abs(np.sin(e/2900+n/4400))*850
        return -220+fade*(broad+ridge)+np.clip((r-9000)/16000,0,1)*1200
    axis=np.linspace(-28000,28000,141)
    def vertex(e,n):return np.array((e,n,height(e,n)))
    def normal(e,n):return K.normalise((height(e-20,n)-height(e+20,n),height(e,n-20)-height(e,n+20),40))
    for ix in range(len(axis)-1):
        for iy in range(len(axis)-1):
            es,ns=axis[ix:ix+2],axis[iy:iy+2]
            if abs(sum(es)/2)<1850 and abs(sum(ns)/2)<1800:continue
            coords=((es[0],ns[0]),(es[1],ns[0]),(es[1],ns[1]),(es[0],ns[1]))
            pts=[vertex(*p) for p in coords];normals=[normal(*p) for p in coords]
            paint="sh_hill_grass" if np.mean(normals,axis=0)[2]>.82 else "sh_hill_rock"
            for tri in ((0,1,2),(0,2,3)):B.card(m,paint,[pts[i] for i in tri],UP,normals=[normals[i] for i in tri])
    # Distant woodland uses native vista models, installed by the editor finishing pass.
    # Radome on a separate rocky ridge, with triangular geodesic-like panels.
    e,n=2850,4600;z=height(e,n)+50
    tower(m,e,n,z,570,340)
    center=np.array((e,n,z+830));r=335
    for row in range(12):
        a0=-math.pi/2+math.pi*row/12;a1=-math.pi/2+math.pi*(row+1)/12
        for col in range(24):
            t0=math.tau*col/24;t1=math.tau*(col+1)/24
            def p(a,t):return center+r*np.array((math.cos(a)*math.cos(t),math.cos(a)*math.sin(t),math.sin(a)))
            ps=[p(a0,t0),p(a0,t1),p(a1,t1),p(a1,t0)]
            for tri in ((ps[0],ps[1],ps[2]),(ps[0],ps[2],ps[3])):
                B.card(m,"or_radome",tri,np.mean(tri,axis=0)-center)
                for i in range(3):pipe(m,tri[i],tri[(i+1)%3],.9,"or_steel",sides=5)
    for e,n,z,h in ((-2600,2900,100,1400),(2100,3100,240,1600),(-3600,6000,700,1700),(900,6500,900,1900)):
        tower(m,e,n,height(e,n),h,100)
    # Distant low industrial sheds, tanks and pipe racks.
    for e in range(-3300,3600,650):
        n=2450+int(rng.integers(0,400))
        z=height(e+210,n+160)
        box(m,e,e+420,n,n+320,z-60,z+260,"or_concrete",False)
        box(m,e-10,e+430,n-10,n+330,z+260,z+276,"or_steel",False)
    for e in (-2300,-1950,2200,2500):
        B.lathe(m,(e,2100,height(e,2100)),UP,[(110,0),(110,350),(95,365),(0,385)],"or_silver",sides=24)

def configure(m):
    for p in m.polygons:
        family=p.split("_")[0]
        folder={"or":"orion","bx":"boxyard","ar":"ares","co":"collider","rv":"riverdale","sh":"stillhouse"}.get(family)
        if folder is None:raise ValueError(p)
        m.material_overrides[p]=f"materials/{folder}/{p}.vmat"
        m.tile_overrides[p]=M.TILES.get(p,AM.TILES.get(p,64.))
        if p=="or_dryfloor":m.tile_overrides[p]=384.
        if family=="bx":m.tile_overrides[p]=1.
        if p in ("rv_rock_far","sh_hill_rock","sh_hill_grass","or_earth"):m.tile_overrides[p]=512.
    m.anchored_paints=set();m.decal_paints=set()
    return m

def build():
    LIGHTS.clear();models={name:K.Model() for name,_,_ in MODELS}
    building(models["orion_west"],-1);building(models["orion_east"],1)
    yard(models["orion_yard"]);detail(models["orion_detail"])
    rocket(models["orion_rocket"]);backdrop(models["orion_backdrop"])
    return {name:configure(model) for name,model in models.items()}

RED=[(e,n,1) for e in (-1440,-1350) for n in (-1180,-1090,-1000)]
BLUE=[(e,n,1) for e in (1400,1500) for n in (1150,1250,1350)]
DM=RED[:2]+BLUE[:2]+[(e,n,z+1) for e,n,z in (
    (-800,-1300,0),(800,-1300,0),(-70,-1250,0),(50,-700,0),(-450,-400,0),
    (450,-100,0),(-500,150,0),(300,760,0),(-700,1400,0),(600,1450,0),
    (-1210,-1100,G),(1210,-1100,G),(-980,400,G),(980,420,G),
    (-530,960,G),(990,1600,G),(-1250,1200,G),(1250,1200,G))]
DOM=[("A",(-950,-450,1)),("B",(0,-320,1)),("C",(970,1000,G+1))]
HOT=[("Cargo Yard",(0,-550,1)),("Launch Deck",(-540,900,G+1)),("Service",(200,1390,1))]
SITES=[("A","Launch Pad",-670,-430,780,1040,G),("B","Cargo Yard",140,460,-1000,-760,0)]
RETAKES={"bombsite_a":{"planter":[(-550,900,G+1),(-550,1000,G+1)],
          "defender":[(-990,950,G+1),(-1220,1000,G+1),(-1220,1400,G+1)],"attacker":BLUE},
         "bombsite_b":{"planter":[(300,-880,1),(220,-940,1)],
          "defender":[(850,-1100,1),(850,-800,1),(740,-1250,1)],"attacker":RED}}
CASH=[("Cargo",(0,-550,0),(-1330,-1120,0)),("Launch",(-540,900,G),(1230,1250,G)),
      ("Service",(200,1390,0),(0,-1100,0))]

def comp(kind,key,**values):return K.component(IDS,kind,key,**values)
def go(name,key,**values):return K.game_object(IDS,name,key,**values)
def trigger(key,size):return comp("Sandbox.BoxCollider",key,Scale=K.vec(size),Center="0,0,0",Static=True,IsTrigger=True)
def spawn(name,key,p,team,tags=""):
    return go(name,key,position=K.to_world(p),rotation=K.yaw_rotation(K.plan_yaw((-p[0],-p[1]))),tags=tags,
              components=[comp("TeamSpawnPoint",key+"/component",Team=team)])
def group(name,key,modes,children,inverse=False):
    return go(name,key,components=[comp("Facepunch.GameModeObject",key+"/mode",GameModes=modes,Inverse=inverse)],children=children)

def scene_data():
    models=[]
    for name,title,solid in MODELS:
        path=f"{RESOURCE}/{name}.vmdl"
        components=[comp("Sandbox.ModelRenderer",name+"/render",Model=path,BodyGroups=18446744073709551615,Tint="1,1,1,1")]
        if solid:components.append(comp("Sandbox.ModelCollider",name+"/collider",Model=path,Static=True,IsTrigger=False))
        models.append(go(title,name,components=components))
    # Reuse the project's detailed forklift as an ordinary static model instance.
    models.append(go("Forklift","forklift",position=K.to_world((680,-770,0)),rotation=K.yaw_rotation(-35),components=[
        comp("Sandbox.ModelRenderer","forklift/render",Model="models/props/lowtide/forklift.vmdl"),
        comp("Sandbox.ModelCollider","forklift/collider",Model="models/props/lowtide/forklift.vmdl",Static=True)]))
    info=go("Scene Information","info",components=[
        comp("Sandbox.SceneInformation","info/scene",Title="Orion",Description="A rain-soaked launch complex beneath an orbital vehicle. Three routes, control rooms and elevated service decks."),
        comp("Facepunch.MapInformation","info/map",Image="ui/maps/orion.png",IsVisibleInMenu=True),
        comp("Facepunch.MapSpawnSettings","info/spawn",UseMapSpawnPoints=False,AllowNavMeshSpawns=False)])
    env=[
        go("Evening sun","sun",rotation=K.angles_rotation(18,-150),components=[
            comp("Sandbox.DirectionalLight","sun/light",LightColor="1.9,1.39,.85,1",SkyColor=".24,.29,.36,1",Shadows=True,
                 ContactShadows=True,ShadowBias=.0005,ShadowCascadeCount=4,ShadowCascadeSplitRatio=.93,ShadowHardness=0)]),
        go("Sky","sky",components=[comp("Sandbox.SkyBox2D","sky/box",SkyIndirectLighting=True,
            SkyMaterial="materials/orion/sky/orion_sky.vmat",Tint="1,1,1,1")]),
        go("Distance haze","fog",components=[comp("Sandbox.GradientFog","fog/component",Color=".39,.45,.51,.85",
            StartDistance=2600,EndDistance=10500,FalloffExponent=1.1,Height=6000,VerticalFalloffExponent=1.3)]),
        go("Look","look",components=[
            comp("Sandbox.PostProcessVolume","look/volume",EditorPreview=True,BlendWeight=1,Priority=0,SceneVolume={"Type":"Infinite"}),
            comp("Sandbox.AmbientOcclusion","look/ao",**{"__version":1},Intensity=.9,Radius=45,FalloffRange=1,ThinCompensation=2),
            comp("Sandbox.Bloom","look/bloom",**{"__version":1},Mode="Additive",Strength=.13,Threshold=2.8,Tint="1,1,1,1"),
            comp("Sandbox.Tonemapping","look/tonemap",**{"__version":3},AutoExposureEnabled=True,MinimumExposure=.85,MaximumExposure=1.8,Mode="ACES",Rate=1)])]
    lights=[go(name,"lights/"+str(i),position=K.to_world(p),components=[comp("Sandbox.PointLight","lights/"+str(i)+"/light",
        LightColor=color,Radius=radius,Shadows=shadow,Attenuation=1,FogMode="Disabled",FogStrength=0)])
        for i,(name,p,color,radius,shadow) in enumerate(LIGHTS)]
    sites=[]
    for i,(name,title,e0,e1,n0,n1,z) in enumerate(SITES):
        key="site/"+name
        sites.append(go("bombsite_"+name.lower(),key,position=K.to_world(((e0+e1)/2,(n0+n1)/2,z+78)),tags="zone,bombsite",components=[
            comp("BombSite",key+"/site",Index=i,DamageFalloffDistance=1750,MaxBombDamage=500),
            comp("Zone",key+"/zone",DisplayName=title,Color="1,0,0,1"),trigger(key+"/box",(n1-n0,e1-e0,156))]))
    buy=[]
    for name,p,team in (("Launch Control",(-1450,-1140,85),"Terrorist"),("Operations",(1450,1250,85),"CounterTerrorist")):
        key="buy/"+name
        buy.append(go(name,key,position=K.to_world(p),tags="zone",components=[comp("Zone",key+"/zone",DisplayName=name),
            comp("Facepunch.BuyZone",key+"/buy",Team=team),trigger(key+"/box",(450,500,170))]))
    objectives=[go(f"{kind} {name}",f"objectives/{kind}/{name}",position=K.to_world(p),components=[
        comp("Facepunch.ObjectiveSpot",f"objectives/{kind}/{name}/spot",Kind=kind,Label=name)])
        for kind,points in (("Domination",DOM),("HotZone",HOT)) for name,p in points]
    zones=[]
    for name,bounds in (("Cargo Yard",(-1100,1100,-1400,580,-20,215)),("Launch Deck",(-1100,1100,580,1700,215,600)),
          ("Service Tunnel",(-1100,1100,580,1700,-20,215)),("Launch Control",(-1800,-1100,-1400,1700,-20,620)),
          ("Operations",(1100,1800,550,1700,-20,620)),("Fuel Processing",(1100,1800,-1400,550,-20,620)),
          ("West Catwalk",(-1100,-850,-1400,580,215,600)),("East Catwalk",(850,1100,-1400,580,215,600))):
        e0,e1,n0,n1,z0,z1=bounds;key="zone/"+name
        zones.append(go(name,key,position=K.to_world(((e0+e1)/2,(n0+n1)/2,(z0+z1)/2)),tags="zone",components=[
            comp("Zone",key+"/zone",DisplayName=name,Color=".8,.6,.2,1"),comp("Facepunch.MapLocation",key+"/location"),
            trigger(key+"/box",(n1-n0,e1-e0,z1-z0))]))
    previous=A.ids
    try:
        A.ids=IDS;cash=[A.cash_point(name,"cash/"+name,p,e) for name,p,e in CASH]
    finally:A.ids=previous
    area=go("Play Area","play",position=K.to_world((0,150,400)),tags="zone",components=[
        comp("Zone","play/zone"),comp("Facepunch.PlayArea","play/area",Zone={"_type":"component","component_id":IDS("play/zone"),"go":IDS("play"),"component_type":"Zone"}),
        trigger("play/box",(3100,3600,900))])
    objects=[info,*env,go("Orion launch complex","world",children=models),go("Work lighting","lights",children=lights),
        group("Team Spawns","spawns",["Deathmatch","Gun Game","Retakes"],
            [spawn(f"Red {i+1}",f"red/{i}",p,"Terrorist") for i,p in enumerate(RED)]+
            [spawn(f"Blue {i+1}",f"blue/{i}",p,"CounterTerrorist") for i,p in enumerate(BLUE)],True),
        group("Deathmatch Spawns","dm",["Deathmatch","Gun Game"],[spawn(f"DM {i+1}",f"dm/{i}",p,"Unassigned","deathmatch") for i,p in enumerate(DM)]),
        group("Retakes Spawns","retakes",["Retakes"],[spawn(f"{site} {role} {i+1}",f"retakes/{site}/{role}/{i}",p,
            "CounterTerrorist" if role=="attacker" else "Terrorist",f"retakes,{site},{role}")
            for site,roles in RETAKES.items() for role,points in roles.items() for i,p in enumerate(points)]),
        go("Bomb Sites","sites",children=sites),go("Buy Zones","buy",children=buy),go("Callouts","zones",children=zones),
        go("Objective Spots","objectives",children=objectives),group("Cash Grab","cash",["Cash Grab"],cash),area,
        go("Minimap Renderer","minimap",position=K.to_world((0,150,1700)),components=[comp("Facepunch.MinimapRenderer","minimap/renderer",
            CurrentMinimapPath="ui/minimaps/minimap_orion.png",Size=4000,ExportResolution="1024,1024")]),
        K.prefab_instance(IDS,"prefabs/game_modes/team_deathmatch.prefab"),K.prefab_instance(IDS,"prefabs/game_modes/bomb_defusal.prefab"),
        K.prefab_instance(IDS,"scenes/maps/defusemap_01/game_setup.prefab")]
    return {"__guid":IDS("scene"),"GameObjects":objects,"SceneProperties":{"NetworkInterpolation":True,"PhysicsMode":"Physics3D", "TimeScale":1,"WantsSystemScene":True,
        "Metadata":{"Title":"Orion","Image":"ui/maps/orion.png","IsVisibleInMenu":"True",
            "GameModes":"prefabs/game_modes/team_deathmatch.prefab, prefabs/game_modes/bomb_defusal.prefab"},
        "NavMesh":{"Enabled":True,"IncludeStaticBodies":True,"IncludeKeyframedBodies":True,"EditorAutoUpdate":True,
            "AgentHeight":64,"AgentRadius":16,"AgentStepSize":18,"AgentMaxSlope":40,"ExcludedBodies":"zone","IncludedBodies":"",
            "DeferGeneration":False,"CustomBounds":True,"Bounds":{"Mins":K.vec(K.to_world((1800,-1400,-30))),"Maxs":K.vec(K.to_world((-1800,1700,360)))}}},
        "ResourceVersion":3,"Title":"Orion","Description":"Orbital launch complex","__references":[],"__version":3}

def all_spots():
    return ([(f"red {i}",p) for i,p in enumerate(RED)]+[(f"blue {i}",p) for i,p in enumerate(BLUE)]+
        [(f"dm {i}",p) for i,p in enumerate(DM)]+DOM+HOT+
        [(f"{site} {role} {i}",p) for site,roles in RETAKES.items() for role,points in roles.items() for i,p in enumerate(points)]+
        [(f"cash {name}",(p[0],p[1],p[2]+1)) for name,p,_ in CASH]+
        [(f"extract {name}",(p[0],p[1],p[2]+1)) for name,_,p in CASH]+
        [(f"site {label}",((e0+e1)/2,(n0+n1)/2,z+1)) for label,_,e0,e1,n0,n1,z in SITES])

def minimap(models):
    out=STAGE/"ui/minimaps";out.mkdir(parents=True,exist_ok=True)
    picture=Image.new("RGBA",(1024,1024),(0,0,0,0));d=ImageDraw.Draw(picture)
    def pos(e,n):return ((e+2000)/4000*1024,(2150-n)/4000*1024)
    d.rectangle((*pos(-1800,1700),*pos(1800,-1400)),fill=(77,88,94,255),outline=(190,202,209,255),width=3)
    for m in models:
        for center,axes,size,surface in m.boxes:
            if size[2]<30 and abs(center[2]+size[2]/2-G)<1:continue
            if center[2]+size[2]/2<12 or center[2]-size[2]/2>70:continue
            corners=[center+np.asarray(axes[0])*size[0]*a/2+np.asarray(axes[1])*size[1]*b/2 for a,b in ((-1,-1),(1,-1),(1,1),(-1,1))]
            d.polygon([pos(*p[:2]) for p in corners],fill=(27,36,41,255),outline=(155,169,178,255),width=1)
    for x in (-980,980):d.line([pos(x,-1000),pos(x,1650)],fill=(204,174,89,255),width=7)
    for name,_,e0,e1,n0,n1,z in SITES:
        p=pos((e0+e1)/2,(n0+n1)/2);d.ellipse((p[0]-13,p[1]-13,p[0]+13,p[1]+13),outline=(245,212,114,255),width=3)
    picture.save(out/"minimap_orion.png")

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument("--check",action="store_true");args=parser.parse_args()
    models=build();out=STAGE/RESOURCE
    for name,m in models.items():print(f"{name}: {K.write_model(out,RESOURCE,name,m)} triangles; {len(m.boxes)} boxes, {len(m.hulls)} hulls",flush=True)
    (STAGE/"orion.scene.json").write_text(json.dumps(scene_data(),indent=2)+"\n",encoding="utf-8")
    (ROOT/"output/orion/check-points.json").write_text(json.dumps([{"name":name,"position":K.to_world(p).tolist()} for name,p in all_spots()],indent=2))
    solid=[models[name] for name,_,collision in MODELS if collision];minimap(solid)
    config={"width":1536,"height":1024,"views":[ART,{"name":"yard","eye":[-70,-1250,68],"target":[110,900,650],"fov":86},
        {"name":"control","eye":[-1240,-600,310],"target":[-1430,-240,290],"fov":84},
        {"name":"deck","eye":[-950,500,308],"target":[180,1150,850],"fov":86}]}
    (ROOT/"output/orion/capture-config.json").write_text(json.dumps(config,indent=2))
    print(f"{len(LIGHTS)} lights, {sum(1 for l in LIGHTS if l[-1])} shadow casters, {len(all_spots())} player/objective positions",flush=True)
    if args.check:
        errors=R.check_spots(R.collision_aabbs(solid),all_spots())
        print(f"Clearance/support errors: {errors}",flush=True)
        reachable=R.check_reach(solid,all_spots(),ROOT/"output/orion/reach.png",bounds=PLAY)
        sight=R.check_retakes_sight(R.Blockers(solid),RETAKES)
        (ROOT/"output/orion/layout-validation.json").write_text(json.dumps({"positions":len(all_spots()),"clearance_errors":errors,"unreachable":reachable,"retakes_exposed":sight},indent=2))
        print(f"Connectivity errors: {reachable}; exposed Retakes pairs: {sight}",flush=True)

if __name__=="__main__":main()

