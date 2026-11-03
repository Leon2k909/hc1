"""Approved central-platform station clock; render geometry only."""
import math
import numpy as np
import map_kit as K
import riverdale_parts as G
MAT="materials/railhead/clock-v1"
def model():
    m=K.Model();Z=np.array((0.,0.,1.));C=np.array((0.,1110.,240.))
    def lathe(c,axis,profile,paint,sides=64):G.lathe_axis(m,c,axis,[(float(r),float(t)) for r,t in profile],paint,sides=sides)
    def cylinder(c,axis,length,r,paint,sides=20):lathe(c,axis,[(0,0),(r,0),(r,length),(0,length)],paint,sides)
    def bolt(c,axis,r=.15,h=.09):
        cylinder(c,axis,.035,r*1.25,'steel',12);cylinder(c+axis*.035,axis,h,r,'steel',6)
    axis=np.array((0.,1.,0.))
    # Rolled housing halves with a real recessed dial seat on both faces.
    profile=[(11.08,-2.10),(11.48,-2.33),(11.93,-2.36),(12.28,-2.15),(12.4,-1.88),(12.4,1.88),(12.28,2.15),(11.93,2.36),(11.48,2.33),(11.08,2.10),(11.08,-2.10)]
    lathe(C,axis,profile,'housing',96)
    G.torus(m,C,axis,12.405,.035,'seal',seg=96,sides=6)
    for s in (-1,1):
        out=np.array((0.,float(s),0.));right=np.cross(Z,out)
        def P(u,d,z):return C+right*u+out*d+Z*z
        # Dial and seal are set behind the front retaining lip.
        lathe(C,out,[(0,1.37),(11.1,1.37),(11.1,1.55),(0,1.55)],'dial',96)
        lathe(C,out,[(11.04,1.58),(11.20,1.58),(11.20,2.1),(11.04,2.1),(11.04,1.58)],'seal',96)
        lathe(C,out,[(11.18,2.08),(11.4,2.14),(11.48,2.24),(11.4,2.30),(11.18,2.21),(11.18,2.08)],'steel',96)
        # Physically separate indices and hands retain the saved clock's 14:03 face.
        def bar(angle,r0,r1,width,depth,thickness,paint='ink',bevel=.015):
            rad=right*math.sin(angle)+Z*math.cos(angle);tan=right*math.cos(angle)-Z*math.sin(angle)
            centre=C+rad*((r0+r1)/2)+out*depth
            G.bevel_box(m,centre,(tan,rad,out),(width,r1-r0,thickness),paint,bevel=bevel)
        for minute in range(60):
            major=minute%5==0
            bar(minute*math.pi/30,7.7 if major else 9.5,10.4,.76 if major else .24,1.595,.075,bevel=.012)
        bar(math.radians(61.5),-1.1,6.95,.95,1.73,.14,bevel=.035)
        bar(math.radians(18),-1.55,9.2,.6,1.91,.14,bevel=.025)
        cylinder(P(0,1.91,0),out,.10,.54,'ink',32)
        cylinder(P(0,2.01,0),out,.035,.20,'steel',20)
        for k in range(6):
            a=k*math.pi/3+math.pi/6
            bolt(P(11.83*math.cos(a),2.34,11.83*math.sin(a)),out,.13,.07)
        # A closed, shallow convex cover, without heavy blur or tinted lettering.
        lathe(C,out,[(0,2.05),(11.12,2.05),(11.12,2.14),(8,2.20),(4,2.23),(0,2.24)],'glass',96)
    # Mounting clevis, captive pin, hanger ferrules and the ceiling flange.
    G.bevel_box(m,C+Z*13.1,(np.array((1.,0.,0.)),axis,Z),(3.2,3.0,2.2),'housing',bevel=.35)
    for s in (-1,1):bolt(C+Z*13.2+axis*s*1.52,axis*s,.32,.18)
    lathe(C,Z,[(0,13.7),(.82,13.7),(.82,15.0),(.45,15.5),(.45,29.9),(.9,29.9),(.9,30.1),(0,30.1)],'housing',32)
    lathe(C,Z,[(0,30.0),(2.2,30.0),(2.4,30.2),(2.4,30.4),(0,30.4)],'housing',48)
    for x in (-1.6,1.6):bolt(C+np.array((x,0,29.9)),-Z,.20,.12)
    m.material_overrides={name:MAT+'/'+name+'.vmat' for name in ('housing','dial','ink','steel','seal')}
    m.material_overrides['glass']='materials/railhead/rw_case_glass.vmat'
    m.tile_overrides={paint:16 for paint in m.polygons}
    return m

def append_to(target):
    m=model()
    for paint,faces in m.polygons.items():
        alias="rh_sc_"+paint
        target.material_overrides[alias]=m.material_overrides[paint]
        target.tile_overrides[alias]=m.tile_overrides[paint]
        for i,(points,normal) in enumerate(faces):
            target.polygon(alias,points,normal,uv=m.polygon_uvs.get((paint,i)),normals=m.polygon_normals.get((paint,i)))
