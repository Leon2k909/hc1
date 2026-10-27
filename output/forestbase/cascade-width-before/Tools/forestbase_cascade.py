"""Unique rock escarpment and broad, terrain-following cascade outside the playable compound."""
import math
import copy
import numpy as np
import map_kit as K
from scipy.ndimage import distance_transform_edt, minimum_filter, maximum_filter, gaussian_filter

# The front is authored by proportion-preserving photogrammetry instances.
# This mesh only closes the distant ridge; it must not become the visible face.
SCANS=((-1280,3650,-330,-8,3.65),(-120,3510,-330,3,3.8),
       (1230,3660,-330,-6,4.05),(2510,3880,-330,12,3.75),
       (900,3790,-400,14,4.05))
DISTANT_SCANS=((-2400,7900,-1800,-28,9.0),(-280,8150,-1800,-3,9.5),
               (1800,8700,-1800,34,10.5))
# Height, forward advance, and vertical rounding of two shared rock ledges.
# These remain outside the playable compound and add no collision.
WATER_TERRACES=((650,48,28),(230,52,32))

def terrace_level(level,index,u):
    return level+14*math.sin(u*19+index*2)+8*noise(u*11,index+23)

def terrace_offset(z,u):
    offset=0.
    for index,(level,advance,rounding) in enumerate(WATER_TERRACES):
        level=terrace_level(level,index,u)
        t=max(0.,min(1.,(level+rounding*.5-z)/rounding))
        offset+=advance*t*t*(3-2*t)
    return offset

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

def basin_outline():
    return [np.array((430+math.cos(t)*540*r,3370+math.sin(t)*450*r,-255))
            for t in np.linspace(0,math.tau,48,endpoint=False)
            for r in (1+.045*math.sin(t*5)+.035*math.sin(t*9),)]

class CascadeProfile:
    """One connected water surface: neighbouring bands share all edge vertices.

    Each column follows its actual rock envelope. Ledge advance tapers before
    the existing basin rim, instead of pushing wide flows into the bank.
    """
    def __init__(self,scan):
        self.scan=scan
        self.us=np.linspace(0,1,97);self.vs=np.linspace(0,1,129)
        heights=np.array([scan.height(-245+1315*u) for u in self.us])
        self.sources=np.minimum(heights-45,gaussian_filter(minimum_filter(heights,size=5),1)-45)
        north=np.array([[scan.front(self.east(u,v),self.height(u,v))-12
                         for u in self.us] for v in self.vs])
        north=np.minimum(north,gaussian_filter(minimum_filter(north,size=(3,5)),(.7,1)))
        self.north=np.minimum.accumulate(north,axis=0)
        rim=basin_outline()
        def front(e):
            values=[]
            for a,b in zip(rim,rim[1:]+rim[:1]):
                if min(a[0],b[0])<=e<=max(a[0],b[0]) and abs(b[0]-a[0])>1e-6:
                    values.append(a[1]+(b[1]-a[1])*(e-a[0])/(b[0]-a[0]))
            return min(values)+24
        available=np.array([self.north[-1,j]-front(self.east(u,1)) for j,u in enumerate(self.us)])
        # All columns must fit before any outward ledge advance is applied.
        assert np.min(available)>0,'Rock envelope leaves insufficient basin clearance'
        factors=np.clip(available/sum(t[1] for t in WATER_TERRACES),0,1)
        self.advance=np.minimum(factors,gaussian_filter(minimum_filter(factors,size=5),1))

    def source(self,u):return float(np.interp(u,self.us,self.sources))
    def height(self,u,v):return self.source(u)*(1-v)-345*v
    def east(self,u,v):
        t=max(0,min(1,v/.75));t=t*t*(3-2*t)
        return 412.5+(430-412.5)*t+(u-.5)*(1315+(640-1315)*t)
    def __call__(self,u,v):
        x=np.clip(u*96,0,95.999999);y=np.clip(v*128,0,127.999999)
        a,b=int(x),int(y);du,dv=x-a,y-b
        north=((self.north[b,a]*(1-du)+self.north[b,a+1]*du)*(1-dv)+
               (self.north[b+1,a]*(1-du)+self.north[b+1,a+1]*du)*dv)
        z=self.height(u,v)
        north-=terrace_offset(z,u)*float(np.interp(u,self.us,self.advance))
        return np.array((self.east(u,v),north,z))

def crest(e):
    shoulders=175*math.exp(-((e+800)/570)**2)+230*math.exp(-((e-1470)/640)**2)
    channel=330*math.exp(-((e-430)/525)**4)
    return 1450+shoulders+120*noise(e/460,3)+65*noise(e/95,9)-channel

def face(e,z):
    retreat=170*math.tanh((e-430)/1500)**2
    ledges=70*math.tanh((z-510)/45)+48*math.tanh((z-880)/35)
    relief=65*noise(e/320,z/400)+18*noise(e/45,z/70,41)
    return 3480+.18*(z+250)+ledges+retreat+relief

