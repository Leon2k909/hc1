"""Scanned shoreline rocks and a smooth wet bank outside the playable footprint."""
import math
import numpy as np
import map_kit as K
from forestbase_floor import BASIN_BOUNDS
from forestbase_cascade import basin_radius

RESOURCE='models/maps/forestbase'
MATERIAL='materials/forestbase/shore_rock.vmat'

def materials():
    for name,folder,color,normal,rough,ao in (
        ('shore_rock','models/maps/forestbase/boulder','diff.jpg','nor_gl.jpg','rough.png','ao.png'),
        ('shore_bank','materials/forestbase/scans','mud_forest_diff.jpg','mud_forest_nor_gl.jpg','mud_forest_rough.jpg','mud_forest_ao.jpg')):
        K.write_text(K.ASSETS/f'materials/forestbase/{name}.vmat',
            '"Layer0"\n{\n shader "shaders/forestbase_shore.shader"\n F_SPECULAR "1"\n'
            f' TextureColor "{folder}/{color}"\n TextureNormal "{folder}/{normal}"\n'
            f' TextureRoughness "{folder}/{rough}"\n TextureAmbientOcclusion "{folder}/{ao}"\n'
            ' TextureMetalness "[0 0 0 0]"\n'+
            (' ShoreSoil "1"\n' if name=='shore_bank' else '')+'}\n')
    template=(K.ASSETS/'models/maps/forestbase/boulder/cliff.vmdl').read_text()
    K.write_text(K.ASSETS/f'{RESOURCE}/shore_boulder.vmdl',template.replace('models/maps/forestbase/boulder/cliff.vmat',MATERIAL))
    grass=(K.ASSETS/'models/grass/grass_far.vmat').read_text()
    grass=grass.replace('g_flRiseStart "1000.000"','g_flRiseStart "0.000"').replace('g_flRiseEnd "1450.000"','g_flRiseEnd "0.000"')
    grass=grass.replace('TextureColor "models/grass/grass_blades.png"','g_flTintColor "[.66 .72 .58]"\n\tTextureColor "models/grass/grass_blades.png"')
    K.write_text(K.ASSETS/'materials/forestbase/shore_grass.vmat',grass)
    template=(K.ASSETS/'models/grass/grass_far_short.vmdl').read_text()
    K.write_text(K.ASSETS/f'{RESOURCE}/shore_grass.vmdl',template.replace('models/grass/grass_far.vmat','materials/forestbase/shore_grass.vmat'))

def bank(angle,depth):
    x,y=math.cos(angle),math.sin(angle); ray=max(abs(x),abs(y))
    e0,e1,n0,n1=BASIN_BOUNDS
    outer=np.array(((e0+e1)/2+x*(e1-e0)/2/ray,
                    (n0+n1)/2+y*(n1-n0)/2/ray,-120))
    # Use the pool's own contour, inset far enough for its opaque surface to
    # end beneath the bank. Independent outlines left narrow strips of air.
    variation=basin_radius(angle)
    inner=np.array((430+x*540*.86*variation,3370+y*450*.86*variation,-285+math.sin(angle*7)*8))
    p=inner*(1-depth)+outer*depth
    # Meet the flat outer forest floor tangentially instead of leaving a lit
    # rectangular crease. Both rims stay fixed, including the submerged one.
    eased=1-(1-depth)**3
    p[2]=inner[2]*(1-eased)+outer[2]*eased
    p[2]+=math.sin(depth*math.pi)**2*(7*math.sin(angle*13+depth*4)+4*math.cos(angle*19-depth*5))
    return p

