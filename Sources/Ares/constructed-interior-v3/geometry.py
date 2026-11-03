"""Constructed pressure hall and reactor, in Ares plan inches. Render detail only."""
import math
import numpy as np
import map_kit as K
import riverdale_parts as P
import ares_interior as I
X,Y,Z=I.X,I.Y,I.Z
PAINT='ar_v3_paint';DARK='ar_v3_dark';STEEL='ar_v3_steel';RED='ar_v3_red';RUBBER='ar_v3_rubber';COPPER='ar_v3_copper';CEILING='ar_v3_ceiling';FLOOR='ar_v3_floor';SKIN='ar_v3_skin'
MATERIALS={p:'materials/ares/constructed-v3/'+p[6:]+'.vmat' for p in (PAINT,DARK,STEEL,RED,RUBBER,COPPER,CEILING,FLOOR,SKIN)}
def lathe(m,c,axis,profile,paint,sides=12,**kwargs):
    return P.lathe_axis(m,c,axis,[(float(r),float(z)) for r,z in profile],paint,sides,**kwargs)
def config(m):
    import ares_map as A
    A.configure(m)
    for p,path in MATERIALS.items():
        if p in m.polygons:m.material_overrides[p]=path;m.tile_overrides[p]=96 if p in (PAINT,CEILING) else 48
    return m
def box(m,c,size,paint=PAINT,b=1,axes=(X,Y,Z)):
    P.bevel_box(m,c,axes,size,paint,b)
def hexbolt(m,c,axis,r=.65):
    lathe(m,c,axis,[(r*1.25,0),(r*1.25,.15),(r,.15),(r,.65),(r*.8,.85)],STEEL,6,cap=STEEL)
def roundband(m,r,z,h,paint,thick=3):
    # A stepped, chamfered rolled ring, not a flat disk filling the chamber.
    p=[(r-thick,z),(r-1,z),(r,z+1),(r,z+h-1),(r-1,z+h),(r-thick,z+h)]
    lathe(m,(0,0,0),Z,p,paint,96)
def radial(a,r,z):return np.array((r*math.cos(a),r*math.sin(a),z))
def axes(a):
    out=np.array((math.cos(a),math.sin(a),0.));tangent=np.array((-math.sin(a),math.cos(a),0.))
    return tangent,-out,Z
def rbox(m,a,r,z,size,paint=PAINT,b=1):box(m,radial(a,r,z),size,paint,b,axes(a))
def curved_plate(m,r,z0,z1,a0,a1,paint=PAINT,thick=3,bevel=1.3):
    """Closed curved shell with separately shaded rolled edges and panel reveals."""
    steps=max(3,int((a1-a0)*r/12));angles=np.linspace(a0,a1,steps+1)
    # Cross section round the shell: inner, eased top/bottom, outer face.
    prof=[(r-thick,z0+bevel),(r-thick,z1-bevel),(r-thick+bevel,z1),
          (r-bevel,z1),(r,z1-bevel),(r,z0+bevel),(r-bevel,z0),(r-thick+bevel,z0)]
    for aa,ab in zip(angles[:-1],angles[1:]):
        for j,(ra,za) in enumerate(prof):
            rb,zb=prof[(j+1)%len(prof)]
            # Per-edge normals, smooth around the circumference.
            nr,nz=za-zb,rb-ra
            normal0=K.normalise(np.array((math.cos(aa)*nr,math.sin(aa)*nr,nz)));normal1=K.normalise(np.array((math.cos(ab)*nr,math.sin(ab)*nr,nz)))
            face_paint=SKIN if paint==PAINT and j==4 else paint
            uv=None
            if face_paint==SKIN:
                uv=[((a-a0)/(a1-a0),(z-z0-bevel)/(z1-z0-2*bevel)) for a,z in ((aa,za),(ab,za),(ab,zb),(aa,zb))]
            P.card(m,face_paint,[radial(aa,ra,za),radial(ab,ra,za),radial(ab,rb,zb),radial(aa,rb,zb)],normal0+normal1,uv=uv,normals=[normal0,normal1,normal1,normal0])
    for a,sign in ((a0,-1),(a1,1)):
        P.card(m,paint,[radial(a,rp,z) for rp,z in prof],np.array((-math.sin(a),math.cos(a),0))*sign)