def mesh_grid(m,paint,fn,columns,rows,uv=False,reverse=False,horizontal=False,flat=False,uv_transform=None):
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
            tex=[uv_transform(u,v) for u,v in coords] if uv_transform else coords if uv else [(p[0]/tile,-p[1 if horizontal else 2]/tile) for p in pts]
            m.polygon(paint,pts,normals=None if flat else ns,uv=tex)

def terrace_rock(m,water):
    """Closed rock shelves directly beneath the two bends of a broad flow.

    Top faces follow the same water profile with a small recessed offset. Their
    landward backs overlap the scanned cliff rather than leaving floating slabs.
    """
    for index,(level,advance,rounding) in enumerate(WATER_TERRACES):
        def surface(u,v):
            # A broken stone rim extends a little beyond the foamy water edge.
            uu=(u-.5)*1.04+.5
            source=water.source(uu)
            z=terrace_level(level,index,uu)+rounding*(.5-v)
            vv=(source-z)/(source+345)
            p=water(uu,vv)+np.array((0.,6.,-4.))
            edge=max(0,min(1,(.30-min(u,1-u))/.30))
            edge=edge*edge*(3-2*edge)
            p[2]-=65*edge
            # Bury shelf ends in the actual cliff instead of exposing the
            # rectangular side caps of a freestanding wedge.
            retreat=max(600,water.scan.front(p[0],p[2],lip=True)+180-p[1])
            p[1]+=retreat*edge
            return p
        def back(u):
            p=surface(u,0).copy()
            p[1]+=230+35*noise(p[0]/150,index+level/200)
            p[2]+=22+12*noise(p[0]/95,index+4)
            return p
        def lower(u):
            p=surface(u,1).copy()
            p[1]+=30+26*noise(p[0]/70,index+7)
            p[2]-=88+30*noise(p[0]/95,index+9)
            return p
        mesh_grid(m,'cascade_rock',surface,24,8,reverse=True,horizontal=True)
        mesh_grid(m,'cascade_rock',lambda u,v:back(u)*(1-v)+surface(u,0)*v,
                  24,4,reverse=True,horizontal=True)
        mesh_grid(m,'cascade_rock',lambda u,v:surface(u,1)*(1-v)+lower(u)*v,
                  24,5,reverse=True)
        # Close the landward and lower faces as well as the two fracture ends.
        def back_lower(u):
            p=back(u).copy();p[2]=lower(u)[2]
            return p
        mesh_grid(m,'cascade_rock',lambda u,v:back(u)*(1-v)+back_lower(u)*v,24,1)
        mesh_grid(m,'cascade_rock',lambda u,v:lower(u)*(1-v)+back_lower(u)*v,24,1,
                  reverse=True,horizontal=True)
        for u in (0,1):
            points=[back(u),surface(u,0),surface(u,1),lower(u),back_lower(u)]
            if u==0:points.reverse()
            m.polygon('cascade_rock',points)

def build(m,material_output=None):
    if m.__class__.__name__=='CollisionOnlyModel': return
    material_output=K.ASSETS/'materials/forestbase' if material_output is None else material_output
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
    # The wider flows nearly meet, with rough edges breaking their silhouette.
    # Two stone shelves interrupt the vertical fall at common world heights.
    water=CascadeProfile(scan)
    terrace_rock(m,water)
    impacts=[]
    for stream in range(4):
        paint=f'waterfall_{stream}'
        m.material_overrides[paint]='materials/forestbase/waterfall_0.vmat'
        m.tile_overrides[paint]=128
        K.write_text(material_output/f'{paint}.vmat',
            '"Layer0"\n{\n shader "shaders/forestbase_waterfall.shader"\n'
            ' FlowMask "materials/forestbase/waterfall_froth_v2.png"\n'
            f' FlowTop "{max(water.sources):.3f}"\n FlowPhase "0"\n FlowTiling "4"\n}}\n')
        # Adjacent material bands use shared global UVs and identical phases.
        # They join without the four edge fades of the former separate jets.
        mesh_grid(m,paint,lambda u,v:water((stream+u)/4,v),24,128,
                  reverse=True,uv_transform=lambda u,v:((stream+u)/4,v))
        u=(stream+.5)/4;source=water.source(u)
        impact=water(u,(source+255)/(source+345))
        e,n=impact[:2];impacts.append((e,n))
        n-=12
        m.polygon('waterfall_impact',[(e-85,n,-250),(e+85,n,-250),
                                    (e+125,n-25,-65),(e-125,n-25,-65)],
                  uv=((0,1),(1,1),(1,0),(0,0)),both_sides=True)
        for index,(level,advance,rounding) in enumerate(WATER_TERRACES):
            z=terrace_level(level,index,u)
            e,n=water(u,(source-z)/(source+345))[:2];n-=25
            spread,height=65,75
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
    K.write_text(material_output/'plunge_basin.vmat',
        '"Layer0"\n{\n shader "shaders/forestbase_basin.shader"\n'
        ' FrothMask "materials/forestbase/waterfall_foam_mask.png"\n'+params+'}\n')
    # Irregular opaque pool closes the plunge basin without rectangular edges.
    m.polygon('plunge_basin',basin_outline())