def build(m,instances):
    rng=np.random.default_rng(6334)
    for index,angle in enumerate((3.33,3.68,4.12,4.95,5.37,5.90)):
        size=rng.uniform(42,85)
        position=(430+math.cos(angle)*550,3370+math.sin(angle)*465,-285)
        instances.append((f'Shore boulder {index}',f'{RESOURCE}/shore_boulder.vmdl',position,
                          float(rng.uniform(0,360)),(size,size*.82,size*.95)))
    grass=np.random.default_rng(17714)
    for index in range(24):
        angle=float(grass.uniform(3.2,6.25));depth=float(grass.uniform(.70,.96))
        position=bank(angle,depth);position[2]-=2
        scale=float(grass.uniform(1.15,1.70))
        instances.append((f'Shore grass {index}',f'{RESOURCE}/shore_grass.vmdl',tuple(position),
                          float(grass.uniform(0,360)),(scale,)*3))
    if m.__class__.__name__=='CollisionOnlyModel':return
    m.material_overrides['shore_bank']='materials/forestbase/shore_bank.vmat'
    m.material_overrides['shore_rock']=MATERIAL
    m.tile_overrides.update(shore_bank=92,shore_rock=80)
    shift=K.uv_offset(getattr(m,'uv_source_name','vista'))
    tile=m.tile_overrides['shore_bank']
    def normal(angle,depth):
        a=bank(angle+.0001,depth)-bank(angle-.0001,depth)
        b=bank(angle,depth+.0001)-bank(angle,depth-.0001)
        n=K.normalise(np.cross(a,b))
        return n if n[2]>0 else -n
    for k in range(96):
        a,b=math.tau*k/96,math.tau*(k+1)/96
        for start,end in zip(np.linspace(0,1,9)[:-1],np.linspace(0,1,9)[1:]):
            coords=[(a,start),(b,start),(b,end),(a,end)]
            points=[bank(*x) for x in coords]
            if np.cross(points[1]-points[0],points[2]-points[0])[2]<0:
                coords.reverse();points.reverse()
            # Continue the existing floor's scan chart across the bank. Facet
            # projection rotated it at every slope and exposed the square rim.
            uv=[(e/tile+shift[0],n/tile+shift[1]) for e,n,z in points]
            m.polygon('shore_bank',points,normals=[normal(*x) for x in coords],uv=uv)
    # Reuse the scan's far mesh/UVs for small stones, merged in the existing vista.
    vertices=[];uv=[];normals=[];faces=[]
    for line in (K.ASSETS/f'{RESOURCE}/boulder/cliff_lod2.obj').read_text().splitlines():
        if line.startswith('v '):vertices.append([float(x) for x in line.split()[1:]])
        elif line.startswith('vt '):uv.append([float(x) for x in line.split()[1:]])
        elif line.startswith('vn '):normals.append([float(x) for x in line.split()[1:]])
        elif line.startswith('f '):faces.append([tuple(int(x)-1 for x in item.split('/')) for item in line.split()[1:]])
    assert vertices and uv and normals and all(len(v)==3 for face in faces for v in face)
    vertices=np.asarray(vertices)[:,[0,2,1]];vertices[:,0]*=-1
    normals=np.asarray(normals)[:,[0,2,1]];normals[:,0]*=-1
    for index in range(34):
        angle=float(rng.uniform(3.20,6.20));depth=float(rng.uniform(.08,.58))
        center=bank(angle,depth);size=float(rng.uniform(8,24))
        center[2]-=size*.35
        scale=np.array((size,size*rng.uniform(.65,1.05),size*rng.uniform(.85,1.35)))
        yaw=float(rng.uniform(0,math.tau));c,s=math.cos(yaw),math.sin(yaw)
        rotation=np.array(((c,-s,0),(s,c,0),(0,0,1)))
        placed=vertices*scale@rotation.T+center
        ns=(normals/scale)@rotation.T
        ns/=np.linalg.norm(ns,axis=1,keepdims=True)
        for face in faces:
            m.polygon('shore_rock',[placed[v] for v,t,n in face],
                      uv=[uv[t] for v,t,n in face],normals=[ns[n] for v,t,n in face])

if __name__=='__main__':materials()
