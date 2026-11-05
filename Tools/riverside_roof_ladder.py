"""Approved L1 roof ladder, reusing the retained quay-ladder design and materials."""
import inspect
import numpy as np
import map_kit as K
import riverdale_parts as G
import lowtide_quay_ladders as A
H=220.0
def model(lod):
    s=inspect.getsource(A.model)
    edits={'def model(n=-1450.):':'def model(n=0.):','for n in (-8,8):':'for n in (-9,9):','P(234,n,-132),P(234,n,15)':f'P(234,n,0),P(234,n,{H+18})','np.linspace(math.pi,0,17)':f'np.linspace(math.pi,0,{(17,11,7)[lod]})','15+3*math.sin(angle)':f'{H+18}+3*math.sin(angle)','P(240,n,1.0)':'P(240,n,roof(n)+1.0)','box(240,n,.6':'box(240,n,roof(n)+.6','P(240,n+offset,1.21),P(240,n+offset,1.5)':'P(240,n+offset,roof(n+offset)+1.21),P(240,n+offset,roof(n+offset)+1.5)','for z in (-15,-66,-116):':'for z in (150.,200.):','box(239.65,n,z':'box(274-38*z/220,n,z','P(239.3,n,z)':'P(273.65-38*z/220,n,z)','bolt(239.2,n,z+dz)':'bolt(273.55-38*z/220,n,z+dz)','P(234,n,-132),P(234,n,-130.7)':'P(234,n,0),P(234,n,1.3)','range(-120,0,12)':f'range(12,{int(H)},12)','P(234,-8,z),P(234,8,z)':'P(234,-9,z),P(234,9,z)','2.9,14.1,.32':'2.9,16.1,.32','.17,13.9,.22':'.17,15.9,.22','np.linspace(-6,6,9)':f'np.linspace(-7,7,{(9,5,0)[lod]})','(-7.4,7.4)':'(-8.4,8.4)','points=[np.asarray(p,float) for p in points];rings=[];norms=[]':f'sides=max(4,int(round(sides*{(1,.67,.42)[lod]})));points=[np.asarray(p,float) for p in points];rings=[];norms=[]'}
    for a,b in edits.items():assert s.count(a)==1,a;s=s.replace(a,b)
    env=dict(A.__dict__);env['roof']=lambda n:H-1-5.5*abs(40+n)/62.5;exec(compile(s,'fitted-approved-roof-ladder','exec'),env);proto=env['model']()
    matrix=np.array(((1,0,38/H),(0,1,0),(0,0,1.)),float);normal_matrix=np.linalg.inv(matrix).T;m=K.Model()
    for paint,polys in proto.polygons.items():
        for i,(pts,normal) in enumerate(polys):
            points=[matrix@(q-np.array((234.,0.,0.))) for q in pts];ns=proto.polygon_normals.get((paint,i))
            G.card(m,paint,points,normal_matrix@normal,uv=proto.polygon_uvs.get((paint,i)),normals=None if ns is None else [K.normalise(normal_matrix@n) for n in ns])
    m.material_overrides=dict(proto.material_overrides);m.material_overrides['paint']='materials/riverside/tower_ladder_legacy_steel/steel.vmat';m.tile_overrides=dict(proto.tile_overrides)
    return m

def append_to(target,foot):
    m=model(0);offset=np.asarray(foot,float)
    for paint,faces in m.polygons.items():
        alias='roof_ladder_'+paint
        target.material_overrides[alias]=m.material_overrides[paint]
        target.tile_overrides[alias]=m.tile_overrides[paint]
        for i,(points,normal) in enumerate(faces):
            target.polygon(alias,[p+offset for p in points],normal,uv=m.polygon_uvs.get((paint,i)),normals=m.polygon_normals.get((paint,i)))
