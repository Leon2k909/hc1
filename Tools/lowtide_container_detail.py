"""Physical folded-sheet bends, rail bevels and hollow corner castings.

Only used by Lowtide's container builder. Dimensions remain inside the existing
prop bounds; the original Railhead collision and shared prop are untouched.
"""
import math
import numpy as np
import map_kit as K


def polygon(model, paint, points, normal, normals=None):
    points = np.asarray(points, float)
    normal = K.normalise(normal)
    if np.dot(np.cross(points[1]-points[0], points[2]-points[0]), normal) < 0:
        points = points[::-1]
        if normals is not None:
            normals = list(reversed(normals))
    model.polygon(paint, points, normal, normals=normals)


def opening(model, paint, centre, half, axis, sign, bevel):
    """Open lifting aperture through a cast wall into the common hollow interior."""
    j, k = (axis+1) % 3, (axis+2) % 3
    a, b = half[j]-bevel, half[k]-bevel
    angles = sorted(set([2*math.pi*i/32 for i in range(32)] +
                        [math.atan2(sb*b, sa*a) % (2*math.pi) for sa in (-1,1) for sb in (-1,1)]))
    # ISO corner apertures are elongated, leaving a substantial casting web.
    radii = np.minimum(np.array((a,b))-.58, np.array((1.65,1.15)) if a>b else np.array((1.15,1.65)))
    outer, lip, inner, deep, inside = [], [], [], [], []
    for angle in angles:
        direction = np.array((math.cos(angle), math.sin(angle)))
        rect = direction / max(abs(direction[0])/a, abs(direction[1])/b)
        for ring, xy, depth in ((outer,rect,0), (lip,direction*(radii+.10),0),
                                (inner,direction*radii,.12), (deep,direction*radii,.65),
                                (inside,direction/max(abs(direction[0])/(half[j]-.65),abs(direction[1])/(half[k]-.65)),.65)):
            p = centre.copy()
            p[axis] += sign*(half[axis]-depth)
            p[j] += xy[0]
            p[k] += xy[1]
            ring.append(p)
    outward = np.eye(3)[axis]*sign
    for i in range(len(angles)):
        n = (i+1) % len(angles)
        polygon(model,paint,[outer[i],outer[n],lip[n],lip[i]],outward)
        toward = K.normalise(-(inner[i]+inner[n])/2 + centre + outward*(half[axis]-.12))
        polygon(model,paint,[lip[i],lip[n],inner[n],inner[i]],outward+toward)
        polygon(model,paint,[inner[i],inner[n],deep[n],deep[i]],toward)
        polygon(model,"rw_black",[inside[i],inside[n],deep[n],deep[i]],-outward)


def bevel_box(model, lo, hi, paint, bevel, holes=()):
    centre = (np.asarray(lo)+hi)/2
    half = (np.asarray(hi)-lo)/2
    bevel = min(bevel, float(half.min())*.45)
    def draw(points,normal):
        polygon(model,paint,[centre+p for p in points],normal)
    for i in range(3):
        j,k = (i+1)%3,(i+2)%3
        for sign in (-1,1):
            if (i,sign) in holes:
                opening(model,paint,centre,half,i,sign,bevel)
                continue
            points=[]
            for sj,sk in ((-1,-1),(1,-1),(1,1),(-1,1)):
                p=np.zeros(3)
                p[i],p[j],p[k]=sign*half[i],sj*(half[j]-bevel),sk*(half[k]-bevel)
                points.append(p)
            draw(points,np.eye(3)[i]*sign)
            if holes:
                # The interior faces are needed when looking through a real aperture.
                inside=[]
                for sj,sk in ((-1,-1),(1,-1),(1,1),(-1,1)):
                    p=centre.copy()
                    p[i]+=sign*(half[i]-.65)
                    p[j]+=sj*(half[j]-.65)
                    p[k]+=sk*(half[k]-.65)
                    inside.append(p)
                polygon(model,"rw_black",inside,-np.eye(3)[i]*sign)
    for i in range(3):
        j,k=(i+1)%3,(i+2)%3
        for sj in (-1,1):
            for sk in (-1,1):
                points=[]
                for si,near_j in ((-1,True),(1,True),(1,False),(-1,False)):
                    p=np.zeros(3)
                    p[i]=si*(half[i]-bevel)
                    p[j]=sj*(half[j] if near_j else half[j]-bevel)
                    p[k]=sk*(half[k]-bevel if near_j else half[k])
                    points.append(p)
                normal=np.zeros(3)
                normal[j],normal[k]=sj,sk
                draw(points,normal)
    for sx in (-1,1):
        for sy in (-1,1):
            for sz in (-1,1):
                signs=np.array((sx,sy,sz))
                draw([signs*(half-bevel)+signs*np.eye(3)[i]*bevel for i in range(3)],signs)