def wall_lamp(m,c,normal,w=16,h=8):
    n=K.normalise(normal);side=K.normalise(np.cross(n,Z))
    # Right-handed local frame; the diffuser is a separate recessed glass face.
    ax=(side,n,Z)
    box(m,c,(w+5,7,h+5),DARK,1.4,ax)
    box(m,np.asarray(c)+n*3.7,(w,1.0,h),'ar_led_warm',.35,ax)
    box(m,np.asarray(c)+n*4.3+Z*(h/2+1.5),(w+6,3.0,2.2),STEEL,.5,ax)

def portal(m,e):
    path=[(e,-691,208),(e,-691,476)]
    path+=I.bezier((e,-691,476),(e,-691,602),(e,-614,677),(e,-498,677),12)[1:]
    path+=[(e,615,677)]
    path+=I.bezier((e,615,677),(e,760,677),(e,834,609),(e,815,548),12)[1:]
    path+=[(e,734,208)]
    I.ribbon(m,path,X,44,56,PAINT,3.6)
    for sign in (-1,1):
        I.ribbon(m,[np.asarray(p)+X*sign*22.5 for p in path],X,2.7,41,DARK,.7)
    for n,z in ((-691,223),(734,223)):
        box(m,(e,n,z),(60,70,30),DARK,3)
        for dx in (-23,23):
            for dn in (-26,26):hexbolt(m,(e+dx,n+dn,239),Z,1.1)
    for n,z,sign in ((-691,426,1),(781,426,-1)):
        box(m,(e,n+sign*28,z),(46,8,84),DARK,2.2)
        box(m,(e,n+sign*33,z),(40,2.5,74),RED,1.1)
        for dx in (-14,14):
            for dz in (-29,29):hexbolt(m,(e+dx,n+sign*34.5,z+dz),Y*sign,.85)
        wall_lamp(m,(e,n+sign*30,z+48),Y*sign,23,8)
    # Flush inspection plates and visible fixings on the broad side faces.
    for p in path[1:-1:3]:
        c=np.asarray(p)
        for sign in (-1,1):
            for dn in (-12,12):hexbolt(m,c+X*sign*24+Y*dn,X*sign,.55)

def haunch(m,side,n):
    path=[(side*1070,n,208),(side*1070,n,487)]
    path+=I.bezier((side*1070,n,487),(side*1070,n,608),(side*995,n,680),(side*891,n,680),14)[1:]
    I.ribbon(m,path,Y,48,56,PAINT,3.6)
    for sign in (-1,1):I.ribbon(m,[np.asarray(p)+Y*sign*24.6 for p in path],Y,3,40,DARK,.7)
    box(m,(side*1041,n,426),(8,48,84),DARK,2.2)
    box(m,(side*1035,n,426),(2.5,40,74),RED,1.1)
    front=-side*X
    wall_lamp(m,(side*1034,n,476),front,25,8)
    for dn in (-14,14):
        for z in (397,455):hexbolt(m,(side*1033.5,n+dn,z),front,.85)
    box(m,(side*1065,n,226),(70,65,36),DARK,3)
    for i in (3,6,9):
        c=np.asarray(path[i])
        for s in (-1,1):hexbolt(m,c+Y*s*25,Y*s,.8)

