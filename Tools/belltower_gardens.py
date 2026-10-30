"""Built garden props, with the original cover collision kept by the caller.

Timber uses Belltower's photographed board strips. Firewood cut faces reuse the
existing oak end-grain material; its source textures are not modified.
"""
import math
import zlib
import numpy as np

import belltower_furniture as F
import belltower_padlock as Padlock
import belltower_shed_wood as ShedWood
from map_kit import normalise

END_GRAIN = 'garden_endgrain'
END_MATERIAL = 'materials/gunsmith_range/bench_oak_endgrain.vmat'


def _seed(*values):
    return zlib.crc32(','.join(f'{v:g}' for v in values).encode())


def _box(model, lo, hi, paint=F.WOOD, bevel=.12, seed=0):
    lo, hi = np.asarray(lo, float), np.asarray(hi, float)
    F.bevel_box(model, (lo+hi)/2, np.eye(3), hi-lo, paint, bevel, seed)


def shed(model, e0, e1, n0, n1, z, door, small=False):
    """Close the lean-to wedge and build its cladding, braced door and ribbed roof."""
    height = 84 if small else 100
    seed = _seed(e0, n0, z)
    slope = 16/(n1-n0+16)
    across = np.array((1., 0., 0.))
    down = normalise((0., 1., -slope))
    up = np.cross(across, down)
    roof_centre = np.array(((e0+e1)/2, (n0+n1)/2, z+height+10))
    width, length = e1-e0+12, math.hypot(n1-n0+16, 16)

    def top(n):
        # The walls meet the underside of the roof deck at every point.
        return roof_centre[2]-slope*(n-roof_centre[1])-1.45/up[2]

    # A closed backing keeps the small board joints dark and fills the former
    # 2..18-inch open wedge under the roof. All four sides follow its slope.
    for points, normal in (
        ([(e0,n0,z),(e0,n1,z),(e0,n1,top(n1)),(e0,n0,top(n0))],(-1,0,0)),
        ([(e1,n0,z),(e1,n1,z),(e1,n1,top(n1)),(e1,n0,top(n0))],(1,0,0)),
        ([(e0,n0,z),(e1,n0,z),(e1,n0,top(n0)),(e0,n0,top(n0))],(0,-1,0)),
        ([(e0,n1,z),(e1,n1,z),(e1,n1,top(n1)),(e0,n1,top(n1))],(0,1,0)),
    ):
        normal = np.asarray(normal, float)
        F.face(model, F.DARK, [np.asarray(p)-normal*1.1 for p in points], normal)

    sides = (
        ('-n', e0, e1, np.array((0.,n0,0.)), across, np.array((0.,-1.,0.))),
        ('+n', e0, e1, np.array((0.,n1,0.)), across, np.array((0.,1.,0.))),
        ('-e', n0, n1, np.array((e0,0.,0.)), np.array((0.,1.,0.)), np.array((-1.,0.,0.))),
        ('+e', n0, n1, np.array((e1,0.,0.)), np.array((0.,1.,0.)), np.array((1.,0.,0.))),
    )
    vertical = np.array((0.,0.,1.))
    for side, start, end, origin, run, outward in sides:
        def at(r, d, h):
            return origin+run*r+outward*d+vertical*h

        def wall_top(r):
            return top(at(r,0,0)[1])

        centre = (start+end)/2
        # Recess boards behind the trim. Coplanar front faces flicker against
        # the bottom rails and corner stiles in the engine's depth buffer.
        count = max(1, round((end-start)/6.5))
        cuts = np.linspace(start,end,count+1)
        if side == door:
            cuts = np.unique(np.concatenate((cuts,[centre-20,centre+20])))
        for i,(a,b) in enumerate(zip(cuts,cuts[1:])):
            lower = z+77.5 if side==door and centre-20<(a+b)/2<centre+20 else z+.35
            upper = min(wall_top(a),wall_top(b))-.1
            if upper<=lower:
                continue
            if i < 2 or i >= len(cuts)-3:
                ShedWood.board(model,at((a+b)/2,-.575,(lower+upper)/2),(run,outward,vertical),
                               (b-a-.12,.65,upper-lower),F.WOOD,seed+i+len(side))
            else:
                F.bevel_box(model,at((a+b)/2,-.575,(lower+upper)/2),(run,outward,vertical),
                            (b-a-.12,.65,upper-lower),F.WOOD,.08,seed+i+len(side))
        # A bottom rail and corner stiles visually tie the cladding together.
        intervals = ((start,centre-20.5),(centre+20.5,end)) if side==door else ((start,end),)
        for a,b in intervals:
            ShedWood.board(model,at((a+b)/2,-.32,z+2),(run,outward,vertical),
                           (b-a,.64,3.8),F.DARK,seed+73,trim=True)
        for r in (start+1.8,end-1.8):
            upper = wall_top(r)-.4
            # A real corner board needs thickness for a worn, rounded arris.
            ShedWood.board(model,at(r,-.30,(z+upper)/2),(run,outward,vertical),
                           (3.5,1.10,upper-z),F.DARK,seed+80+round(r),trim=True)
        # Fascia overlaps the cut board ends under the sloping eaves.
        F.beam(model,at(start,-.2,wall_top(start)-1.8),at(end,-.2,wall_top(end)-1.8),
               (1.0,3.4),F.DARK,.14,seed+91,up=vertical)
        if side != door:
            continue

        # Closed, separately boarded door in the former leaf's footprint.
        for k in range(8):
            a=centre-19.7+k*4.925
            ShedWood.board(model,at(a+2.40,.66,z+38),(run,outward,vertical),
                           (4.77,1.08,75.6),F.DARK,seed+110+k)
        for h in (12,40,66):
            F.bevel_box(model,at(centre,1.50,z+h),(run,outward,vertical),
                        (38,1.0,3.5),F.WOOD,.16,seed+140+h)
        F.beam(model,at(centre-17,1.50,z+14),at(centre+17,1.50,z+64),
               (3.0,.85),F.WOOD,.12,seed+160,up=outward)
        for h in (12,66):
            F.bevel_box(model,at(centre-13,2.05,z+h),(run,outward,vertical),
                        (13,.23,1.6),F.IRON,.07,seed+180+h)
            for r in (centre-18,centre-8):
                F.bolt(model,at(r,2.18,z+h),outward,.23,False)
        for r in (centre-21,centre+21):
            ShedWood.board(model,at(r,.62,z+38.5),(run,outward,vertical),
                           (2.0,1.24,77),F.WOOD,seed+200+round(r),trim=True)
        ShedWood.board(model,at(centre,.62,z+78),(run,outward,vertical),
                       (44,1.24,2.6),F.WOOD,seed+202,trim=True)
        Padlock.build(model,at(centre+14,0,z+38),(run,outward,vertical),seed+206)

    # Fitted sheathing and exposed rafter tails replace the floating flat slab.
    F.bevel_box(model,roof_centre-up*1.0,(across,down,up),(width-4,length-4,.9),F.DARK,.10,seed+220)
    for x in np.linspace(-width/2+7,width/2-7,max(3,round(width/25))):
        F.beam(model,roof_centre+across*x-down*(length/2-2)-up*2.8,
               roof_centre+across*x+down*(length/2-2)-up*2.8,
               (2.2,3.0),F.WOOD,.15,seed+240+round(x),up=up)
    for x in (-width/2+1.4,width/2-1.4):
        F.beam(model,roof_centre+across*x-down*(length/2-1)-up*.4,
               roof_centre+across*x+down*(length/2-1)-up*.4,
               (1.15,2.2),F.DARK,.12,seed+280,up=up)

    # The existing corrugated material has 24 ribs per 64-unit tile. Match that
    # phase and physical pitch, rather than double-counting unrelated rib scales.
    pitch=64/24
    steps=max(4,math.ceil(width/pitch*6))
    xs=np.linspace(-width/2,width/2,steps+1)
    phase_offset=(seed%24)*pitch
    def roof_point(x,y,lower=False):
        normal_offset=.64+.44*math.sin((x+phase_offset)*math.tau/pitch)-(.12 if lower else 0)
        return roof_centre+across*x+down*y+up*normal_offset
    def roof_normal(x):
        derivative=.44*math.tau/pitch*math.cos((x+phase_offset)*math.tau/pitch)
        return normalise(up-across*derivative)
    for a,b in zip(xs,xs[1:]):
        xy=((a,-length/2),(b,-length/2),(b,length/2),(a,length/2))
        uv=[((x+phase_offset)/64,y/64+(seed%113)/113) for x,y in xy]
        F.face(model,'corrugated',[roof_point(x,y) for x,y in xy],up,uv,
               [roof_normal(x) for x,y in xy])
        F.face(model,F.IRON,[roof_point(x,y,True) for x,y in xy],-up)
        for y,sign in ((-length/2,-1),(length/2,1)):
            F.face(model,F.IRON,[roof_point(a,y),roof_point(b,y),roof_point(b,y,True),roof_point(a,y,True)],down*sign)
    for x,sign in ((-width/2,-1),(width/2,1)):
        F.face(model,F.IRON,[roof_point(x,-length/2),roof_point(x,length/2),
                            roof_point(x,length/2,True),roof_point(x,-length/2,True)],across*sign)
    # Screw rows make the sheet construction readable.
    for x in np.linspace(-width/2+1,width/2-1,max(3,round(width/26)+1)):
        for y in (-length/2+5,length/2-5):
            F.bolt(model,roof_point(x,y),up,.24,False)


