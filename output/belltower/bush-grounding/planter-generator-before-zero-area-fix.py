"""Worn masonry street planters inside their existing 40 x 40 x 28 cover boxes.

Geometry supplies the joints, mitred coping, chips and recessed soil. Cut-stone
UVs sample inside individual blocks of the unchanged Poly Haven photograph.
"""
import math
import numpy as np
from scipy.spatial import HalfspaceIntersection, ConvexHull
import belltower_furniture as F
from map_kit import normalise

STONE='planter_cut_stone'
SOIL='planter_compost'
RESOURCE='materials/belltower/planters-v1'
TILE=2000/25.4
# (u0, image-y0, u1, image-y1), wholly inside the photographed mortar lines.
PATCHES=((.153,.018,.454,.190),(.034,.431,.349,.599),
         (.328,.638,.591,.787),(.136,.840,.454,.983))
CENTRES=((-1780,330),(-1180,330),(-870,-80))


def chipped_stone(model, centre, axes, footprint, height, rng, coping=False):
    """Closed convex stone, with unequal eased edges and occasional corner chips."""
    poly=np.asarray(footprint,float)
    origin=poly.mean(axis=0)
    poly=poly-origin
    half=height/2
    planes=[]
    edge_normals=[]
    for i,a in enumerate(poly):
        edge=poly[(i+1)%len(poly)]-a
        n=normalise((edge[1],-edge[0]))
        c=float(np.dot(n,a));assert c>0
        edge_normals.append(n)
        planes.append((*n,0,-c))
        for sign in (-1,1):
            bevel=rng.uniform(.22,.40) if coping else rng.uniform(.13,.30)
            planes.append((*n,sign,-(c+half-bevel)))
    planes.extend(((0,0,-1,-half),(0,0,1,-half)))
    for i,p in enumerate(poly):
        normal=normalise(edge_normals[i-1]+edge_normals[i])
        c=float(np.dot(normal,p))
        planes.append((*normal,0,-(c-rng.uniform(.12,.28))))
        # Sparse, unequal chips break the silhouette without jagged noise.
        if rng.random() < (.68 if coping else .28):
            planes.append((*normal,1,-(c+half-rng.uniform(.48,.95))))
    vertices=HalfspaceIntersection(np.array(planes),np.zeros(3)).intersections
    hull=ConvexHull(vertices)
    axes=np.asarray(axes,float);centre=np.asarray(centre,float)
    span=np.ptp(vertices,axis=0)
    available=[rect for rect in PATCHES
               if (rect[2]-rect[0])*TILE>max(span[0],span[1])+.06
               and (rect[3]-rect[1])*TILE>max(span[1],span[2])+.06]
    assert available,span
    rect=available[int(rng.integers(len(available)))]
    uv_centre=np.array(((rect[0]+rect[2])/2,1-(rect[1]+rect[3])/2))
    projection_centre=(vertices.min(axis=0)+vertices.max(axis=0))/2
    for tri,equation in zip(hull.simplices,hull.equations):
        local=vertices[tri]+np.array((*origin,0.))
        normal=equation[:3]
        dominant=int(np.argmax(np.abs(normal)))
        u,v=(1,2) if dominant==0 else ((0,2) if dominant==1 else (0,1))
        uv=[tuple(uv_centre+np.array((p[u]-projection_centre[u],p[v]-projection_centre[v]))/TILE) for p in local]
        # Every sample remains in stone, never in the source photograph's joints.
        assert all(rect[0] <= a <= rect[2] and 1-rect[3] <= b <= 1-rect[1] for a,b in uv)
        F.face(model,STONE,[centre+p@axes for p in local],normal@axes,uv)


def soil_height(x,y):
    return (23.05+.44*math.sin(.53*x+.31*y)+.27*math.cos(.71*y-.24*x)
            +.18*math.sin(1.1*x+.93*y)+.78*math.exp(-(x*x+y*y)/70))


