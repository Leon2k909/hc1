"""Ares pressure-hall architecture from the approved November 2026 concept.

All additions are render geometry. Existing navigation, doors and collision stay
with the original hall. Dimensions are authored in plan (east, north, up), inches.
"""
import math
import numpy as np
import map_kit as K
import riverdale_parts as P

X=np.array((1.,0.,0.));Y=np.array((0.,1.,0.));Z=np.array((0.,0.,1.))
PANEL='ar_in_panel'; FRAME='ar_in_frame'; RED='ar_in_red'
ALLOY='ar_in_alloy'; DARK='ar_in_dark'; FLOOR='ar_in_floor'
MATERIALS={p:f'materials/ares/interior-v1/{p[6:]}.vmat' for p in (PANEL,FRAME,RED,ALLOY,DARK,FLOOR)}

MATERIALS[FLOOR]='materials/ares/floor-finish-v4/plate.vmat'
MATERIALS['ar_floor']='materials/ares/floor-finish-v4/grip.vmat'

def configure(m):
    for paint,path in MATERIALS.items():
        if paint in m.polygons:
            m.material_overrides[paint]=path
            m.tile_overrides[paint]=80. if paint in (FLOOR,'ar_floor') else 96. if paint==PANEL else 48.
    return m

def box(m,c,size,paint=PANEL,bevel=.3,axes=(X,Y,Z)):
    P.bevel_box(m,np.asarray(c,float),axes,size,paint,bevel)

def bolt(m,c,axis,r=.5):
    P.lathe_axis(m,c,axis,[(r,0),(r,.22),(r*.8,.35),(0,.35)],ALLOY,6)

def ribbon(m,path,across,width,depth,paint=PANEL,bevel=1.):
    """Continuous chamfered rectangular section along a planar structural curve."""
    path=[np.asarray(p,float) for p in path];across=K.normalise(across)
    w,d=width/2,depth/2;b=min(bevel,w*.4,d*.4)
    section=[(w-b,d),(w,d-b),(w,-d+b),(w-b,-d),(-w+b,-d),(-w,-d+b),(-w,d-b),(-w+b,d)]
    rings=[];normals=[]
    for i,p in enumerate(path):
        tangent=K.normalise(path[min(i+1,len(path)-1)]-path[max(i-1,0)])
        normal=K.normalise(np.cross(tangent,across))
        rings.append([p+across*a+normal*c for a,c in section])
        normals.append(normal)
    for i in range(len(path)-1):
        for k in range(8):
            j=(k+1)%8
            a=(section[k][0]+section[j][0])/2;c=(section[k][1]+section[j][1])/2
            n0=K.normalise(across*a+normals[i]*c)
            n1=K.normalise(across*a+normals[i+1]*c)
            P.card(m,paint,[rings[i][k],rings[i][j],rings[i+1][j],rings[i+1][k]],n0+n1,normals=[n0,n0,n1,n1])
    P.card(m,paint,rings[0],path[0]-path[1]);P.card(m,paint,rings[-1],path[-1]-path[-2])

def bezier(a,b,c,d,steps=8):
    return [(1-t)**3*np.asarray(a)+3*(1-t)**2*t*np.asarray(b)+3*(1-t)*t*t*np.asarray(c)+t**3*np.asarray(d)
            for t in np.linspace(0,1,steps+1)]

def portal(m,e):
    # Feet seat on the perimeter galleries; the leaned north foot follows the
    # existing window mullion. All curves are well above player head clearance.
    path=[(e,-721,208),(e,-721,490)]
    path+=bezier((e,-721,490),(e,-721,605),(e,-650,686),(e,-530,686))[1:]
    path+=[(e,635,686)]
    path+=bezier((e,635,686),(e,765,686),(e,849,629),(e,846,556))[1:]
    path+=[(e,759,208)]
    ribbon(m,path,X,30,30,PANEL,1.7)
    # A dark inset spine gives the pressure frame thickness without clutter.
    ribbon(m,[np.asarray(p)+X*15.7 for p in path],X,2.1,18,FRAME,.5)
    ribbon(m,[np.asarray(p)-X*15.7 for p in path],X,2.1,18,FRAME,.5)
    for nn,zz in ((-721,398),(-721,430)):
        box(m,(e,nn,zz),(34,34,13),RED,1.0)
        for side in (-1,1):
            bolt(m,np.array((e+side*17.1,nn-8,zz)),X*side,.72)
    box(m,(e,759,229),(36,34,40),FRAME,1.3)

