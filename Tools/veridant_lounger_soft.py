"""Soft sewn upholstery and lightly weathered, rounded teak furniture members.

All dimensions are inches. Deformations stay small and deterministic: foam has
weight and cloth pulls at seams, while assembled furniture remains structurally
straight. No random vertex jitter or painted fake folds.
"""
import math
import numpy as np
from scipy.spatial import Delaunay
import riverdale_parts as P


def piping(model, path, radius, axes, centre, sides=6, phase=0.):
    """Sweep an already curved seam without adding extra bend tessellation."""
    path=np.array(path);rings=[];normals=[]
    for i,point in enumerate(path):
        tangent=P.unit(path[(i+1)%len(path)]-path[i-1])
        outward=P.unit(np.cross(tangent,(0.,0.,1.)))
        other=np.cross(tangent,outward)
        radius_here=radius*(1+.045*math.sin(i*.63+phase))
        ns=[outward*math.cos(t)+other*math.sin(t) for t in np.linspace(0,math.tau,sides,endpoint=False)]
        rings.append([point+n*radius_here for n in ns]);normals.append(ns)
    for i in range(len(path)):
        j=(i+1)%len(path)
        for a in range(sides):
            b=(a+1)%sides
            model.polygon('vr_lounger_piping',
                          [centre+p@axes for p in (rings[i][a],rings[i][b],rings[j][b],rings[j][a])],
                          normals=[n@axes for n in (normals[i][a],normals[i][b],normals[j][b],normals[j][a])])


