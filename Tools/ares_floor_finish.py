"""Generated Ares floor plates. Render geometry only; floor collision stays at z0."""
import numpy as np
import map_kit as K
import riverdale_parts as P
X=np.array((1.,0.,0.));Y=np.array((0.,1.,0.));Z=np.array((0.,0.,1.))
FLOOR='ar_in_floor';DARK='ar_in_dark'
def box(m,c,size,paint,b):P.bevel_box(m,c,(X,Y,Z),size,paint,b)
def floor(m):
    # Human-scale manufactured deck panels with eased edges. All tops remain at
    # the original floor height and the solid collision floor remains intact.
    P.card(m,DARK,[(-1100,-720,-.85),(1100,-720,-.85),(1100,720,-.85),(-1100,720,-.85)],Z)
    for ie in range(28):
        for jn in range(18):
            e0=-1100+2200*ie/28;n0=-720+80*jn
            w=2200/28-.7;h=79.3;c=np.array((e0+2200/56,n0+40,-.5))
            first=len(m.polygons[FLOOR]);box(m,c,(w,h,1),FLOOR,.24)
            # Rotate the same coordinated texture to avoid rows of identical
            # scuffs. The four normal-map fasteners stay at each panel's corners.
            turn=(ie+jn*3)%4
            for index in range(first,len(m.polygons[FLOOR])):
                pts,normal=m.polygons[FLOOR][index]
                if normal[2]<.99:continue
                uv=[]
                for p in pts:
                    u=(p[0]-c[0])/w+.5;v=(p[1]-c[1])/h+.5
                    for k in range(turn):u,v=1-v,u
                    uv.append((u,v))
                m.polygon_uvs[(FLOOR,index)]=uv