def side_haunch(m,side,n):
    path=[(side*1094,n,208),(side*1094,n,510)]
    path+=bezier((side*1094,n,510),(side*1094,n,620),(side*1042,n,690),(side*930,n,690))[1:]
    ribbon(m,path,Y,32,18,PANEL,1.3)
    for sign in (-1,1):
        ribbon(m,[np.asarray(p)+Y*sign*16.5 for p in path],Y,1.6,14,FRAME,.45)
    box(m,(side*1088,n,436),(25,36,40),RED,1.1)

def wall_panels(m):
    # Thin skins remain behind the existing wall signs and door hardware. Deep
    # reveals come from the haunches and service frames, not blocked doorways.
    for side in (-1,1):
        inward=-side*X
        for n0,n1 in ((-716,-606),(-594,-156),(-144,294),(306,715)):
            w=n1-n0
            if w<100:continue
            c=np.array((side*1099.65,(n0+n1)/2,536.))
            box(m,c,(.50,w-5,323),DARK,.10)
            box(m,c+inward*.34,(.28,w-8,319),PANEL,.12)
            # Shallow access-panel joints sit behind the original posters.
            for zz in (420,531,642):
                box(m,(side*1099.24,(n0+n1)/2,zz),(.16,w-20,1.05),FRAME,.06)
                for nn in (n0+13,n1-13):
                    bolt(m,np.array((side*1099.16,nn,zz+8)),inward,.42)
            # Vertical frame channels, kept clear of both posters.
            for nn in (n0+2,n1-2):
                box(m,(side*1098.2,nn,536),(2.1,2.0,323),FRAME,.3)
            for nn in (n0+11,n1-11):
                for zz in (389,682):bolt(m,np.array((side*1098.9,nn,zz)),inward,.55)
        # Continue the pressure skin down to gallery level around the two door
        # openings. Its front stays behind signs, lamps and doorway trim.
        for n0,n1 in ((-716,-426),(-254,570),(710,716)):
            if n1-n0<12:continue
            box(m,(side*1099.55,(n0+n1)/2,282),(.58,n1-n0-2,146),PANEL,.20)
            for nn in np.arange(n0+72,n1-8,144):
                box(m,(side*1099.17,nn,282),(.14,.9,135),FRAME,.05)
        # Lower maintenance panels only in the blank south bays; all established
        # entrances and the control-room consoles remain uncovered.
        for nn in (-635,-205):
            box(m,(side*1098.2,nn,98),(3.2,104,130),FRAME,.8)
            box(m,(side*1096.3,nn,98),(.6,96,120),PANEL,.25)
            for zz in (66,72,78,84):
                box(m,(side*1095.8,nn,zz),(.5,72,2.0),DARK,.2)
            box(m,(side*1094.9,nn+34,132),(1.3,3,18),ALLOY,.5)

def fascia(m,a,b,out):
    a,b=np.asarray(a,float),np.asarray(b,float);along=K.normalise(b-a)
    length=float(np.linalg.norm(b-a));out=K.normalise(out)
    frame=(along,out,Z)
    if np.dot(np.cross(along,out),Z)<0:frame=(-along,out,Z)
    box(m,(a+b)/2+out*.7+Z*199,(length,1.8,15),FRAME,.5,frame)
    count=max(1,int(length/165))
    for k in range(count):
        c=a+(b-a)*(k+.5)/count+out*1.9+Z*199
        box(m,c,(length/count-6,.65,10.5),PANEL,.25,frame)
        # Small recessed lower seam, rather than a continuous warning band.
        box(m,c-Z*3.5+out*.4,(length/count-18,.3,1.1),DARK,.1,frame)

def galleries(m):
    fascia(m,(-880,560,0),(880,560,0),(0,-1,0))
    fascia(m,(-880,-540,0),(880,-540,0),(0,1,0))
    for side in (-1,1):
        for n0,n1 in ((-540,-470),(-158,-80),(80,560)):
            fascia(m,(side*880,n0,0),(side*880,n1,0),(-side,0,0))
        for n in (-340,570):
            box(m,(side*890,n,173),(17.6,17.6,26),RED,.9)
    for n in (-550,570):
        for e in (-600,-300,300,600):
            box(m,(e,n,174),(17.4,17.4,24),RED,.9)
    # Formed brackets below the north/south gallery edges, aligned with existing
    # columns; no floor-level collision or sightline changes.
    for n,sign in ((560,-1),(-540,1)):
        for e in (-600,-300,300,600):
            path=[(e,n-sign*10,144),(e,n+sign*23,181),(e,n+sign*23,190)]
            ribbon(m,path,X,7,7,FRAME,.6)

