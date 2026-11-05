import math
import numpy as np
import map_kit as K
import riverdale_parts as G
MAT="materials/riverside/shelving-v1"
X=np.array((1.,0,0));Y=np.array((0.,-1,0));Z=np.array((0.,0,1.))
def p(x,d,z):return X*x+Y*d+Z*z
def model(lod=0):
    m=K.Model();sides=(12,8,6)[lod]
    def box(c,sz,paint,b=.07):G.bevel_box(m,p(*c),(X,Y,Z),sz,paint,bevel=b if lod<2 else .001)
    def panel(c,right,up,w,h,paint):
        c=np.asarray(c);a=np.asarray(right)*w/2;b=np.asarray(up)*h/2
        m.polygon(paint,[c-a-b,c+a-b,c+a+b,c-a+b],np.cross(a,b),uv=[(0,0),(1,0),(1,1),(0,1)])
    def can(cx,depth,z,variant):
        label=f'label{variant}';start=len(m.polygons[label]);center=p(cx,depth,z)
        profile=[(0,0),(1.18,0),(1.28,.15),(1.28,.28),(1.23,.28),(1.23,4.35),(1.28,4.46),(1.28,4.60),(0,4.60)]
        G.lathe_axis(m,center,Z,profile,['steel','steel','steel','steel',label,'steel','steel','steel'],sides=sides)
        for index in range(start,len(m.polygons[label])):
            points,_=m.polygons[label][index];angles=[(math.atan2(q[0]-center[0],-(q[1]-center[1]))/(2*math.pi)+.5+(.5 if depth<0 else 0))%1 for q in points]
            if max(angles)-min(angles)>.5:angles=[a+1 if a<.5 else a for a in angles]
            m.polygon_uvs[(label,index)]=[(u,(q[2]-z-.28)/4.07) for u,q in zip(angles,points)]
        if lod==0:box((cx,depth,z+4.63),(.42,.70,.055),'steel',.06)
    def carton(cx,depth,z,variant,side):
        label=f'box{variant}';start=len(m.polygons[label]);height=7.65 if variant==0 else 6.8
        G.bevel_box(m,p(cx,depth,z+height/2),(X,Y,Z),(4.8,2.8,height),{'default':'cardboard',('+y' if side>0 else '-y'):label},bevel=.06 if lod<2 else .001)
        for index in range(start,len(m.polygons[label])):
            pts,_=m.polygons[label][index]
            m.polygon_uvs[(label,index)]=[((q[0]-cx)/4.8*side+.5,(q[2]-z)/height) for q in pts]
    # Two-sided steel gondola, solid center sheet, feet, adjustable shelf brackets.
    box((0,0,3.1),(69,35.5,5.4),'paint',.20)
    box((0,0,.55),(66.6,33.6,1.1),'rubber',.12)
    box((0,0,30.3),(66,.40,50.6),'paint',.09)
    for cx in (-33.3,33.3):
        box((cx,0,28),(1.2,2.2,56),'paint',.12)
        if lod<2:
            for zz in range(10,54,4):
                for side in (-1,1):box((cx,side*1.11,zz),(.24,.028,.9),'rubber',.02)
    for level,z in enumerate((5.7,19.7,33.7,47.7)):
        for side in (-1,1):
            box((0,side*9.0,z),(66,16.6,.58),'paint',.09)
            box((0,side*17.44,z-.05),(66,.45,1.18),'paint',.07)
            panel(p(0,side*17.685,z-.05),X*side,Z,65.6,.85,'prices')
            if lod<2:
                for cx in (-31.9,31.9):box((cx,side*8.9,z-.72),(.30,15.7,1.25),'paint',.07)
            for col,cx in enumerate(np.linspace(-28.5,28.5,8)):
                if (level,col,side) in [(1,2,1),(2,5,-1),(3,7,1),(0,6,-1)]:continue
                kind=(col+level)%3
                if kind==0:carton(float(cx),side*12.8,z+.30,(col+level)%2,side)
                else:can(float(cx),side*12.8,z+.30,(col+level)%4)
            if lod<2:
                for col,cx in enumerate((-24.,-8.,8.,24.)):
                    if level==3 and col==2:continue
                    can(cx,side*6.5,z+.30,(col+level+1)%4)
    for paint,polys in m.polygons.items():
        for index,(pts,normal) in enumerate(polys):
            if (paint,index) in m.polygon_uvs:continue
            if abs(normal[2])>.6:uv=[((q[0]+35)/70,(-q[1]+18)/36) for q in pts]
            elif abs(normal[0])>.7:uv=[((-q[1]+18)/36,q[2]/56) for q in pts]
            else:uv=[((q[0]+35)/70,q[2]/56) for q in pts]
            m.polygon_uvs[(paint,index)]=uv
    m.material_overrides={paint:MAT+'/'+paint+'.vmat' for paint in m.polygons};m.tile_overrides={paint:48 for paint in m.polygons}
    return m