def compost_bin(model,e0,e1,n0,n1,z,height=36):
    """Separate slats and posts around recessed soil, inside the original cover box."""
    seed=_seed(e0,n0,z)
    # Dark soil behind the joints avoids seeing through solid gameplay cover.
    model.box((e0+.8,n0+.8,z),(e1-.8,n1-.8,z+height-4),{'default':'soil'})
    for k in range(5):
        a=z+.5+k*7
        b=min(a+5.7,z+height-.5)
        for n in (n0+.7,n1-.7):
            _box(model,(e0,n-.7,a),(e1,n+.7,b),F.WOOD,.12,seed+k)
        for e in (e0+.7,e1-.7):
            _box(model,(e-.7,n0+1.4,a),(e+.7,n1-1.4,b),F.WOOD,.12,seed+k+10)
    for e in (e0+1.8,e1-1.8):
        for n in (n0+1.8,n1-1.8):
            _box(model,(e-1.7,n-1.7,z),(e+1.7,n+1.7,z+height),F.DARK,.18,seed+20)
            for h in (5,19,32):
                normal=(0,-1,0) if n<(n0+n1)/2 else (0,1,0)
                point=(e,n0+.32 if normal[1]<0 else n1-.32,z+h)
                F.bolt(model,point,normal,.20,False)


