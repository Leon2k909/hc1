"""The two approved monitor backs: moulded charcoal and graphite/aluminium.

All dimensions use the console's original local frame. These are visual meshes;
the console generator still owns its unmodified cover collision and LCD faces.
Vents are recessed geometry, so they also hold up at an oblique player angle.
"""
import math

import numpy as np

FINISHES = {
    "rh_monitor_graphite": ((0.30, 0.32, 0.34), 0.46, 0.0),
    "rh_monitor_trim": ((0.17, 0.19, 0.21), 0.42, 0.0),
    "rh_monitor_recess": ((0.045, 0.052, 0.060), 0.76, 0.0),
    "rh_monitor_aluminium": ((0.68, 0.70, 0.72), 0.33, 0.95),
    "rh_monitor_label": ((0.37, 0.40, 0.42), 0.65, 0.0),
    "rh_monitor_ink": ((0.12, 0.14, 0.15), 0.72, 0.0),
}
SHELL, TRIM, DARK, METAL, LABEL, INK = FINISHES


def write_textures(folder):
    """Small deterministic PBR finish maps, shared by all sixteen displays."""
    from PIL import Image
    from scipy.ndimage import gaussian_filter
    rng = np.random.default_rng(141026)
    grain = gaussian_filter(rng.normal(size=(256,256)),0.65,mode="wrap")
    grain /= grain.std()
    brush = gaussian_filter(rng.normal(size=(256,256)),(12,0.7),mode="wrap")
    brush /= brush.std()
    for name,height,strength,rough in (("polymer",grain,0.045,0.46),
                                        ("brushed",brush,0.025,0.33)):
        dx=(np.roll(height,-1,1)-np.roll(height,1,1))*strength
        dy=(np.roll(height,-1,0)-np.roll(height,1,0))*strength
        normal=np.stack((-dx,dy,np.ones_like(dx)),axis=-1)
        normal/=np.linalg.norm(normal,axis=-1,keepdims=True)
        Image.fromarray(np.uint8(np.clip((normal*0.5+0.5)*255,0,255))).save(folder/f"rh_monitor_{name}_normal.png")
        Image.fromarray(np.uint8(np.clip((rough+height*0.018)*255,0,255))).save(folder/f"rh_monitor_{name}_rough.png")