class Source(K.Model):
    """Intercept the prop's structural boxes, leaving its collisions unchanged."""
    def __init__(self,paint,origin,height):
        super().__init__()
        self.paint=paint
        self.container_centre=np.asarray(origin,float)+np.array((0,0,height/2))

    def box(self,lo,hi,paints,surface=None,skip=()):
        lo,hi=np.minimum(lo,hi).astype(float),np.maximum(lo,hi).astype(float)
        size=hi-lo
        if isinstance(paints,str) and paints==self.paint and sorted(size)[1]<=8:
            bevel_box(self,lo,hi,paints,.16)
        elif isinstance(paints,str) and paints=="rw_steel_dark" and size.min()>4 and size.max()<8:
            centre=(lo+hi)/2
            holes=tuple((i,1 if centre[i]>self.container_centre[i] else -1) for i in range(3))
            bevel_box(self,lo,hi,paints,.22,holes)
        elif isinstance(paints,str) and paints=="rw_steel_grey":
            bevel_box(self,lo,hi,paints,.08)
        elif isinstance(paints,dict) and paints.get("+z")==self.paint and min(size[:2])>80 and abs(size[2]-1.5)<1e-6:
            # Roof sheets stop at the corner castings, leaving the upper lift holes clear.
            dx,dy=(7.2,6.6) if size[0]<size[1] else (6.6,7.2)
            for x0,x1,y0,y1 in ((lo[0],hi[0],lo[1]+dy,hi[1]-dy),
                                (lo[0]+dx,hi[0]-dx,lo[1],lo[1]+dy),
                                (lo[0]+dx,hi[0]-dx,hi[1]-dy,hi[1])):
                super().box((x0,y0,lo[2]),(x1,y1,hi[2]),paints,None,skip)
            if surface:
                self.collision_box(lo,hi,surface)
            return
        elif isinstance(paints,dict) and paints.get("-z")=="rw_steel_dark" and min(size[:2])>80 and abs(size[2]-5)<1e-6:
            # The original rectangular underplate passed through the bottom castings.
            # Trim its four corners so it cannot cap their downward lifting apertures.
            super().box(lo,hi,{**paints,"-z":None},surface,skip)
            dx,dy=(4.25,3.55) if size[0]<size[1] else (3.55,4.25)
            for x0,x1,y0,y1 in ((lo[0],hi[0],lo[1]+dy,hi[1]-dy),
                                (lo[0]+dx,hi[0]-dx,lo[1],lo[1]+dy),
                                (lo[0]+dx,hi[0]-dx,hi[1]-dy,hi[1])):
                polygon(self,"rw_steel_dark",[(x0,y0,lo[2]),(x1,y0,lo[2]),(x1,y1,lo[2]),(x0,y1,lo[2])],(0,0,-1))
            return
        else:
            return super().box(lo,hi,paints,surface,skip)
        if surface:
            self.collision_box(lo,hi,surface)


def rounded_profile(knots,trim=.28,steps=4):
    """Quadratic bend segments with analytic tangent normals; straight spans stay flat."""
    knots=np.asarray(knots,float)
    result=[(knots[0],K.normalise(np.r_[knots[1]-knots[0],0])[:2])]
    for i in range(1,len(knots)-1):
        p=knots[i]
        before=p-knots[i-1]
        after=knots[i+1]-p
        before/=np.linalg.norm(before)
        after/=np.linalg.norm(after)
        distance=min(trim,np.linalg.norm(p-knots[i-1])*.20,np.linalg.norm(knots[i+1]-p)*.20)
        start,end=p-before*distance,p+after*distance
        for t in np.linspace(0,1,steps+1):
            point=(1-t)**2*start+2*(1-t)*t*p+t*t*end
            tangent=2*(1-t)*(p-start)+2*t*(end-p)
            result.append((point,tangent/np.linalg.norm(tangent)))
    tangent=knots[-1]-knots[-2]
    result.append((knots[-1],tangent/np.linalg.norm(tangent)))
    return result


def sheet(model,paint,points,normal,frame,shift,tile,pitch,wall_depth,roof_depth):
    points=np.asarray(points,float)
    normal=K.normalise(normal)
    along=frame.x if abs(normal[2])>.9 else np.array((0.,0.,1.))
    across=np.cross(along,normal)
    centre=points.mean(axis=0)
    us,vs=(points-centre)@across,(points-centre)@along
    u0,u1,v0,v1=us.min(),us.max(),vs.min(),vs.max()
    depth=roof_depth if abs(normal[2])>.9 else wall_depth
    ribs=max(1,int(round((u1-u0)/pitch)))
    pitch=(u1-u0)/ribs
    knots=[(u0+(i+t)*pitch,h*depth) for i in range(ribs)
           for t,h in ((0.,0.),(.30,0.),(.50,-1.),(.80,-1.))]+[(u1,0.)]
    profile=rounded_profile(knots,trim=.30 if abs(normal[2])<.9 else .20)
    for (a,ta),(b,tb) in zip(profile,profile[1:]):
        pa,pb=a[0],b[0]
        pts=[centre+across*u+along*v+normal*h for u,v,h in
             ((pa,v0,a[1]),(pb,v0,b[1]),(pb,v1,b[1]),(pa,v1,a[1]))]
        uv=[[(u-u0)/tile+shift[0],(v-v0)/tile+shift[1]] for u,v in
            ((pa,v0),(pb,v0),(pb,v1),(pa,v1))]
        na=normal*ta[0]-across*ta[1]
        nb=normal*tb[0]-across*tb[1]
        model.polygon(paint,pts,uv=uv,normals=[na,nb,nb,na])