def build(model, centre, z=0., size=40., seed=0):
    start=model.triangle_count()
    model.material_overrides.update({STONE:f'{RESOURCE}/cut_stone.vmat',SOIL:f'{RESOURCE}/compost.vmat'})
    model.tile_overrides.update({STONE:TILE,SOIL:64.})
    centre=np.array((*centre,z),float)
    scale=size/40
    rng=np.random.default_rng(seed+73191)
    # Recessed backing keeps the mortar joints and the planter's base closed.
    model.box(centre+np.array((-18.25,-18.25,.12))*scale,
              centre+np.array((18.25,18.25,21.5))*scale,SOIL)
    for course,(outer,inner,low,high) in enumerate(((18.7,15.3,.22,12.30),
                                                 (19.15,15.3,12.50,25.30),
                                                 (20.,14.5,25.40,28.0))):
        for side in range(4):
            angle=side*math.pi/2
            along=np.array((math.cos(angle),math.sin(angle),0.))
            outward=np.array((-math.sin(angle),math.cos(angle),0.))
            axes=np.array((along,outward,(0,0,1.)))
            # Alternating joints and corner mitres describe how it was assembled.
            split=((-2.4 if side%2 else 2.1) if course==1 else 0.)+rng.uniform(-.45,.45)
            for half in (0,1):
                gap=.085
                if half==0:
                    footprint=[(-outer,outer),(split-gap,outer),(split-gap,inner),(-inner,inner)]
                else:
                    footprint=[(split+gap,outer),(outer,outer),(inner,inner),(split+gap,inner)]
                footprint=list(reversed(footprint))
                # Keep each block's UV origin near its centre, at physical scale.
                p=np.array(footprint);offset=p.mean(axis=0);p-=offset
                height=high-low-rng.uniform(0,.06)
                block_centre=centre+(offset[0]*along+offset[1]*outward+np.array((0,0,(low+high)/2)))*scale
                chipped_stone(model,block_centre,axes,p*scale,height*scale,rng,coping=course==2)
    # A shallow, irregular soil mesh sits beneath the coping, with smooth normals.
    grid=np.linspace(-14.8,14.8,12)
    def at(x,y): return centre+np.array((x,y,soil_height(x,y)))*scale
    def normal(x,y):
        delta=.02
        dx=(soil_height(x+delta,y)-soil_height(x-delta,y))/(2*delta)
        dy=(soil_height(x,y+delta)-soil_height(x,y-delta))/(2*delta)
        return normalise((-dx,-dy,1))
    for x0,x1 in zip(grid,grid[1:]):
        for y0,y1 in zip(grid,grid[1:]):
            for coordinates in (((x0,y0),(x1,y0),(x1,y1)),((x0,y0),(x1,y1),(x0,y1))):
                F.face(model,SOIL,[at(x,y) for x,y in coordinates],(0,0,1),
                       [(x/64+.273,y/64+.419) for x,y in coordinates],
                       [normal(x,y) for x,y in coordinates])
    # Actual clods and a few small stones catch light above the dirt surface.
    for i in range(18):
        x,y=rng.uniform(-13.8,13.8,2)
        radius=rng.uniform(.22,.53)
        points=rng.uniform(.72,1.1,(10,1))*rng.normal(size=(10,3))
        points/=np.maximum(np.linalg.norm(points,axis=1,keepdims=True),1e-9)
        points*=np.array((radius,radius*.82,radius*.50))
        hull=ConvexHull(points)
        paint=STONE if i<5 else SOIL
        origin=at(x,y)+np.array((0,0,radius*.12))*scale
        for tri,equation in zip(hull.simplices,hull.equations):
            uv=None
            if paint==STONE:
                rect=PATCHES[i%len(PATCHES)];uc=(rect[0]+rect[2])/2;vc=1-(rect[1]+rect[3])/2
                uv=[(uc+p[0]/TILE,vc+p[1]/TILE) for p in points[tri]]
            F.face(model,paint,[origin+p*scale for p in points[tri]],equation[:3],uv)
    # The existing shrub starts at z~29.6. A single slender curved root joins it
    # to the recessed soil, rather than adding a bundle of parallel wooden stakes.
    nodes=((-0.45,.22,soil_height(-.45,.22)-.3),(-.24,.15,26.4),
           (.18,-.08,28.2),(0.,0.,30.1))
    radii=(.38,.32,.28,.24)
    for i,(a,b) in enumerate(zip(nodes,nodes[1:])):
        a,b=centre+np.asarray(a)*scale,centre+np.asarray(b)*scale
        axis=normalise(b-a)
        u=normalise(np.cross(axis,(0,1,0)))
        F.turned(model,a,axis,u,[(radii[i]*scale,0),(radii[i+1]*scale,np.linalg.norm(b-a))],
                 F.DARK,8,True,seed=seed)
    return model.triangle_count()-start
