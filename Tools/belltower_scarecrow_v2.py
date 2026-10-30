"""A hand-stuffed field scarecrow: draped work shirt, dished hat and loose straw.

Reuses the established seven material slots; owns no collision or scene objects.
All random variation is local and repeatable.
"""
import math
import numpy as np
import belltower_furniture as F
import belltower_scarecrow as S

TAU=math.tau


def unit(v):
    v=np.asarray(v,float)
    return v/max(np.linalg.norm(v),1e-12)


def build(model,p):
    rng=np.random.default_rng(27017)
    original_collision=(len(model.boxes),len(model.hulls),len(model.props))
    model.material_overrides.update(S.MATERIALS)
    model.tile_overrides.update({paint:12 for paint in S.MATERIALS})

    def normal(n):return p.x*n[0]+p.y*n[1]+p.z*n[2]

    def face(paint,pts,n,uv=None,normals=None):
        F.face(model,paint,[p.at(v) for v in pts],normal(n),uv,
               [normal(v) for v in normals] if normals is not None else None)

    def tube(a,b,r,paint=S.TWINE,sides=6,taper=1.,caps=True):
        a,b=np.asarray(a,float),np.asarray(b,float)
        axis=unit(b-a)
        u=unit(np.cross(axis,(0,0,1) if abs(axis[2])<.9 else (0,1,0)))
        v=np.cross(axis,u)
        rim=[u*math.cos(k*TAU/sides)+v*math.sin(k*TAU/sides) for k in range(sides)]
        length=np.linalg.norm(b-a)
        for k in range(sides):
            d0,d1=rim[k],rim[(k+1)%sides]
            face(paint,[a+r*d0,a+r*d1,b+r*taper*d1,b+r*taper*d0],d0+d1,
                 [(k/sides,0),((k+1)/sides,0),((k+1)/sides,length/9),(k/sides,length/9)],
                 [d0,d1,d1,d0])
        if caps:
            face(paint,[a+r*d for d in rim],-axis)
            face(paint,[b+r*taper*d for d in rim],axis)

    def cord(points,r=.10,paint=S.TWINE,sides=5):
        for a,b in zip(points,points[1:]):tube(a,b,r,paint,sides,caps=False)

    def surface(paint,point,outward,u0,u1,v0,v1,cols,rows,uv=None):
        def vertex(u,v):
            q=np.asarray(point(u,v),float)
            du=np.asarray(point(u+1e-4,v))-np.asarray(point(u-1e-4,v))
            dv=np.asarray(point(u,v+1e-4))-np.asarray(point(u,v-1e-4))
            n=unit(np.cross(du,dv));out=np.asarray(outward(u,v))
            if np.dot(n,out)<0:n=-n
            if np.linalg.norm(n)<.1:n=unit(out)
            return q,n
        for j in range(rows):
            va,vb=v0+(v1-v0)*j/rows,v0+(v1-v0)*(j+1)/rows
            for i in range(cols):
                ua,ub=u0+(u1-u0)*i/cols,u0+(u1-u0)*(i+1)/cols
                pairs=[(ua,va),(ub,va),(ub,vb),(ua,vb)]
                values=[vertex(u,v) for u,v in pairs]
                if np.linalg.norm(values[0][0]-values[1][0])<1e-5:pairs,values=pairs[1:],values[1:]
                elif np.linalg.norm(values[2][0]-values[3][0])<1e-5:pairs,values=pairs[:3],values[:3]
                pts=[q for q,n in values];ns=[n for q,n in values]
                if np.linalg.norm(np.cross(pts[1]-pts[0],pts[2]-pts[0]))<1e-9:continue
                coords=[uv(u,v) if uv else (u/TAU,v) for u,v in pairs]
                # Triangulate curved cells explicitly so concave folds cannot invert a fan.
                for k in range(1,len(pts)-1):
                    ids=(0,k,k+1)
                    if np.linalg.norm(np.cross(pts[k]-pts[0],pts[k+1]-pts[0]))<1e-9:continue
                    face(paint,[pts[x] for x in ids],sum(ns[x] for x in ids),
                         [coords[x] for x in ids],[ns[x] for x in ids])

    # Exposed timber is still grounded at the original garden stake.
    F.bevel_box(model,p.at((0,0,37)),(p.x,p.y,p.z),(3,3,74),F.DARK,.23,517)
    tube((-24,0,54.1),(23.5,0,54.1),1.32,F.DARK,8)

    def hem(theta):
        return 29.4+1.05*math.sin(3*theta+.5)+.50*math.sin(7*theta+1.2)+.26*math.sin(13*theta)

    def torso(theta,t):
        t=float(t);c,s=math.cos(theta),math.sin(theta)
        width=np.interp(t,[0,.12,.38,.60,.76,.86,1],[11.8,12.3,10.6,12.1,14.1,12.3,4.0])
        depth=np.interp(t,[0,.18,.42,.68,.84,1],[5.3,6.3,6.8,7.5,6.4,2.7])
        # Hanging vertical folds at the lower shirt and compressed diagonal folds
        # from shoulders to the cinched waist; no straight cylindrical hem.
        lower=max(0.,1-t)**1.5*(.78*math.sin(9*theta+.7)+.30*math.sin(17*theta+4*t))
        shoulder=math.exp(-((t-.68)/.21)**2)*.55*math.sin(8*theta+18*t)
        waist=-.72*math.exp(-((t-.38)/.050)**2)
        ripple=lower+shoulder+waist
        x=math.copysign(abs(c)**.85,c)*(width+ripple)-.65*math.sin(math.pi*t)
        y=math.copysign(abs(s)**.86,s)*(depth+.48*ripple)+.35*math.sin(5*t)
        z=hem(theta)*(1-t)+(60.4+.55*c)*t
        return np.array((x,y,z))

    surface(S.SHIRT,torso,lambda u,v:(math.cos(u),math.sin(u),0),0,TAU,0,1,64,30,
            lambda u,v:(2*u/TAU,1.65*v))
    # Turned-back hem, including a visible dark inside rather than a paper edge.
    surface(S.SHIRT,lambda u,v:torso(u,v*.04)-np.array((math.cos(u),math.sin(u),0))*.15,
            lambda u,v:(-math.cos(u),-math.sin(u),0),0,TAU,0,1,64,2,
            lambda u,v:(2*u/TAU,v*.08))
    hemline=[torso(k*TAU/100,.045)+np.array((math.cos(k*TAU/100),math.sin(k*TAU/100),0))*.045 for k in range(101)]
    cord(hemline,.045,S.TWINE,4)
    stuffing=[torso(k*TAU/64,0)*np.array((.89,.89,1))+(0,0,.65) for k in range(64)]
    for k in range(64):
        face(S.SACK,[(0,0,31.2),stuffing[k],stuffing[(k+1)%64]],(0,0,-1))

    # Long sleeves hang from the timber and buckle around the crossbar.
    sleeve_functions=[]
    for side in (-1,1):
        def sleeve(theta,t,side=side):
            t=float(t);r=np.interp(t,[0,.2,.5,.74,1],[4.9,5.2,4.6,3.6,3.15])
            r+=.40*math.sin(7*theta+13*t)*math.sin(math.pi*t)**2
            r+=.24*math.sin(3*theta+7*t)
            cuff=.26*math.sin(5*theta)+.14*math.sin(11*theta+.8)
            z=54.3-(1.4 if side<0 else 2.4)*t-1.1*math.sin(math.pi*t)+r*math.sin(theta)
            return np.array((side*(6.5+21.3*t+cuff*t**9),r*math.cos(theta)+.35*t,z))
        sleeve_functions.append((side,sleeve))
        surface(S.SHIRT,sleeve,lambda u,v:(0,math.cos(u),math.sin(u)),0,TAU,0,1,40,24,
                lambda u,v:(u/TAU,1.2*v))
        cord([sleeve(k*TAU/64,.28)+np.array((0,math.cos(k*TAU/64),math.sin(k*TAU/64)))*.045
              for k in range(65)],.042,S.TWINE,4)
        # Thick, rolled cuffs with a loose, uneven opening and inner cloth.
        surface(S.SHIRT,lambda u,v,sleeve=sleeve,side=side:
                    sleeve(u,.87+.13*v)+np.array((0,math.cos(u),math.sin(u)))*(.15+.17*math.sin(math.pi*v)),
                lambda u,v:(0,math.cos(u),math.sin(u)),0,TAU,0,1,40,4)
        surface(S.SHIRT,lambda u,v,sleeve=sleeve:
                    sleeve(u,.94+.06*v)-np.array((0,math.cos(u),math.sin(u)))*.16,
                lambda u,v:(0,-math.cos(u),-math.sin(u)),0,TAU,0,1,40,2)
        cord([sleeve(k*TAU/60,.90)+np.array((0,math.cos(k*TAU/60),math.sin(k*TAU/60)))*.35 for k in range(61)],.065,S.TWINE)

    # A real front fastening sits on the deformed cloth, with five sewn buttons.
    def front(t,angle=math.pi/2,offset=.12):
        q=torso(angle,t);q[1]+=offset
        return q
    surface(S.SHIRT,lambda u,v:front(v,math.pi/2+u,.17),lambda u,v:(0,1,0),
            -.046,.046,.10,.96,4,28,lambda u,v:(.25+u,v*1.65))
    for edge in (-.049,.049):cord([front(t,math.pi/2+edge,.23) for t in np.linspace(.10,.94,60)],.042,S.TWINE,4)
    for t in (.23,.39,.55,.70,.84):
        q=front(t,offset=.28)
        tube(q,q+(0,.16,0),.24,S.STITCH,12)
        tube(q+(-.065,.18,-.06),q+(.065,.18,.06),.035,S.TWINE,4)
    # Pointed, softly turned collar leaves an opening around the tied sack neck.
    for side in (-1,1):
        def collar(u,v,side=side):
            outer=np.array((side*(5.25-2.15*u),4.0+.6*u,59.3-4.0*u))
            inner=np.array((side*(2.55-.8*u),2.55+3.1*u,60.6-5.6*u))
            q=outer*(1-v)+inner*v
            q[1]+=.30*math.sin(math.pi*u)*math.sin(math.pi*v)
            return q
        surface(S.SHIRT,collar,lambda u,v:(0,1,.4),0,1,0,1,10,5)
        surface(S.SHIRT,lambda u,v:collar(u,v)-(0,.13,0),lambda u,v:(0,-1,-.4),0,1,0,1,10,5)
        cord([collar(t,0)+(0,.06,0) for t in np.linspace(0,1,25)],.055,S.TWINE,4)

    # Small cloth repairs conform to the shirt folds, their borders stitched down.
    def repair(u0,u1,v0,v1):
        def patch(u,v):
            q=torso(u,v);q[:2]+=unit((q[0],q[1],0))[:2]*(.10+.04*math.sin(7*u+14*v))
            return q
        surface(S.PATCH,patch,lambda u,v:(math.cos(u),math.sin(u),0),u0,u1,v0,v1,10,10,
                lambda u,v:((u-u0)/(u1-u0),(v-v0)/(v1-v0)))
        for a,b,c,d,count in ((u0,u1,v0,v0,12),(u0,u1,v1,v1,12),(u0,u0,v0,v1,10),(u1,u1,v0,v1,10)):
            for k in range(count):
                t=(k+.15)/count;s=(k+.67)/count
                tube(patch(a+(b-a)*t,c+(d-c)*t)+(0,.045,0),patch(a+(b-a)*s,c+(d-c)*s)+(0,.045,0),.050,S.TWINE,4,caps=False)
    repair(.93,1.28,.16,.34)
    repair(1.91,2.14,.59,.70)

    # Uneven bale stuffing, tapered split stalks and loose thread ends.
    def straw_bundle(origin,direction,count,spread,length):
        axis=unit(direction);u=unit(np.cross(axis,(0,1,0)));v=np.cross(axis,u)
        for k in range(count):
            a=rng.uniform(0,TAU);r=spread*math.sqrt(rng.uniform(0,1))
            start=np.asarray(origin)+u*math.cos(a)*r+v*math.sin(a)*r
            stalk=length*rng.uniform(.55,1.12)
            middle=start+axis*stalk*.56+u*rng.uniform(-.25,.25)
            tip=start+axis*stalk+u*rng.uniform(-.65,.65)+v*rng.uniform(-.45,.45)
            tube(start,middle,rng.uniform(.045,.075),S.HAT,4,taper=.82,caps=False)
            tube(middle,tip,.043,S.HAT,4,taper=.10,caps=False)
    for side,sleeve in sleeve_functions:
        centre=np.mean([sleeve(k*TAU/16,.96) for k in range(16)],axis=0)
        disc_centre=centre+np.array((side*.24,0,0))
        face(S.SACK,[disc_centre+np.array((0,math.cos(a)*2.74,math.sin(a)*2.74))
                     for a in np.linspace(0,TAU,32,endpoint=False)],(side,0,0))
        straw_bundle(centre,(side,0,-.18),29,2.55,4.0)
        for k in range(9):
            q=sleeve(k*TAU/9,1)
            cord([q,q+(side*.4,.08,-.45),q+(side*.7,.10,-.7)],.032,S.TWINE,4)
    for theta in (.48,.85,1.34,1.82,2.25,2.75,4.0,5.3):
        q=torso(theta,.01);q[:2]*=.82;q[2]+=.40
        straw_bundle(q,(.10*math.cos(theta),.10*math.sin(theta),-1),5,.55,3.0)
    for k in range(27):
        a=rng.uniform(0,TAU);q=torso(a,.005)
        cord([q,q+(rng.uniform(-.15,.15),.04,-rng.uniform(.25,.65))],.025,S.TWINE,4)

    # A lumpy, slightly cocked bag; the seam gathers instead of ending in an oval.
    def head(theta,lat):
        c=max(0,math.cos(lat));s=math.sin(lat)
        wobble=1+.047*math.sin(3*theta+lat)+.020*math.cos(7*theta-2*lat)
        gather=.25*c*math.exp(-((lat+1.12)/.22)**2)*math.sin(14*theta)
        x=(6.8*c*wobble+gather)*math.cos(theta)-.90*s-.20
        y=(5.85*c*wobble+gather)*math.sin(theta)+.15*s
        z=68.35+7.95*s+.32*c*math.sin(2*theta+.6)
        return np.array((x,y,z))
    surface(S.SACK,head,lambda u,v:(math.cos(v)*math.cos(u),math.cos(v)*math.sin(u),math.sin(v)),
            0,TAU,-math.pi/2,math.pi/2,64,30,lambda u,v:(u/TAU*1.45,v/math.pi+.5))

    def headfront(x,z):
        lat=math.asin(np.clip((z-68.35)/7.95,-.96,.96))
        theta=math.acos(np.clip((x+.90*math.sin(lat)+.20)/(6.8*math.cos(lat)),-.97,.97))
        # Newton correction follows the lumpy sack rather than a nominal sphere.
        for k in range(6):
            q=head(theta,lat);dx=(head(theta+.001,lat)[0]-head(theta-.001,lat)[0])/.002
            if abs(dx)>.01:theta=np.clip(theta-(q[0]-x)/dx,.04,math.pi-.04)
        q=head(theta,lat);q[1]+=.095
        return q
    for x,z,tilt in ((-2.4,69.7,.10),(2.1,69.4,-.15)):
        for direction in (-1,1):
            a=headfront(x-.56,z-.62*direction+tilt);b=headfront(x+.56,z+.62*direction-tilt)
            cord([a,(a+b)/2+(0,.09,0),b],.093,S.STITCH,6)
    mouth=[]
    for x in np.linspace(-3.1,3.0,25):mouth.append(headfront(x,64.85+.095*x*x+.11*x))
    cord(mouth,.078,S.STITCH,5)
    for x in np.linspace(-2.9,2.8,11):
        z=64.85+.095*x*x+.11*x
        tube(headfront(x-.05,z-.23),headfront(x+.04,z+.24),.050,S.STITCH,4,caps=False)
    for angle in (0.05,math.pi-.05):
        for lat in np.linspace(-1.1,1.15,29):
            q=head(angle,lat);q[:2]+=unit((q[0],q[1],0))[:2]*.055
            r=head(angle+.025,lat+.025);r[:2]+=unit((r[0],r[1],0))[:2]*.055
            tube(q,r,.050,S.TWINE,4,caps=False)

    # A gathered sack neck, tied twice, with a visibly knotted front.
    for z,r in ((60.7,3.15),(60.98,3.18)):
        cord([(r*math.cos(a),r*math.sin(a),z+.05*math.sin(5*a)) for a in np.linspace(0,TAU,65)],.14,S.TWINE,6)
    cord([(-.55,3.5,61),(.15,3.9,61.3),(.58,3.5,60.9),(-.1,3.7,60.6),(-.55,3.5,61)],.19,S.TWINE)
    cord([(-.1,3.8,60.7),(-1.2,4.4,59.1),(-1.4,4.2,57.3)],.12,S.TWINE)
    cord([(.1,3.8,60.7),(1.5,4.2,59.4),(1.1,4.1,58.0)],.12,S.TWINE)
    straw_bundle((0,0,59.9),(0,.12,1),12,2.6,2.4)

    # Crushed, pinched field hat; the swept brim has local dips and real thickness.
    def brim(theta,t):
        r=5.55+7.5*t
        wave=.9*math.sin(2*theta+.4)+.48*math.sin(3*theta-1)+.24*math.cos(7*theta)
        return np.array((-.9+r*math.cos(theta),r*.91*math.sin(theta),
            74.5+t*t*(wave-.55)+.18*math.cos(theta)))
    surface(S.HAT,brim,lambda u,v:(0,0,1),0,TAU,0,1,64,10,lambda u,v:(u/TAU*1.9,v))
    surface(S.HAT,lambda u,v:brim(u,v)-(0,0,.18),lambda u,v:(0,0,-1),0,TAU,0,1,64,10,
            lambda u,v:(u/TAU*1.9,v))
    for k in range(64):
        a,b=k*TAU/64,(k+1)*TAU/64;q,r=brim(a,1),brim(b,1)
        face(S.HAT,[q,r,r-(0,0,.18),q-(0,0,.18)],(math.cos(a),math.sin(a),0))
    # The inside of the crown closes the opening around the sack's rounded top.
    face(S.STITCH,[(-.9+5.6*math.cos(a),5.6*.91*math.sin(a),74.32)
                   for a in np.linspace(0,TAU,64,endpoint=False)],(0,0,-1))
    cord([brim(t,1)+(0,0,.025) for t in np.linspace(0,TAU,161)],.080,S.HAT,5)
    def crown(theta,t):
        r=np.interp(t,[0,.15,.52,.8,1],[5.8,5.9,5.3,4.65,4.45])
        dent=(.38*math.cos(2*theta)+.17*math.sin(5*theta+.4))*math.sin(math.pi*t/2)**2
        return np.array((-.9+(r+dent)*math.cos(theta)-.65*t,
            (r+dent)*.88*math.sin(theta),74.45+6.65*t+.30*t*math.sin(theta-.3)))
    surface(S.HAT,crown,lambda u,v:(math.cos(u),math.sin(u),.1),0,TAU,0,1,64,13,
            lambda u,v:(u/TAU*1.9,v))
    # Join the crown to the warped inner brim; their unequal ellipses otherwise
    # leave a thin sky slit visible from below the hat.
    surface(S.HAT,lambda u,v:crown(u,0)*(1-v)+brim(u,0)*v,
            lambda u,v:(0,0,-1),0,TAU,0,1,64,1,
            lambda u,v:(u/TAU*1.9,v*.04))
    def top(theta,t):
        edge=crown(theta,1);centre=np.array((-1.55,0,80.25))
        q=centre*(1-t)+edge*t
        q[2]-=.72*(1-t)*math.exp(-((q[1]/2.0)**2))
        return q
    surface(S.HAT,top,lambda u,v:(0,0,1),0,TAU,0,1,64,9,
            lambda u,v:(.5+.45*v*math.cos(u),.5+.45*v*math.sin(u)))
    surface(S.STITCH,lambda u,v:crown(u,v)+np.array((math.cos(u),math.sin(u),0))*.09,
            lambda u,v:(math.cos(u),math.sin(u),0),0,TAU,.13,.25,64,3)
    for k in range(25):
        a=rng.uniform(0,TAU);q=brim(a,.985)
        cord([q,q+(math.cos(a)*.35,math.sin(a)*.35,-.12),q+(math.cos(a)*rng.uniform(.4,.8),math.sin(a)*.55,-.20)],.032,S.HAT,4)

    assert (len(model.boxes),len(model.hulls),len(model.props))==original_collision
