"""Unique rock escarpment and broad, terrain-following cascade outside the playable compound."""
import math
import copy
import numpy as np
import map_kit as K
from scipy.ndimage import distance_transform_edt, minimum_filter, maximum_filter, gaussian_filter

# The front is authored by proportion-preserving photogrammetry instances.
# This mesh only closes the distant ridge; it must not become the visible face.
SCANS=((-1280,3650,-330,-8,3.65),(-120,3510,-330,3,3.8),
       (1230,3660,-330,-6,4.05),(2510,3880,-330,12,3.75))
DISTANT_SCANS=((-2400,7900,-1800,-28,9.0),(-280,8150,-1800,-3,9.5),
               (1800,8700,-1800,34,10.5))
# Wider crown channels converge while still on the upper rock slope; their
# lower free jets stay inside the existing compact plunge basin.
WATER_CHANNELS=((-80,190,250,95),(240,345,300,140),
                (605,530,255,100),(920,680,180,65))

class ScanFront:
    """Orthographic front-depth raster of the actual placed scan triangles.

    Water is fitted to this geometry rather than to a different analytic cliff.
    Twelve-inch sampling is much finer than a player's distant view of the fall.
    """
    def __init__(self,placements=SCANS,e0=-3500,z0=-340,shape=(161,600),step=12,default_height=900):
        vertices=[]; faces=[]
        for line in (K.ASSETS/'models/maps/forestbase/mountainside/cliff_lod0.obj').read_text().splitlines():
            if line.startswith('v '): vertices.append([float(x) for x in line.split()[1:4]])
            elif line.startswith('f '): faces.append([int(x.split('/')[0])-1 for x in line.split()[1:4]])
        obj=np.array(vertices); indices=np.array(faces)
        world=obj[:,[2,0,1]]
        self.step=step; self.e0=e0; self.z0=z0
        depth=np.full(shape,np.inf)
        for e,n,z,yaw,scale in placements:
            placed=world@K.rotation_matrix(0,yaw,0).T*scale+K.to_world((e,n,z))
            plan=placed[:,[1,0,2]]; plan[:,0]*=-1
            for triangle in plan[indices]:
                a,b,c=triangle
                det=(b[2]-c[2])*(a[0]-c[0])+(c[0]-b[0])*(a[2]-c[2])
                if abs(det)<1e-5: continue
                x0=max(0,math.ceil((min(triangle[:,0])-self.e0)/self.step))
                x1=min(depth.shape[1]-1,math.floor((max(triangle[:,0])-self.e0)/self.step))
                y0=max(0,math.ceil((min(triangle[:,2])-self.z0)/self.step))
                y1=min(depth.shape[0]-1,math.floor((max(triangle[:,2])-self.z0)/self.step))
                if x1<x0 or y1<y0: continue
                zz,ee=np.mgrid[y0:y1+1,x0:x1+1]
                ee=ee*self.step+self.e0; zz=zz*self.step+self.z0
                u=((b[2]-c[2])*(ee-c[0])+(c[0]-b[0])*(zz-c[2]))/det
                v=((c[2]-a[2])*(ee-c[0])+(a[0]-c[0])*(zz-c[2]))/det
                inside=(u>=-.001)&(v>=-.001)&(u+v<=1.001)
                values=u*a[1]+v*b[1]+(1-u-v)*c[1]
                patch=depth[y0:y1+1,x0:x1+1]
                np.minimum(patch,np.where(inside,values,np.inf),out=patch)
        self.heights=np.array([self.z0+self.step*np.flatnonzero(np.isfinite(depth[:,x]))[-1]
            if np.any(np.isfinite(depth[:,x])) else default_height for x in range(depth.shape[1])])
        missing=~np.isfinite(depth)
        nearest=distance_transform_edt(missing,return_distances=False,return_indices=True)
        depth=depth[tuple(nearest)]
        self.raw=depth
        self.column=np.min(depth,axis=0)
        # A falling sheet bridges small cavities rather than following every
        # crack; taking the front envelope keeps it out of protruding stones.
        self.depth=gaussian_filter(minimum_filter(depth,size=(7,5)),sigma=(2,1))-30
    def height(self,e):
        return float(np.interp((e-self.e0)/self.step,np.arange(len(self.heights)),self.heights))
    def jet(self,e):
        return float(np.interp((e-self.e0)/self.step,np.arange(len(self.column)),self.column))-90
    def front(self,e,z,lip=False):
        x=np.clip((e-self.e0)/self.step,0,self.depth.shape[1]-1.001)
        y=np.clip((z-self.z0)/self.step,0,self.depth.shape[0]-1.001)
        a,b=int(x),int(y); u,v=x-a,y-b
        d=self.raw if lip else self.depth
        return float((d[b,a]*(1-u)+d[b,a+1]*u)*(1-v)+(d[b+1,a]*(1-u)+d[b+1,a+1]*u)*v)

