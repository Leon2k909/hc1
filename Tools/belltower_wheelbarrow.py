"""Pressed, worn garden wheelbarrow. Render geometry only; no scene or collision edits."""
import math
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from scipy.ndimage import gaussian_filter
from scipy.spatial import Delaunay
import map_kit as K
import belltower_furniture as F
import riverdale_parts as P

X=np.array((1.,0.,0.));Y=np.array((0.,1.,0.));Z=np.array((0.,0.,1.))
PREFIX='materials/belltower/wheelbarrow-v2'
MATERIALS={f'bw2_{name}':f'{PREFIX}/{name}.vmat' for name in ('paint','inner','frame','rubber','steel')}
MATERIALS['bw2_wood']='materials/belltower/furniture_wood.vmat'


def outline(length,rear,front,corner,z=0.):
    """A rounded trapezoid; the basin opens wider towards the wheel."""
    result=[]
    for cx,cy,start in ((length-corner,front-corner,0),(-length+corner,rear-corner,90),
                        (-length+corner,-rear+corner,180),(length-corner,-front+corner,270)):
        for step in range(9):
            a=math.radians(start+step*90/8)
            result.append(np.array((cx+corner*math.cos(a),cy+corner*math.sin(a),z)))
    return np.array(result)


def tube(m,points,radius=.72,paint='bw2_frame',sides=12):
    points=[np.asarray(p,float) for p in points];smooth=[points[0]]
    for a,b,c in zip(points,points[1:],points[2:]):
        length=min(np.linalg.norm(b-a),np.linalg.norm(c-b))
        cut=min(2.5,length*.30)
        lo=b-(b-a)/np.linalg.norm(b-a)*cut;hi=b+(c-b)/np.linalg.norm(c-b)*cut
        smooth.extend([(1-t)**2*lo+2*(1-t)*t*b+t*t*hi for t in np.linspace(0,1,7)])
    smooth.append(points[-1]);rings=[];normals=[];dist=0.;lengths=[0.]
    for i,centre in enumerate(smooth):
        axis=smooth[min(i+1,len(smooth)-1)]-smooth[max(0,i-1)]
        axis/=np.linalg.norm(axis);u=Y-axis*np.dot(Y,axis)
        if np.linalg.norm(u)<.1:u=X-axis*np.dot(X,axis)
        u/=np.linalg.norm(u);v=np.cross(axis,u)
        ns=[u*math.cos(k*math.tau/sides)+v*math.sin(k*math.tau/sides) for k in range(sides)]
        normals.append(ns);rings.append([centre+n*radius for n in ns])
        if i:dist+=np.linalg.norm(centre-smooth[i-1]);lengths.append(dist)
    for i in range(len(rings)-1):
        for k in range(sides):
            j=(k+1)%sides
            pts=[rings[i][k],rings[i][j],rings[i+1][j],rings[i+1][k]]
            ns=[normals[i][k],normals[i][j],normals[i+1][j],normals[i+1][k]]
            uv=[(k/sides,lengths[i]/32),((k+1)/sides,lengths[i]/32),
                ((k+1)/sides,lengths[i+1]/32),(k/sides,lengths[i+1]/32)]
            P.card(m,paint,pts,sum(ns),uv=uv,normals=ns)
    for i,normal in ((0,smooth[0]-smooth[1]),(-1,smooth[-1]-smooth[-2])):P.card(m,paint,rings[i],normal)