def variant(index, centre):
    # Six + six + four displays: inverse paired runs in the two long banks give
    # exactly eight of each, while both types also appear at the short desk.
    return (index // 2 + int(centre[1] < 0)) % 2


def rounded_rect(bounds, radius, steps=4):
    a, b, lo, hi = bounds
    r = min(radius, (b-a)/2, (hi-lo)/2)
    corners = ((b-r,hi-r,0), (a+r,hi-r,90),
               (a+r,lo+r,180), (b-r,lo+r,270))
    return [(x+r*math.cos(math.radians(start+90*k/steps)),
             y+r*math.sin(math.radians(start+90*k/steps)))
            for x,y,start in corners for k in range(steps+1)]


class MonitorMesh:
    def __init__(self, model, frame, centre, z):
        import reefhall_map as R
        self.R, self.model, self.fr = R, model, frame
        self.centre, self.z = centre, z

    def point(self, p):
        return self.fr.p(p[0]+self.centre, p[1], p[2]+self.z)

    def face(self, paint, points, towards, normals=None):
        points = [np.asarray(p, float) for p in points]
        # Corner fans sometimes meet at the same outer vertex. Drop duplicate
        # vertices before triangulating, rather than writing zero-area faces.
        keep = [i for i,p in enumerate(points)
                if np.linalg.norm(p-points[i-1]) > 1e-7]
        points = [points[i] for i in keep]
        if normals is not None:
            normals = [normals[i] for i in keep]
        if len(points) < 3:
            return
        n = sum((np.cross(points[k]-points[0], points[k+1]-points[0])
                 for k in range(1,len(points)-1)), np.zeros(3))
        if np.linalg.norm(n) < 1e-9:
            return
        if np.dot(n, towards) < 0:
            points = points[:1]+points[:0:-1]
            if normals is not None:
                normals = normals[:1]+normals[:0:-1]
        self.model.polygon(paint, [self.point(p) for p in points],
                           normals=None if normals is None else
                           [self.fr.vec(*n) for n in normals])

    def rect(self, bounds, depth, paint, sign=1):
        a,b,lo,hi = bounds
        self.face(paint, [(a,depth,lo),(b,depth,lo),(b,depth,hi),(a,depth,hi)], (0,sign,0))

    def loft(self, rings, paint):
        """Smooth normals shared around and along the rounded shell's profile."""
        rings = np.asarray(rings, float)
        normals = np.zeros_like(rings)
        faces = []
        for i in range(len(rings)-1):
            for j in range(len(rings[0])):
                k = (j+1) % len(rings[0])
                ids = ((i,j),(i,k),(i+1,k),(i+1,j))
                ps = [rings[t] for t in ids]
                n = np.cross(ps[1]-ps[0],ps[2]-ps[0]) + np.cross(ps[2]-ps[0],ps[3]-ps[0])
                middle = np.mean(ps,axis=0)
                centre = np.mean(rings,axis=(0,1))
                if np.dot(n,middle-centre) < 0:
                    n = -n
                if np.linalg.norm(n) < 1e-9:
                    continue
                n /= np.linalg.norm(n)
                for t in ids:
                    normals[t] += n
                faces.append((ids,n))
        lengths = np.linalg.norm(normals,axis=2,keepdims=True)
        normals /= np.maximum(lengths,1e-9)
        for ids,n in faces:
            self.face(paint,[rings[t] for t in ids],n,[normals[t] for t in ids])

    def solid(self, bounds, d0, d1, radius, paint, axis="w", bevel=0.12):
        a,b,lo,hi = bounds
        bevel = min(bevel,(d1-d0)/3,radius/2)
        project = ((lambda x,y,d:(x,d,y)) if axis=="w" else
                   (lambda x,y,d:(x,y,d)))
        profile = ((d0,bevel),(d0+bevel,0),(d1-bevel,0),(d1,bevel))
        rings = [[project(x,y,d) for x,y in rounded_rect((a+t,b-t,lo+t,hi-t),radius-t)]
                 for d,t in profile]
        self.loft(rings,paint)
        direction = (0,1,0) if axis=="w" else (0,0,1)
        self.face(paint,rings[0],-np.array(direction))
        self.face(paint,rings[-1],direction)

    def hole(self, cell, opening, radius, depth, paint=SHELL, bottom=True, back=None):
        """A real recessed rounded opening, with a tessellated surrounding face."""
        a,b,lo,hi = cell
        outline = rounded_rect(opening,radius,steps=2)
        outer_corners = ((b,hi),(a,hi),(a,lo),(b,lo))
        outer = [outer_corners[i//3] for i in range(len(outline))]
        cu,cz = (opening[0]+opening[1])/2,(opening[2]+opening[3])/2
        back = depth-0.22 if back is None else back
        for i,(x,y) in enumerate(outline):
            j = (i+1)%len(outline)
            xx,yy = outline[j]
            self.face(paint,[(outer[i][0],depth,outer[i][1]),
                              (outer[j][0],depth,outer[j][1]),(xx,depth,yy),(x,depth,y)],(0,1,0))
            self.face(TRIM,[(x,depth,y),(xx,depth,yy),(xx,back,yy),(x,back,y)],
                      (cu-(x+xx)/2,0,cz-(y+yy)/2))
        if bottom:
            self.face(DARK,[(x,back,y) for x,y in outline],(0,1,0))

    def panel(self, bounds, depth, paint, regions):
        """Fill a plane around rectangular inset regions, with no stacked decals."""
        a,b,lo,hi = bounds
        xs = sorted({a,b,*[p for r in regions for p in r[:2]]})
        zs = sorted({lo,hi,*[p for r in regions for p in r[2:]]})
        for x0,x1 in zip(xs,xs[1:]):
            for z0,z1 in zip(zs,zs[1:]):
                x,z = (x0+x1)/2,(z0+z1)/2
                if not any(r[0]<x<r[1] and r[2]<z<r[3] for r in regions):
                    self.rect((x0,x1,z0,z1),depth,paint)

    def tube(self, points, radius, paint, sides=8):
        # One continuous tube, with shared bend rings: no overlapping elbow caps.
        knots = np.asarray(points,float)
        points = []
        for i in range(len(knots)-1):
            p0,p1,p2,p3 = (knots[max(i-1,0)],knots[i],knots[i+1],knots[min(i+2,len(knots)-1)])
            for t in np.linspace(0,1,5,endpoint=False):
                points.append(0.5*((2*p1)+(-p0+p2)*t+(2*p0-5*p1+4*p2-p3)*t*t+(-p0+3*p1-3*p2+p3)*t*t*t))
        points = np.asarray(points+[knots[-1]])
        rings = []
        for i,p in enumerate(points):
            tangent = points[min(i+1,len(points)-1)]-points[max(0,i-1)]
            tangent /= np.linalg.norm(tangent)
            ref = (0,1,0) if abs(tangent[1])<0.9 else (0,0,1)
            a = np.cross(tangent,ref)
            a /= np.linalg.norm(a)
            b = np.cross(tangent,a)
            rings.append([p+radius*(a*math.cos(k*math.tau/sides)+b*math.sin(k*math.tau/sides))
                          for k in range(sides)])
        # A cable can bend in any direction; its outward normal is radial, not
        # relative to the centre of the whole curve as on the casing's loft.
        for i in range(len(rings)-1):
            for j in range(sides):
                k = (j+1)%sides
                ps = [rings[i][j],rings[i][k],rings[i+1][k],rings[i+1][j]]
                ns = [ps[0]-points[i],ps[1]-points[i],ps[2]-points[i+1],ps[3]-points[i+1]]
                self.face(paint,ps,np.mean(ns,axis=0),ns)

    def screw(self,u,z,depth):
        self.R.tube(self.model,self.point((u,depth-0.04,z)),self.point((u,depth+0.025,z)),
                    0.19,TRIM,sides=12,cap=True)
        self.rect((u-0.10,u+0.10,z-0.027,z+0.027),depth+0.03,DARK)


def build(model, frame, u, z, kind):
    m = MonitorMesh(model,frame,u,z)
    # An unchanged screen plane at w=8.74 sits just ahead of this front bezel.
    m.solid((-19.4,19.4,42.6,66),8.8,9.6,0.65,TRIM,bevel=0.10)
    profile = ((9.65,(-19.35,19.35,42.65,65.95),0.7),
               (10.15,(-19.25,19.25,42.75,65.85),0.8),
               (11.25,(-18.9,18.9,43.1,65.5),1.0),
               (12.25,(-18.0,18.0,44.0,64.6),1.15),
               (12.60,(-17.0,17.0,45.0,63.8),0.8),
               (12.60,(-16.7,16.7,45.3,63.5),0.5))
    m.loft([[(x,d,y) for x,y in rounded_rect(bounds,r)] for d,bounds,r in profile],SHELL)
    # The last planar rounded border joins a rectangular work area. Four corner
    # fans close it without covering the openings added below.
    outer = rounded_rect((-16.7,16.7,45.3,63.5),0.5)
    inner = [(max(-16.2,min(16.2,x)),max(45.8,min(63.0,y))) for x,y in outer]
    for i,p in enumerate(outer):
        j=(i+1)%len(outer)
        m.face(SHELL,[(p[0],12.6,p[1]),(outer[j][0],12.6,outer[j][1]),
                      (inner[j][0],12.6,inner[j][1]),(inner[i][0],12.6,inner[i][1])],(0,1,0))
    vent_regions = [(-14.8,-4.9,59.5,62.7),(4.9,14.8,59.5,62.7)]
    port_region = (-9.0,9.0,45.8,48.4)
    m.panel((-16.2,16.2,45.8,63.0),12.6,SHELL,vent_regions+[port_region])
    for a,b,lo,hi in vent_regions:
        if kind == 0:
            for row in range(5):
                z0,z1 = lo+(hi-lo)*row/5,lo+(hi-lo)*(row+1)/5
                mid=(z0+z1)/2
                m.hole((a,b,z0,z1),(a+0.15,b-0.15,mid-0.10,mid+0.10),0.10,12.6)
        else:
            for row in range(5):
                for col in range(22):
                    x0,x1=a+(b-a)*col/22,a+(b-a)*(col+1)/22
                    z0,z1=lo+(hi-lo)*row/5,lo+(hi-lo)*(row+1)/5
                    x,zz=(x0+x1)/2,(z0+z1)/2
                    m.hole((x0,x1,z0,z1),(x-0.115,x+0.115,zz-0.115,zz+0.115),
                           0.115,12.6,back=12.40)
    # Socket bay: inset well, plugged leads and one spare input. All are behind
    # the case's outline rather than stuck on top of its rear surface.
    m.hole(port_region,(-8.5,8.5,45.85,48.1),0.25,12.6,back=11.7)
    for x,width in ((-6.1,0.9),(-4.2,0.6),(5.3,1.15)):
        m.solid((x-width/2,x+width/2,46.3,47.1),11.72,12.1,0.12,TRIM,bevel=0.04)
    # Small screw-fastened VESA plate and the horizontal tilt barrel.
    m.solid((-3.5,3.5,49.8,56.8),12.62,13.05,0.40,TRIM,bevel=0.09)
    for x in (-2.85,2.85):
        for zz in (50.45,56.15):
            m.screw(x,zz,13.06)
    m.R.tube(model,m.point((-1.65,13.55,53.3)),m.point((1.65,13.55,53.3)),
             0.72,TRIM,sides=16,cap=True)
    # Rounded foot with a separate rubber underside.
    m.solid((-7,7,6,15.7),36.3,36.5,0.85,DARK,axis="z",bevel=0.06)
    m.solid((-7,7,6,15.7),36.5,37.1,0.85,TRIM,axis="z",bevel=0.14)
    spine = METAL if kind else TRIM
    m.solid((-1.5,1.5,37.05,53.5),13.0,14.3,0.24,spine,bevel=0.10)
    # The charcoal version has a full-height cable guide; the aluminium version
    # exposes its spine above a shorter recessed dark cable-management channel.
    channel_top = 44.3 if kind else 49.2
    m.solid((-0.65,0.65,37.25,channel_top),14.30,14.40,0.35,DARK,bevel=0.025)
    for x,offset in ((-6.1,-0.22),(-4.2,0.22)):
        m.tube([(x,12.15,46.55),(x,13.1,45.1),(x*0.65,14.5,43.6),
                (x*0.26,14.75,42.6),(offset,14.76,41.2),
                (offset,14.76,38.2),(offset,14.5,37.2),(offset,15.4,36.4)],0.105,DARK)
    m.solid((-0.85,0.85,39.0,39.42),14.60,14.98,0.12,TRIM,bevel=0.04)
    for x in (-15.6,15.6):
        m.screw(x,46.5,12.62)
    # A restrained service sticker, with vector-like tiny type bars and barcode.
    # It is deliberately small and generic rather than a fictitious brand logo.
    m.rect((9.8,14.6,46.0,47.4),12.64,LABEL)
    for row,length in enumerate((2.5,3.7,2.9)):
        m.rect((10.1,10.1+length,47.05-row*0.18,47.10-row*0.18),12.65,INK)
    for k in range(26):
        x=10.1+k*0.16
        m.rect((x,x+(0.07 if k%3 else 0.035),46.15,46.49),12.65,INK)