def noise(x,y,seed=17):
    def h(a,b):
        v=math.sin(a*127.1+b*311.7+seed*43.9)*43758.5453
        return (v-math.floor(v))*2-1
    a,b=math.floor(x),math.floor(y); u,v=x-a,y-b
    u=u*u*(3-2*u);v=v*v*(3-2*v)
    return ((h(a,b)*(1-u)+h(a+1,b)*u)*(1-v)+
            (h(a,b+1)*(1-u)+h(a+1,b+1)*u)*v)

def crest(e):
    shoulders=175*math.exp(-((e+800)/570)**2)+230*math.exp(-((e-1470)/640)**2)
    channel=330*math.exp(-((e-430)/525)**4)
    return 1450+shoulders+120*noise(e/460,3)+65*noise(e/95,9)-channel

def face(e,z):
    retreat=170*math.tanh((e-430)/1500)**2
    ledges=70*math.tanh((z-510)/45)+48*math.tanh((z-880)/35)
    relief=65*noise(e/320,z/400)+18*noise(e/45,z/70,41)
    return 3480+.18*(z+250)+ledges+retreat+relief

def mesh_grid(m,paint,fn,columns,rows,uv=False,reverse=False,horizontal=False,flat=False):
    def normal(u,v):
        a=fn(u+.0001,v)-fn(u-.0001,v)
        b=fn(u,v+.0001)-fn(u,v-.0001)
        n=K.normalise(np.cross(a,b))
        return -n if reverse else n
    for j in range(rows):
        for i in range(columns):
            coords=[(i/columns,j/rows),((i+1)/columns,j/rows),((i+1)/columns,(j+1)/rows),(i/columns,(j+1)/rows)]
            if reverse: coords.reverse()
            pts=[fn(u,v) for u,v in coords]
            ns=[normal(u,v) for u,v in coords]
            tile=m.tile_overrides.get(paint,220)
            tex=coords if uv else [(p[0]/tile,-p[1 if horizontal else 2]/tile) for p in pts]
            m.polygon(paint,pts,normals=None if flat else ns,uv=tex)

