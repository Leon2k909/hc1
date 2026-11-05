"""Rebuild Orion's hilltop radome as a geodesic panel assembly with service access. Review only."""
from pathlib import Path
import sys,math,json,hashlib
import numpy as np
sys.dont_write_bytecode=True
ROOT=Path(__file__).absolute().parents[3];sys.path.insert(0,str(ROOT/'Tools'))
import map_kit as K
import riverdale_parts as G
import orion_parts as O
import orion_map as R
OUT=ROOT/'output/orion/radome-v1';STAGE=OUT/'stage/Assets';RES='models/props/orion/radome_v1';MAT='materials/orion/radome_v1';MODEL=STAGE/RES;MATS=STAGE/MAT
for d in (MODEL/'review',MATS):d.mkdir(parents=True,exist_ok=True)
X=np.array((1.,0,0));Y=np.array((0.,1.,0));Z=np.array((0.,0.,1.));RAD=340.;BASE=200.;CENTER=BASE+RAD*.72;RB=RAD*math.sqrt(1-.72**2)
for name,color,rough,metal in [('panel',(.70,.72,.70),.6,0),('panel_alt',(.67,.69,.67),.63,0),('gasket',(.018,.022,.021),.85,0),('zinc',(.38,.41,.40),.44,.75)]:
    (MATS/f'{name}.vmat').write_text(f'''Layer0
{{
 shader "shaders/complex.shader"
 F_SPECULAR "1"
 TextureColor "[{' '.join(map(str,color))} 1]"
 TextureNormal "materials/default/default_normal.tga"
 TextureRoughness "[{rough} {rough} {rough} 0]"
 TextureAmbientOcclusion "materials/default/default_ao.tga"
 g_flMetalness "{metal}"
 g_flModelTintAmount "1"
 g_flRoughnessScaleFactor "1"
}}
''')
def geodesic(level):
    t=(1+math.sqrt(5))/2
    vertices=np.array([(-1,t,0),(1,t,0),(-1,-t,0),(1,-t,0),(0,-1,t),(0,1,t),(0,-1,-t),(0,1,-t),(t,0,-1),(t,0,1),(-t,0,-1),(-t,0,1)],float)
    vertices/=np.linalg.norm(vertices,axis=1,keepdims=True);vertices=list(vertices)
    triangles=[(0,11,5),(0,5,1),(0,1,7),(0,7,10),(0,10,11),(1,5,9),(5,11,4),(11,10,2),(10,7,6),(7,1,8),(3,9,4),(3,4,2),(3,2,6),(3,6,8),(3,8,9),(4,9,5),(2,4,11),(6,2,10),(8,6,7),(9,8,1)]
    for _ in range(level):
        cache={};new=[]
        def midpoint(a,b):
            key=tuple(sorted((a,b)))
            if key not in cache:
                q=(vertices[a]+vertices[b])*.5;q/=np.linalg.norm(q);cache[key]=len(vertices);vertices.append(q)
            return cache[key]
        for a,b,c in triangles:
            ab,bc,ca=midpoint(a,b),midpoint(b,c),midpoint(c,a);new.extend([(a,ab,ca),(b,bc,ab),(c,ca,bc),(ab,bc,ca)])
        triangles=new
    return np.array(vertices),triangles
def clipped(points):
    out=[];floor=-.72
    for a,b in zip(points,points[1:]+points[:1]):
        ina,inb=a[2]>=floor,b[2]>=floor
        if ina:out.append(a)
        if ina!=inb:
            q=a+(b-a)*((floor-a[2])/(b[2]-a[2]));out.append(q)
    return out
