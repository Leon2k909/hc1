"""Formed service cabinet within the original 36 x 26 x 79 inch envelope."""
import math
import numpy as np
import map_kit as K
import riverdale_parts as P

X=P.v(1,0,0);Y=P.v(0,1,0);Z=P.v(0,0,1)
MATS={name:f'materials/spillway/service-cabinet-v1/{name[3:]}.vmat' for name in
      ('sc_body','sc_door','sc_dark','sc_rubber','sc_alloy','sc_red','sc_yellow','sc_label','sc_tag','sc_green')}

def cabinet(m,centre=(0,0,0)):
    origin=np.asarray(centre,float)
    def q(p):return origin+np.asarray(p,float)
    def b(c,size,paint='sc_body',bevel=.12):P.bevel_box(m,q(c),(X,Y,Z),size,paint,bevel)
    def rod(a,c,r,paint='sc_alloy',sides=16):P.rod(m,q(a),q(c),r,paint,sides,caps=True)
    def screw(x,y,z,face='front',r=.24):
        if face=='front':
            rod((x,y+.10,z),(x,y-.08,z),r,sides=12)
            b((x,y-.09,z),(.29,.018,.055),'sc_dark',.01)
        elif face=='right':
            rod((x-.10,y,z),(x+.08,y,z),r,sides=12)
            b((x+.09,y,z),(.018,.29,.055),'sc_dark',.01)
    # Folded enclosure and overhanging drip cap, with a recessed front closure.
    b((0,.60,42.25),(35.2,24.2,69.5),'sc_body',.30)
    b((0,-11.54,42.1),(33.0,.18,66.0),'sc_rubber',.35)
    b((0,-11.72,42.1),(32.15,.45,65.25),'sc_door',.22)
    b((0,0,77.8),(36,26,2.4),'sc_body',.28)
    b((0,-12.72,76.8),(35.3,.5,.45),'sc_alloy',.09)
    # Open fabricated base, with bolted feet and bottom gland plate.
    for x in (-15.8,15.8):
        b((x,0,3.6),(1.7,23.4,6.8),'sc_dark',.15)
        for y in (-9.7,9.7):
            b((x,y,.85),(3.8,5.0,1.7),'sc_alloy',.14)
            rod((x,y,1.70),(x,y,2.02),.40,sides=6)
    for y in (-10.8,10.8):b((0,y,2.5),(30,1.5,4.5),'sc_dark',.10)
    b((0,0,7.8),(32.8,22.4,.7),'sc_alloy',.12)
    for x in (-9,0,9):
        profile=[(.70,4.2),(.88,4.5),(.88,5.8),(1.10,5.8),(1.10,6.5),(.72,6.5),(.72,8.2)]
        for j in range(len(profile)-1):
            r0,z0=profile[j];r1,z1=profile[j+1]
            P.lathe(m,(origin[0]+x,origin[1]-6),[(r0,origin[2]+z0),(r1,origin[2]+z1)],'sc_alloy',16)
        P.cylinder(m,(origin[0]+x,origin[1]-6),1.22,origin[2]+6,origin[2]+6.6,'sc_alloy',6,top='sc_alloy')
        rod((x,-6,1.8),(x,-6,4.4),.45,'sc_rubber',12)
    # Three captured hinges, pin ends and separate mounting leaves.
    for z in (18,42,67):
        b((-15.7,-11.90,z),(2.25,.25,5.0),'sc_alloy',.10)
        rod((-16.0,-12.0,z-2.6),(-16.0,-12.0,z+2.6),.56,sides=20)
        for h in (-1.75,0,1.75):
            P.torus(m,q((-16.0,-12.0,z+h)),Z,.57,.055,'sc_dark',20,5)
        for dz in (-1.55,1.55):screw(-14.95,-12.055,z+dz,r=.20)
    # Raised pull handle, black grip and a separate key barrel.
    for z in (35.8,47.0):
        b((12.0,-12.03,z),(1.9,.30,1.65),'sc_alloy',.22)
        rod((12.0,-12.10,z),(12.0,-12.57,z),.25)
        screw(12.0,-12.22,z,r=.20)
    rod((12,-12.57,35.8),(12,-12.57,47),.27)
    rod((12,-12.57,37.3),(12,-12.57,45.5),.43,'sc_rubber',20)
    rod((12,-11.96,31.8),(12,-12.20,31.8),.61,sides=24)
    b((12,-12.215,31.8),(.065,.025,.49),'sc_dark',.015)
    # Rotary isolation switch, yellow guard and witness marks.
    b((-6,-12.03,48.3),(4.8,.35,4.8),'sc_yellow',.32)
    rod((-6,-12.05,48.3),(-6,-12.4,48.3),1.35,'sc_dark',24)
    r=P.unit((.58,0,.82));up=P.unit(np.cross(r,Y))
    P.bevel_box(m,q((-6,-12.61,48.3)),(r,Y,up),(3.75,.52,.85),'sc_red',.22)
    b((-6,-12.025,51.8),(5.5,.12,1.5),'sc_dark',.06)
    P.card(m,'sc_tag',[q((-8.6,-12.09,51.15)),q((-3.4,-12.09,51.15)),q((-3.4,-12.09,52.45)),q((-8.6,-12.09,52.45))],-Y,
           uv=[(0,0),(1,0),(1,1),(0,1)])
    # Flush engraved equipment plate, with an explicitly mapped label.
    b((-3.8,-12.01,64),(17.2,.24,9.8),'sc_alloy',.15)
    P.card(m,'sc_label',[q((-11.6,-12.15,59.6)),q((4.0,-12.15,59.6)),q((4.0,-12.15,68.4)),q((-11.6,-12.15,68.4))],-Y,
           uv=[(0,0),(1,0),(1,1),(0,1)])
    for x in (-11.9,4.3):
        for z in (59.55,68.45):screw(x,-12.16,z,r=.16)
    # Two small pilot lenses and individual bezels.
    for x,paint in ((7.6,'sc_green'),(11.8,'sc_red')):
        rod((x,-11.99,66),(x,-12.15,66),.79,'sc_alloy',24)
        rod((x,-12.16,66),(x,-12.38,66),.57,paint,24)
    # Hooded lower louvres. Actual angled metal blades sit over a dark recess.
    b((-1,-12.01,21.3),(26.4,.16,12.8),'sc_dark',.15)
    for x in (-14.45,12.45):b((x,-12.05,21.3),(1.0,.24,13.8),'sc_door',.10)
    for z in (14.5,28.1):b((-1,-12.05,z),(27.0,.25,.85),'sc_door',.10)
    for z in np.linspace(15.7,26.7,8):
        pts=[q((-13.9,-12.45,z-.42)),q((11.9,-12.45,z-.42)),q((11.9,-11.98,z+.48)),q((-13.9,-11.98,z+.48))]
        P.card(m,'sc_door',pts,(0,-1,1))
        for x in (-13.9,11.9):P.card(m,'sc_body',[q((x,-12.45,z-.42)),q((x,-11.98,z+.48)),q((x,-11.98,z-.42))],(-1 if x<0 else 1,0,0))
    for x in (-14.45,12.45):
        for z in (15.2,27.4):screw(x,-12.20,z,r=.18)
    # Side access vent and visible fasteners.
    b((17.62,4,59),(.18,11.3,14.0),'sc_dark',.08)
    for z in np.linspace(53.2,64.8,8):
        P.card(m,'sc_body',[q((17.95,-1.1,z-.4)),q((17.95,9.1,z-.4)),q((17.70,9.1,z+.4)),q((17.70,-1.1,z+.4))],(1,0,1))
    for y in (-2.1,10.1):
        for z in (51.5,66.5):screw(17.71,y,z,'right',.20)
    # Quiet chips confined to the lower door edge and the handled side.
    for x,z,w in ((-12.5,10.0,1.2),(-11.0,9.7,.50),(9.5,9.7,.7),(14.3,37,.35)):
        b((x,-11.952,z),(w,.012,.065),'sc_alloy',.01)
    for paint,path in MATS.items():
        m.material_overrides[paint]=path
        m.tile_overrides[paint]=18
    return m

def model():return cabinet(K.Model())