def woodpile(model,e0,e1,n0,n1,z,height=40):
    """Staggered, individually cut logs, with no rectangular visual backing."""
    model.material_overrides[END_GRAIN]=END_MATERIAL
    model.tile_overrides[END_GRAIN]=12
    rng=np.random.default_rng(_seed(e0,n0,z))
    radius=min(height/7.3,(e1-e0)/18.3)
    spacing=(e1-e0-2*radius)/8
    previous=[]
    def surface(profile,x,upper):
        intersections=[]
        for a,b in zip(profile,profile[1:]+profile[:1]):
            if min(a[0],b[0])-1e-7<=x<=max(a[0],b[0])+1e-7 and abs(b[0]-a[0])>1e-7:
                t=(x-a[0])/(b[0]-a[0])
                intersections.append(a[1]+t*(b[1]-a[1]))
        return (max if upper else min)(intersections)
    for row in range(4):
        current=[]
        count=9 if row%2==0 else 8
        for k in range(count):
            e=e0+radius+(row%2)*spacing*.5+k*spacing
            angle=rng.uniform(-.30,.30)
            # Removing one vertex gives a broad split face rather than an
            # identical seven-sided timber. The remaining polygon is convex.
            omit=int(rng.integers(0,8))
            scale=rng.uniform(.94,1.0)
            profile=[(math.cos(angle+j*math.tau/8)*radius*scale,
                      math.sin(angle+j*math.tau/8)*radius*scale)
                     for j in range(8) if j!=omit]
            # Rest each cross-section on the actual logs below it. Uniform row
            # heights would leave visibly floating pieces after the split cuts.
            footprint=[(e+x,h) for x,h in profile]
            centre_z=z-min(p[1] for p in profile)+.04
            for support in previous:
                lo=max(min(p[0] for p in footprint),min(p[0] for p in support))
                hi=min(max(p[0] for p in footprint),max(p[0] for p in support))
                if hi<=lo:
                    continue
                xs=[lo,hi]+[p[0] for p in footprint+support if lo<p[0]<hi]
                centre_z=max(centre_z,max(surface(support,x,True)-surface(footprint,x,False) for x in xs)+.02)
            current.append([(e+x,centre_z+h) for x,h in profile])
            start=n0+rng.uniform(.15,2.4)
            end=n1-rng.uniform(.15,2.4)
            def at(point,n):
                return np.array((e+point[0],n,centre_z+point[1]))
            for i,(a,b) in enumerate(zip(profile,profile[1:]+profile[:1])):
                normal=np.array((b[1]-a[1],0,a[0]-b[0]))
                u0,u1=F.STRIPS[(k+row+i)%len(F.STRIPS)]
                points=[at(a,start+.15),at(b,start+.15),at(b,end-.15),at(a,end-.15)]
                uv=[(u0,start/F.TILE),(u1,start/F.TILE),(u1,end/F.TILE),(u0,end/F.TILE)]
                F.face(model,F.DARK if (k+i)%3 else F.WOOD,points,normal,uv)
                for n,inner,sign in ((start,start+.15,-1),(end,end-.15,1)):
                    # Small end chips catch light without another box shell.
                    F.face(model,F.WOOD,[at(a,inner),at(b,inner),at(np.asarray(b)*.97,n),at(np.asarray(a)*.97,n)],
                           normal+np.array((0,sign*radius,0)),uv)
            offset=rng.random(2)
            uv_angle=rng.uniform(0,math.tau)
            c,s=math.cos(uv_angle),math.sin(uv_angle)
            uv=[((p[0]*c-p[1]*s)/12+offset[0],(p[0]*s+p[1]*c)/12+offset[1]) for p in profile]
            for n,normal in ((start,(0,-1,0)),(end,(0,1,0))):
                F.face(model,END_GRAIN,[at(np.asarray(p)*.97,n) for p in profile],normal,uv)
        previous=current


def wheelbarrow(model,p):
    from belltower_wheelbarrow import build
    return build(model,p)