def build(m):
    if m.__class__.__name__=='CollisionOnlyModel': return
    m.material_overrides['cascade_rock']='materials/forestbase/cascade_rock.vmat'
    m.material_overrides['waterfall_impact']='materials/forestbase/waterfall_impact.vmat'
    m.tile_overrides['waterfall_impact']=256
    m.material_overrides['waterfall_plunge']='materials/forestbase/waterfall_plunge.vmat'
    m.tile_overrides['waterfall_plunge']=256
    # Rock Face 03 covers 2.7 metres, approximately 106 engine inches.
    m.tile_overrides['cascade_rock']=106
    scan=ScanFront()
    def close_scan(front,east0,east1,base,depth,columns,rows):
        # Photogrammetry contains deep undercuts. Fill them from behind with
        # an opaque terrain mass fitted to the placed scan's real crown.
        crown=gaussian_filter(front.heights.astype(float),4 if front.step==12 else 8)-55
        # Nearest-filled scan gaps can jump several metres in one column.
        # Recess their backing into a broad transition instead of extruding
        # that raster seam into a tall side-facing wall. Keep the water's
        # original front envelope and source heights independent of this fill.
        backing=copy.copy(front)
        backing.depth=np.maximum(front.depth,gaussian_filter(
            maximum_filter(front.depth,size=(3,21)),sigma=(2,6)))
        distant_ridge=front.step>12
        ridge_north=gaussian_filter(np.max(front.raw,axis=0),16)+400
        def backing_north(e,z):
            if not distant_ridge: return backing.front(e,z)+170
            # A continuous sloping mountain mass sits behind the far scans.
            # Their missing-depth raster is unsuitable for a visible side wall.
            x=(e-front.e0)/front.step
            n=float(np.interp(x,np.arange(len(ridge_north)),ridge_north))
            return n+.32*(z-base)
        def edge_taper(e):
            t=max(0,min(1,(e-east0)/600,(east1-e)/600))
            # Retain a narrow end section so cap and tangent normals remain
            # well-defined instead of collapsing the mesh to a line.
            return max(.025,t*t*(3-2*t))
        def height(e):
            x=(e-front.e0)/front.step
            crown_z=max(base+8,float(np.interp(x,np.arange(len(crown)),crown)))
            return base+(crown_z-base)*edge_taper(e)
        def wall(u,v):
            e=east0+(east1-east0)*u; z=base+(height(e)-base)*v
            # Use the scan-derived smooth envelope to avoid raster-shaped
            # facets. Broken, inclined beds add relief to exposed infill.
            # The positive retreat leaves the original scan in front.
            bed=(z+e*.075+28*noise(e/240,2))/115
            phase=bed-math.floor(bed)
            ledge=42*min(phase/.18,1)*(1-phase)
            joints=22*abs(noise(e/105,z/145,51))
            return np.array((e,backing_north(e,z)+ledge+joints,z))
        def top(u,v):
            e=east0+(east1-east0)*u; z=height(e)
            taper=edge_taper(e)
            n=wall(u,1)[1]+depth*v*taper
            return np.array((e,n,z+taper*(-160*v+45*noise(e/460,v*4)*math.sin(math.pi*v))))
        mesh_grid(m,'cascade_rock',wall,columns,rows)
        mesh_grid(m,'cascade_rock',top,columns,10,horizontal=True)
        for u in (0,1):
            a,b=wall(u,0),wall(u,1);c=top(u,1);d=c.copy();d[2]=base
            points=[a,b,c,d]
            if u==0: points.reverse()
            m.polygon('cascade_rock',points)
        mesh_grid(m,'cascade_rock',lambda u,v:top(u,1)*(1-v)+np.array((top(u,1)[0],top(u,1)[1],base))*v,columns,1,reverse=True)
    close_scan(scan,-2900,3600,-330,1050,144,64)
    distant=ScanFront(DISTANT_SCANS,e0=-6500,z0=-1900,shape=(190,600),step=24,default_height=-120)
    close_scan(distant,-4800,4500,-1900,1500,128,48)
    # Four unequal channels remain separated by exposed rock ribs. Their
    # irregular widths give the overall fall a broader, broken silhouette.
    impacts=[]
    for stream,(crown_center,center,crown_width,width) in enumerate(WATER_CHANNELS):
        source=min(scan.height(e) for e in np.linspace(crown_center-crown_width*.5,crown_center+crown_width*.5,19))-65
        paint=f'waterfall_{stream}'
        m.material_overrides[paint]=f'materials/forestbase/{paint}.vmat'
        m.tile_overrides[paint]=128
        K.write_text(K.ASSETS/f'materials/forestbase/{paint}.vmat',
            '"Layer0"\n{\n shader "shaders/forestbase_waterfall.shader"\n'
            ' FlowMask "materials/forestbase/waterfall_froth_v2.png"\n'
            f' FlowTop "{source:.3f}"\n FlowPhase "{stream*.37:.3f}"\n}}\n')
        progress=np.linspace(0,1,73)
        heights=source-(source+345)*progress
        def channel_center(v):
            t=min(1,max(0,v/.38)); t=t*t*(3-2*t)
            return crown_center+(center-crown_center)*t
        def channel_width(v):
            widen=1-.22*min(v/.25,1)+.32*v*v+.08*math.sin(v*11+stream)+.04*math.sin(v*29+stream*2)
            return width*widen+(crown_width-width)*(1-min(v/.45,1))**2
        envelope=np.array([min(scan.front(e,max(z,-260)) for e in
            np.linspace(channel_center(v)-channel_width(v)*.68,
                        channel_center(v)+channel_width(v)*.68,19))-12
            for v,z in zip(progress,heights)])
        # A free jet can pass a protruding ledge, but cannot turn back uphill
        # into the rock after it. Keep the outward envelope monotonic.
        envelope=np.minimum.accumulate(envelope)
        envelope=np.minimum(envelope,envelope[0]-(source-heights)*.06)
        def water(u,v):
            e=channel_center(v)+(u-.5)*channel_width(v)+math.sin(v*6+stream)*8*v
            # Continue below the opaque pool, so the jet cannot terminate as
            # a floating cut edge above the impact surface.
            z=source-(source+345)*v+8*math.sin(u*math.pi*3+stream)*(1-v)
            # The crown fans descend along the slope before narrowing into
            # free jets. Fit the envelope across their actual moving width.
            n=float(np.interp(v,progress,envelope))
            # Water bends over the crown, then develops a spreading foot.
            return np.array((e,n,z))
        # v increases downward: reverse winding to face the compound.
        mesh_grid(m,paint,water,16,72,uv=True,reverse=True)
        # The opaque scan hides the upstream river. A separate rectangular
        # inlet card left a bright straight line floating across the crown.
        e=center; n=float(np.interp((source+252)/(source+345),progress,envelope))
        impacts.append((center+math.sin((source+255)/(source+345)*6+stream)*8*(source+255)/(source+345),n))
        # Surface froth is shaded in the basin itself. One compact raised
        # plume supplies the aerated impact, avoiding stacked white foam cards.
        n-=12
        m.polygon('waterfall_impact',[(e-85,n,-250),(e+85,n,-250),
                                    (e+125,n-25,-65),(e-125,n-25,-65)],
                  uv=((0,1),(1,1),(1,0),(0,0)),both_sides=True)
        # Small wisps at the ledges, rather than a second full cloud per foot.
        for z,spread,height in ((source*.37,65,75),(source*.73,45,65)):
            v=(source-z)/(source+345)
            e=channel_center(v)
            n=float(np.interp(v,progress,envelope))-25
            m.polygon('waterfall_spray',[(e-spread,n-10,z-35),(e+spread,n-10,z-35),
                                        (e+spread*.7,n+15,z+height),(e-spread*.7,n+15,z+height)],
                      uv=((0,1),(1,1),(1,0),(0,0)),both_sides=True)
    # A low cloud spreads beyond the vertical jets across the entire impact
    # zone. Its feathered masks overlap in depth, with no hard rectangular edge.
    for e,n,z,spread,height in ((400,3120,-235,390,270),(520,3060,-200,450,310)):
        m.polygon('waterfall_spray',[(e-spread,n,z),(e+spread,n,z),
                                    (e+spread*.85,n+40,z+height),(e-spread*.85,n+40,z+height)],
                  uv=((0,1),(1,1),(1,0),(0,0)),both_sides=True)
    # Opaque rippled water and foam share the actual pool surface. Impact
    # uniforms are derived from these jets instead of guessed shader positions.
    m.material_overrides['plunge_basin']='materials/forestbase/plunge_basin.vmat'
    m.tile_overrides['plunge_basin']=128
    params=''.join(f' ImpactEast{i} "{e:.3f}"\n ImpactNorth{i} "{n:.3f}"\n' for i,(e,n) in enumerate(impacts))
    K.write_text(K.ASSETS/'materials/forestbase/plunge_basin.vmat',
        '"Layer0"\n{\n shader "shaders/forestbase_basin.shader"\n'
        ' FrothMask "materials/forestbase/waterfall_foam_mask.png"\n'+params+'}\n')
    # Irregular opaque pool closes the plunge basin without rectangular edges.
    pool=[]
    for t in np.linspace(0,math.tau,48,endpoint=False):
        r=1+.045*math.sin(t*5)+.035*math.sin(t*9)
        pool.append((430+math.cos(t)*540*r,3370+math.sin(t)*450*r,-255))
    m.polygon('plunge_basin',pool)