def basin(m):
    lower=outline(13.9,6.7,8.0,3.2,12.6)
    upper=outline(19.7,11.65,13.65,4.1,25.7)
    count=len(upper);rings=[];normals=[]
    for t in np.linspace(0,1,11):
        ring=[];ns=[]
        for k,(a,d) in enumerate(zip(lower,upper)):
            radial=d-a;radial[2]=0;radial/=np.linalg.norm(radial)
            b=a+radial*2.4;c=d-radial*.75-Z*3.8
            q=(1-t)**3*a+3*(1-t)**2*t*b+3*(1-t)*t*t*c+t**3*d
            derivative=3*(1-t)**2*(b-a)+6*(1-t)*t*(c-b)+3*t*t*(d-c)
            tangent=upper[(k+1)%count]-upper[(k-1)%count]
            n=np.cross(tangent,derivative);n/=np.linalg.norm(n)
            # Broad, shallow handling dents; the manufactured rim remains stable.
            dent=-.20*math.exp(-((q[0]+6)/5)**2-((q[1]+10)/3)**2-((q[2]-20)/4)**2)
            dent-=.13*math.exp(-((q[0]-11)/3)**2-((q[1]-10)/3)**2-((q[2]-19)/4)**2)
            q+=n*dent*math.sin(t*math.pi)
            ring.append(q);ns.append(n)
        rings.append(ring);normals.append(ns)
    for inner in (False,True):
        paint='bw2_inner' if inner else 'bw2_paint'
        def vertex(i,k):return rings[i][k]-normals[i][k]*.095 if inner else rings[i][k]
        for i in range(len(rings)-1):
            for k in range(count):
                j=(k+1)%count;indices=((i,k),(i,j),(i+1,j),(i+1,k))
                pts=[vertex(*q) for q in indices];ns=[normals[a][b]*(-1 if inner else 1) for a,b in indices]
                if inner:uv=[(p[0]/44+.5,p[1]/32+.5) for p in pts]
                else:uv=[(b/count,a/(len(rings)-1)) for a,b in ((i,k),(i,k+1),(i+1,k+1),(i+1,k))]
                P.card(m,paint,pts,sum(ns),uv=uv,normals=ns)
        # Three shallow stamped floor channels strengthen the thin basin sheet.
        # They belong to both sheet surfaces, with no extra bars above the load bed.
        perimeter=lower[:,:2];floor=list(perimeter.copy())
        for x in np.arange(-13.,14.,1.):
            for y in np.arange(-7.,8.,1.):
                q=np.array((x,y))
                if all((perimeter[(k+1)%count][0]-a[0])*(q[1]-a[1])-
                       (perimeter[(k+1)%count][1]-a[1])*(q[0]-a[0])>.45 for k,a in enumerate(perimeter)):
                    floor.append(q)
        floor=np.array(floor);mesh=Delaunay(floor)
        def floor_height(x,y):
            longitudinal=np.exp(-(x/10.3)**8)
            grooves=sum(np.exp(-((y-centre)/.40)**2) for centre in (-3.,0.,3.))
            return 12.6-.14*longitudinal*grooves
        vertices=[];shade=[]
        for k,(x,y) in enumerate(floor):
            height=12.6 if k<count else floor_height(x,y)
            dx=(floor_height(x+.015,y)-floor_height(x-.015,y))/.03
            dy=(floor_height(x,y+.015)-floor_height(x,y-.015))/.03
            n=np.array((-dx,-dy,1.));n/=np.linalg.norm(n)
            if k<count:n=Z
            vertices.append(np.array((x,y,height+(.095 if inner else 0))));shade.append(n if inner else -n)
        for ids in mesh.simplices:
            pts=[vertices[i] for i in ids];ns=[shade[i] for i in ids]
            P.card(m,paint,pts,sum(ns),uv=[(p[0]/44+.5,p[1]/32+.5) for p in pts],normals=ns)
    # A real curled sheet-metal rim, continuous around the basin.
    sections=[];rim_normals=[]
    for k,centre in enumerate(upper):
        tangent=upper[(k+1)%count]-upper[(k-1)%count];tangent/=np.linalg.norm(tangent)
        out=np.cross(tangent,Z);out/=np.linalg.norm(out)
        ns=[out*math.cos(j*math.tau/10)+Z*math.sin(j*math.tau/10) for j in range(10)]
        sections.append([centre+n*.26 for n in ns]);rim_normals.append(ns)
    for k in range(count):
        j=(k+1)%count
        for a in range(10):
            b=(a+1)%10;ns=[rim_normals[k][a],rim_normals[j][a],rim_normals[j][b],rim_normals[k][b]]
            paint='bw2_steel' if (k in (3,4,12,25,26,31) and a in (1,2,3,4)) else 'bw2_frame'
            P.card(m,paint,[sections[k][a],sections[j][a],sections[j][b],sections[k][b]],sum(ns),normals=ns)


