"""Worn shipping-crate joinery, retaining Belltower's original cover envelope.

Separate cupped boards, rebated corners, a recessed lid and cleats supply depth.
The existing photographed timber/end-grain materials are reused unchanged.
"""
import math
import numpy as np
import belltower_furniture as F

END = 'garden_endgrain'
END_MATERIAL = 'materials/gunsmith_range/bench_oak_endgrain.vmat'


def board(model, centre, axes, size, seed, paint=F.WOOD, cup=.045):
    """Worn plank with a physical cup; backing closes its concealed reverse."""
    rng = np.random.default_rng(seed)
    centre, axes = np.asarray(centre, float), np.asarray(axes, float)
    length, width, thick = map(float, size)
    half, depth = width/2, thick/2
    bevel = min(rng.uniform(.16, .25), thick*.28, width*.15)
    # Clockwise cross-section viewed along the grain. The small concavity on
    # its outer face catches light without making aged boards look melted.
    profile = np.array(((-half+bevel,-depth),(half-bevel,-depth),
        (half,-depth+bevel),(half,depth-bevel),(half-bevel,depth),
        (0,depth-cup),
        (-half+bevel,depth),(-half,depth-bevel),(-half,-depth+bevel)))
    end_bevel = rng.uniform(.12,.22)
    xs = (-length/2, -length/2+end_bevel, length/2-end_bevel, length/2)
    offsets = (0., rng.uniform(-.035,.035), rng.uniform(-.035,.035), 0.)
    sections = []
    for k, x in enumerate(xs):
        section = profile.copy()
        if k in (0,3):
            section[:,0] *= 1-min(.08,end_bevel/half)
            section[:,1] *= 1-min(.24,end_bevel/depth)
        section[:,1] += offsets[k]
        sections.append(np.column_stack((np.full(len(section),x),section)))
    u0,u1=F.STRIPS[seed%len(F.STRIPS)]
    v0=(seed*.61803398875)%1
    def world(q):return centre+q@axes
    for a,b in zip(sections,sections[1:]):
        for i in range(len(profile)):
            if i in (0,1,len(profile)-1):
                continue  # Hidden reverse; the fitted backing/adjacent boards close it.
            j=(i+1)%len(profile)
            local=[a[i],b[i],b[j],a[j]]
            points=[world(q) for q in local]
            normal=np.cross(points[1]-points[0],points[2]-points[0])
            edge=profile[j]-profile[i]
            outward=edge[1]*axes[1]-edge[0]*axes[2]
            if np.dot(normal,outward)<0:normal=-normal
            uv=[(u0+(q[1]/width+.5)*(u1-u0),q[0]/F.TILE+v0) for q in local]
            F.face(model,paint,points,normal,uv)
    # The cut ends use end grain, rather than stretching lengthwise board grain.
    for section,sign in ((sections[0],-1),(sections[-1],1)):
        uv=[(q[1]/12+.5,q[2]/12+.5) for q in section]
        F.face(model,END,[world(q) for q in section],axes[0]*sign,uv)


def nail(model, point, normal, radius=.12):
    """Small, low round nail head; a bolt's tall hex head is too prominent here."""
    normal=np.asarray(normal,float);normal/=np.linalg.norm(normal)
    u=np.cross(normal,(0,0,1) if abs(normal[2])<.9 else (0,1,0));u/=np.linalg.norm(u)
    F.turned(model,point,normal,u,[(radius,0),(radius*.88,.055)],F.IRON,8,False)
    v=np.cross(normal,u)
    F.face(model,F.IRON,[np.asarray(point)+normal*.055+radius*.88*(
        u*math.cos(k*math.tau/8)+v*math.sin(k*math.tau/8)) for k in range(8)],normal)


def build(model,p,size):
    size=float(size);half=size/2;rows=max(4,round(size/6))
    rng=np.random.default_rng(F.seed_at(p,461))
    model.material_overrides[END]=END_MATERIAL
    model.tile_overrides[END]=12
    # Recessed backing keeps the fine joints dark without replacing the outer
    # boards with one flat visible cube. It adds no collision.
    F.box(model,p,(-half+1.4,-half+1.4,.3),(half-1.4,half-1.4,size-1.8),F.DARK,.15,440)
    for row in range(rows):
        za,zb=row*size/rows+.15,(row+1)*size/rows-.15
        for side in (-1,1):
            face=side*(half-.67+rng.uniform(-.075,.025))
            # One end rebates into the other; their edges do not share a plane.
            board(model,p.at((0,face,(za+zb)/2)),(p.x,p.z,p.y*side),
                (size-rng.uniform(.03,.16),zb-za,1.30),F.seed_at(p,500+row*11+side))
            face=side*(half-.67+rng.uniform(-.075,.025))
            board(model,p.at((face,0,(za+zb)/2)),(p.y,p.z,p.x*side),
                (size-2.65,zb-za,1.30),F.seed_at(p,600+row*11+side))
    # Lower lid boards leave room for the two real cleats. Their highest faces
    # remain at the original stack height, size.
    for k in range(rows):
        x0=-half+k*size/rows+.16;x1=-half+(k+1)*size/rows-.16
        height=size-1.47+rng.uniform(-.06,.025)
        board(model,p.at(((x0+x1)/2,0,height)),(p.y,p.x,p.z),
            (size-.12,x1-x0,1.25),F.seed_at(p,700+k))
    for side in (-1,1):
        for y in (-half-.58,half+.58):
            x=side*half*.7
            board(model,p.at((x,y,size/2)),(p.z,p.x,p.y*math.copysign(1,y)),
                (size,3.35,1.18),F.seed_at(p,810+side+(10 if y>0 else 0)),F.DARK,.035)
            for row in range(rows):
                z=(row+.5)*size/rows
                nail(model,p.at((x+(.35 if row%2 else -.35),y+math.copysign(.60,y),z)),
                     p.y*math.copysign(1,y))
    for k,y in enumerate((-half*.67,half*.67)):
        F.box(model,p,(-half+.10,y-1.55,size-1.22),(half-.10,y+1.55,size),F.DARK,.23,860+k)
        for x in (-half*.70,half*.70):
            nail(model,p.at((x,y,size-.055)),p.z)
