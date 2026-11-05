"""Approved Riverside camper exterior. Pure geometry; collision/propane stay in the map."""
import math
import numpy as np
import map_kit as K
import riverdale_parts as G
import riverside_parts as P
MAT='materials/riverside/camper_v2'
X=np.array((1.,0.,0.));Y=np.array((0.,1.,0.));Z=np.array((0.,0.,1.))
def make(lod):
    m=K.Model();n=(40,24,12)[lod]
    def box(c,size,paint='shell',b=.12,axes=(X,Y,Z)):
        if b and lod<2:G.bevel_box(m,np.array(c,float),axes,size,paint,bevel=b)
        else:m.oriented_box(np.array(c,float),axes,size,paint)
    def face(pts,normal,paint='shell',uv=None):G._face(m,paint,[np.array(p,float) for p in pts],towards=np.array(normal,float),uv=uv)
    def rod(a,b,r=.2,paint='trim',sides=None):G.tube(m,[np.array(a,float),np.array(b,float)],r,paint,sides=sides or (8,6,4)[lod])
    def cyl(c,axis,r,length,paint='trim',sides=None):G.lathe_axis(m,np.array(c,float),axis,[(0,0),(r,0),(r,length),(0,length)],paint,sides=sides or (16,10,6)[lod])
    def screw(c,axis):
        if lod<2:cyl(c,axis,.16,.07,'trim',8)
    def strip(a,b,width,depth,paint='trim'):
        a,b=np.array(a,float),np.array(b,float);along=b-a;length=np.linalg.norm(along);along/=length
        right=np.cross(along,Z if abs(along[2])<.9 else Y);right/=np.linalg.norm(right);up=np.cross(along,right)
        box((a+b)*.5,(length,width,depth),paint,.06,(along,right,up))
    # Formed body: radiused end corners, actual folded horizontal siding, and a curved roof shoulder.
    xs=np.array((-160,-159,-154,-136,-112,-80,-45,-36,-30,-20,-10,-4,8,40,72,110,134,142,150,157,160),float)
    if lod==2:xs=np.array((-160,-154,-80,-36,-20,-4,72,142,150,160),float)
    def width(x):return float(np.interp(x,(-160,-159,-154,142,150,157,160),(42,45,48,48,46,39,30)))
    rows={26.,28.,30.,54.3,55.7,57.75,62.25,110.}
    if lod<2:
        for z in np.arange(28,110,6):rows.update((float(z),float(z+.48),float(min(z+1.0,110))))
    rows=sorted(rows)
    def ridge(z):
        t=(z-28)%6
        return .20*max(0,1-abs(t-.48)/.53) if lod<2 else 0.
    for side in (-1,1):
        for xa,xb in zip(xs,xs[1:]):
            for za,zb in zip(rows,rows[1:]):
                midx=(xa+xb)*.5;midz=(za+zb)*.5
                # A small real wheel cutout sits beneath its formed fender.
                if abs(midx+20)<17 and midz<13+math.sqrt(max(0,17**2-(midx+20)**2)):continue
                paint='stripe' if 54.3<midz<55.7 or 57.75<midz<62.25 else 'shell'
                pts=[(xa,side*(width(xa)+ridge(za)),za),(xb,side*(width(xb)+ridge(za)),za),
                     (xb,side*(width(xb)+ridge(zb)),zb),(xa,side*(width(xa)+ridge(zb)),zb)]
                face(pts,(0,side,0),paint,[( (p[0]+160)/96,(p[2]-22)/96) for p in pts])
        angles=np.linspace(0,math.pi/2,(9,6,4)[lod])
        for xa,xb in zip(xs,xs[1:]):
            for a,b in zip(angles,angles[1:]):
                pts=[(xa,side*(width(xa)-8+8*math.cos(a)),110+8*math.sin(a)),
                     (xb,side*(width(xb)-8+8*math.cos(a)),110+8*math.sin(a)),
                     (xb,side*(width(xb)-8+8*math.cos(b)),110+8*math.sin(b)),
                     (xa,side*(width(xa)-8+8*math.cos(b)),110+8*math.sin(b))]
                face(pts,(0,side*math.cos((a+b)/2),math.sin((a+b)/2)))
        # Rolled roof rail and bottom extrusion replace painted edge strips.
        rail=[(float(x),side*(width(x)-.05),109.5) for x in xs]
        G.tube(m,[np.array(p) for p in rail],.42,'trim',sides=(8,6,4)[lod])
        for a,b in zip(rail,rail[1:]):
            rod((a[0],a[1],26.4),(b[0],b[1],26.4),.35)
        if lod==0:
            for x in np.arange(-145,140,18):
                for z in (28,108.5):screw((x,side*(width(x)+.3),z),Y*side)
    for xa,xb in zip(xs,xs[1:]):
        face([(xa,-width(xa)+8,118),(xb,-width(xb)+8,118),(xb,width(xb)-8,118),(xa,width(xa)-8,118)],Z)
    for end in (-160,160):
        w=width(end);out=X*np.sign(end)
        for za,zb in zip(rows,rows[1:]):
            z=(za+zb)*.5;paint='stripe' if 54.3<z<55.7 or 57.75<z<62.25 else 'shell'
            face([(end,-w,za),(end,w,za),(end,w,zb),(end,-w,zb)],out,paint)
        pts=[(end,-w,110),(end,w,110)]+[(end,w-8+8*math.cos(a),110+8*math.sin(a)) for a in np.linspace(0,math.pi/2,9)]+[(end,-w+8,118)]+[(end,-w+8-8*math.cos(a),110+8*math.sin(a)) for a in np.linspace(math.pi/2,0,9)]
        face(pts,out)
    box((-4,0,24),(308,86,4),'chassis',.4)
    # Chassis, crossmembers, leaf springs and axle stay within the old trailer footprint.
    for side in (-1,1):
        box((-5,side*28,18),(306,3.2,6),'chassis',.25)
        for leaf in range((4,3,1)[lod]):
            points=[(-45+50*t,side*29,10.5+leaf*.24+3*(2*t-1)**2) for t in np.linspace(0,1,9)]
            for a,b in zip(points,points[1:]):strip(a,b,1.9,.18,'chassis')
    for x in (-130,-65,0,65,128):box((x,0,19),(3.2,65,4),'chassis',.12)
    rod((-20,-44,13),(-20,44,13),1.2,'chassis')
    # Formed tyres with tread blocks, recessed steel wheels, hub caps and individual lug nuts.
    def wheel(center,axis,diameter=26,wide=8):
        c=np.array(center,float);axis=np.array(axis,float);axis/=np.linalg.norm(axis);r=diameter*.5
        prof=[(r*.55,-wide*.5),(r*.82,-wide*.5),(r*.94,-wide*.42),(r,-wide*.27),(r,wide*.27),(r*.94,wide*.42),(r*.82,wide*.5),(r*.55,wide*.5),(r*.55,-wide*.5)]
        G.lathe_axis(m,c,axis,prof,'rubber',sides=n)
        for side in (-1,1):
            a=axis*side;at=c+a*(wide*.44)
            G.lathe_axis(m,at,a,[(0,-.8),(r*.38,-.8),(r*.55,-.25),(r*.59,.2),(r*.51,.55),(r*.35,.66),(0,.66)],'wheel',sides=n)
            G.torus(m,at+a*.2,a,r*.57,.12,'trim',seg=n,sides=5)
            cyl(at+a*.66,a,r*.20,.8,'trim')
            e1,e2=G.perp(a)
            for angle in np.linspace(0,2*math.pi,6,endpoint=False):
                p=at+a*.65+(e1*math.cos(angle)+e2*math.sin(angle))*r*.30
                cyl(p,a,.33,.32,'chassis',6)
        if lod<2:
            e1,e2=G.perp(axis)
            for angle in np.linspace(0,2*math.pi,(40,24)[lod],endpoint=False):
                radial=e1*math.cos(angle)+e2*math.sin(angle);tangent=np.cross(axis,radial)
                for offset in (-wide*.25,wide*.25):
                    box(c+radial*(r-.04)+axis*offset,(.8,wide*.40,.22),'rubber',0,(tangent,axis,radial))
    for side in (-1,1):
        wheel((-20,side*44,13),Y)
        # Pressed curved wheel arch, with a raised lip and mounting screws.
        angles=np.linspace(0,math.pi,(25,15,9)[lod])
        for a,b in zip(angles,angles[1:]):
            for r0,r1 in ((15.6,17.2),(17.2,17.7)):
                yy=side*(48.2 if r0<17 else 48.7)
                face([(-20+r0*math.cos(a),yy,13+r0*math.sin(a)),(-20+r0*math.cos(b),yy,13+r0*math.sin(b)),
                      (-20+r1*math.cos(b),yy,13+r1*math.sin(b)),(-20+r1*math.cos(a),yy,13+r1*math.sin(a))],Y*side,'trim')
        for x in (-37.5,-2.5):screw((x,side*48.8,18),Y*side)
    # Deep framed windows with glass, seals and separate split, uneven boarding.
    def side_window(x,side,w,h,z=84):
        yy=side*48.5
        box((x,yy,z),(w+3,.8,h+3),'seal',.35)
        box((x,yy+side*.4,z),(w, .25,h),'seal',.4)
        box((x,yy+side*.65,z),(w-.9,.10,h-.9),'glass',.2)
        for dz in (-h*.5-.55,h*.5+.55):box((x,yy+side*.9,z+dz),(w+2.1,.7,1.1),'trim',.18)
        for dx in (-w*.5-.55,w*.5+.55):box((x+dx,yy+side*.9,z),(1.1,.7,h),'trim',.18)
        for row in range(3):
            length=w+8+(row%2)*3;zz=z+(row-1)*h*.34;angle=(-.035,.018,-.012)[row]
            along=np.array((math.cos(angle),0,math.sin(angle)));up=np.cross(along,Y*side)
            if up[2]<0:up=-up
            box((x+(row-1)*.5,yy+side*(1.45+.17*row),zz),(length,.60,h*.28),'wood',.11,(along,Y,up))
            if lod<2:
                for dx in (-w*.40,w*.40):screw((x+dx,yy+side*(1.82+.17*row),zz),Y*side)
        if lod==0:
            # A short splinter points past one board's cut edge.
            face([(x-w*.5-4,yy+side*1.8,z-h*.22),(x-w*.5-7,yy+side*1.85,z-h*.18),(x-w*.5-4,yy+side*1.8,z-h*.14)],Y*side,'wood')
    for side in (-1,1):
        for x,w,h in ((100,46,28),(20,30,26),(-90,48,28)):side_window(x,side,w,h)
    # Front window, inset between radiused corners, boarded with real planks.
    box((160.4,0,78),(1.1,52,32),'seal',.6)
    box((161.1,0,78),(.12,48,28),'glass',.2)
    for yy in (-25.4,25.4):box((161.3,yy,78),(.6,1.1,31),'trim',.12)
    for zz in (62.6,93.4):box((161.3,0,zz),(.6,52,1.1),'trim',.12)
    for row in range(3):box((161.7+row*.15,0,78+(row-1)*10),(.6,60,8.3),'wood',.10)
    # Separate entry door with recessed pane, moulded surround, hinges and latch.
    yy=-48.8;cx=-40
    box((cx,yy,62),(28.2,1.6,74),'seal',1.4)
    box((cx,yy-.65,62),(26.2,1.25,72),'shell',.7)
    for dx in (-13.6,13.6):box((cx+dx,yy-.9,62),(1.0,.8,73),'trim',.15)
    for zz in (25.5,98.5):box((cx,yy-.9,zz),(28,.8,1.1),'trim',.15)
    box((cx,yy-1.4,82),(17.5,.3,20),'seal',.7)
    box((cx,yy-1.62,82),(15.6,.08,18.2),'glass',.4)
    rod((cx+9.5,yy-2.0,58),(cx+9.5,yy-2.0,64),.35,'trim')
    box((cx+8.3,yy-1.65,61),(3.2,.8,2.1),'seal',.25)
    for z in (38,62,87):
        box((cx-13.1,yy-1.4,z),(3.4,.35,2.0),'trim',.1)
        cyl((cx-14.2,yy-1.4,z-1.1),Z,.34,2.2,'trim')
    # Folded step stows against the lower skirt rather than blocking the walkway.
    box((cx,-48.5,21),(25.5,1.7,7.2),'chassis',.15)
    for x in np.arange(cx-10,cx+11,3):rod((x,-49.5,18.2),(x,-49.5,24),.13)
    # Roof vent and perimeter seams; no additional light or gameplay component.
    box((35,0,118.6),(24,24,1.2),'seal',.7)
    box((35,0,119.6),(22,22,1.5),'shell',1.0)
    for yy in (-7,7):box((35,yy,120.4),(12,.5,.25),'trim',.06)
    if lod<2:
        for xx in (-154,142):
            for yy in np.arange(-28,29,8):screw((xx,yy,118.25),Z)
    # Rear ladder with curved handholds and stand-offs, plus the spare wheel and tail lamps.
    for yy in (-9,9):
        path=[(-163,yy,26),(-163,yy,109),(-163,yy,119),(-158,yy,122),(-151,yy,122)]
        G.tube(m,[np.array(p,float) for p in path],.65,'trim',sides=(10,7,5)[lod],bend_radius=3)
        for zz in (31,75,106):rod((-160,yy,zz),(-163,yy,zz),.45)
    for zz in np.arange(36,116,10):rod((-163,-9,float(zz)),(-163,9,float(zz)),.48)
    wheel((-166,30,50),X,26,7)
    box((-164,0,23),(5,90,5),'chassis',.7)
    for side in (-1,1):
        box((-160.8,side*34,40),(1,5.5,8.5),'trim',.5)
        box((-161.5,side*34,40),(.35,4.4,7.4),'red',.4)
        for xx in (-146,144):box((xx,side*48.7,29),(3,.6,1.7),'amber',.3)
    # Welded A-frame, tank tray, formed coupler, latch, jack and slack safety chains.
    for side in (-1,1):strip((150,side*27,17),(196,0,14),3.2,4,'chassis')
    box((172,0,17.7),(24,30,1.0),'chassis',.2)
    for yy in (-14.6,14.6):box((172,yy,19),(24,.6,3),'chassis',.1)
    box((195,0,14.5),(15,6.5,5),'trim',1.4)
    box((194,0,18),(8,2,1.1),'chassis',.3)
    strip((191,0,18.4),(197,0,21),1.2,.45)
    cyl((188,0,2.4),Z,1.2,16,'trim')
    cyl((188,0,1.0),Z,2.7,1.4,'chassis')
    rod((188,0,20),(188,6,20),.3);cyl((188,6,18),Z,.5,3.2,'seal')
    if lod<2:
        for side in (-1,1):
            for k in range((16,9)[lod]):
                t=k/((16,9)[lod]-1);c=np.array((180+17*t,side*(7+4*math.sin(math.pi*t)),12-7*math.sin(math.pi*t)))
                axis=Y if k%2 else Z
                G.torus(m,c,axis,.78,.15,'chassis',seg=(10,7)[lod],sides=4)
    # Preserve the six existing hand/smear/splatter decals exactly on the body.
    for name,c,right,h,off in (
        ('hand',(60,-48,76),(1,0,0),22,.9),('smear',(30,-48,66),(1,0,0),18,.85),
        ('hand',(120,48,74),(-1,0,0),20,.9),('hand',(-110,48,80),(-1,0,0),26,.95),
        ('smear',(-70,48,66),(-1,0,0),22,.9),('splatter',(-130,48,56),(-1,0,0),30,.85)):
        P.blood(m,name,np.array(c,float),np.array(right,float),h,off=off)
    m.material_overrides['rs_blood']='materials/riverside/rs_blood.vmat'
    m.tile_overrides['rs_blood']=64
    for paint in m.polygons:
        if paint not in m.material_overrides:m.material_overrides[paint]=f'{MAT}/{paint}.vmat'
        m.tile_overrides.setdefault(paint,96 if paint=='shell' else 64)
    m.grain_paints={'wood'}
    return m