def hardware(m,centre,axis,r=.30):
    P.lathe_axis(m,centre,axis,[(r*1.6,0),(r*1.6,.08),(r*.95,.10)],'bw2_steel',sides=12,cap='bw2_steel')
    P.lathe_axis(m,np.asarray(centre)+axis*.08,axis,[(r,0),(r,.20),(r*.83,.27)],'bw2_steel',sides=6,cap='bw2_steel')


def handle(m,a,b,seed):
    a,b=np.asarray(a,float),np.asarray(b,float);axis=b-a;length=np.linalg.norm(axis);axis/=length
    u=Y-axis*np.dot(Y,axis);u/=np.linalg.norm(u);v=np.cross(axis,u)
    profile=[(.86,0),(1.06,.50),(1.12,2.0),(1.13,length-3),(.98,length-1),(.65,length-.22),(.24,length)]
    rings=[];ns=[]
    for radius,t in profile:
        d=[u*math.cos(k*math.tau/20)+v*.86*math.sin(k*math.tau/20) for k in range(20)]
        rings.append([a+axis*t+q*radius for q in d]);ns.append([q/np.linalg.norm(q) for q in d])
    u0,u1=F.STRIPS[seed%len(F.STRIPS)]
    for i in range(len(rings)-1):
        for k in range(20):
            j=(k+1)%20;norms=[ns[i][k],ns[i][j],ns[i+1][j],ns[i+1][k]]
            uv=[(u0+(u1-u0)*k/20,profile[i][1]/F.TILE),(u0+(u1-u0)*(k+1)/20,profile[i][1]/F.TILE),
                (u0+(u1-u0)*(k+1)/20,profile[i+1][1]/F.TILE),(u0+(u1-u0)*k/20,profile[i+1][1]/F.TILE)]
            P.card(m,'bw2_wood',[rings[i][k],rings[i][j],rings[i+1][j],rings[i+1][k]],sum(norms),uv=uv,normals=norms)
    P.card(m,'bw2_wood',rings[0],-axis);P.card(m,'bw2_wood',rings[-1],axis)
    for t in (.8,2.1):
        centre=a+axis*t
        P.lathe_axis(m,centre,axis,[(1.09,0),(1.09,.08)],'bw2_steel',sides=20)


def wheel(m):
    centre=np.array((26.,0.,8.))
    profile=[(5.05,-1.40),(5.4,-1.92),(6.4,-2.20),(7.25,-2.05),(7.75,-1.55),(7.80,-.85),
             (7.80,.85),(7.75,1.55),(7.25,2.05),(6.4,2.20),(5.4,1.92),(5.05,1.40)]
    P.lathe_axis(m,centre,Y,profile,'bw2_rubber',sides=64)
    # Narrow staggered chevrons have real gaps and softened outside corners.
    for k in range(40):
        theta=(k+.18)*math.tau/40
        for side in (-1,1):
            rings=[]
            for y in (side*.10,side*1.25):
                shift=abs(y)*.035
                rings.append([centre+Y*y+(X*math.cos(theta+d+shift)+Z*math.sin(theta+d+shift))*r
                    for d,r in ((-.030,7.78),(-.025,7.98),(.025,7.98),(.030,7.78))])
            for i in range(4):
                j=(i+1)%4;pts=[rings[0][i],rings[0][j],rings[1][j],rings[1][i]]
                normal=(np.mean(pts,axis=0)-centre)*np.array((1.,0.,1.))
                if i in (1,3):normal+=Y*side*(1 if i==1 else -1)
                P.card(m,'bw2_rubber',pts,normal)
            for ring,sign in zip(rings,(-side,side)):P.card(m,'bw2_rubber',ring,Y*sign)
    # Recessed stamped hub dishes and rolled bead seats on both sides.
    for side in (-1,1):
        axis=Y*side
        P.lathe_axis(m,centre,axis,[(5.20,1.65),(5.02,1.88),(4.5,1.65),(3.6,1.15),(2.1,.80),(1.10,1.0)],'bw2_frame',sides=48)
        P.lathe_axis(m,centre,axis,[(1.12,.8),(1.12,2.60),(.8,2.85)],'bw2_steel',sides=24,cap='bw2_steel')
        for j in range(4):
            a=j*math.tau/4+.4;hardware(m,centre+(X*math.cos(a)+Z*math.sin(a))*2.0+axis*1.08,axis,.21)
        hardware(m,centre+axis*3.45,axis,.52)
    P.lathe_axis(m,centre-Y*7.3,Y,[(.55,0),(.55,14.6)],'bw2_steel',sides=16,cap='bw2_steel')
    # A visible tyre valve instead of an undetailed black disc.
    valve=centre+X*4.35-Y*1.98
    P.lathe_axis(m,valve,-Y,[(.19,0),(.19,.65),(.25,.66),(.25,.95)],'bw2_rubber',sides=8,cap='bw2_rubber')