def ceiling(m):
    # Closed cassette soffits and real shadow gaps, with the roof above intact.
    for e0,e1 in ((-1098,-924),(-876,-524),(-476,-244),(-244,0),(0,244),(244,476),(524,876),(924,1098)):
        for n in range(-700,830,190):
            if abs((e0+e1)/2)<245 and abs(n+89)<250:continue
            box(m,((e0+e1)/2,n+92,714),(e1-e0-4,182,8),CEILING,1.1)
            for e in (e0+12,e1-12):
                for nn in (n+12,n+164):hexbolt(m,(e,nn,706.4),-Z,.6)
    # Proper I-section transverse members between the pressure frames.
    for n in (-508,-108,292,692):
        for a,b in ((-1090,-240),(240,1090)):
            box(m,((a+b)/2,n,691),(b-a,23,4),DARK,.7)
            box(m,((a+b)/2,n,677),(b-a,5,24),DARK,.6)
            box(m,((a+b)/2,n,663),(b-a,29,5),DARK,.8)
    # Rolled ventilation ducts with circumferential slip joints, red flange
    # clamps, hanger shoes and threaded suspension rods.
    for side in (-1,1):
        e=side*720
        for j,n in enumerate(range(-610,780,160)):
            lathe(m,(e,n,649),Y,[(38,0),(39,3),(39,150),(38,156)],STEEL,48)
            lathe(m,(e,n,649),Y,[(39,-3),(43,-2),(43,2),(39,3)],RED if j%3==0 else DARK,48)
            P.torus(m,(e,n+78,649),Y,39,.65,DARK,48,6)
            box(m,(e,n,691),(100,12,5),DARK,1)
            for de in (-46,46):
                P.rod(m,(e+de,n,690),(e+de,n,711),1.1,STEEL,8,True)
                hexbolt(m,(e+de,n,688),-Z,1.4)
        # Cable ladder, drawn with open rungs instead of a solid tray box.
        te=e-side*115
        for n in range(-650,790,48):
            for de in (-30,30):box(m,(te+de,n+22,679),(3,45,20),DARK,.6)
            for dn in (0,22,44):box(m,(te,n+dn,673),(64,3,4),STEEL,.5)
        for de in (-21,-12,-3,8,19):
            P.rod(m,(te+de,-650,678),(te+de,830,678),2.1,RED if de in (-21,8) else COPPER if de==-3 else RUBBER,10,True)
    # Brighter, broader lamp housings with proper rolled edge and end caps.
    for e in (-900,-600,-300,300,600,900):
        for n in (-450,-50,350,700):
            box(m,(e,n,625),(23,114,9),DARK,2)
            box(m,(e,n,620),(15,102,2),'ar_led_warm',.6)
            for dn in (-52,52):box(m,(e,n+dn,620),(25,4,7),STEEL,.8)
            for de in (-10,10):box(m,(e+de,n,620),(2,112,6),STEEL,.5)
            for dn in (-44,44):P.rod(m,(e,n+dn,630),(e,n+dn,703),.7,STEEL,6,True)

def gallery_edge(m,a,b,out):
    a,b=np.asarray(a,float),np.asarray(b,float);out=K.normalise(out)
    along=K.normalise(b-a);ax=(along,out,Z)
    if np.linalg.det(np.stack(ax))<0:ax=(-along,out,Z)
    length=np.linalg.norm(b-a);mid=(a+b)/2
    box(m,mid+out*1.2+Z*194,(length,5,26),DARK,1.2,ax)
    count=max(1,round(length/128))
    for k in range(count):
        c=a+(b-a)*(k+.5)/count+out*4+Z*193
        box(m,c,(length/count-7,3.5,22),PAINT,1,ax)
        box(m,c+out*2+Z*2,(length/count-21,.9,10),DARK,.5,ax)
        for s in (-1,1):hexbolt(m,c+along*s*(length/count/2-11)+out*2,out,.65)
    for k in range(1,max(2,int(length/190))):
        c=a+(b-a)*k/max(2,int(length/190))+out*1.5
        wall_lamp(m,c+Z*172,out,24,5)
    box(m,mid+out*5+Z*207,(length,5,2.4),STEEL,.6,ax)
def galleries(m):
    gallery_edge(m,(-880,560,0),(880,560,0),-Y)
    gallery_edge(m,(-880,-540,0),(880,-540,0),Y)
    for side in (-1,1):
        for n0,n1 in ((-540,-470),(-158,-80),(80,560)):
            gallery_edge(m,(side*880,n0,0),(side*880,n1,0),-side*X)
    # Collars and curved knee braces on existing load-bearing columns.
    for n,sign in ((570,-1),(-550,1)):
        for e in (-600,-300,300,600):
            box(m,(e,n,173),(25,25,34),RED,2)
            for side in (-1,1):
                path=I.bezier((e+side*5,n,143),(e+side*16,n,168),(e+side*37,n,183),(e+side*58,n,185),8)
                I.ribbon(m,path,Y,8,9,DARK,1)
    # Formed gallery-front ring and bridge fascia, with radial expansion joints.
    for k in range(32):
        a0=2*math.pi*k/32+.006;a1=2*math.pi*(k+1)/32-.006
        curved_plate(m,292,182,206,a0,a1,PAINT,4,1.0)
        mid=(a0+a1)/2
        rbox(m,mid,293,194,(25,2,11),DARK,.8)
        if k%2==0:wall_lamp(m,radial(mid,292,173),radial(mid,1,0),20,4)
        for a in (a0+.018,a1-.018):hexbolt(m,radial(a,293,191),radial(a,1,0),.75)
    for side in (-1,1):
        for n,sign in ((-80,-1),(80,1)):
            a,b=(side*294,n,0),(side*870,n,0)
            gallery_edge(m,a,b,Y*sign)

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

