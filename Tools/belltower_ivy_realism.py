"""Interwoven climbing runners and overlapping, individually cupped ivy leaves.

The old patch bounds remain the clearance envelope. Shoots follow curved rising
paths with irregular node spacing; foliage forms overlapping pockets instead
of horizontal ranks. This builds visual polygons only, with no scene objects.
"""
import math
import zlib
import numpy as np

LEAF, STEM, SHOOT = 'ivy_leaf3d', 'ivy_stem3d', 'ivy_shoot3d'
DIRECTORY = 'materials/belltower/ivy-realism-v3'
ATLAS = DIRECTORY+'/leaves.png'
MATERIALS = {LEAF:DIRECTORY+'/leaves.vmat',STEM:DIRECTORY+'/stems.vmat',SHOOT:DIRECTORY+'/shoots.vmat'}


def unit(value):
    value=np.asarray(value,float)
    return value/max(1e-12,np.linalg.norm(value))


def curve(a,b,c,d,t):
    return (1-t)**3*a+3*(1-t)**2*t*b+3*(1-t)*t*t*c+t**3*d


def build(model,points,outward,hanging=False):
    before=(len(model.boxes),len(model.hulls),len(model.props))
    points=np.round(np.asarray(points,float),3); outward=unit(outward)
    up=np.array((0.,0.,1.)); right=unit(np.cross(up,outward))
    centre=points.mean(axis=0); width=np.ptp(points@right)
    lo,hi=points[:,2].min(),points[:,2].max(); height=hi-lo
    direction=-1 if hanging else 1
    base=centre.copy(); base[2]=hi if hanging else lo
    key=','.join(f'{v:.3f}' for v in (abs(centre[0]),centre[1],lo,hi,width,int(hanging)))
    rng=np.random.default_rng(zlib.crc32(key.encode())+3107)
    model.material_overrides.update(MATERIALS)
    model.tile_overrides.update({LEAF:12,STEM:24,SHOOT:24})
    stats={'leaves':0,'stem_segments':0,'width':float(width),'height':float(height)}
    def world(q):return base+right*q[0]+up*(direction*q[1])+outward*q[2]
    def local(q):
        q=q-base
        return np.array((q@right,direction*q[2],q@outward))

    def tube(a,b,r0,r1,paint=STEM,sides=5):
        a,b=world(a),world(b); length=np.linalg.norm(b-a)
        if length<.04:return
        tangent=(b-a)/length
        u=unit(np.cross(tangent,outward if abs(tangent@outward)<.93 else up)); v=np.cross(tangent,u)
        rim=[u*math.cos(k*math.tau/sides)+v*math.sin(k*math.tau/sides) for k in range(sides)]
        for k in range(sides):
            p,q=rim[k],rim[(k+1)%sides]
            model.polygon(paint,[a+r0*p,a+r0*q,b+r1*q,b+r1*p],normal=p+q,normals=[p,q,q,p],
                uv=[(k/sides,0),((k+1)/sides,0),((k+1)/sides,length/14),(k/sides,length/14)])
        stats['stem_segments']+=1

    def leaf(root,growth,fraction):
        # Blades face a spread of directions in 3D. Older leaves droop and turn
        # towards the light; the smaller terminal leaves follow their shoot.
        young=fraction>.82
        size=rng.uniform(2.8,4.3)*(rng.uniform(.55,.78) if young else 1)
        if rng.random()<.12 and not young:size*=1.18
        normal=unit(outward*rng.uniform(.52,1.05)+up*rng.uniform(-.15,.88)+right*rng.normal(0,.38))
        angle=rng.normal(0,1.0)+(math.pi if hanging else 0)
        wanted=up*math.cos(angle)+right*math.sin(angle)+outward*rng.uniform(.1,.65)
        if young:wanted=unit(world(root+growth)-world(root))*.65+wanted*.35
        long=unit(wanted-normal*(wanted@normal))
        across=unit(np.cross(long,normal)); normal=unit(np.cross(across,long))
        span=size*rng.uniform(.83,1.08)
        petiole=rng.uniform(.35,1.1)
        anchor=world(root)+normal*petiole+right*rng.normal(0,.23)+up*rng.normal(0,.22)
        cup=rng.uniform(.035,.085); curl=rng.uniform(-.11,.10); twist=rng.uniform(-.075,.075)
        def point(u,v):
            bend=cup*(1-4*u*u)*math.sin(math.pi*v)+curl*v*v+twist*u*v
            return anchor+across*(u*span)+long*((v-.04)*size)+normal*(size*bend)
        def vertex(u,v):
            du=point(u+1e-4,v)-point(u-1e-4,v); dv=point(u,v+1e-4)-point(u,v-1e-4)
            return point(u,v),unit(np.cross(du,dv))
        vertices={(i,j):vertex(i*.5-.5,j*.5) for i in range(3) for j in range(3)}
        positions=[local(q) for q,n in vertices.values()]
        if any(abs(q[0])>width*.494 or q[1]<.13 or q[1]>height-.13 for q in positions):return
        offset=outward*max(0.,.16-min(q[2] for q in positions))
        cell=int(rng.choice([0,1,2,3,4,5,6,7],p=[.13,.06,.16,.13,.12,.17,.09,.14]))
        if young and rng.random()<.4:cell=1
        column,row=cell%4,cell//4
        def uv(i,j):return ((column+i*.5)/4,(1-row*.5)-.5+j*.25)
        for j in range(2):
            for i in range(2):
                ids=[(i,j),(i+1,j),(i+1,j+1),(i,j+1)]
                values=[vertices[k] for k in ids]
                model.polygon(LEAF,[q+offset for q,n in values],normal=sum(n for q,n in values),
                    normals=[n for q,n in values],uv=[uv(*k) for k in ids])
        tube(root,local(point(0,.045)+offset),.033,.022,SHOOT,3)
        stats['leaves']+=1

    def shoot(a,side,length,rise,depth,juvenile=False):
        # A curved diagonal shoot with smaller sprays from its inner nodes.
        end=np.array((np.clip(a[0]+side*length,-width*.45,width*.45),
            np.clip(a[1]+rise,2,height-3),np.clip(a[2]+depth,.22,6.5)))
        c1=a+np.array((side*length*rng.uniform(.12,.4),rise*rng.uniform(.2,.65),depth*.3))
        c2=end+np.array((-side*length*.24,-rise*.18,rng.uniform(-.5,.8)))
        count=max(4,int(np.linalg.norm(end-a)/3))
        for k in range(count):
            t0,t1=k/count,(k+1)/count
            tube(curve(a,c1,c2,end,t0),curve(a,c1,c2,end,t1),.09*(1-t0)+.025,.09*(1-t1)+.025,SHOOT,4)
        nodes=max(5,int(np.linalg.norm(end-a)/rng.uniform(1.25,1.85)))
        for k in range(nodes):
            t=(k+rng.uniform(.08,.93))/nodes
            origin=curve(a,c1,c2,end,t)
            tangent=unit(curve(a,c1,c2,end,min(1,t+.02))-curve(a,c1,c2,end,max(0,t-.02)))
            leaf(origin,tangent,t)
            # Irregular second leaves fill little pockets, rather than adding
            # another evenly spaced rank all the way along the branch.
            if .16<t<.79 and rng.random()<.18:
                short=origin+np.array((rng.normal(0,1.25),rng.normal(0,1.1),rng.uniform(.3,1.3)))
                tube(origin,short,.042,.025,SHOOT,3)
                leaf(short,tangent,t+.08)

    count=max(4,int(width/18))
    for main in range(count):
        lateral=(main-(count-1)/2)/max(1,(count-1)/2)
        reach=height*rng.uniform(.53,.80) if abs(lateral)>.65 else height*rng.uniform(.88,.985)
        root=np.array((lateral*width*.10+rng.normal(0,1.2),.15,.14))
        end=np.array((lateral*width*rng.uniform(.18,.32)+rng.normal(0,width*.045),reach,rng.uniform(.2,.9)))
        c1=np.array((root[0]+rng.normal(0,width*.16),reach*.28,rng.uniform(.1,.55)))
        c2=np.array((end[0]+rng.normal(0,width*.14),reach*.72,rng.uniform(.2,.85)))
        steps=max(12,int(reach/3.4))
        for k in range(steps):
            t0,t1=k/steps,(k+1)/steps
            r0=.40*(1-t0)**1.3+.052; r1=.40*(1-t1)**1.3+.052
            tube(curve(root,c1,c2,end,t0),curve(root,c1,c2,end,t1),r0,r1)
        # Random node spacing and correlated curves remove the old ladder-like
        # branch pattern. Short side axes overlap in three distinct depths.
        t=rng.uniform(.035,.075)
        while t<.96:
            a=curve(root,c1,c2,end,t)
            side=-1 if rng.random()<.5 else 1
            room=width*.45-side*a[0]
            length=min(room,width*rng.uniform(.15,.34)*(1-.33*t))
            rise=rng.uniform(5,19)*(1-.45*t)
            if hanging:rise*=rng.uniform(.7,1.2)
            if a[1]+rise>height-3:rise=height-3-a[1]
            if length>3 and rise>1:
                shoot(a,side,length,rise,rng.uniform(.4,4.2))
            t+=rng.uniform(6.0,10.0)/reach
        # Loose terminal sprays thin out towards the younger growing ends.
        for t in (.83,.91,.975):
            origin=curve(root,c1,c2,end,t)
            tangent=unit(end-c2)
            leaf(origin,tangent,.9)
    assert before==(len(model.boxes),len(model.hulls),len(model.props))
    return stats