def build(model,p):
    local=K.Model();basin(local)
    for side in (-1,1):
        tube(local,[(28,side*6.1,8),(-16,side*7.0,9.8),(-27,side*9.7,23.2),(-33,side*11.1,27.2)],.77)
        handle(local,(-32.2,side*11.0,27.0),(-47.6,side*12.0,30.0),4 if side<0 else 6)
        tube(local,[(-8,side*7.5,10.1),(-14,side*9.7,1.1),(-12,side*9.8,.80),(3,side*7.4,9.5)],.65)
        F.bevel_box(local,(-12.4,side*9.8,.32),(X,Y,Z),(5.2,2.35,.64),'bw2_steel',.17)
        for x in (-9,9):
            F.bevel_box(local,(x,side*5,11.5),(X,Y,Z),(4.0,3.0,2.1),'bw2_frame',.24)
            tube(local,[(x,side*5,11.2),(x,side*7.2,9.4)],.52)
            hardware(local,np.array((x,side*5,12.72)),Z,.29)
        F.bevel_box(local,(26,side*3.12,8.45),(X,Y,Z),(3.6,.50,3.9),'bw2_frame',.27)
    tube(local,[(-9,-7,9.9),(-9,7,9.9)],.58)
    tube(local,[(12,-6.6,9),(12,6.6,9)],.58)
    wheel(local)
    assert not local.boxes and not local.hulls
    pts=np.array([q for rows in local.polygons.values() for face,n in rows for q in face])
    assert np.isfinite(pts).all() and pts[:,2].min()>=-.001
    assert pts[:,0].min()>-49.5 and pts[:,0].max()<34.1 and abs(pts[:,1]).max()<14.2 and pts[:,2].max()<31.4
    for paint,rows in local.polygons.items():
        for i,(pts,n) in enumerate(rows):
            ns=local.polygon_normals.get((paint,i));uv=local.polygon_uvs.get((paint,i))
            transform=lambda n:p.x*n[0]+p.y*n[1]+p.z*n[2]
            P.card(model,paint,[p.at(q) for q in pts],transform(n),uv=uv,normals=[transform(q) for q in ns] if ns else None)
    model.material_overrides.update(MATERIALS);model.tile_overrides.update({p:24 for p in MATERIALS})
    return {'triangles':local.triangle_count(),'materials':len(local.polygons),'drawn_only':True,
        'bounds_min':np.min([q for rows in local.polygons.values() for face,n in rows for q in face],axis=0).tolist(),
        'bounds_max':np.max([q for rows in local.polygons.values() for face,n in rows for q in face],axis=0).tolist()}


