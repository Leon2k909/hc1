"""Cloth, sacking and a worn field hat over Belltower's original scarecrow frame.

Visual geometry only. The map generator keeps the existing collision separately.
All materials reuse existing project texture pixels.
"""
import math
import numpy as np
import belltower_furniture as F

RESOURCE = 'materials/belltower/scarecrow-v1'
SACK, SHIRT, HAT, TWINE, STITCH, PATCH = (
    'scarecrow_sack', 'scarecrow_shirt', 'scarecrow_hat',
    'scarecrow_twine', 'scarecrow_stitch', 'scarecrow_patch')
MATERIALS = {
    SACK: 'materials/stillhouse/sh_sack.vmat',
    SHIRT: 'materials/stillhouse/sh_canvas.vmat',
    HAT: f'{RESOURCE}/hat.vmat',
    TWINE: 'materials/stillhouse/sh_rope.vmat',
    STITCH: f'{RESOURCE}/stitch.vmat',
    PATCH: f'{RESOURCE}/patch.vmat',
}


def unit(v):
    v = np.asarray(v, float)
    return v / max(np.linalg.norm(v), 1e-12)


def build(model, p):
    model.material_overrides.update(MATERIALS)
    for paint in MATERIALS:
        model.tile_overrides[paint] = 12

    def normal(n):
        return p.x*n[0] + p.y*n[1] + p.z*n[2]

    def face(paint, points, n, uv=None, normals=None):
        F.face(model, paint, [p.at(v) for v in points], normal(n), uv,
               [normal(v) for v in normals] if normals is not None else None)

    def tube(a, b, radius, paint=TWINE, sides=6):
        a, b = np.asarray(a, float), np.asarray(b, float)
        direction = unit(b-a)
        u = unit(np.cross(direction, (0, 0, 1) if abs(direction[2]) < .9 else (0, 1, 0)))
        v = np.cross(direction, u)
        rim = [u*math.cos(k*math.tau/sides)+v*math.sin(k*math.tau/sides) for k in range(sides)]
        length = np.linalg.norm(b-a)
        for k in range(sides):
            d0, d1 = rim[k], rim[(k+1) % sides]
            face(paint, [a+radius*d0, a+radius*d1, b+radius*d1, b+radius*d0], d0+d1,
                 [(k/sides,0),((k+1)/sides,0),((k+1)/sides,length/8),(k/sides,length/8)],
                 [d0,d1,d1,d0])

    def surface(paint, point, radial, u0, u1, v0, v1, columns, rows, uv=None):
        def vertex(u,v):
            q=np.asarray(point(u,v), float)
            du=np.asarray(point(u+1e-4,v))-np.asarray(point(u-1e-4,v))
            dv=np.asarray(point(u,v+1e-4))-np.asarray(point(u,v-1e-4))
            n=unit(np.cross(du,dv));out=np.asarray(radial(u,v))
            if np.dot(n,out)<0:n=-n
            if np.linalg.norm(n)<.1:n=unit(out)
            return q,n
        for j in range(rows):
            va,vb=v0+(v1-v0)*j/rows,v0+(v1-v0)*(j+1)/rows
            for i in range(columns):
                ua,ub=u0+(u1-u0)*i/columns,u0+(u1-u0)*(i+1)/columns
                pairs=[(ua,va),(ub,va),(ub,vb),(ua,vb)]
                values=[vertex(u,v) for u,v in pairs]
                # Rounded sack poles collapse to a single vertex. Emit a real
                # triangle there rather than exporting degenerate quads.
                if np.linalg.norm(values[0][0]-values[1][0])<1e-6:
                    pairs,values=pairs[1:],values[1:]
                elif np.linalg.norm(values[2][0]-values[3][0])<1e-6:
                    pairs,values=pairs[:3],values[:3]
                points=[q for q,n in values];normals=[n for q,n in values]
                if np.linalg.norm(np.cross(points[1]-points[0],points[2]-points[0]))<1e-9:continue
                coords=[uv(u,v) if uv else (u/math.tau,v) for u,v in pairs]
                face(paint,points,sum(normals),coords,normals)

    # Softened timber edges and lengthwise photographed grain; the structural
    # post and crossbar occupy their original positions.
    for centre,size in [((0,0,37),(3,3,74)),((0,0,56),(48,3,3))]:
        F.bevel_box(model,p.at(centre),(p.x,p.y,p.z),size,F.DARK,.18,517)

    def torso(theta,t):
        width=np.interp(t,[0,.25,.6,.8,.9,1],[13.7,13.2,13.3,15,11.5,4.5])
        depth=np.interp(t,[0,.3,.65,.82,1],[7.3,8.1,8.3,7.2,3.4])
        c,s=math.cos(theta),math.sin(theta)
        fold=1+.035*math.sin(7*theta+2*t)*math.sin(math.pi*t)**2
        belt=1-.075*math.exp(-((t-.43)/.065)**2)
        return np.array((math.copysign(abs(c)**.75,c)*width*fold*belt,
            math.copysign(abs(s)**.75,s)*depth*fold*belt,
            30+30*t+(1-t)**7*(.65*math.sin(5*theta)+.3*math.sin(9*theta))))

    surface(SHIRT,torso,lambda u,v:(math.cos(u),math.sin(u),0),0,math.tau,0,1,40,14,
            lambda u,v:(u/math.tau,v))
    # Dark recessed stuffing closes the underside without a flat visible box.
    hem=[torso(k*math.tau/40,0)+(0,0,.25) for k in range(40)]
    face(SACK,hem,(0,0,-1),[(q[0]/16,q[1]/16) for q in hem])

    for side in (-1,1):
        def sleeve(theta,t):
            r=np.interp(t,[0,.3,.7,1],[6.8,6.4,5.1,3.9])*(1+.065*math.sin(5*theta+3*t))
            return (side*(11+17*t),math.cos(theta)*r,
                    55.2-(3.4 if side<0 else 5.3)*t+math.sin(theta)*r)
        surface(SHIRT,sleeve,lambda u,v:(0,math.cos(u),math.sin(u)),0,math.tau,0,1,28,9,
                lambda u,v:(u/math.tau,.15+.8*v))
        # Folded cuff and a few uneven lengths of straw protruding from it.
        cuff=[]
        for k in range(28):
            a=k*math.tau/28;q=np.array(sleeve(a,.93));cuff.append(q)
            nxt=np.array(sleeve((k+1)*math.tau/28,.93))
            tube(q,nxt,.13,STITCH,4)
        for k in range(9):
            a=k*2.39996;r=1.4+(k%3)*.7
            start=np.array((side*27.4,r*math.cos(a),55.2-(3.4 if side<0 else 5.3)+r*math.sin(a)))
            tip=start+(side*(1.7+(k%4)*.43),.3*math.sin(k),-.9-.22*(k%3))
            tube(start,tip,.065,HAT,4)

    # Rounded, slightly leaning sack head with an actual smooth normal field.
    def head(theta,lat):
        radial=max(0,math.cos(lat))
        wobble=1+.025*math.sin(3*theta+lat)+.015*math.cos(7*theta-lat)
        return (7.0*radial*math.cos(theta)*wobble-.55*math.sin(lat),
                6.3*radial*math.sin(theta)*wobble,68.3+8.2*math.sin(lat))
    surface(SACK,head,lambda u,v:(math.cos(v)*math.cos(u),math.cos(v)*math.sin(u),math.sin(v)),
            0,math.tau,-math.pi/2,math.pi/2,40,16,lambda u,v:(u/math.tau,v/math.pi+.5))

    # Two small sewn crosses and a curved stitched mouth on the garden-facing
    # side. The stitches follow the sack surface rather than hovering in front.
    def front(x,z):
        lat=math.asin(np.clip((z-68.3)/8.2,-.99,.99))
        theta=math.acos(np.clip((x+.55*math.sin(lat))/(7*math.cos(lat)),-.99,.99))
        q=np.array(head(theta,lat));q[1]+=.09
        return q
    for x in (-2.3,2.3):
        for direction in (-1,1):
            tube(front(x-.58,69.5-.65*direction),front(x+.58,69.5+.65*direction),.105,STITCH,6)
    for k in range(9):
        x=-2.8+k*.7;z=65.0+.08*x*x
        tube(front(x,z),front(x+.45,z+.08*((x+.45)**2-x*x)),.085,STITCH,5)
        if k%2==0:tube(front(x+.2,z-.3),front(x+.2,z+.35),.065,STITCH,4)
    # A gathered neck, knot and loose ends.
    for k in range(32):
        a,b=k*math.tau/32,(k+1)*math.tau/32
        tube((3.55*math.cos(a),3.55*math.sin(a),60.8),
             (3.55*math.cos(b),3.55*math.sin(b),60.8),.19,TWINE,6)
    tube((.2,3.8,60.8),(-1.8,4.1,58.2),.16,TWINE)
    tube((.2,3.8,60.8),(1.4,4.2,57.6),.16,TWINE)
    # A curved repair patch with a sewn border breaks up the shirt front.
    def patch(u,v):
        q=torso(u,v);q[:2]+=unit((q[0],q[1],0))[:2]*.12
        return q
    surface(PATCH,patch,lambda u,v:(math.cos(u),math.sin(u),0),.95,1.52,.22,.47,5,5,
            lambda u,v:((u-.95)/.57,(v-.22)/.25))
    for ua,ub,va,vb,count in [(.95,1.52,.22,.22,7),(.95,1.52,.47,.47,7),(.95,.95,.22,.47,6),(1.52,1.52,.22,.47,6)]:
        for k in range(count):
            t=(k+.15)/count;s=(k+.65)/count
            tube(patch(ua+(ub-ua)*t,va+(vb-va)*t),patch(ua+(ub-ua)*s,va+(vb-va)*s),.07,STITCH,4)
    for k in range(40):
        a,b=k*math.tau/40,(k+1)*math.tau/40
        qa,qb=torso(a,.43),torso(b,.43)
        qa[:2]*=1.006;qb[:2]*=1.006
        tube(qa,qb,.16,TWINE,6)
    # A broad, warped brim and rounded crown, with thickness and a darker band.
    def brim(theta,t):
        r=6.1+9.6*t
        return (r*math.cos(theta),r*math.sin(theta),
            76.1+t*t*(.95*math.sin(2*theta+.4)+.35*math.sin(5*theta)-.65))
    surface(HAT,brim,lambda u,v:(0,0,1),0,math.tau,0,1,48,6,lambda u,v:(u/math.tau*2,v))
    surface(HAT,lambda u,v:np.asarray(brim(u,v))-(0,0,.22),lambda u,v:(0,0,-1),
            0,math.tau,0,1,48,6,lambda u,v:(u/math.tau*2,v))
    for k in range(48):
        a,b=k*math.tau/48,(k+1)*math.tau/48
        qa,qb=np.array(brim(a,1)),np.array(brim(b,1))
        face(HAT,[qa,qb,qb-(0,0,.22),qa-(0,0,.22)],(math.cos(a),math.sin(a),0))
    def crown(theta,t):
        r=np.interp(t,[0,.2,.8,1],[6.4,6.5,5.1,4.6])*(1+.025*math.sin(3*theta))
        return (r*math.cos(theta)-.5*t,r*math.sin(theta),
                76+7.8*t+.3*t*math.cos(2*theta+.2))
    surface(HAT,crown,lambda u,v:(math.cos(u),math.sin(u),0),0,math.tau,0,1,48,6,
            lambda u,v:(u/math.tau*2,v))
    top=[crown(k*math.tau/48,1) for k in range(48)]
    face(HAT,top,(0,0,1),[(q[0]/12+.5,q[1]/12+.5) for q in top])
    surface(STITCH,lambda u,v:np.asarray(crown(u,v))+np.array((math.cos(u),math.sin(u),0))*.08,
            lambda u,v:(math.cos(u),math.sin(u),0),0,math.tau,.16,.30,48,1)
    # Cut ends interrupt the otherwise perfectly circular outer brim.
    for k in range(18):
        a=k*2.39996;q=np.array(brim(a,.965))
        tube(q,q+np.array((math.cos(a),math.sin(a),-.18))*(.7+.25*(k%3)),.055,HAT,4)