def model(lod=0):
    m=K.Model();sides=(10,7,5)[lod];segments=(80,56,32)[lod]
    def face(points,normal,paint):G._face(m,paint,[np.asarray(p,float) for p in points],towards=np.asarray(normal,float))
    def box(c,size,paint='oa_steel',b=.25,axes=(X,Y,Z)):
        if lod<2 and b:G.bevel_box(m,np.asarray(c,float),axes,size,paint,bevel=b)
        else:m.oriented_box(np.asarray(c,float),axes,size,paint)
    def tube(a,b,r,paint='zinc',n=None):G.tube(m,[np.asarray(a,float),np.asarray(b,float)],r,paint,sides=n or sides)
    def cyl(c,axis,rad,length,paint='zinc',n=None):G.lathe_axis(m,np.asarray(c,float),np.asarray(axis,float),np.array([(0.,0.),(rad,0.),(rad,length),(0.,length)],float),paint,sides=n or sides)
    def beam(a,b,w,h,paint='oa_steel'):
        a,b=np.array(a,float),np.array(b,float);along=b-a;length=np.linalg.norm(along);along/=length
        side=np.cross(along,Z if abs(along[2])<.9 else Y);side/=np.linalg.norm(side);up=np.cross(along,side)
        box((a+b)/2,(length,w,h),paint,.2,(along,side,up))
    # A real subdivided icosahedral panel layout, clipped precisely at the original mounting plane.
    vertices,triangles=geodesic(3 if lod<2 else 2)
    for index,tri in enumerate(triangles):
        polygon=clipped([vertices[i] for i in tri])
        if len(polygon)<3:continue
        points=[p*RAD+Z*CENTER for p in polygon];center=np.mean(points,axis=0);normal=np.mean(polygon,axis=0);normal/=np.linalg.norm(normal)
        if lod<2:
            # Recessed weather seal behind each actual joint; the panels have formed edges and thickness.
            face([p-normal*1.1 for p in points],normal,'gasket')
            top=[center+(p-center)*.95 for p in points];face(top,normal,'panel_alt' if index%11==0 else 'panel')
            if lod==0:
                for a,b in zip(top,top[1:]+top[:1]):face([a,b,b-normal*1.1,a-normal*1.1],(a+b)/2-center,'panel')
        else:face(points,normal,'panel_alt' if index%11==0 else 'panel')
    # Rolled mounting curb, service platform and an outer handrail safely clear of the dome's overhang.
    for rr,z,h,paint in ((RB+1,195,8,'oa_steel'),(RB+4,198,3,'zinc')):
        G.lathe_axis(m,(0,0,z),Z,np.array([(rr-3,0),(rr,0),(rr,h),(rr-3,h),(rr-3,0)],float),paint,sides=segments)
    inner,outer=RB-8,RB+66
    angles=np.linspace(0,math.tau,segments+1)
    for a,b in zip(angles,angles[1:]):
        pa,pb=np.array((math.cos(a),math.sin(a),0)),np.array((math.cos(b),math.sin(b),0))
        face([pa*inner+Z*192,pa*outer+Z*192,pb*outer+Z*192,pb*inner+Z*192],Z,'oa_grating')
        face([pa*outer+Z*186,pb*outer+Z*186,pb*outer+Z*192,pa*outer+Z*192],pa,'oa_steel')
    for zz in ((214,234) if lod<2 else (234,)):
        G.torus(m,(0,0,zz),Z,outer-1,.95,'zinc',seg=segments,sides=sides)
    for a in np.linspace(0,math.tau,20 if lod<2 else 10,endpoint=False):
        p=np.array((math.cos(a),math.sin(a),0))*(outer-1);tube(p+Z*192,p+Z*234,.9)
    # Ten anchored steel I-columns, angle braces, cap plates and structural gussets.
    for k in range(10):
        a=math.tau*k/10;b=math.tau*(k+1)/10;d=np.array((math.cos(a),math.sin(a),0));t=np.cross(Z,d);p=d*RB;q=np.array((math.cos(b),math.sin(b),0))*RB
        box(p+Z*5,(24,24,10),'oa_render_grey',.8,(t,d,Z));box(p+Z*11.2,(18,18,2.4),'zinc',.4,(t,d,Z))
        for offset in (-4.6,4.6):box(p+d*offset+Z*104,(10,1.2,180),'oa_steel',.12,(t,d,Z))
        box(p+Z*104,(1,8.2,180),'oa_steel',.1,(t,d,Z));box(p+Z*194,(17,17,2),'zinc',.25,(t,d,Z))
        beam(p+Z*16,q+Z*187,3.8,1.2);beam(q+Z*16,p+Z*187,3.8,1.2);beam(p+Z*102,q+Z*102,5,2)
        beam(p+Z*188,d*(outer-3)+Z*188,6,6);beam(p+Z*151,d*(outer-3)+Z*187,3,3)
        if lod<2:
            for dx in (-6.3,6.3):
                for dy in (-6.3,6.3):cyl(p+t*dx+d*dy+Z*12.5,Z,.8,1.2,'zinc',6)
            face([p+t*4+Z*170,p+t*4+Z*191,p+d*27+t*4+Z*191],t,'oa_steel')
    # Equipment shelter within the original concrete block's footprint; actual framed service door and louvres.
    hw=RB*.5
    box((0,0,43),(hw*2,hw*2,86),'oa_render_grey',1.0)
    box((0,0,88),(hw*2+5,hw*2+5,4),'oa_steel',.5)
    doorx=-hw*.42;front=-hw-1
    box((doorx,front,39),(35,1.2,75),'gasket',.4)
    box((doorx,front-1,39),(32,1.0,72),'oa_steel',.5)
    for dx in (-17,17):box((doorx+dx,front-1.5,39),(1.3,1.5,76),'zinc',.18)
    box((doorx,front-1.5,77),(35,1.5,1.3),'zinc',.15)
    tube((doorx+11,front-2.3,38),(doorx+11,front-2.3,43),.45)
    for zz in (15,63):box((doorx-16,front-2,zz),(2,.8,3),'zinc',.2)
    box((hw*.4,front-.4,51),(55,1.0,31),'gasket',.4)
    for zz in np.linspace(38,64,11 if lod<2 else 6):box((hw*.4,front-1,zz),(53,2,1.6),'zinc',.2)
    for side in (-1,1):
        tube((side*(hw-10),-hw-3,12),(side*(hw-10),-hw-3,79),.65)
        box((side*(hw-10),-hw-3.5,56),(12,4,18),'oa_steel',.7)
    # Caged maintenance ladder, mounted on the outer platform, with connected landing handholds.
    yy=-outer+1
    for x in (-10,10):
        tube((x,yy,4),(x,yy,232),1.05)
        for zz in (48,136,186):tube((x,yy,zz),(x,-RB,zz),.75)
    for zz in np.arange(12,193,12 if lod<2 else 24):tube((-10,yy,float(zz)),(10,yy,float(zz)),.75)
    if lod<2:
        for zz in (72,120,168,216):G.torus(m,(0,yy-2,zz),Z,18,.75,'zinc',seg=20 if lod==0 else 14,sides=5,a0=math.pi,a1=math.tau)
        for a in np.linspace(math.pi,math.tau,5):
            point=np.array((18*math.cos(a),yy-2+18*math.sin(a),0));tube(point+Z*72,point+Z*216,.6)
    box((0,yy,1.5),(32,33,3),'oa_render_grey',.5)
    R.configure(m)
    for paint in ('panel','panel_alt','gasket','zinc'):
        if paint in m.polygons:m.material_overrides[paint]=f'{MAT}/{paint}.vmat';m.tile_overrides[paint]=128
    return m