def pump(m,e,n,heading):
    import ares_map as A
    F=A.Frame(e,n,heading);xx=K.normalise(F.p(1,0,0)-F.p(0,0,0));yy=K.normalise(F.p(0,1,0)-F.p(0,0,0))
    ax=(xx,yy,Z)
    box(m,F.p(0,0,5),(72,56,10),DARK,2,ax)
    # Horizontal cast pump/motor case with dished ends and split shell seam.
    profile=[(0,-34),(14,-34),(21,-31),(24,-26),(24,25),(22,30),(15,34),(0,34)]
    lathe(m,F.p(0,0,35),xx,profile,PAINT,40,turn=math.pi/40)
    for x in (-20,20):
        lathe(m,F.p(x,0,35),xx,[(24,-2),(25.1,-1),(25.1,1),(24,2)],RED,40)
        box(m,F.p(x,0,11),(9,45,15),DARK,1,ax)
    # End-face impeller cover, machined bolts, vented motor end and service head.
    for sign in (-1,1):
        end=F.p(sign*34,0,35)
        lathe(m,end,xx*sign,[(14,0),(15.5,1),(15.5,2),(13,3),(0,3)],DARK,32)
        for k in range(8):
            a=k*math.pi/4;hexbolt(m,end+yy*(18*math.cos(a))+Z*(18*math.sin(a))+xx*sign,xx*sign,.7)
    box(m,F.p(-3,-24,36),(30,7,30),DARK,2,ax)
    uv=[A.AM.region_uv(A.AM.SCREEN,A.AM.SCREEN_ATLAS,'screen6',s,t) for s,t in ((0,0),(1,0),(1,1),(0,1))]
    P.quad(m,'ar_screens',F.p(-3,-28.1,38),xx,Z,24,18,uv)
    for x in (-12,6):lathe(m,F.p(x,-28.2,25),-yy,[(1.5,0),(1.5,.8),(0,.9)],RED if x==-12 else STEEL,12)
    for x in (-20,20):
        start=F.p(x,4,58);top=start+Z*46;toward=K.normalise(np.array((-e,-n,0.)))
        end=top+toward*(math.hypot(e,n)-166)
        P.tube(m,[start,top,end],6.4,STEEL,20,bend_radius=19)
        # Seal each feed into a real radial nozzle through the pressure jacket.
        # The connector reaches the glazing instead of ending in empty space.
        radial_dir=K.normalise(np.array((end[0],end[1],0.)))
        length=math.hypot(end[0],end[1])-137
        lathe(m,end,-radial_dir,[(6.4,0),(10.5,1),(10.5,4),(8.5,6),(8.5,length)],DARK,32)
        for point,axis in ((start+Z*7,Z),(end-toward*8,toward)):
            lathe(m,point,axis,[(6.5,-3),(9,-2),(9,2),(6.5,3)],RED,24)

