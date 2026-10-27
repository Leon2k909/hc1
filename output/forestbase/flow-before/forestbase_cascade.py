"""Unique rock escarpment and broad, terrain-following cascade outside the playable compound."""
import math
import numpy as np
import map_kit as K
from scipy.ndimage import distance_transform_edt, minimum_filter, gaussian_filter

# The front is authored by proportion-preserving photogrammetry instances.
# This mesh only closes the distant ridge; it must not become the visible face.
SCANS=((-1280,3650,-330,-8,3.65),(-120,3510,-330,3,3.8),
       (1230,3660,-330,-6,4.05),(2510,3880,-330,12,3.75))

class ScanFront:
    """Orthographic front-depth raster of the actual placed scan triangles.

    Water is fitted to this geometry rather than to a different analytic cliff.
    Twelve-inch sampling is much finer than a player's distant view of the fall.
    """
    def __init__(self):
        vertices=[]; faces=[]
        for line in (K.ASSETS/'models/maps/forestbase/mountainside/cliff_lod0.obj').read_text().splitlines():
            if line.startswith('v '): vertices.append([float(x) for x in line.split()[1:4]])
            elif line.startswith('f '): faces.append([int(x.split('/')[0])-1 for x in line.split()[1:4]])
        obj=np.array(vertices); indices=np.array(faces)
        world=obj[:,[2,0,1]]
        self.step=12; self.e0=-3500; self.z0=-340
        depth=np.full((161,600),np.inf)
        for e,n,z,yaw,scale in SCANS:
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
            if np.any(np.isfinite(depth[:,x])) else 900 for x in range(depth.shape[1])])
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
            tex=coords if uv else [(p[0]/220,-p[1 if horizontal else 2]/220) for p in pts]
            m.polygon(paint,pts,normals=None if flat else ns,uv=tex)

def build(m):
    if m.__class__.__name__=='CollisionOnlyModel': return
    m.material_overrides['cascade_rock']='materials/forestbase/cascade_rock.vmat'
    m.material_overrides['waterfall_impact']='materials/forestbase/waterfall_impact.vmat'
    m.tile_overrides['waterfall_impact']=256
    m.material_overrides['waterfall_plunge']='materials/forestbase/waterfall_plunge.vmat'
    m.tile_overrides['waterfall_plunge']=256
    m.tile_overrides['cascade_rock']=220
    scan=ScanFront()
    def wall(u,v):
        e=-2900+6500*u; z=-325+(crest(e)-300)*v
        return np.array((e,face(e,z)+450,z))
    mesh_grid(m,'cascade_rock',wall,80,32)
    # Close the crown with a sloping upland. Its silhouette comes from one
    # continuous height field, rather than scaled copies of a single flat rock.
    def top(u,v):
        e=-2900+6500*u; z=crest(e)-625
        return np.array((e,face(e,z)+450+900*v,z+140*math.sin(v*math.pi)+65*noise(e/520,v*3)*v))
    mesh_grid(m,'cascade_rock',top,80,10,horizontal=True)
    for u in (0,1):
        e=-2900+6500*u; z=crest(e)-625
        pts=[(e,face(e,-325)+450,-325),(e,face(e,z)+450,z),(e,face(e,z)+1350,z),(e,face(e,-325)+1350,-325)]
        if u==0: pts.reverse()
        m.polygon('cascade_rock',pts)
    # A channel visible at the crown supplies the fall, with three broad
    # main streams separated by exposed rock ribs, like the reference.
    for stream,(center,width) in enumerate(((190,75),(345,110),(530,85),(680,55))):
        source=min(scan.height(e) for e in np.linspace(center-width*.5,center+width*.5,15))-65
        def water(u,v):
            widen=1+.42*v+.16*math.sin(v*17+stream)+.055*math.sin(v*47+stream*3)
            e=center+(u-.5)*width*widen+math.sin(v*8+stream)*7*v
            # Continue below the opaque pool, so the jet cannot terminate as
            # a floating cut edge above the impact surface.
            z=source-(source+345)*v
            # Fit a smooth front envelope of the highest-detail cliff. Narrow
            # streams expose the ledges and diverge around the irregular rock.
            n=scan.front(e,max(z,-260))-20
            # Water bends over the crown, then develops a spreading foot.
            return np.array((e,n,z))
        # v increases downward: reverse winding to face the compound.
        mesh_grid(m,'waterfall',water,16,72,uv=True,reverse=True)
        inlet=[]
        for e in (center-width*.48,center+width*.48):
            for d in (0,100): inlet.append((e,scan.front(e,source)+d,source+2))
        m.polygon('river',[inlet[0],inlet[2],inlet[3],inlet[1]])
        e=center; n=scan.front(e,-252)-30
        m.polygon('waterfall_foam',[(e-160,n-320,-250),(e+160,n-320,-250),(e+160,n+65,-250),(e-160,n+65,-250)],
                  uv=((0,0),(1,0),(1,1),(0,1)))
        # Concentrated white spray occupies the exact pool intersection. The
        # wider, weaker cloud above it supplies drifting atmospheric mist.
        n=scan.front(e,-255)-65
        m.polygon('waterfall_impact',[(e-160,n,-250),(e+160,n,-250),
                                    (e+155,n-20,60),(e-155,n-20,60)],
                  uv=((0,1),(1,1),(1,0),(0,0)),both_sides=True)
        n=scan.front(e,-255)-20
        m.polygon('waterfall_plunge',[(e-145,n-225,-252),(e+145,n-225,-252),
                                    (e+145,n+70,-252),(e-145,n+70,-252)],
                  uv=((0,0),(1,0),(1,1),(0,1)))
        # Broad spray fans cover the turbulent foot and the two ledge impacts.
        for z,spread,height in ((-240,245,300),(source*.37,100,130),(source*.73,75,100)):
            n=scan.front(e,z)-100
            m.polygon('waterfall_spray',[(e-spread,n-10,z-35),(e+spread,n-10,z-35),
                                        (e+spread*.7,n+15,z+height),(e-spread*.7,n+15,z+height)],
                      uv=((0,1),(1,1),(1,0),(0,0)),both_sides=True)
    # A low cloud spreads beyond the vertical jets across the entire impact
    # zone. Its feathered masks overlap in depth, with no hard rectangular edge.
    for e,n,z,spread,height in ((170,2990,-175,370,520),(485,3040,-150,450,560),(810,3090,-165,350,470)):
        m.polygon('waterfall_spray',[(e-spread,n,z),(e+spread,n,z),
                                    (e+spread*.85,n+40,z+height),(e-spread*.85,n+40,z+height)],
                  uv=((0,1),(1,1),(1,0),(0,0)),both_sides=True)
    # Irregular opaque pool closes the plunge basin without rectangular edges.
    pool=[]
    for t in np.linspace(0,math.tau,48,endpoint=False):
        r=1+.045*math.sin(t*5)+.035*math.sin(t*9)
        pool.append((430+math.cos(t)*540*r,3500+math.sin(t)*450*r,-255))
    m.polygon('river',pool)