def outline(length, width, radius=1.9, spacing=2.4):
    points=[]
    radius=min(radius,width*.20,length*.20)
    for sx,sy,start in ((1,1,0),(-1,1,90),(-1,-1,180),(1,-1,270)):
        for angle in np.linspace(start,start+90,6):
            a=math.radians(angle)
            points.append(np.array((sx*(length/2-radius)+radius*math.cos(a),
                                    sy*(width/2-radius)+radius*math.sin(a))))
        end=points[-1]
        nx,ny=((-1,1),(-1,-1),(1,-1),(1,1))[start//90]
        angle=math.radians(start+90)
        target=np.array((nx*(length/2-radius)+radius*math.cos(angle),
                         ny*(width/2-radius)+radius*math.sin(angle)))
        steps=max(1,math.ceil(np.linalg.norm(target-end)/spacing))
        points.extend(end+(target-end)*t/steps for t in range(1,steps))
    return np.array(points)


def cushion(model, centre, axes, length, width, phase=0.):
    axes=np.array(axes);centre=np.array(centre);boundary=outline(length,width)
    half=np.array((length/2,width/2));radius=1.9
    vertices=[];faces=[]

    def distance(x,y):
        q=np.abs((x,y))-(half-radius)
        return -(np.linalg.norm(np.maximum(q,0))+min(max(q),0)-radius)

    def top(x,y):
        edge=max(0.,distance(x,y))
        z=1.56+.79*(1-math.exp(-edge/2.6))
        z-=.46*math.exp(-((x-length*.06)/(length*.28))**2-((y+width*.035)/(width*.35))**2)
        z+=.055*math.sin(x*.19+phase)*math.cos(y*.23-phase*.6)
        # Short seam pulls flare into the cloth, fading before the middle.
        for side in (-1,1):
            inset=width/2-side*y
            if inset<0:continue
            for i,fraction in enumerate((-.39,-.25,-.08,.15,.34,.43)):
                position=length*(fraction+.012*math.sin(phase+i*2.2+side))
                slope=.19*math.sin(phase+i*1.7+side*2)
                across=x-position-slope*inset
                spread=.28+.095*inset
                fold=math.exp(-(across/spread)**2)*math.exp(-inset/2.3)
                shoulder=(math.exp(-((across-spread*1.7)/(spread*1.4))**2)
                          +math.exp(-((across+spread*1.7)/(spread*1.4))**2))*math.exp(-inset/2.7)
                z-=.14*fold
                z+=.030*shoulder
        # A shallow diagonal fold close to the ankle/shoulder end.
        for side in (-1,1):
            inset=length/2-side*x
            if inset>=0:
                z-=.11*math.exp(-((y-width*.17*side-.14*inset)/(.23+.06*inset))**2-inset/2.7)
        return z

    def warp(x,y,z):
        x+=.12*math.sin(y*.37+phase)*(abs(x)/half[0])**7
        y+=.16*math.sin(x*.25+phase*.7)*(abs(y)/half[1])**7
        y+=.035*math.sin(x*.81-phase)*(abs(y)/half[1])**9
        return np.array((x,y,z))

    def seam_wave(x,y):return .055*math.sin(x*.43+phase)*math.cos(y*.31-phase)

    profiles=((.954,-1.68),(.983,-1.45),(1.003,-.83),(1.009,-.10),
              (1.002,.64),(.984,1.18),(.944,None))
    for scale,height in profiles:
        for xy in boundary:
            x,y=xy*scale
            z=top(x,y) if height is None else height+seam_wave(x,y)*math.exp(-((height-1.18)/.9)**2)
            vertices.append(warp(x,y,z))
    count=len(boundary)
    for j in range(len(profiles)-1):
        for i in range(count):
            a=j*count+i;b=j*count+(i+1)%count
            faces.append((a,b,b+count,a+count))
    bottom=len(vertices);vertices.append(np.array((0.,0.,-1.68)))
    for i in range(count):faces.append((bottom,(i+1)%count,i))
    # Sample the top in two dimensions so folds have actual curved geometry.
    rim=boundary*.944
    xy=list(rim)
    for side in (-1,1):
        for i,fraction in enumerate((-.39,-.25,-.08,.15,.34,.43)):
            position=length*(fraction+.012*math.sin(phase+i*2.2+side))
            slope=.19*math.sin(phase+i*1.7+side*2)
            for inset in (.8,1.2,1.9,2.9,4.1):
                for offset in (-2.5,-1.2,0.,1.2,2.5):
                    x=position+slope*inset+offset*(.28+.095*inset)
                    y=side*(width/2-inset)
                    if distance(x/.944,y/.944)>.025:xy.append(np.array((x,y)))
    for x in np.arange(-length*.46,length*.46,1.35):
        for y in np.arange(-width*.46,width*.46,1.35):
            if distance(x/.944,y/.944)>.42 and np.linalg.norm(np.array(xy)-(x,y),axis=1).min()>.18:
                xy.append(np.array((x,y)))
    xy=np.array(xy)
    rim_start=(len(profiles)-1)*count
    indices=list(range(rim_start,rim_start+count))
    for x,y in xy[count:]:
        indices.append(len(vertices));vertices.append(warp(x,y,top(x,y)))
    for tri in Delaunay(xy).simplices:
        a,b,c=xy[tri]
        if (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])<0:tri=tri[::-1]
        faces.append(tuple(indices[i] for i in tri))
    vertices=np.array(vertices);normals=np.zeros_like(vertices)
    for face in faces:
        for j in range(1,len(face)-1):
            ids=[face[0],face[j],face[j+1]];a,b,c=vertices[ids]
            normal=np.cross(b-a,c-a)
            assert np.linalg.norm(normal)>1e-8,'Degenerate cloth triangle'
            normals[ids]+=normal
    normals/=np.linalg.norm(normals,axis=1)[:,None]
    # Evaluate the continuous cloth surface's gradient at top vertices; uneven
    # triangulation must not turn a rounded crease into a faceted dent.
    for index,(x,y) in zip(indices,xy):
        h=.025
        u=warp(x+h,y,top(x+h,y))-warp(x-h,y,top(x-h,y))
        v=warp(x,y+h,top(x,y+h))-warp(x,y-h,top(x,y-h))
        n=P.unit(np.cross(u,v))
        normals[index]=P.unit(n*.75+normals[index]*.25) if index<rim_start+count else n
    assert np.isfinite(normals).all()
    perimeter=np.r_[0.,np.cumsum(np.linalg.norm(np.roll(boundary,-1,axis=0)-boundary,axis=1))]
    for face in faces:
        local=vertices[list(face)]
        side=all(i<rim_start for i in face) and bottom not in face
        if side:
            ids=[i%count for i in face];distances=[perimeter[i] for i in ids]
            if max(ids)==count-1 and min(ids)==0:
                distances=[perimeter[-1] if i==0 else d for i,d in zip(ids,distances)]
            uv=[(d/12,p[2]/12) for d,p in zip(distances,local)]
        else:uv=[(p[0]/12,p[1]/12) for p in local]
        model.polygon('vr_lounger_cloth',[centre+p@axes for p in local],
                      normals=[normals[i]@axes for i in face],uv=uv)
    for scale,height,r,sides in ((.984,1.18,.055,6),(.983,-1.45,.035,5)):
        path=[warp(x*scale,y*scale,height+seam_wave(x*scale,y*scale)) for x,y in boundary]
        piping(model,path,r,axes,centre,sides,phase)
    # A row of small stitches follows the upper rolled seam, with matching wear.
    stitch_path=[]
    for x,y in boundary:
        z=1.18+.25*(top(x*.944,y*.944)-1.18)+seam_wave(x,y)+.025
        stitch_path.append(warp(x*.974,y*.974,z))
    path=np.array(stitch_path)
    for a,b in zip(path,np.roll(path,-1,axis=0)):
        length_segment=np.linalg.norm(b-a);direction=(b-a)/length_segment
        inward=P.unit(np.array((-(a[0]+b[0]),-(a[1]+b[1]),0.)))*.007
        for distance_along in np.arange(.04,length_segment-.13,.24):
            p=a+direction*distance_along;q=p+direction*.12
            local=(p-inward,q-inward,q+inward,p+inward)
            model.polygon('vr_lounger_piping',[centre+point@axes for point in local],
                          normal=np.array((0.,0.,1.))@axes)


