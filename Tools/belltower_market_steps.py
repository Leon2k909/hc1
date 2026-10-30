"""Worn, individually jointed stone treads for the market cross only."""
import math
from collections import Counter
import numpy as np
from scipy.spatial import Delaunay
import map_kit as K
import belltower_furniture as F
import belltower_planters as P
import belltower_stone_chips as Chips

STONE='market_step_stone_v2'
MORTAR='well_mortar'
MATERIALS={STONE:'materials/belltower/market-steps-v2/stone.vmat',
           MORTAR:'materials/belltower/well-v1/well_mortar.vmat'}
TIERS=((100.,0.,12.,4),(80.,12.,24.,3),(60.,24.,36.,2))
REPORT={}


def inset(poly,amounts):
    edges=np.roll(poly,-1,axis=0)-poly
    ns=np.column_stack((-edges[:,1],edges[:,0]))
    ns/=np.linalg.norm(ns,axis=1)[:,None]
    offsets=np.einsum('ij,ij->i',ns,poly)+np.asarray(amounts)
    return np.array([np.linalg.solve(np.array((ns[i-1],ns[i])),offsets[[i-1,i]]) for i in range(len(poly))])


def block(model,poly,low,high,rng):
    poly=np.asarray(poly,float);origin=poly.mean(axis=0);poly-=origin
    edge=poly[1]-poly[0];along=edge/np.linalg.norm(edge)
    inward=np.array((-along[1],along[0]))
    radius=rng.uniform(.72,1.10)
    top=high-rng.uniform(.015,.13)
    radii=np.array((radius,.14,.18,.14))
    profiles=[(low+.025,np.full(4,.12)),(low+.18,np.zeros(4)),(top-radius,np.zeros(4))]
    profiles += [(top-radius+radius*math.sin(t),radii*(1-math.cos(t)))
                 for t in np.linspace(math.pi/10,math.pi/2,5)]
    vertices=[];faces=[]
    for z,offsets in profiles:
        vertices.extend((*p,z) for p in inset(poly,offsets))
    for ring in range(len(profiles)-1):
        for i in range(4):
            a,b=ring*4+i,ring*4+(i+1)%4;c,d=a+4,b+4
            faces.extend(((a,b,d),(a,d,c)))
    faces.extend(((0,2,1),(0,3,2)))
    rim=(len(profiles)-1)*4;top_poly=np.asarray(vertices)[rim:rim+4,:2]
    top_points=list(top_poly)
    for u in (.25,.5,.75):
        for v in (.25,.5,.75):
            top_points.append((1-v)*((1-u)*top_poly[0]+u*top_poly[1])+v*((1-u)*top_poly[3]+u*top_poly[2]))
    ids=list(range(rim,rim+4));dip=rng.uniform(.08,.17)
    for p in top_points[4:]:
        ids.append(len(vertices));vertices.append((*p,top-dip*max(0.,1-float(np.linalg.norm(p)/max(np.linalg.norm(top_poly,axis=1))))**2))
    for tri in Delaunay(np.asarray(top_points)).simplices:
        ids_tri=[ids[i] for i in tri]
        if np.cross(np.asarray(top_points)[tri[1]]-top_points[tri[0]],np.asarray(top_points)[tri[2]]-top_points[tri[0]])<0:ids_tri.reverse()
        faces.append(tuple(ids_tri))
    vertices=np.asarray(vertices);faces=np.asarray(faces)
    if rng.random()<.28:
        pos=poly[0]+rng.uniform(.18,.82)*(poly[1]-poly[0])
        vertices,faces=Chips.chipped_mesh(vertices,faces,
            [((*pos,top-.38),(*inward,-.65),rng.uniform(2.0,3.0),rng.uniform(.55,.85))])
    vertices=np.round(vertices,3)
    edges=Counter(tuple(sorted((tuple(vertices[f[i]]),tuple(vertices[f[(i+1)%3]])))) for f in faces for i in range(3))
    assert set(edges.values())=={2},'Stone must remain closed at OBJ precision.'
    cross=np.cross(vertices[faces[:,1]]-vertices[faces[:,0]],vertices[faces[:,2]]-vertices[faces[:,0]])
    area=np.linalg.norm(cross,axis=1);assert np.all(area>1e-7)
    normals=cross/area[:,None]
    adjacent={i:[] for i in range(len(vertices))}
    for i,f in enumerate(faces):
        for v in f:adjacent[v].append(i)
    # Sample photographed stone interiors. Each block has its own patch and orientation.
    rect=P.PATCHES[int(rng.integers(len(P.PATCHES)))];uv_centre=np.array(((rect[0]+rect[2])/2,1-(rect[1]+rect[3])/2))
    x=vertices[:,:2]@along;y=vertices[:,:2]@inward
    projected=np.column_stack((x,y+vertices[:,2]-top));span=np.ptp(projected,axis=0)
    tile=max(P.TILE,span[0]/(rect[2]-rect[0]-.018),span[1]/(rect[3]-rect[1]-.018))
    middle=(projected.min(axis=0)+projected.max(axis=0))/2
    for i,f in enumerate(faces):
        uv=uv_centre+(projected[f]-middle)/tile
        if abs(float(np.dot(normals[i,:2],along)))>.7:
            side=np.column_stack((y,vertices[:,2]));mid=(side.min(axis=0)+side.max(axis=0))/2
            side_tile=max(tile,np.ptp(side[:,0])/(rect[2]-rect[0]-.018),np.ptp(side[:,1])/(rect[3]-rect[1]-.018))
            uv=uv_centre+(side[f]-mid)/side_tile
        assert np.all(uv[:,0]>=rect[0]) and np.all(uv[:,0]<=rect[2])
        assert np.all(uv[:,1]>=1-rect[3]) and np.all(uv[:,1]<=1-rect[1])
        ns=[]
        for v in f:
            near=np.asarray(adjacent[v]);keep=near[normals[near]@normals[i]>.82]
            n=normals[keep].sum(axis=0);ns.append(n/np.linalg.norm(n))
        points=vertices[f]+np.array((*origin,0.))
        model.polygon(STONE,points,normals[i],uv=uv,normals=ns)
    REPORT['blocks']=REPORT.get('blocks',0)+1
    REPORT['closed_blocks']=REPORT.get('closed_blocks',0)+1


