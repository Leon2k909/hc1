"""Collider: multiplayer research facility matching the supplied accelerator-hall reference.

Plan axes: e east, n north, z up; world = (n,-e,z), all inches.
Main hall e -1400..1400, n -900..650. The upper gallery is z256,
around an open atrium, with two long stairs. Spawn/lab wings on east/west.
The observation window looks north into a separate accelerator chamber;
a playable service lane runs under it. All generated assets are staged,
then imported/validated/saved in the editor, never written over an open scene.
"""
from pathlib import Path
import argparse
import json
import math
import numpy as np
from PIL import Image, ImageDraw
import map_kit as K
import boxyard_map as B
import ares_map as A
import ares_materials as AM
import railhead_map as R
import collider_materials as M
import collider_detail_geometry as D

ROOT = Path(__file__).resolve().parents[1]
STAGE = ROOT / "output/collider/stage"
RESOURCE = "models/maps/collider"
IDS = K.SceneIds("897a19b5-19ef-4d72-98cb-1f2be8a5844e")
G = 256.
PLAY = (-1900.,1900.,-900.,980.)
UP = np.array((0.,0.,1.))
LIGHTS = []
MODELS = (("collider_structure","Structure",True),("collider_detail","Equipment and signs",True),
          ("collider_machine","Particle accelerator",False),("collider_glass","Observation glass",False))
RED = [(-1640,n,1) for n in (-400,-300,-200,-100,0,100)]
BLUE = [(1640,n,1) for n in (-400,-300,-200,-100,0,100)]
DM = RED[:2]+BLUE[:2]+[(e,n,z+1) for e,n,z in (
    (-1180,-700,0),(1180,-700,0),(-700,-350,0),(700,350,0),(-500,100,0),(500,-350,0),
    (-1150,-300,G),(1150,-400,G),(-600,-720,G),(600,-720,G),
    (-600,480,G),(600,480,G),(-1600,450,G),(1600,450,G),(-600,820,0),(600,820,0))]
DOM = [("A",(-1150,0,1)),("B",(0,60,1)),("C",(1150,0,1))]
HOT = [("Atrium",(0,-150,1)),("Observation",(0,480,G+1)),("Service",(0,820,1))]
SITES = [("A","Observation",-900,-500,360,600,G),("B","Operations",450,850,-350,100,0)]
RETAKES = {
    "bombsite_a": {"planter":[(-780,450,G+1),(-650,450,G+1)],
                   "defender":[(-1100,440,G+1),(-1120,100,G+1),(-580,590,G+1)],
                   "attacker":list(BLUE)},
    "bombsite_b": {"planter":[(760,-200,1),(550,-260,1)],
                   "defender":[(1100,-450,1),(1100,50,1),(760,230,1)],
                   "attacker":list(RED)},
}
CASH = [("Observation",(0,480,G),(0,-720,G)),
        ("Operations",(0,-150,0),(0,820,0)),
        ("Service",(0,820,0),(0,-720,G))]
ART_VIEW = {"name":"art","eye":[850,-620,G+74],"target":[-650,500,220],"fov":82}

def configure(m):
    for paint in m.polygons:
        if paint.startswith("co_"):
            m.material_overrides[paint] = f"materials/collider/{paint}.vmat"
            m.tile_overrides[paint] = M.TILES.get(paint,64.)
        elif paint.startswith("ar_"):
            m.material_overrides[paint] = f"materials/ares/{paint}.vmat"
            m.tile_overrides[paint] = AM.TILES.get(paint,64.)
        elif paint.startswith("bx_"):
            m.material_overrides[paint] = f"materials/boxyard/{paint}.vmat"
            m.tile_overrides[paint] = 1.
        else:
            raise ValueError(f"Unknown paint {paint}")
    m.anchored_paints=set()
    m.decal_paints=set()
    return m

def box(m,e0,e1,n0,n1,z0,z1,paint="co_wall",solid=True):
    m.box((e0,n0,z0),(e1,n1,z1),paint,"metal" if solid else None)

def wall(m,axis,run,across,z,openings=()):
    return A.wall(m,axis,run,across,z,openings,outside="co_wall",inside="co_wall",reveal="co_steel")

def pipe(m,a,b,r,paint="co_trim",sides=12):
    a,b=np.array(a,float),np.array(b,float)
    B.lathe(m,a,b-a,[(r,0),(r,float(np.linalg.norm(b-a)))],paint,sides=sides,cap=paint)

def railing(m,a,b,z,lamps=False,collide=True):
    D.rail(m,a,b,z,lamps=lamps,collide=collide)

def ring(m,e,n,z,inner,outer,width,paint="co_silver",sides=48):
    B.lathe(m,(e,n,z),(1,0,0),[(inner,-width/2),(outer,-width/2),(outer,width/2),
        (inner,width/2),(inner,-width/2)],paint,sides=sides)

def sign(m,label,center,facing,width,height):
    c=np.array(center,float); f=K.normalise((facing[0],facing[1],0))
    right=np.array((-f[1],f[0],0))
    m.oriented_box(c-f*.7,(-right,f,UP),(width+1,1.4,height+1),"co_trim")
    c=c+f*.08  # Keep the printed face in front of the backing plate.
    points=[c-right*width/2-UP*height/2,c+right*width/2-UP*height/2,
            c+right*width/2+UP*height/2,c-right*width/2+UP*height/2]
    B.card(m,"co_signs",points,f,uv=[M.uv(label,s,t) for s,t in ((0,0),(1,0),(1,1),(0,1))])

