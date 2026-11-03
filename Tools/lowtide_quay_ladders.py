"""Approved canal ladder geometry, retained for Lowtide generation."""
import numpy as np
import math
import map_kit as K
def model(n=-1450.):
    m=K.Model();N=n
    def P(e,n,z):return np.array((e,N+n,z),float)
    def tube(points,r,paint,sides=12):
        points=[np.asarray(p,float) for p in points];rings=[];norms=[]
        for i,p in enumerate(points):
            tangent=K.normalise(points[min(i+1,len(points)-1)]-points[max(i-1,0)])
            u=np.array((0,1,0),float) if abs(tangent[1])<.9 else np.array((0,0,1),float)
            u=K.normalise(u-tangent*np.dot(tangent,u));v=K.normalise(np.cross(tangent,u))
            ns=[u*math.cos(2*math.pi*k/sides)+v*math.sin(2*math.pi*k/sides) for k in range(sides)]
            rings.append([p+r*n for n in ns]);norms.append(ns)
        distance=0.
        for i in range(len(points)-1):
            length=np.linalg.norm(points[i+1]-points[i])
            for j in range(sides):
                j1=(j+1)%sides
                pts=[rings[i][j],rings[i][j1],rings[i+1][j1],rings[i+1][j]]
                normals=[norms[i][j],norms[i][j1],norms[i+1][j1],norms[i+1][j]]
                m.polygon(paint,pts,normals=normals,uv=[(j/sides,distance/12),((j+1)/sides,distance/12),((j+1)/sides,(distance+length)/12),(j/sides,(distance+length)/12)])
            distance+=length
        m.polygon(paint,rings[0][::-1]);m.polygon(paint,rings[-1])
    def box(e,n,z,de,dn,dz,paint):m.box(P(e-de/2,n-dn/2,z-dz/2),P(e+de/2,n+dn/2,z+dz/2),paint)
    def bolt(e,n,z):
        tube([P(e,n,z),P(e-.3,n,z)],.42,'hardware',6)
        box(e-.32,n,z,.05,.37,.10,'dark')
    # Smooth continuous rails turn over the coping, ending in small foot plates.
    for n in (-8,8):
        path=[P(234,n,-132),P(234,n,15)]
        for angle in np.linspace(math.pi,0,17)[1:]:path.append(P(237+3*math.cos(angle),n,15+3*math.sin(angle)))
        path.append(P(240,n,1.0));tube(path,1.0,'paint',16)
        # Fix to the narrow front lip of the coping, clear of the railing at e=243.
        box(240,n,.6,3.0,5.5,1.2,'paint')
        for offset in (-1.7,1.7):tube([P(240,n+offset,1.21),P(240,n+offset,1.5)],.36,'hardware',6)
        # Wall standoffs transfer the rail to bolted plates, with no floating joins.
        for z in (-15,-66,-116):
            box(239.65,n,z,.7,4.2,6.0,'paint')
            tube([P(234,n,z),P(239.3,n,z)],.65,'paint',12)
            for dz in (-1.8,1.8):bolt(239.2,n,z+dz)
            tube([P(234,n,z-1.2),P(234,n,z+1.2)],1.2,'paint',16)
        tube([P(234,n,-132),P(234,n,-130.7)],1.12,'dark',16)
    # Round-ended anti-slip tread sections; subtle worn edge strips and grip studs.
    for z in range(-120,0,12):
        tube([P(234,-8,z),P(234,8,z)],.62,'paint',12)
        box(233.9,0,z+.57,2.9,14.1,.32,'paint')
        box(232.5,0,z+.60,.17,13.9,.22,'worn')
        for n in np.linspace(-6,6,9):
            box(233.9,float(n),z+.78,1.65,.17,.13,'grip')
        for n in (-7.4,7.4):tube([P(234,n-.24,z),P(234,n+.24,z)],.85,'paint',12)
    m.material_overrides={'paint':'materials/lowtide/structure/lt_cast_iron_v2.vmat','hardware':'materials/lowtide/lt_steel.vmat','dark':'materials/lowtide/structure/lt_cast_iron_v2.vmat','worn':'materials/lowtide/lt_steel.vmat','grip':'materials/lowtide/drainage/lt_grate_cast_iron.vmat'}
    m.tile_overrides={p:12 for p in m.polygons}
    return m

def append_to(target,n):
    m=model(n)
    for paint,faces in m.polygons.items():
        alias='lt_ql_'+paint
        target.material_overrides[alias]=m.material_overrides[paint]
        target.tile_overrides[alias]=m.tile_overrides[paint]
        for i,(points,normal) in enumerate(faces):
            target.polygon(alias,points,normal,uv=m.polygon_uvs.get((paint,i)),normals=m.polygon_normals.get((paint,i)))