def service_runs(m):
    for side in (-1,1):
        e=side*700
        P.rod(m,(e,-610,660),(e,788,660),16.0,ALLOY,24,caps=True)
        for n in range(-550,780,170):
            P.lathe_axis(m,(e,n,660),Y,[(16.1,-3),(17.6,-2),(17.6,2),(16.1,3)],RED,24)
            # Suspended steel straps tie the duct into the existing roof slab.
            for off in (-22,22):
                P.rod(m,(e+off,n,680),(e+off,n,711),1.0,ALLOY,6,caps=True)
            box(m,(e,n,679),(53,7,4),FRAME,.6)
        # Segmented open service tray beside the duct, with readable cable runs.
        te=e+side*54
        for n in range(-620,780,92):
            box(m,(te,n+43,686),(37,84,3),FRAME,.6)
            for off in (-17,17):box(m,(te+off,n+43,692),(2,86,12),FRAME,.4)
            for off in (-10,-2,6,13):
                P.rod(m,(te+off,n,689),(te+off,n+86,689),1.0,RED if off in (-10,6) else DARK,6)

def work_lights(m):
    # Same 24 light origins as ares_map.lights(): fixtures are replaced, the
    # scene gains no lights, shadow maps or additional per-frame lighting work.
    for e in (-900,-600,-300,300,600,900):
        for n in (-450,-50,350,700):
            box(m,(e,n,626),(14,90,6),FRAME,.75)
            P.card(m,'ar_led_warm',[(e-4.5,n-40,622.8),(e-4.5,n+40,622.8),(e+4.5,n+40,622.8),(e+4.5,n-40,622.8)],-Z)
            for offset in (-31,31):
                P.rod(m,(e,n+offset,629),(e,n+offset,711),.65,ALLOY,6,caps=True)
                box(m,(e,n+offset,712),(10,5,3),FRAME,.35)

def outer_floor(m):
    for e0,e1 in ((-2032,-1100),(1100,2032)):
        P.card(m,'ar_floor',[(e0,-752,0),(e1,-752,0),(e1,720,0),(e0,720,0)],Z)
    P.card(m,'ar_floor',[(-1100,-752,0),(1100,-752,0),(1100,-720,0),(-1100,-720,0)],Z)

def floor(m):
    from ares_floor_finish import floor as draw_floor
    return draw_floor(m)


def append_hall(m):
    wall_panels(m)
    for e in (-900,-500,500,900):portal(m,e)
    for side in (-1,1):
        for n in (-600,-150,300):side_haunch(m,side,n)
    galleries(m);service_runs(m);work_lights(m);floor(m)
    configure(m)

def pump_unit(m,e,n,heading):
    """Formed process-pump casing inside the original 72 x 56 x 64 envelope."""
    import ares_map as A
    F=A.Frame(e,n,heading)
    xx=K.normalise(F.p(1,0,0)-F.p(0,0,0));yy=K.normalise(F.p(0,1,0)-F.p(0,0,0))
    axes=(xx,yy,Z)
    F.box(m,-36,36,-28,28,0,64,{'default':None},A.METAL)
    def bb(c,size,paint=PANEL,bevel=1.):box(m,F.p(*c),size,paint,bevel,axes)
    bb((0,0,4),(71.8,55.8,8),FRAME,1.4)
    bb((0,0,35),(71.7,55.7,58),PANEL,5.0)
    bb((0,0,11),(70,55.9,8),RED,1.)
    # The vent insert and separate service cover give the housing a purpose.
    bb((13,-27.88,31),(35,.3,31),DARK,.14)
    for z in range(20,45,4):bb((13,-28.05,z),(31,.25,1.4),ALLOY,.1)
    bb((-21,-27.95,33),(22,.35,30),FRAME,.15)
    uv=[A.AM.region_uv(A.AM.SCREEN,A.AM.SCREEN_ATLAS,'screen6',s,t) for s,t in ((0,0),(1,0),(1,1),(0,1))]
    P.quad(m,'ar_screens',F.p(-21,-28.2,35),xx,Z,18,21,uv)
    for x in (-31,31):
        for z in (17,53):bolt(m,F.p(x,-27.98,z),-yy,.65)
    for x in (-20,20):
        P.lathe_axis(m,F.p(x,0,61),Z,[(8,0),(8,2.5),(6,3)],FRAME,16)
        a=F.p(x,0,64);b=F.p(x,0,150)
        towards=K.normalise(np.array((-e,-n,0.)))
        c=b+towards*(math.hypot(e,n)-A.RING_R0+4)
        P.tube(m,[a,b,c],6.0,ALLOY,16,bend_radius=18)
        for point,axis in ((a+Z*8,Z),(c-towards*8,towards)):
            P.lathe_axis(m,point,axis,[(6.1,-2),(8.5,-1),(8.5,1),(6.1,2)],RED,16)
    configure(m)