def monitor(m,center,facing,width,height,index=0):
    c=np.asarray(center,float); f=K.normalise((*facing,0)); right=np.cross(UP,f)
    m.oriented_box(c-f*2,(-right,f,UP),(width+5,4,height+5),"co_case")
    c=c+f*.08  # Separate the display from the bezel's front face to prevent z-fighting.
    pts=[c-right*width/2-UP*height/2,c+right*width/2-UP*height/2,
         c+right*width/2+UP*height/2,c-right*width/2+UP*height/2]
    u=(index%2)/2; v=1-(index//2+1)/2
    B.card(m,"co_screens",pts,f,uv=[(u,v),(u+.5,v),(u+.5,v+.5),(u,v+.5)])
    m.oriented_box(c-UP*(height/2+1.5)+f*.2,(-right,f,UP),(3,.5,.65),"co_beam")

def floor_stencil(m,label,e,n,z,width=140,height=100,angle=0):
    i=M.MARKINGS.index(label);a=math.radians(angle)
    right=np.array((math.cos(a),math.sin(a),0));forward=np.cross(UP,right)
    c=np.array((e,n,z+.14));u=(i%2)/2;v=1-(i//2+1)/2
    points=[c-right*width/2-forward*height/2,c+right*width/2-forward*height/2,
            c+right*width/2+forward*height/2,c-right*width/2+forward*height/2]
    B.card(m,"co_markings",points,UP,uv=[(u,v),(u+.5,v),(u+.5,v+.5),(u,v+.5)])

def control_desk(m,side,n,z,collide=True):
    """Sloped operator station and chair, against the outer control-room wall."""
    def part(e0,e1,n0,n1,z0,z1,paint,solid=False):
        lo,hi=sorted((side*e0,side*e1)); box(m,lo,hi,n+n0,n+n1,z+z0,z+z1,paint,solid)
    part(1780,1870,-56,56,6,38,"co_steel",collide)
    part(1776,1874,-59,59,36,40,"co_trim")
    # The keyboard deck rises toward its screen; it is not a floating flat sign.
    points=[(side*1755,n-56,z+40),(side*1816,n-56,z+58),
            (side*1816,n+56,z+58),(side*1755,n+56,z+40)]
    B.card(m,"co_steel",points,(-side*.3,0,1))
    for nn in (-56,56):
        m.beam((side*1755,n+nn,z+40),(side*1816,n+nn,z+58),(3,3),"co_trim")
    for row in range(4):
        for col in range(12):
            e=1765+row*5
            part(e,e+3,-36+col*5.6,-32+col*5.6,43+(e-1765)*.295,44+(e-1765)*.295,"co_trim")
    for nn in (42,49):
        part(1783,1787,nn,nn+3,49,50,"co_beam" if nn==42 else "co_amber")
    part(1820,1825,-4,4,38,76,"co_trim")
    monitor(m,(side*1818,n,z+83),(-side,0),100,48,index=int((n+200)//100)%4)
    # Chair frame and padded seat, with one simple player clip.
    part(1700,1746,-22,22,0,52,None,collide)
    part(1706,1740,-20,20,22,27,"co_case")
    part(1702,1708,-20,20,27,53,"co_case")
    pipe(m,(side*1723,n,z+4),(side*1723,n,z+22),2.4,"co_trim",10)
    for nn in (-17,17):
        m.beam((side*1705,n+nn,z+3),(side*1740,n-nn,z+3),(2.5,3),"co_trim")
        part(1710,1730,nn-1,nn+1,34,37,"co_trim")

def observation_bezel(m):
    """Rounded steel surround, fasteners and bolted mullion plates."""
    left,right,bottom,top,r=-1330,1330,G+12,820,108
    path=[]
    for e,z,start in ((right-r,top-r,0),(left+r,top-r,90),
                      (left+r,bottom+r,180),(right-r,bottom+r,270)):
        for degrees in np.linspace(start,start+90,9):
            a=math.radians(degrees); path.append((e+r*math.cos(a),632,z+r*math.sin(a)))
    for a,b in zip(path,path[1:]+path[:1]):
        m.beam(a,b,(17,26),"co_trim",up=(0,-1,0))
    # Fill the corners outside the curved aperture; the glass behind stays continuous.
    for ce,cz,sx,sz in ((left+r,top-r,-1,1),(right-r,top-r,1,1),
                        (left+r,bottom+r,-1,-1),(right-r,bottom+r,1,-1)):
        corner=(ce+sx*r,631,cz+sz*r)
        arc=[(ce+sx*r*math.cos(a),631,cz+sz*r*math.sin(a)) for a in np.linspace(0,math.pi/2,9)]
        for a,b in zip(arc,arc[1:]): B.card(m,"co_steel",[corner,a,b],(0,-1,0))
    for e in np.linspace(-1330,1330,8):
        for z in (G+38,790):
            box(m,e-11,e+11,628,635,z-22,z+22,"co_steel",False)
            for dz in (-15,15):
                for de in (-6,6): pipe(m,(e+de,627,z+dz),(e+de,625,z+dz),1.4,"co_silver",6)

def lamp(m,name,e,n,z,length=64,color="white",shadow=False,radius=440,axis="e",power=3.4):
    if axis=="e":
        box(m,e-length/2,e+length/2,n-4,n+4,z,z+4,"co_trim",False)
        box(m,e-length/2+3,e+length/2-3,n-2,n+2,z-.5,z,f"co_{color}",False)
    else:
        box(m,e-4,e+4,n-length/2,n+length/2,z,z+4,"co_trim",False)
        box(m,e-2,e+2,n-length/2+3,n+length/2-3,z-.5,z,f"co_{color}",False)
    rgb={"white":(1.,.93,.82),"red":(1.,.07,.035),"beam":(.22,.48,1.)}[color]
    LIGHTS.append((name,(e,n,z-10),",".join(str(round(c*power,3)) for c in rgb)+",1",radius,shadow))

def portal(m,name,axis,center,cross,z=0,width=160,height=192):
    A.door_frame(m,axis,center-width/2,center+width/2,cross-12,cross+12,z,z+height)
    if axis=="e":
        for n in (cross-16,cross+16):
            lamp(m,name+str(n),center,n,z+height-8,width-10,"red",n<cross,280,power=4.0)
            record=LIGHTS[-1]; LIGHTS[-1]=(record[0],(center,n,z+height*.55),*record[2:])
            for e in (center-width/2-3,center+width/2+3):
                box(m,e-1.1,e+1.1,n-.6,n+.6,z+25,z+height-24,"co_red",False)
    else:
        for e in (cross-16,cross+16):
            lamp(m,name+str(e),e,center,z+height-8,width-10,"red",False,280,axis="n",power=4.0)
            record=LIGHTS[-1]; LIGHTS[-1]=(record[0],(e,center,z+height*.55),*record[2:])
            for n in (center-width/2-3,center+width/2+3):
                box(m,e-.6,e+.6,n-1.1,n+1.1,z+25,z+height-24,"co_red",False)

def hardcase(m,e,n,z=0,w=78,d=46,h=55,heading=0):
    D.hardcase(m,e,n,z,w,d,h,heading,label=sign)

def shell(m,glass):
    box(m,-1900,1900,-900,980,-20,0,"co_floor")
    box(m,-1900,1900,-924,-900,0,900,"co_wall")
    box(m,-1924,-1900,-900,980,0,900)
    box(m,1900,1924,-900,980,0,900)
    box(m,-1924,1924,980,1004,0,256)
    # Broad two-level observation hall, with open upper circulation.
    box(m,-1400,-1000,-900,650,G-18,G,"co_floor")
    box(m,1000,1400,-900,650,G-18,G,"co_floor")
    box(m,-1000,1000,-900,-550,G-18,G,"co_floor")
    box(m,-1000,1000,300,650,G-18,G,"co_floor")
    # The service passage runs under the window ledge.
    box(m,-1900,1900,650,980,G-18,G,"co_floor")
    # Main side walls include ground doors and large control-room glazing upstairs.
    for s in (-1,1):
        across=tuple(sorted((s*1400,s*1424)))
        doors=[(-650,176,0,192),(0,176,0,192),(480,176,0,192),
               (-650,176,G,G+192),(480,176,G,G+192),(0,500,G+64,G+240),
               (0,680,568,832)]
        wall(m,"n",(-900,650),across,(0,900),doors)
        for n in (-650,0,480):
            portal(m,f"{s} ground {n}","n",n,s*1412,0,176)
        for n in (-650,480):
            portal(m,f"{s} upper {n}","n",n,s*1412,G,176)
        e=s*1412
        box(glass,e-1,e+1,-250,250,G+64,G+240,"co_glass",False)
        box(m,e-2,e+2,-250,250,G+64,G+240,None)
        for n in (-250,-125,0,125,250):
            box(m,e-6,e+6,n-2,n+2,G+64,G+240,"co_trim",False)
        # A second glazed laboratory level gives the control elevation the reference's depth.
        box(glass,e-1,e+1,-340,340,568,832,"co_glass",False)
        for n in range(-340,341,170):
            box(m,e-6,e+6,n-3,n+3,568,832,"co_trim",False)
        lo,hi=sorted((s*1270,s*1400))
        box(m,lo,hi,-350,350,542,560,"co_floor",False)
        railing(m,(s*1270,-350),(s*1270,350),560,collide=False)
    wall(m,"e",(-1400,1400),(650,674),(0,G),[(-900,160,0,192),(900,160,0,192)])
    for e in (-900,900):
        portal(m,f"service {e}","e",e,662,0)
    # Main window, framed by heavy concrete piers and a light header.
    box(m,-1400,1400,650,674,820,900,"co_concrete")
    box(m,-1400,-1330,650,690,G,820,"co_concrete")
    box(m,1330,1400,650,690,G,820,"co_concrete")
    box(glass,-1330,1330,660,662,G+12,820,"co_glass",False)
    box(m,-1330,1330,660,662,G+12,820,None)
    for e in np.linspace(-1330,1330,8):
        box(m,e-5,e+5,639,673,G+10,822,"co_trim",False)
    box(m,-1336,1336,645,676,G,G+12,"co_trim",False)
    box(m,-1336,1336,645,676,812,826,"co_trim",False)
    observation_bezel(m)
    box(m,-1424,1424,-924,690,900,920,"co_steel")
    # The two atrium stairs are open above their whole run.
    D.stair(m,"e",-210,-50,-400,-1000,0,G)
    D.stair(m,"e",40,200,400,1000,0,G)
    for n in (-550,300):
        railing(m,(-1000,n),(1000,n),G)
    for e,gap in ((-1000,(-210,-50)),(1000,(40,200))):
        railing(m,(e,-550),(e,gap[0]),G)
        railing(m,(e,gap[1]),(e,300),G)
    # Tall primary columns, with the lighter concrete tops seen in the reference.
    for e in (-960,960):
        for n in (-500,300):
            box(m,e-38,e+38,n-38,n+38,0,440,None)
            box(m,e-6,e+6,n-38,n+38,8,440,"co_steel",False)
            for nn in (n-34,n+34):
                box(m,e-38,e+38,nn-4,nn+4,8,440,"co_steel",False)
            box(m,e-38,e+38,n-38,n+38,440,900,"co_concrete")
            box(m,e-44,e+44,n-44,n+44,0,8,"co_trim")
            for z in (G-25,G+3,430):
                box(m,e-40,e+40,n-40,n+40,z,z+5,"co_trim",False)
    for e in range(-1200,1201,300):
        box(m,e-9,e+9,-900,650,866,900,"co_steel",False)
        for n in (-820,-420,0,460):
            box(m,e-14,e+14,n-5,n+5,828,866,"co_trim",False)

def wings(m):
    # Upper slabs leave a 180x640 opening over each wing stair.
    for s in (-1,1):
        def mirrored(e0,e1,n0,n1,z0,z1,paint="co_floor"):
            lo,hi=sorted((s*e0,s*e1)); box(m,lo,hi,n0,n1,z0,z1,paint)
        mirrored(1424,1700,-900,650,G-18,G)
        mirrored(1700,1900,-900,-780,G-18,G)
        mirrored(1700,1900,-140,650,G-18,G)
        lo,hi=sorted((s*1710,s*1880))
        D.stair(m,"n",lo,hi,-770,-140,0,G)
        mirrored(1424,1900,-900,980,880,900,"co_steel")
        mirrored(1400,1900,650,674,G,900,"co_wall")
        mirrored(1424,1900,-350,350,544,560,"co_floor")
        # Dogleg spawn cover blocks a shot from the opposite team's middle door.
        mirrored(1500,1524,-160,160,0,164,"co_concrete")
        # The upper middle opening is glass: it needs no spawn cover in front of the displays.
        for index,n in enumerate((-190,-65,65,190)):
            for row,z in enumerate((G+125,G+203)):
                monitor(m,(s*1880,n,z),(-s,0),112,66,(index+row)%4)
        for n in (-55,95,245):
            control_desk(m,s,n,G)
        for index,n in enumerate((-220,-70,80,230)):
            control_desk(m,s,n,560,collide=False)
            monitor(m,(s*1880,n,738),(-s,0),118,74,index)
        lamp(m,f"upper control {s}",s*1620,0,815,240,radius=620,power=4.2,axis="n")
        for z in (0,G):
            for n in (-550,360,780):
                lamp(m,f"wing {s} {z} {n}",s*1635,n,z+188,80,radius=550,shadow=False,power=5.5)
        for n in (-650,480):
            lamp(m,f"wing top {s} {n}",s*1770,n,610,80,radius=390,power=2.8)

def detail(m):
    floor_stencil(m,"c1",590,-735,G,180,125,180)
    floor_stencil(m,"c1",-1180,-620,G,155,110,90)
    floor_stencil(m,"a1",-610,380,0,165,115)
    floor_stencil(m,"c2",1110,360,0,155,110,90)
    sign(m,"accelerator",(-400,633,858),(0,-1),900,70)
    sign(m,"observation",(980,633,858),(0,-1),610,70)
    sign(m,"control",(-1383,0,535),(1,0),340,100)
    sign(m,"sector",(-1383,-550,685),(1,0),280,300)
    sign(m,"science",(-960,260,620),(0,-1),72,245)
    sign(m,"science",(960,260,620),(0,-1),72,245)
    sign(m,"cleaner",(960,259,151),(0,-1),66,190)
    sign(m,"a1",(-680,633,135),(0,-1),140,180)
    sign(m,"c2",(1150,633,145),(0,-1),170,200)
    sign(m,"b1",(-1383,-350,130),(1,0),170,180)
    for e,n,z,w,d,h,head in (
        (-1120,-520,G,110,58,76,0),(-1130,-400,G,90,50,62,0),
        (-790,-760,G,110,52,65,0),(820,-770,G,106,54,72,0),
        (-500,540,G,100,52,65,0),(500,540,G,100,52,65,0),(1130,230,G,96,54,68,90),
        (-700,100,0,96,54,66,0),(-650,160,0,80,42,50,0),
        (600,-60,0,110,62,75,0),(670,20,0,84,50,60,90),
        (-1150,-350,0,100,56,65,0),(1160,-300,0,100,56,65,0),
        (-260,-710,0,100,50,60,0),(260,-710,0,100,50,60,0),
        (-420,-790,G,106,58,72,0),(-290,-790,G,98,54,66,0),
        (160,-605,G,106,54,60,0),(25,-620,G,94,52,55,0),
        (-120,540,G,98,58,68,0),(0,540,G,98,58,68,0),(120,540,G,98,58,68,0),
        (0,540,G+68,82,48,55,0),
        (1270,-300,G,96,52,72,90),(1270,-210,G,82,48,60,90),(-1260,-50,G,106,60,74,90),
        (-200,210,0,100,56,72,0),(200,210,0,100,56,72,0),
        (-850,-350,0,106,58,74,0),(850,-420,0,106,58,74,0),
        (-850,480,0,110,60,72,0),(850,480,0,110,60,72,0),
        (-100,-450,0,100,58,68,0),(100,-450,0,100,58,68,0),
        (-1150,820,0,90,50,65,0),(1150,820,0,90,50,65,0)):
        hardcase(m,e,n,z,w,d,h,head)
    # A few taller server cabinets make solid mid-lane cover.
    for e,n in ((-430,80),(430,80)):
        box(m,e-24,e+24,n-30,n+30,0,138,"co_case")
        for k in range(11):
            box(m,e-20,e+20,n-31,n-30,12+k*10,18+k*10,"co_trim",False)
            box(m,e-17,e-12,n-31.5,n-31,14+k*10,16+k*10,"co_beam",False)
    # Parallel cable trays, suspended conduits and junctions at the ceiling.
    for n in (-820,-500,100,500):
        box(m,-1380,1380,n-13,n+13,804,812,"co_trim",False)
        for off in (-8,-3,3,8):
            pipe(m,(-1380,n+off,820),(1380,n+off,820),1.8,"co_case",8)
        for e in range(-1300,1301,180):
            box(m,e-1.5,e+1.5,n-15,n+15,802,804,"co_silver",False)
            pipe(m,(e,n,812),(e,n,878),.8,"co_silver",8)
    for e in (-1280,-1200,-1110,1110,1200,1280):
        for z,r in ((770,5),(796,3.5)):
            pipe(m,(e,-880,z),(e,620,z),r,"co_silver" if r==5 else "co_trim",12)
            for n in range(-820,621,140):
                ring_start=(e,n,z)
                pipe(m,(e,n-2,z),(e,n+2,z),r+2,"co_trim",12)
        for n in (-600,-100,400):
            box(m,e-10,e+10,n-15,n+15,730,756,"co_case",False)
            pipe(m,(e,n,756),(e,n,796),2,"co_silver",10)
    # Floor trench strips, expansion seams and yellow route markings on the upper gallery.
    for e in (-1320,1320):
        box(m,e-12,e+12,-870,610,G+.12,G+.3,"ar_grating",False)
        for n in range(-850,601,150):
            box(m,e-15,e+15,n-2,n+2,G+.3,G+.6,"co_silver",False)
    for n in (-840,590):
        box(m,-1300,1300,n-9,n+9,G+.12,G+.3,"ar_grating",False)
    for e in (-1012,1012):
        for n in range(-500,250,120):
            if (e<0 and -240<n<0) or (e>0 and 0<n<230): continue
            box(m,e-2,e+2,n,n+65,G+.15,G+.3,"co_amber",False)
    for e in (-1370,1370):
        for z in (735,755,780):
            pipe(m,(e,-880,z),(e,620,z),4,"co_trim")
        for n in range(-800,601,160):
            box(m,e-8,e+8,n-3,n+3,720,800,"co_silver",False)
    # Broken-up pools of warm light, with cool spill from the machine.
    for e in (-1050,-350,350,1050):
        for n in (-720,100):
            lamp(m,f"high {e} {n}",e,n,800,116,radius=1250,power=14.0,shadow=abs(e)==1050 and n==100)
        for n in (-720,460):
            lamp(m,f"under {e} {n}",e,n,224,76,radius=700,power=7.0,shadow=abs(e)==350 and n==460)
    for e in (-1150,1150):
        for n in (-350,100):
            lamp(m,f"arcade {e} {n}",e,n,225,60,radius=450,power=5.0)
    for e in (-850,0,850):
        lamp(m,f"service {e}",e,820,230,80,radius=400,power=3.1)

def machine(m):
    # The large tunnel is visible through the full observation wall.
    box(m,-1900,1900,1004,1900,-30,0,"co_floor",False)
    box(m,-1920,-1900,674,1900,0,1040,"co_concrete",False)
    box(m,1900,1920,674,1900,0,1040,"co_concrete",False)
    box(m,-1920,1920,1880,1900,0,1040,"co_wall",False)
    box(m,-1920,1920,674,1900,1020,1040,"co_steel",False)
    n,z=1260.,540.
    for e in (-1650,-1100,-550,0,550,1100,1650):
        ring(m,e,n,z,368,405,68,"co_steel",64)
        ring(m,e,n,z,406,418,88,"co_trim",64)
        for offset in (-39,39):
            ring(m,e+offset,n,z,370,376,4,"co_trim",64)
            ring(m,e+offset,n,z,401,407,4,"co_silver",64)
        for k in range(24):
            theta=2*math.pi*k/24
            dn,dz=math.cos(theta),math.sin(theta)
            radial=np.array((0,dn,dz)); tangent=np.array((0,dz,-dn))
            p=np.array((e,n,z))+radial*389
            # Individual face cassettes, seams and radial ribs break up each structural ring.
            for side in (-1,1):
                face=p+np.array((side*37,0,0))
                m.oriented_box(face,((1,0,0),tangent,radial),(5,82,27),"co_silver")
                rib=p+np.array((side*43,0,0))+tangent*44
                m.oriented_box(rib,((1,0,0),tangent,radial),(13,6,47),"co_trim")
                for along in (-31,31):
                    bolt=face+tangent*along
                    pipe(m,bolt+np.array((side*3,0,0)),bolt+np.array((side*6,0,0)),2.2,"co_trim",6)
            m.oriented_box(p+np.array((47,0,0)),((1,0,0),tangent,radial),(3,26,9),
                           "co_amber" if k%4==0 else "co_trim")
            if k%3==0:
                pipe(m,(e-10,n+355*dn,z+355*dz),(e+10,n+355*dn,z+355*dz),4,"co_white",8)
        # Machine supports and footings.
        for nn in (n-170,n+170):
            box(m,e-18,e+18,nn-16,nn+16,0,455,"co_steel",False)
            box(m,e-36,e+36,nn-30,nn+30,0,10,"co_trim",False)
            m.beam((e,nn,90),(e,n,480),(14,14),"co_silver")
    # Horizontal beam with segmented magnet housings, bolts, ties and cables.
    pipe(m,(-1830,n,z),(1830,n,z),16,"co_beam",32)
    for index,e in enumerate(range(-1750,1751,175)):
        ring(m,e,n,z,28,69,30,"co_silver",40)
        ring(m,e-35,n,z,28,58,9,"co_trim",40)
        ring(m,e+35,n,z,28,58,9,"co_trim",40)
        ring(m,e,n,z,24,32,124,"co_silver",40)
        for off in (-57,57):
            ring(m,e+off,n,z,30,40,6,"co_beam",40)
        for k in range(8):
            theta=2*math.pi*k/8
            dn,dz=math.cos(theta),math.sin(theta)
            pipe(m,(e-55,n+60*dn,z+60*dz),(e+55,n+60*dn,z+60*dz),4,"co_trim",10)
            pipe(m,(e-16,n+62*dn,z+62*dz),(e+16,n+62*dn,z+62*dz),5,"co_amber" if k%2 else "co_silver",10)
            # Eight magnet housings leave a visible illuminated bore between modules.
            radial=np.array((0,dn,dz)); tangent=np.array((0,dz,-dn))
            p=np.array((e,n,z))+radial*76
            m.oriented_box(p,((1,0,0),tangent,radial),(47,34,22),"co_steel")
            for off in (-21,21):
                m.oriented_box(p+np.array((off,0,0))+radial*12,
                               ((1,0,0),tangent,radial),(5,30,3),"co_silver")
            if k%2==0:
                m.oriented_box(p+radial*14,((1,0,0),tangent,radial),(18,12,2),"co_amber")
        # Staggered diagnostic boxes and hoses avoid one repeated silhouette along the beam.
        if index%3!=1:
            box(m,e-32,e+32,n-112,n-86,z-24,z+35,"co_case",False)
            monitor(m,(e,n-113,z+9),(0,-1),45,32,index%4)
            for off in (-20,20):
                pipe(m,(e+off,n-100,z+35),(e+off,n-126,z+65),2.5,"co_amber",8)
        # Curved rings are made as full annuli; the bright core stays visible in between.
        if e%525 == 175:
            lamp(m,f"beam spill {e}",e,n-120,z-20,45,"beam",False,800,power=7.0)
        # Braided leads from each magnet to an overhead bus, bent in three runs.
        for side in (-1,1):
            p0=(e+28,n+side*62,z+30); p1=(e+65,n+side*92,z+72)
            p2=(e+65,n+side*115,z+150); p3=(e+95,n+side*160,z+180)
            for a,b in ((p0,p1),(p1,p2),(p2,p3)):
                pipe(m,a,b,3,"co_trim",10)
    for dn,dz in ((-240,260),(240,260),(-340,0),(340,0)):
        for j in range(3):
            pipe(m,(-1800,n+dn+j*7,z+dz),(1800,n+dn+j*7,z+dz),2.5,"co_trim",10)
    # Coolant risers, cable ladders and lower equipment make the chamber a working machine room.
    for e in (-1470,-920,-370,180,730,1280):
        for nn in (n-285,n+285):
            pipe(m,(e,nn,110),(e,nn,795),5,"co_silver",12)
            for zz in range(160,761,100):
                pipe(m,(e,nn,zz-3),(e,nn,zz+3),7,"co_trim",12)
            pipe(m,(e,nn,795),(e+70,nn,860),5,"co_silver",12)
            pipe(m,(e+70,nn,860),(e+230,nn,860),5,"co_silver",12)
        box(m,e-53,e+53,1710,1785,20,250,"co_steel",False)
        for zz in range(43,230,17):
            box(m,e-44,e+44,1708,1710,zz,zz+7,"co_trim",False)
        monitor(m,(e,1707,211),(0,-1),56,28,2)
    # Segmented service panels and ribs line the far half of the cylindrical chamber.
    for e in range(-1800,1801,300):
        for k in range(-4,5):
            a=k*math.pi/12
            radial=np.array((0,math.cos(a),math.sin(a)))
            tangent=np.array((0,math.sin(a),-math.cos(a)))
            p=np.array((e,n,z))+radial*432
            m.oriented_box(p,((1,0,0),tangent,radial),(278,101,9),"co_steel")
            for j in (-90,90):
                pp=p+np.array((j,0,0))-radial*6
                m.oriented_box(pp,((1,0,0),tangent,radial),(5,88,3),"co_silver")
    # Maintenance catwalks inside the machine hall.
    for nn in (850,1690):
        box(m,-1850,1850,nn-70,nn+70,305,315,"ar_grating",False)
        railing(m,(-1850,nn-68),(1850,nn-68),315,collide=False)
        railing(m,(-1850,nn+68),(1850,nn+68),315,collide=False)
    sign(m,"ring",(1820,1230,640),(-1,0),330,240)
    sign(m,"warning",(0,1875,240),(0,-1),320,140)
    for e in (-1400,-700,0,700,1400):
        lamp(m,f"machine overhead {e}",e,n,960,120,"white",False,950,power=8.0)
        LIGHTS.append((f"blue chamber {e}",(e,1010,650),"2.5,4,7,1",750,False))

def build():
    LIGHTS.clear()
    structure,details,accel,glass=K.Model(),K.Model(),K.Model(),K.Model()
    shell(structure,glass)
    wings(structure)
    detail(details)
    machine(accel)
    return dict(zip((p[0] for p in MODELS),map(configure,(structure,details,accel,glass))))

def component(kind,key,**values): return K.component(IDS,kind,key,**values)
def go(name,key,**values): return K.game_object(IDS,name,key,**values)
def collider(key,size,trigger=True):
    return component("Sandbox.BoxCollider",key,Scale=K.vec(size),Center="0,0,0",IsTrigger=trigger,Static=True)
def spawn(name,key,p,team,tags=""):
    return go(name,key,position=K.to_world(p),rotation=K.yaw_rotation(K.plan_yaw((-p[0],0))),
        tags=tags,components=[component("TeamSpawnPoint",key+"/spawn",Team=team)])
def group(name,key,modes,children,inverse=False):
    return go(name,key,components=[component("Facepunch.GameModeObject",key+"/mode",GameModes=modes,Inverse=inverse)],children=children)

def callouts():
    areas=[("Operations",-1400,1400,-900,650,-10,G-18),
           ("Observation",-1400,1400,300,650,G-18,760),
           ("South Gallery",-1400,1400,-900,-550,G-18,760),
           ("Service",-1900,1900,674,980,-10,G-18),
           ("West Gallery",-1400,-1000,-550,300,G-18,760),
           ("East Gallery",1000,1400,-550,300,G-18,760),
           ("Control",-1900,-1424,-900,674,-10,640),
           ("Laboratory",1424,1900,-900,674,-10,640)]
    result=[]
    for label,e0,e1,n0,n1,z0,z1 in areas:
        key="callout/"+label
        result.append(go(label,key,position=K.to_world(((e0+e1)/2,(n0+n1)/2,(z0+z1)/2)),tags="zone",components=[
            component("Zone",key+"/zone",DisplayName=label,Color="0.3,0.6,1,1"),
            component("Facepunch.MapLocation",key+"/location"),collider(key+"/box",(n1-n0,e1-e0,z1-z0))]))
    return result

def cash_points():
    # Use the shared Cash Grab component wiring with this map's stable ID namespace.
    previous=A.ids
    try:
        A.ids=IDS
        return [A.cash_point(label,"cash/"+label,cash,extract) for label,cash,extract in CASH]
    finally:
        A.ids=previous

def scene_data():
    world=[]
    for name,title,collide in MODELS:
        path=f"{RESOURCE}/{name}.vmdl"
        components=[component("Sandbox.ModelRenderer",name+"/render",Model=path,BodyGroups=18446744073709551615,
                              RenderType="On",Tint="1,1,1,1")]
        if collide: components.append(component("Sandbox.ModelCollider",name+"/collision",Model=path,Static=True,IsTrigger=False))
        world.append(go(title,name,components=components))
    lights=[go(name,"light/"+name,position=K.to_world(p),components=[
        component("Sandbox.PointLight","light/"+name+"/component",LightColor=color,Radius=radius,Shadows=shadow,Attenuation=1,FogMode="Disabled",FogStrength=0,
                  Contribution="Diffuse, Transmissive" if name.startswith(("high ","machine overhead ")) else "Diffuse, Specular, Transmissive")])
        for name,p,color,radius,shadow in LIGHTS]
    probes=[]
    for label,center,bounds in (("Hall",(0,-100,310),(-1450,1450,-924,674,0,900)),
         ("Beam",(0,1280,540),(-1900,1900,674,1900,0,1040)),
         ("West",(-1660,0,200),(-1900,-1424,-900,980,0,640)),("East",(1660,0,200),(1424,1900,-900,980,0,640))):
        e0,e1,n0,n1,z0,z1=bounds; at=K.to_world(center)
        probes.append(go(label,"probe/"+label,position=at,components=[
            component("Sandbox.EnvmapProbe","probe/"+label+"/component",
                Bounds={"Mins":K.vec(K.to_world((e1,n0,z0))-at),"Maxs":K.vec(K.to_world((e0,n1,z1))-at)},
                Projection="Box",UpdateStrategy="OnEnabled",RenderDynamically=True,FrameInterval=5,Feathering=.05,
                ZNear=4,ZFar=6000,TintColor="1,1,1,1")]))
    info=go("Scene Information","info",components=[
        component("Sandbox.SceneInformation","info/scene",Title="Collider",Author="",Description="A research facility overlooking a working particle accelerator."),
        component("Facepunch.MapInformation","info/map",Image="ui/maps/collider.png",IsVisibleInMenu=True),
        component("Facepunch.MapSpawnSettings","info/spawns",UseMapSpawnPoints=False,AllowNavMeshSpawns=False)])
    post=go("Look","look",components=[
        component("Sandbox.PostProcessVolume","look/volume",SceneVolume={"Type":"Infinite"},EditorPreview=True,BlendWeight=1,Priority=0),
        component("Sandbox.AmbientOcclusion","look/ao",**{"__version":1},Intensity=.75,Radius=80,FalloffRange=1,ThinCompensation=5),
        component("Sandbox.Bloom","look/bloom",**{"__version":1},Mode="Additive",Strength=.15,Threshold=2.6,Tint="1,1,1,1"),
        component("Sandbox.Tonemapping","look/tone",**{"__version":3},AutoExposureEnabled=True,MinimumExposure=1.0,MaximumExposure=2.3,Mode="ACES",Rate=1)])
    sites=[]
    for i,(name,title,e0,e1,n0,n1,z) in enumerate(SITES):
        key="site/"+name
        sites.append(go("bombsite_"+name.lower(),key,position=K.to_world(((e0+e1)/2,(n0+n1)/2,z+78)),tags="zone,bombsite",components=[
            component("BombSite",key+"/site",Index=i,DamageFalloffDistance=1750,MaxBombDamage=500),
            component("Zone",key+"/zone",DisplayName=title,Color="1,0,0,1"),collider(key+"/box",(n1-n0,e1-e0,156))]))
    objectives=[go(f"{kind} {label}",f"objective/{kind}/{label}",position=K.to_world(p),components=[
        component("Facepunch.ObjectiveSpot",f"objective/{kind}/{label}/point",Kind=kind,Label=label)])
        for kind,items in (("Domination",DOM),("HotZone",HOT)) for label,p in items]
    buy=[]
    for s,team in ((-1,"Terrorist"),(1,"CounterTerrorist")):
        key=f"buy/{s}"
        buy.append(go(f"Buy {team}",key,position=K.to_world((s*1690,-200,90)),tags="zone",components=[
            component("Zone",key+"/zone",Color="1,1,1,1",DisplayName="Laboratory"),
            component("Facepunch.BuyZone",key+"/buy",Team=team),collider(key+"/box",(900,430,180))]))
    area=go("Play Area","play",position=K.to_world((0,40,400)),tags="zone",components=[
        component("Zone","play/zone",Color="1,1,1,1"),
        component("Facepunch.PlayArea","play/area",Zone={"_type":"component","component_id":IDS("play/zone"),"go":IDS("play"),"component_type":"Zone"}),
        collider("play/box",(1880,3800,900))])
    objects=[info,post,
        go("Ambient","ambient",rotation=K.angles_rotation(60,25),components=[
            component("Sandbox.DirectionalLight","ambient/light",LightColor=".05,.06,.08,1",SkyColor=".14,.18,.24,1",Shadows=True)]),
        go("Collider","world",children=world),go("Lights","lights",children=lights),
        go("Reflection Probes","probes",children=probes),
        group("Team Spawns","spawns",["Deathmatch","Gun Game","Retakes"],
            [spawn(f"Red {i+1}",f"spawn/red/{i}",p,"Terrorist") for i,p in enumerate(RED)]+
            [spawn(f"Blue {i+1}",f"spawn/blue/{i}",p,"CounterTerrorist") for i,p in enumerate(BLUE)],True),
        group("Deathmatch Spawns","spawns/dm",["Deathmatch","Gun Game"],
            [spawn(f"DM {i+1}",f"spawn/dm/{i}",p,"Unassigned","deathmatch") for i,p in enumerate(DM)]),
        group("Retakes Spawns","spawns/retakes",["Retakes"],
            [spawn(f"{site} {role} {i+1}",f"retakes/{site}/{role}/{i}",p,
                   "CounterTerrorist" if role=="attacker" else "Terrorist",f"retakes,{site},{role}")
             for site,roles in RETAKES.items() for role,points in roles.items() for i,p in enumerate(points)]),
        go("Bomb Sites","sites",children=sites),go("Buy Zones","buy",children=buy),
        go("Callouts","callouts",children=callouts()),
        group("Cash Grab","cash",["Cash Grab"],cash_points()),
        go("Objective Spots","objectives",children=objectives),area,
        go("Minimap Renderer","minimap",position=K.to_world((0,40,1500)),components=[
            component("Facepunch.MinimapRenderer","minimap/renderer",CurrentMinimapPath="ui/minimaps/minimap_collider.png",Size=4200,ExportResolution="1024,1024")]),
        K.prefab_instance(IDS,"prefabs/game_modes/team_deathmatch.prefab"),
        K.prefab_instance(IDS,"prefabs/game_modes/bomb_defusal.prefab"),
        K.prefab_instance(IDS,"scenes/maps/defusemap_01/game_setup.prefab")]
    # Preserve the reviewed native bake when regenerating source geometry and mode setup.
    indirect=ROOT/"Sources/Collider/lighting/indirect-light.json"
    if indirect.is_file(): objects.append(json.loads(indirect.read_text()))
    reflections=ROOT/"Sources/Collider/lighting/reflections.json"
    if reflections.is_file():
        saved=json.loads(reflections.read_text())
        next(obj for obj in objects if obj.get("Name")=="Reflection Probes")["Children"]=saved
    return {"__guid":IDS("scene"),"GameObjects":objects,"SceneProperties":{
        "NetworkInterpolation":True,"PhysicsMode":"Physics3D","TimeScale":1,"WantsSystemScene":True,
        "Metadata":{"Title":"Collider","Image":"ui/maps/collider.png","IsVisibleInMenu":"True",
                    "Description":"A research facility overlooking a working particle accelerator.","ZombiesOnly":False,
                    "GameModes":"prefabs/game_modes/team_deathmatch.prefab, prefabs/game_modes/bomb_defusal.prefab"},
        "NavMesh":{"Enabled":True,"IncludeStaticBodies":True,"IncludeKeyframedBodies":True,"EditorAutoUpdate":True,
            "AgentHeight":64,"AgentRadius":16,"AgentStepSize":18,"AgentMaxSlope":40,"ExcludedBodies":"zone",
            "IncludedBodies":"","DeferGeneration":False,"CustomBounds":True,
            "Bounds":{"Mins":K.vec(K.to_world((1900,-900,-30))),"Maxs":K.vec(K.to_world((-1900,980,400)))}}},
        "ResourceVersion":3,"Title":"Collider","Description":None,"__references":[],"__version":3}

def all_spots():
    return ([(f"red {i}",p) for i,p in enumerate(RED)]+[(f"blue {i}",p) for i,p in enumerate(BLUE)]
        +[(f"dm {i}",p) for i,p in enumerate(DM)]+DOM+HOT
        +[(f"{site} {role} {i}",p) for site,roles in RETAKES.items() for role,points in roles.items() for i,p in enumerate(points)]
        +[(f"cash {name}",p) for name,p,_ in CASH]+[(f"extract {name}",p) for name,_,p in CASH]
        +[(f"site {label}",((e0+e1)/2,(n0+n1)/2,z+1)) for label,_,e0,e1,n0,n1,z in SITES])

def write_check_points():
    points=[{"name":name,"position":K.to_world(p).tolist()} for name,p in all_spots()]
    (ROOT/"output/collider/check-points.json").write_text(json.dumps(points,indent=2)+"\n")

def minimap(models):
    out=STAGE/"ui/minimaps"; out.mkdir(parents=True,exist_ok=True)
    # Collision geometry determines the map rather than a decorative diagram.
    names=("MINIMAP_FILE","MINIMAP_CENTRE","MINIMAP_SIZE","G","PLAY","HALL_N1","RING_R0")
    old={name:getattr(A,name) for name in names}
    drawn=[]
    for source in models:
        model=K.Model()
        # The service corridor's ceiling is not an accessible upper gallery.
        model.boxes=[entry for entry in source.boxes if not
            (abs(entry[0][2]+entry[2][2]/2-G)<.1 and entry[2][2]<30 and entry[0][1]-entry[2][1]/2>=650)]
        model.hulls=list(source.hulls)
        drawn.append(model)
    try:
        A.MINIMAP_FILE=out/"minimap_collider.png"; A.MINIMAP_CENTRE=(0.,40.); A.MINIMAP_SIZE=4200.; A.G=G
        A.PLAY=PLAY; A.HALL_N1=PLAY[3]-60; A.RING_R0=0
        A.write_minimap(drawn)
    finally:
        for name,value in old.items(): setattr(A,name,value)

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check",action="store_true")
    args=parser.parse_args()
    models=build()
    out=STAGE/RESOURCE
    for name,m in models.items():
        count=K.write_model(out,RESOURCE,name,m)
        print(f"{name}: {count} triangles, {len(m.boxes)} collision boxes, {len(m.hulls)} hulls")
    data=scene_data()
    (STAGE/"collider.scene.json").write_text(json.dumps(data,indent=2)+"\n",encoding="utf-8")
    write_check_points()
    solid=[models[name] for name,_,collision in MODELS if collision]
    minimap(solid)
    print(f"{len(LIGHTS)} lights, {sum(1 for l in LIGHTS if l[-1])} casting shadows")
    if args.check:
        problems=R.check_spots(R.collision_aabbs(solid),all_spots())
        reach=R.check_reach(solid,all_spots(),ROOT/"output/collider/reach.png",bounds=PLAY)
        seen=R.check_retakes_sight(R.Blockers(solid),RETAKES)
        print(f"CHECK: {problems} obstructed/unsupported spots; {reach} unreachable spots; {seen} exposed Retakes pairs")
        (ROOT/"output/collider/layout-validation.json").write_text(json.dumps({
            "checked_spots":len(all_spots()),"obstructed_or_unsupported":problems,"unreachable":reach,
            "exposed_retakes_pairs":seen,"method":"Authored player bounds, collision walk graph and standing/crouching sight rays",
            "native_navmesh_verified":False},indent=2)+"\n")
        if problems or reach or seen: raise SystemExit(1)

if __name__=="__main__": main()