def timber(model, centre, axes, size, paint, bevel=.18, phase=0.):
    """Rounded cross sections, sanded ends and small longitudinal variation."""
    axes=np.array(axes);centre=np.array(centre);size=np.array(size)
    long=int(np.argmax(size));a=(long+1)%3;b=(long+2)%3
    along=axes[long];across=axes[a];up=axes[b]
    length=size[long];half=size[[a,b]]/2
    bevel=min(bevel,min(half)*.72)
    stations=[-length/2,*np.linspace(-length/2+bevel,length/2-bevel,max(2,math.ceil(length/12)+1)),length/2]
    rings=[];normals=[];uvs=[]
    for j,u in enumerate(stations):
        t=(u+length/2)/length
        shrink=bevel*.55 if j in (0,len(stations)-1) else 0.
        # Legs taper very slightly toward their protective feet.
        taper=.94+.06*t if long==2 else 1.
        extents=half*taper-shrink
        radius=min(bevel*(1+.13*math.sin(t*5.3+phase)),min(extents)*.80)
        bow=(across*.035*math.sin(math.pi*t)*math.sin(phase)
             +up*.040*math.sin(math.pi*t)*math.sin(t*4.1+phase))
        ring=[];shading=[];uv=[]
        for sx,sy,start in ((1,1,0),(-1,1,90),(-1,-1,180),(1,-1,270)):
            for angle in np.linspace(start,start+90,4):
                angle=math.radians(angle);nx,ny=math.cos(angle),math.sin(angle)
                x=sx*(extents[0]-radius)+radius*nx
                y=sy*(extents[1]-radius)+radius*ny
                ring.append(centre+along*u+across*x+up*y+bow)
                normal=across*nx+up*ny
                if j==0:normal-=along*.75
                elif j==len(stations)-1:normal+=along*.75
                shading.append(P.unit(normal))
                uv.append((math.atan2(y/half[1],x/half[0])*sum(half)/8+phase*.13,u/48+phase*.19))
        rings.append(ring);normals.append(shading);uvs.append(uv)
    count=len(rings[0])
    for j in range(len(rings)-1):
        for i in range(count):
            k=(i+1)%count
            coordinates=[uvs[j][i],uvs[j][k],uvs[j+1][k],uvs[j+1][i]]
            period=math.tau*sum(half)/8
            maximum=max(p[0] for p in coordinates)
            coordinates=[(u+period if maximum-u>period/2 else u,v) for u,v in coordinates]
            model.polygon(paint,[rings[j][i],rings[j][k],rings[j+1][k],rings[j+1][i]],
                          normals=[normals[j][i],normals[j][k],normals[j+1][k],normals[j+1][i]],
                          uv=coordinates)
    for j,normal in ((0,-along),(-1,along)):
        points=rings[j] if j==-1 else rings[j][::-1]
        model.polygon(paint,points,normal=normal,
                      uv=[(float(np.dot(p-centre,across)/8),float(np.dot(p-centre,up)/8)) for p in points])