def reactor(m):
    """Fabricated outer housings; original plasma, glass and labels stay in place."""
    # The existing 232-inch collider plinth receives a visible stepped shell;
    # its original small core label remains mounted on this front face.
    lathe(m,(0,0,0),Z,[(224,0),(230,0),(233,2),(233,12),(228,16),(198,16)],DARK,96)
    roundband(m,231,12,3,STEEL,6)
    for k in range(24):hexbolt(m,radial(k*math.pi/12,216,16.2),Z,.95)
    lathe(m,(0,0,0),Z,[(151,362),(151,470)],DARK,96)
    # Large segmented skirting, lower jacket and service access cassettes.
    for k in range(16):
        a0=2*math.pi*k/16+.012;a1=2*math.pi*(k+1)/16-.012;a=(a0+a1)/2
        curved_plate(m,194,19,65,a0,a1,PAINT,8,2.5)
        rbox(m,a,194.6,42,(52,2.0,25),DARK,1.4)
        for dz in (-8,-4,0,4,8):rbox(m,a,196,42+dz,(43,1,1.3),STEEL,.2)
        for aa in (a0+.035,a1-.035):
            for z in (27,57):hexbolt(m,radial(aa,195,z),radial(aa,1,0),.95)
    roundband(m,197,17,7,DARK,12);roundband(m,197,63,7,STEEL,12)
    # Reinforced glazing ends at each chamber, with segmented white bolted
    # service housings and black gasket reveals.
    for z0,z1,r in ((163,190,173),(336,364,168),(469,493,167)):
        roundband(m,r-3,z0-3,5,RUBBER,13)
        for k in range(16):
            a0=2*math.pi*k/16+.01;a1=2*math.pi*(k+1)/16-.01
            curved_plate(m,r,z0,z1,a0,a1,PAINT,6,1.7)
            for a in (a0+.04,a1-.04):hexbolt(m,radial(a,r+.6,(z0+z1)/2),radial(a,1,0),.9)
        roundband(m,r+1,z1-2,5,STEEL,8)
    # Face plates bordering the label collar. Curved shells have deliberate
    # dark gaps; exposed pull handles and hinge pins explain their assembly.
    for k in range(16):
        a0=2*math.pi*k/16+.008;a1=2*math.pi*(k+1)/16-.008;a=(a0+a1)/2
        for z0,z1 in ((363,375),(458,470)):
            curved_plate(m,163,z0,z1,a0,a1,DARK,8,1.5)
            hexbolt(m,radial(a,164,(z0+z1)/2),radial(a,1,0),.8)
    for k in range(4):
        a=k*math.pi/2
        rbox(m,a,160,417,(31,12,86),PAINT,3)
        for off in (-10,10):
            for z in (384,450):hexbolt(m,radial(a,167,z)+np.array((-math.sin(a),math.cos(a),0))*off,radial(a,1,0),1)
        out=radial(a,1,0);tan=np.array((-math.sin(a),math.cos(a),0))
        p=radial(a,168,417)
        P.tube(m,[p-Z*9,p+out*5-Z*9,p+out*5+Z*9,p+Z*9],1.3,STEEL,10,bend_radius=3)
    # Large chamber stanchions: machined feet, captive flange bolts, thin dark
    # mullions against the glow and substantial outer rails.
    for z0,z1,r,posts in ((69,162,146,12),(222,335,146,12),(494,557,134,10)):
        for k in range(posts):
            a=2*math.pi*(k+.5)/posts
            rbox(m,a,r+1,(z0+z1)/2,(8,9,z1-z0),DARK,1.2)
            for z in (z0+4,z1-4):
                rbox(m,a,r+3,z,(15,14,12),STEEL,1.4)
                hexbolt(m,radial(a,r+11,z),radial(a,1,0),.9)
    # Heavy rolled upper hood, segmented skin panels, recessed downward lamps
    # and radial mounting webs. Existing ring collision remains at r224.
    for k in range(24):
        a0=2*math.pi*k/24+.005;a1=2*math.pi*(k+1)/24-.005;a=(a0+a1)/2
        curved_plate(m,225,567,588,a0,a1,PAINT,5,2)
        rbox(m,a,207,592,(13,35,5),DARK,1)
        for z in (573,582):hexbolt(m,radial(a,226,z),radial(a,1,0),.85)
    roundband(m,226,564,5,DARK,15);roundband(m,227,586,6,STEEL,12)
    # Stack stiffening bands and vertical service spines, entirely inside the
    # original upper-pipe envelope.
    for z in (615,660,704):roundband(m,116,z,8,DARK,10)
    for k in range(12):
        a=2*math.pi*k/12
        rbox(m,a,113,658,(8,8,98),DARK,1)
    # Paired insulated risers with swept elbows and service flanges running
    # through the existing gaps between the four label panels.
    for k in range(4):
        a=math.pi*k/2;out=radial(a,1,0);tan=np.array((-math.sin(a),math.cos(a),0))
        for offset in (-12,12):
            p=out*154+tan*offset
            P.tube(m,[p+Z*70,p+Z*135,p+out*3+Z*160,p+out*3+Z*291,p+Z*326,p+Z*345],8.5,STEEL,24,bend_radius=19)
            for z,r in ((95,154),(263,157),(324,154)):
                pos=out*r+tan*offset+Z*z
                lathe(m,pos,Z,[(8.7,-4),(11,-3),(11,3),(8.7,4)],DARK,24)
                for j in range(6):
                    b=2*math.pi*j/6;hexbolt(m,pos+np.array((math.cos(b),math.sin(b),0))*10.3+Z*3,Z,.6)
    for e,n in ((270,270),(-270,270),(-270,-270),(270,-270)):
        pump(m,e,n,math.degrees(math.atan2(n,e))+90)