def build(model,centre,surface=None):
    REPORT.clear();rng=np.random.default_rng(771903);centre=np.asarray(centre,float)
    model.material_overrides.update(MATERIALS)
    model.tile_overrides.update({STONE:P.TILE,MORTAR:P.TILE})
    def ring(inner,outer,low,high,count):
        points=lambda r,k:centre+r*np.array((math.cos(math.pi/8+k*math.pi/4),math.sin(math.pi/8+k*math.pi/4)))
        for k in range(8):
            ends=np.r_[0.,np.cumsum(rng.uniform(.78,1.22,count))];ends/=ends[-1]
            for a,b in zip(ends,ends[1:]):
                gap=.10/max(1.,np.linalg.norm(points(outer,k+1)-points(outer,k)))
                a+=gap;b-=gap
                at=lambda r,t:points(r,k)*(1-t)+points(r,k+1)*t
                block(model,[at(outer,a),at(outer,b),at(inner,b),at(inner,a)],low,high,rng)
    for radius,low,high,count in TIERS:
        # Gameplay hulls match the previous three original octagonal tiers exactly.
        model.cylinder(centre,radius,low,high,{},sides=8,surface=surface,turn=math.pi/8)
        model.cylinder(centre,radius-1.5,low+.08,high-.95,
            {'side':MORTAR,'top':MORTAR},sides=8,turn=math.pi/8)
        ring(radius-26,radius,low,high,count)
    ring(10.,33.8,24.08,36.,1)
    model.cylinder(centre,10.5,24.,35.1,{'top':MORTAR,'side':MORTAR},sides=8,turn=math.pi/8)
    REPORT.update(tiers=3,step_heights=[12.,24.,36.],radii=[100.,80.,60.])
    return dict(REPORT)