counts=[];models=[]
for lod in range(3):
    m=model(lod);models.append(m);counts.append(K.write_obj(MODEL/f'radome_lod{lod}.obj',m,f'radome_lod{lod}'))
K.write_vmdl(MODEL/'radome.vmdl',RES,'radome_lod0',models[0]);doc=(MODEL/'radome.vmdl').read_text();a=doc.index('\t\t\t{\n\t\t\t\t_class = "RenderMeshList"');b=doc.index('\n\t\t\t},',a)+len('\n\t\t\t},')
files='\n'.join(f'{{ _class = "RenderMeshFile" name = "lod{i}" filename = "{RES}/radome_lod{i}.obj" import_scale = 1 align_origin_x_type = "None" align_origin_y_type = "None" align_origin_z_type = "None" import_filter = {{ exclude_by_default = false exception_list = [] }} }},' for i in range(3))
groups='\n'.join(f'{{ _class = "LODGroup" switch_threshold = {d} meshes = ["lod{i}"] }},' for i,d in enumerate((0,75,180)))
(MODEL/'radome.vmdl').write_text(doc[:a]+f'{{ _class = "RenderMeshList" children = [ {files} ] }},\n{{ _class = "LODGroupList" children = [ {groups} ] }},'+doc[b:])
old=K.Model();O.radome(old,(0,0,0),RAD,BASE,16,40);R.configure(old);K.write_model(MODEL/'review',RES+'/review','before',old)
floor=K.Model();floor.box((-1800,-1800,-5),(1800,1800,0),'oa_render_grey');R.configure(floor);K.write_model(MODEL/'review',RES+'/review','floor',floor)
audit=dict(checked=['Sources/Orion','all Sources/Tools radar/radome/geodesic references','Assets radar/radome/dish model filenames'],
           existing='Current baked Orion lathed sphere with triangular material; no standalone upgraded radome',
           related_unsuitable=['small Stillhouse boat radar housing','Forest Base open satellite-dish materials'])
(OUT/'existing-model-audit.json').write_text(json.dumps(audit,indent=2))
manifest=dict(preview_only=True,triangles=counts,before_triangles=sum(l.startswith('f ') for l in (MODEL/'review/before.obj').read_text().splitlines()),
              protected={p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT/'Assets/scenes/maps/Orion/orion.scene',ROOT/'Assets/models/maps/orion/orion_vista.obj',ROOT/'Assets/models/maps/orion/orion_vista.vmdl')},
              files={p.relative_to(STAGE).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in STAGE.rglob('*') if p.is_file()})
(OUT/'manifest.json').write_text(json.dumps(manifest,indent=2));print(json.dumps({k:v for k,v in manifest.items() if k!='files'},indent=2))
