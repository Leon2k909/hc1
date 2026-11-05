"""Approved Lucky Stop ice cabinet geometry; preserve original collision and porch light."""
import numpy as np
import map_kit as K
import riverdale_parts as G
MAT="materials/riverside/ice-cabinet-v1"
X=np.array((1.,0.,0.));Y=np.array((0.,-1.,0.));Z=np.array((0.,0.,1.))
def point(x,d,z):return X*x+Y*d+Z*z
def model(lod=0):
    m=K.Model();sides=(20,12,8)[lod]
    def box(c,sz,paint,bevel=.12,paints=None):
        G.bevel_box(m,point(*c),(X,Y,Z),sz,paints or paint,bevel=bevel)
    def cyl(c,axis,length,r,paint):
        G.lathe_axis(m,point(*c),axis,[(0.,0.),(r,0.),(r,length),(0.,length)],paint,sides=sides)
    def screw(x,d,z):
        cyl((x,d,z),Y,.07,.14,'steel')
        if lod==0:
            box((x,d+.078,z),(.20,.012,.038),'recess',.005)
            box((x,d+.078,z),(.038,.012,.20),'recess',.005)
    # Same 38 x 30 x 60 inch cabinet volume as the original; corner chamfers catch porch lighting.
    box((0,-.45,30.2),(38,29.1,59.6),'enamel',.48)
    box((0,0,2.0),(37.6,29.4,2.7),'rubber',.35)
    for x in (-15.2,15.2):
        for d in (-11.4,11.4):cyl((x,d,0),Z,.85,1.22,'rubber')
    # An inset gasket remains visible around the solid insulated door.
    box((0,14.13,33.8),(33.5,.30,42.8),'rubber',.40)
    box((0,14.49,33.8),(31.8,.78,41.2),'enamel',.46,
        paints={'default':'enamel','+y':'door'})
    # Raised header and recessed intake, with actual spaced louvres rather than a flat vent picture.
    box((0,14.18,57.35),(33.4,.50,3.65),'enamel',.24,
        paints={'default':'enamel','+y':'header'})
    box((0,14.13,7.6),(32.4,.18,8.4),'recess',.15)
    count=(10,8,5)[lod]
    for z in np.linspace(4.0,11.1,count):box((0,14.58,float(z)),(30.8,.68,.26 if lod<2 else .36),'enamel',.07)
    for x in (-16.2,16.2):box((x,14.54,7.6),(.48,.75,8.4),'enamel',.12)
    for z in (3.35,11.85):box((0,14.52,z),(32.8,.65,.5),'enamel',.13)
    # Stainless pull handle with two standoffs; the grip is separate from the door surface.
    for z in (29.,39.):
        cyl((-11.8,14.9,z),Y,.25,.65,'rubber')
        cyl((-11.8,15.04,z),Y,1.48,.32,'steel')
    G.tube(m,[point(-11.8,16.52,29),point(-11.8,16.52,39)],.32,'steel',sides=sides)
    # Three hinge barrels, mounting leaves and a keyed latch.
    for z in (17.,34.,50.):
        box((15.68,15.01,z),(1.18,.18,2.65),'steel',.09)
        cyl((16.22,15.05,z-1.18),Z,2.36,.29,'steel')
        if lod<2:
            for zz in (z-.85,z+.85):screw(15.45,15.14,zz)
    cyl((-9.5,14.94,34),Y,.18,.43,'steel')
    box((-9.5,15.14,34),(.055,.015,.43),'recess',.01)
    if lod<2:
        for x in (-15.,15.):
            for z in (3.4,11.85,57.35):screw(x,14.95,z)
        # Side service cover and folded flange, with thin seams and fasteners.
        box((19.01,-2.5,15),(.14,17.,18.),'rubber',.11)
        box((19.10,-2.5,15),(.14,16.55,17.55),'enamel',.08)
        for d in (-9.7,4.7):
            for z in (7.4,22.6):cyl((19.2,d,z),X,.07,.13,'steel')
    if lod==0:
        # A few isolated chips at exposed corners, not uniformly orange edges.
        for x,d,z in [(18.85,13.8,6.8),(-18.85,13.8,8.0),(16.7,14.83,2.8),(-14.3,14.86,3.45)]:
            box((x,d,z),(.28,.035,.10),'rust',.01)
    # Explicit panel UVs keep dirt near the floor and the lettering upright.
    for paint,polys in m.polygons.items():
        for index,(pts,normal) in enumerate(polys):
            coords=[]
            for p in pts:
                x,d,z=p[0],-p[1],p[2]
                if paint=='door':u=(x+15.44)/30.88;v=(z-13.66)/40.28
                elif paint=='header':u=(x+16.46)/32.92;v=(z-55.77)/3.16
                elif abs(normal[2])>.7:u=(x+19)/38;v=(d+15)/30
                elif abs(normal[0])>.7:u=(d+15)/30;v=z/60
                else:u=(x+19)/38;v=z/60
                coords.append((float(u),float(v)))
            m.polygon_uvs[(paint,index)]=coords
    m.material_overrides={p:f'{MAT}/{p}.vmat' for p in m.polygons}
    m.tile_overrides={p:60 for p in m.polygons}
    m.oriented_box(np.array((0.,0.,30.)),(X,np.array((0.,1.,0.)),Z),(38,30,60),{'default':None},'metal')
    return m

def append_to(target,position):
    m=model(0)
    offset=np.asarray(position,float)
    for paint,faces in m.polygons.items():
        alias="icev1_"+paint
        target.material_overrides[alias]=m.material_overrides[paint]
        target.tile_overrides[alias]=m.tile_overrides[paint]
        for i,(points,normal) in enumerate(faces):
            target.polygon(alias,[p+offset for p in points],normal,uv=m.polygon_uvs.get((paint,i)),normals=m.polygon_normals.get((paint,i)))
    for center,axes,size,surface in m.boxes:target.boxes.append((center+offset,axes,size,surface))
