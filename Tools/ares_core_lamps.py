"""Mounted luminaires on the actual 48-sided underside of Ares' flared core ring."""
import math
import numpy as np
import riverdale_parts as P

UP=np.array((0.,0.,1.))


def legacy_lamps(model):
    """Exact old render blocks, used solely by the scoped mesh migration."""
    for k in range(24):
        a=math.tau*k/24
        p=np.array((208*math.cos(a),208*math.sin(a),566.))
        model.box(p-np.array((4,4,1.2)),p+np.array((4,4,.6)),'ar_led_warm')


def frames():
    # Each fixture is centred within one real mesh facet instead of straddling
    # a cone vertex. Tangent/upslope/outward form a right-handed orthonormal set.
    half=math.pi/48
    slope=(224.-150.)/(568.-560.)*math.cos(half)
    for k in range(24):
        a=(2*k+.5)*math.tau/48
        radial=np.array((math.cos(a),math.sin(a),0.))
        tangent=np.array((-math.sin(a),math.cos(a),0.))
        outward=P.unit(radial-UP*slope)
        upslope=P.unit(radial*slope+UP)
        origin=radial*((150.+(566.-560.)*9.25)*math.cos(half))+UP*566.
        yield k,origin,tangent,upslope,outward


def flared_ring_lamps(model):
    """Render detail only: embedded mounting plates, housings, bezels and lenses."""
    collision_counts=(len(model.boxes),len(model.hulls))
    reports=[]
    for k,origin,tangent,upslope,outward in frames():
        axes=(tangent,upslope,outward)
        assert np.dot(np.cross(tangent,upslope),outward)>.99999
        # Back face sits 0.10 inch inside the actual cone facet. The plate has
        # real contact across its entire footprint, not just one cube corner.
        P.bevel_box(model,origin+outward*.075,axes,(10.5,8.5,.35),'ar_steel',bevel=.12)
        model.oriented_box(origin+outward*.29,axes,(9.6,7.4,.12),'ar_gunmetal')
        P.bevel_box(model,origin+outward*.66,axes,(9.2,7.0,.85),'ar_gunmetal',bevel=.16)
        # Raised protective rim surrounds a recessed emitting face. Only this
        # face glows; the housing, fasteners, sides and mounting plate do not.
        for sign in (-1,1):
            P.bevel_box(model,origin+tangent*(sign*4.25)+outward*1.20,
                        axes,(.55,6.60,.52),'ar_steel',bevel=.08)
            P.bevel_box(model,origin+upslope*(sign*3.02)+outward*1.20,
                        axes,(8.10,.55,.52),'ar_steel',bevel=.08)
        face=[(-3.94,-2.68),(3.94,-2.68),(4.01,-2.58),(4.01,2.58),
              (3.94,2.68),(-3.94,2.68),(-4.01,2.58),(-4.01,-2.58)]
        P.card(model,'ar_led_warm',[origin+tangent*x+upslope*y+outward*1.115 for x,y in face],outward)
        for x in (-4.83,4.83):
            for y in (-3.80,3.80):
                at=origin+tangent*x+upslope*y
                P.rod(model,at+outward*.255,at+outward*.46,.25,'ar_steel',8,caps=True)
                # A shallow dark drive slot, supported by the screw head.
                model.oriented_box(at+outward*.464,axes,(.28,.075,.018),'ar_gunmetal')
        # Geometric evidence: plane contact and footprint inside the facet.
        mount=[origin+tangent*x+upslope*y-outward*.10 for x in (-5.05,5.05) for y in (-4.,4.)]
        distances=[float(np.dot(p-origin,outward)) for p in mount]
        assert max(abs(d+.10) for d in distances)<1e-8
        min_face_half=min((150.+(p[2]-560.)*9.25)*math.sin(math.pi/48) for p in mount)
        assert min_face_half>5.25
        reports.append({'index':k,'surface_origin':origin.tolist(),'surface_normal':outward.tolist(),
                        'mount_back_plane_distances':distances,'lens_recess_inches':1.46-1.115})
    assert (len(model.boxes),len(model.hulls))==collision_counts
    return reports