def write_materials(directory):
    out=Path(directory);out.mkdir(parents=True,exist_ok=True)
    Image.new('RGB',(16,16),(128,128,255)).save(out/'flat_normal.png')
    n=1024;yy,xx=np.mgrid[:n,:n];rng=np.random.default_rng(27102641)
    fine=rng.normal(0,1,(n,n)).astype(np.float32);cloud=gaussian_filter(rng.normal(0,1,(n,n)),26);cloud/=cloud.std()
    for name,base,rough,metal in (('paint',(61,88,68),.49,0),('inner',(67,87,64),.58,0),
        ('frame',(43,65,51),.47,0),('rubber',(29,28,25),.83,0),('steel',(116,113,101),.38,.92)):
        colour=np.clip(np.array(base)[None,None,:]+fine[...,None]*.60+cloud[...,None]*1.4,0,255)
        wear=Image.new('L',(n,n));d=ImageDraw.Draw(wear)
        if name=='inner':
            for k in range(145):
                x=float(rng.uniform(.20,.80)*n);y=float(rng.uniform(.24,.76)*n)
                d.line((x,y,x+float(rng.uniform(15,170)),y+float(rng.uniform(-30,30))),fill=int(rng.uniform(35,180)),width=int(rng.integers(1,4)))
            for k in range(22):
                x=float(rng.uniform(.23,.70)*n);y=float(rng.uniform(.31,.69)*n)
                d.line((x,y,x+float(rng.uniform(28,165)),y+float(rng.uniform(-8,8))),fill=int(rng.uniform(100,220)),width=int(rng.integers(3,9)))
            bed=np.exp(-(((xx/n-.5)/.31)**4+((yy/n-.5)/.21)**4))
            soil=np.clip(.38*bed*(1+cloud*.30),0,.57)
            colour=colour*(1-soil[...,None])+np.array((86,70,47))*soil[...,None]
            # Irregular rubbed-through islands and residue at the pressed channels.
            rubbed=np.clip((cloud-.25)*.24,0,.55)*bed
            colour=colour*(1-rubbed[...,None])+np.array((107,103,86))*rubbed[...,None]
            for centre in (-3.,0.,3.):
                channel=np.exp(-((yy/n-(.5+centre/32))/.009)**2)*np.exp(-((xx/n-.5)/.24)**8)
                colour*=1-channel[...,None]*.15
        elif name in ('paint','frame'):
            for k in range(55 if name=='paint' else 26):
                x=float(rng.uniform(0,n));y=float(rng.uniform(0,n))
                if name=='paint':y=float(rng.choice((rng.uniform(0,.13*n),rng.uniform(.86*n,n))))
                d.line((x,y,x+float(rng.uniform(2,35)),y+float(rng.uniform(-5,5))),fill=int(rng.uniform(30,140)),width=int(rng.integers(1,3)))
            if name=='paint':
                for k in range(12):
                    x=float(rng.uniform(0,n));y=float(rng.choice((rng.uniform(0,.06*n),rng.uniform(.94*n,n))))
                    d.line((x,y,x+float(rng.uniform(8,48)),y+float(rng.uniform(-4,4))),fill=int(rng.uniform(100,225)),width=int(rng.integers(2,6)))
        amount=np.asarray(wear,dtype=np.float32)/255
        colour=colour*(1-amount[...,None])+np.array((104,96,77))*amount[...,None]
        Image.fromarray(np.uint8(np.clip(colour,0,255))).save(out/(name+'_color.png'))
        r=np.clip(rough+fine*.004+cloud*.012+amount*.08,.1,.98)
        Image.fromarray(np.uint8(r*255)).save(out/(name+'_rough.png'))
        text=('// Tools/belltower_wheelbarrow.py\n"Layer0"\n{\n    shader "shaders/complex.shader"\n'
            '    F_SPECULAR "1"\n'+f'    g_flMetalness "{metal}"\n    g_flRoughnessScaleFactor "1"\n'
            f'    TextureColor "{PREFIX}/{name}_color.png"\n    TextureNormal "{PREFIX}/flat_normal.png"\n'
            f'    TextureRoughness "{PREFIX}/{name}_rough.png"\n'
            '    TextureAmbientOcclusion "materials/default/default_ao.tga"\n    g_vColorTint "[1 1 1 1]"\n    g_flModelTintAmount "1"\n}\n')
        (out/(name+'.vmat')).write_text(text)
