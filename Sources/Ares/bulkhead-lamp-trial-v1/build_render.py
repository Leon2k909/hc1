"""Build a real private model and render installed/proposed geometry identically.

Blender background script. All distances are authored in inches then converted to
metres. No HC1 asset, material, model reference or scene is modified.
"""
from pathlib import Path
from collections import defaultdict
import hashlib, json, math, sys
import bpy, bmesh
from mathutils import Vector

ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent
OUT=ROOT/'output/asset-improvement-20261030/bulkhead-lamp'
TEX=HERE/'textures';S=.0254
sys.path.insert(0,str(ROOT/'Tools'))
import belltower_render as R
draft='--draft' in sys.argv
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)

def simple(name,color,rough=.5,metal=0):
    m=bpy.data.materials.new(name);m.use_nodes=True
    p=m.node_tree.nodes.get('Principled BSDF')
    p.inputs['Base Color'].default_value=(*color,1)
    p.inputs['Roughness'].default_value=rough;p.inputs['Metallic'].default_value=metal
    return m

def textured(name,prefix,rough,metal):
    m=simple(name,(.14,.16,.17),rough,metal);n=m.node_tree.nodes;l=m.node_tree.links;p=n.get('Principled BSDF')
    for suffix,socket in [('color','Base Color'),('roughness','Roughness'),('metallic','Metallic')]:
        path=TEX/(prefix+'_'+suffix+'.png')
        if not path.exists():continue
        tex=n.new('ShaderNodeTexImage');tex.image=bpy.data.images.load(str(path),check_existing=True)
        if suffix!='color':tex.image.colorspace_settings.name='Non-Color'
        l.new(tex.outputs['Color'],p.inputs[socket])
    path=TEX/(prefix+'_normal.png')
    if path.exists():
        tex=n.new('ShaderNodeTexImage');tex.image=bpy.data.images.load(str(path),check_existing=True);tex.image.colorspace_settings.name='Non-Color'
        normal=n.new('ShaderNodeNormalMap');normal.inputs['Strength'].default_value=.65
        l.new(tex.outputs['Color'],normal.inputs['Color']);l.new(normal.outputs['Normal'],p.inputs['Normal'])
    return m

housing=textured('Fine cast graphite enamel','housing',.63,0)
steel=textured('Machined stainless hardware','steel',.39,.96)
gasket=simple('Seated EPDM seal',(.014,.018,.020),.84)
edge=simple('Small exposed alloy chips',(.30,.33,.34),.58,.8)
glass=simple('Moulded ribbed borosilicate',(.91,.86,.68),.19)
gp=glass.node_tree.nodes.get('Principled BSDF');gp.inputs['Transmission Weight'].default_value=.94;gp.inputs['IOR'].default_value=1.47;gp.inputs['Roughness'].default_value=.105
diffuser=simple('Warm internal diffuser',(.9,.76,.48),.56)
dp=diffuser.node_tree.nodes.get('Principled BSDF');dp.inputs['Emission Color'].default_value=(1,.839216,.627451,1);dp.inputs['Emission Strength'].default_value=.48
emitter=simple('Internal sealed warm light source',(.96,.85,.66),.32)
ep=emitter.node_tree.nodes.get('Principled BSDF');ep.inputs['Emission Color'].default_value=(1,.839216,.627451,1);ep.inputs['Emission Strength'].default_value=5
plate=simple('Laser marked service plate',(.08,.10,.10),.52,.65)
pn=plate.node_tree.nodes;pt=pn.new('ShaderNodeTexImage');pt.image=bpy.data.images.load(str(TEX/'identification_color.png'))
plate.node_tree.links.new(pt.outputs['Color'],pn.get('Principled BSDF').inputs['Base Color'])

candidate=[];baseline=[]
def mesh(name,vs,fs,mat,smooth=True,uv=None,fix=True):
    data=bpy.data.meshes.new(name);data.from_pydata([tuple(c*S for c in p) for p in vs],[],fs);data.update()
    obj=bpy.data.objects.new(name,data);bpy.context.collection.objects.link(obj);data.materials.append(mat)
    if fix:
        bm=bmesh.new();bm.from_mesh(data);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(data);bm.free()
    if uv is not None:
        layer=data.uv_layers.new(name='UVMap')
        for loop in data.loops:layer.data[loop.index].uv=uv[loop.vertex_index]
    else:
        # Physically consistent 25.4 cm texture repeat, with no generator randomness.
        layer=data.uv_layers.new(name='UVMap')
        for p in data.polygons:
            normal=p.normal
            axis=max(range(3),key=lambda i:abs(normal[i]))
            axes=[i for i in range(3) if i!=axis]
            for li in p.loop_indices:
                point=vs[data.loops[li].vertex_index]
                layer.data[li].uv=(point[axes[0]]/10,point[axes[1]]/10)
    for p in data.polygons:p.use_smooth=smooth and len(p.vertices)<=4
    candidate.append(obj);return obj

def manufactured_edges(obj,width=.035):
    bpy.context.view_layer.objects.active=obj
    mod=obj.modifiers.new('Small physical edge breaks','BEVEL');mod.width=width*S;mod.segments=3
    mod.limit_method='ANGLE';mod.angle_limit=math.radians(48);mod.harden_normals=True
    bpy.ops.object.modifier_apply(modifier=mod.name)
    mod=obj.modifiers.new('Preserve planar cast faces','WEIGHTED_NORMAL');mod.keep_sharp=True;mod.weight=30
    bpy.ops.object.modifier_apply(modifier=mod.name)
    return obj

def rr(w,h,r,steps=12):
    p=[]
    for cx,cz,start in [(w/2-r,h/2-r,0),(-w/2+r,h/2-r,90),(-w/2+r,-h/2+r,180),(w/2-r,-h/2+r,270)]:
        for i in range(steps+1):
            a=math.radians(start+i*90/steps);p.append((cx+r*math.cos(a),cz+r*math.sin(a)))
    return p

def solid(name,levels,mat):
    vs=[]
    for depth,w,h,r in levels:vs.extend((x,-depth,z) for x,z in rr(w,h,r))
    n=len(vs)//len(levels);fs=[tuple(reversed(range(n))),tuple(range((len(levels)-1)*n,len(vs)))]
    for k in range(len(levels)-1):
        for i in range(n):j=(i+1)%n;fs.append((k*n+i,k*n+j,(k+1)*n+j,(k+1)*n+i))
    return manufactured_edges(mesh(name,vs,fs,mat))

def frame(name,depths,outer,inner,mat):
    a=rr(*outer);b=rr(*inner);n=len(a)
    vs=[(x,-d,z) for d in depths for ring in (a,b) for x,z in ring];fs=[]
    for i in range(n):
        j=(i+1)%n
        fs.extend([(i,j,n+j,n+i),(2*n+i,3*n+i,3*n+j,2*n+j),
            (i,2*n+i,2*n+j,j),(n+i,n+j,3*n+j,3*n+i)])
    return manufactured_edges(mesh(name,vs,fs,mat),.028)

def cube(name,p,size,mat,bevel=.06):
    bpy.ops.mesh.primitive_cube_add(size=1,location=tuple(v*S for v in p));o=bpy.context.object;o.name=name
    o.dimensions=tuple(v*S for v in size);bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    o.data.materials.append(mat)
    if bevel:
        mod=o.modifiers.new('Manufactured edge radius','BEVEL');mod.width=bevel*S;mod.segments=3
        bpy.ops.object.modifier_apply(modifier=mod.name)
        mod=o.modifiers.new('Area weighted normals','WEIGHTED_NORMAL');mod.keep_sharp=True
        bpy.ops.object.modifier_apply(modifier=mod.name)
    # Blender primitive box carries a complete UV layout.
    candidate.append(o);return o

def tube(name,points,r,mat,sides=10):
    points=[Vector(p) for p in points];vs=[]
    spans=[max(p[i] for p in points)-min(p[i] for p in points) for i in range(3)]
    basis=Vector(tuple(1 if i==spans.index(min(spans)) else 0 for i in range(3)))
    for i,p in enumerate(points):
        tangent=(points[min(i+1,len(points)-1)]-points[max(0,i-1)]).normalized()
        a=(basis-tangent*basis.dot(tangent)).normalized();b=tangent.cross(a).normalized()
        for k in range(sides):
            v=p+(a*math.cos(k*math.tau/sides)+b*math.sin(k*math.tau/sides))*r;vs.append(tuple(v))
    fs=[tuple(reversed(range(sides))),tuple(range(len(vs)-sides,len(vs)))]
    for i in range(len(points)-1):
        for j in range(sides):fs.append((i*sides+j,i*sides+(j+1)%sides,(i+1)*sides+(j+1)%sides,(i+1)*sides+j))
    return mesh(name,vs,fs,mat)

def turn(name,p,axis,profile,mat,sides=32):
    p=Vector(p);axis=Vector(axis).normalized();ref=Vector((0,0,1)) if abs(axis.z)<.9 else Vector((1,0,0))
    a=axis.cross(ref).normalized();b=axis.cross(a);vs=[]
    for radius,depth in profile:
        for k in range(sides):vs.append(tuple(p+axis*depth+radius*(a*math.cos(k*math.tau/sides)+b*math.sin(k*math.tau/sides))))
    fs=[]
    for k in range(len(profile)-1):
        for i in range(sides):j=(i+1)%sides;fs.append((k*sides+i,k*sides+j,(k+1)*sides+j,(k+1)*sides+i))
    fs.extend([tuple(reversed(range(sides))),tuple(range(len(vs)-sides,len(vs)))])
    return mesh(name,vs,fs,mat)

def screw(name,x,z,depth,r=.22):
    # A real lip and recessed socket, with a separate contact washer.
    turn(name+' washer',(x,-depth,z),(0,-1,0),[(r*1.35,0),(r*1.35,.045),(r,.06)],steel,24)
    turn(name+' cap',(x,-depth-.06,z),(0,-1,0),[(r,0),(r,.11),(r*.84,.16),(r*.39,.16),(r*.39,.07)],steel,24)
    turn(name+' recessed socket',(x,-depth-.125,z),(0,-1,0),[(r*.39,0),(r*.39,.008)],gasket,6)

# Four real mounting ears plus a closed, stepped casting.
solid('Wall mounting plate',[(.05,9.8,5.8,.65),(.18,9.9,5.9,.70),(.48,9.9,5.9,.70),(.60,9.65,5.65,.66)],housing)
solid('Pressure cast rear shell',[(.50,9.28,5.28,.85),(.68,9.50,5.50,.95),(1.5,9.5,5.5,.95),(1.86,9.15,5.15,1.0)],housing)
frame('Compression gasket',(1.82,1.94),(9.22,5.22,1.02),(7.98,3.98,.8),gasket)
frame('Cast front bezel',(1.93,2.35),(9.3,5.3,1.04),(8.05,4.05,.9),housing)
frame('Lens retaining lip',(2.34,2.44),(8.57,4.57,.94),(8.02,4.02,.9),steel)
frame('Outer lens seal',(2.40,2.47),(8.20,4.20,.92),(7.98,3.98,.9),gasket)
solid('Internal warm diffuser',[(2.02,7.75,3.75,.92),(2.15,7.75,3.75,.92)],diffuser)
for z in (-.68,.68):
    turn('Warm internal light bar',(-3.32,-2.15,z),(1,0,0),[(.20,0),(.25,.1),(.25,6.54),(.20,6.64)],emitter,32)
    for x in (-3.38,3.38):cube('Ceramic light bar socket',(x,-2.12,z),(.33,.52,.64),gasket,.07)

# Closed glass volume. Moulded optical ribs are geometry, not drawn stripes.
nx=100;nz=22;vs=[]
for side in range(2):
    for ix in range(nx+1):
        x=-3.94+7.88*ix/nx
        half=1.96
        if abs(x)>3.05:half=1.06+math.sqrt(max(0,.9**2-(abs(x)-3.05)**2))
        for iz in range(nz+1):
            z=-half+2*half*iz/nz
            dome=max(0,1-(x/4)**4)*max(0,1-(z/2.0)**4)
            depth=2.46 if side else 2.48+.77*dome**.6+.052*(.5+.5*math.cos(x*math.tau/.29))*dome**.35
            vs.append((x,-depth,z))
layer=(nx+1)*(nz+1);fs=[]
for side in range(2):
    for i in range(nx):
        for j in range(nz):
            a=side*layer+i*(nz+1)+j;b=a+nz+1
            fs.append((a,b,b+1,a+1))
for i in range(nx):
    a=i*(nz+1);b=(i+1)*(nz+1)
    fs.extend([(a,a+layer,b+layer,b),(a+nz,b+nz,b+nz+layer,a+nz+layer)])
for j in range(nz):
    a=j;b=nx*(nz+1)+j
    fs.extend([(a,a+1,a+1+layer,a+layer),(b,b+layer,b+1+layer,b+1)])
mesh('Closed prismatic borosilicate lens',vs,fs,glass)

# A one-piece protective cage: curved vertical ribs meet a perimeter and crossrail.
outline=rr(8.72,4.72,1.02,10);outline.append(outline[0])
tube('Continuous cage perimeter',[(x,-2.63,z) for x,z in outline],.092,housing,12)
for x in (-3.,-1.5,0.,1.5,3.):
    pts=[]
    for i in range(25):
        z=-2.28+4.56*i/24
        d=2.65+1.40*math.sin(math.pi*i/24)**.75*(1-.10*(abs(x)/3))
        pts.append((x,-d,z))
    tube('Cage bowed rib '+str(x),pts,.105,housing,12)
pts=[]
for i in range(49):
    x=-4.22+8.44*i/48
    d=2.64+1.40*min(1,max(0,(4.22-abs(x))/.95))**.7
    # Horizontal member follows the front rib junctions.
    d-=.14*min(1,abs(x)/3)
    pts.append((x,-d,0))
tube('Cage horizontal protector',pts,.108,housing,12)
for x in (-4.28,4.28):
    for z in (-1.94,1.94):
        cube('Cast cage mounting lug',(x,-2.3,z),(.59,.55,.60),housing,.12)
        screw('Captive bezel fastener',x,z,2.60,.18)
for x in (-4.38,4.38):
    for z in (-2.55,2.55):screw('Wall anchor',x,z,.52,.15)

# Side blanking plug and rear cooling ribs remain inside the old overall envelope.
turn('Cable entry sealing ring',(4.60,-1.15,0),(1,0,0),[(.44,0),(.44,.16)],gasket,32)
turn('Recessed cable entry plug',(4.73,-1.15,0),(1,0,0),[(.40,0),(.43,.07),(.40,.15)],steel,12)
for z in (-1.75,-1.05,-.35,.35,1.05,1.75):
    for sign in (-1,1):cube('Cast side cooling rib',(sign*4.67,-.96,z),(.15,.78,.105),housing,.045)

# Service plate on the lower bezel; its UVs remain separate from tiled surfaces.
mesh('Service identification plate',[(-1.65,-2.454,-2.07),(1.65,-2.454,-2.07),(1.65,-2.454,-2.73),(-1.65,-2.454,-2.73)],[(0,1,2,3)],plate,False,[(0,1),(1,1),(1,0),(0,0)],False)
for x in (-1.49,1.49):screw('Identification rivet',x,-2.40,2.46,.052)

# A few localized chips at exposed service edges, restrained indoor wear.
import random
rng=random.Random(62)
for i in range(24):
    x=rng.uniform(-3.0,3.0);z=rng.choice((-2.627,2.627));w=rng.uniform(.018,.085)
    mesh('Localized edge nick',[(x,-2.355,z),(x+w,-2.355,z),(x+w*.7,-2.355,z-math.copysign(.023,z))],[(0,1,2)],edge,False,fix=False)

# Load the exact installed baseline with copied UVs and split normals.
base=json.loads((HERE/'before.json').read_text())
for paint,faces in base.items():
    shader,keys=R.parse_vmat('materials/ares/'+paint+'.vmat')
    mat=R.standard_material('Installed '+paint,keys)
    for n in mat.node_tree.nodes:
        if n.type=='BSDF_PRINCIPLED':
            if keys.get('TextureRoughness','').startswith('['):n.inputs['Roughness'].default_value=R.floats(keys['TextureRoughness'])[0]
            if keys.get('F_SELF_ILLUM')=='1':
                n.inputs['Emission Color'].default_value=(*R.floats(keys['g_vColorTint'])[:3],1)
                n.inputs['Emission Strength'].default_value=float(keys['g_flSelfIllumBrightness'])
    vertices=[];fs=[];uv=[];ns=[]
    for face in faces:
        fs.append(tuple(range(len(vertices),len(vertices)+3)));vertices+=face['vertices'];uv+=face['uv'];ns+=face['normals']
    o=mesh('Installed '+paint,vertices,fs,mat,True,uv,False);candidate.remove(o);baseline.append(o)
    o.data.normals_split_custom_set_from_vertices(ns)

# Freeze all candidate modifiers and export the actual reviewed model.
for o in bpy.context.selected_objects:o.select_set(False)
for o in candidate:o.select_set(True)
bpy.context.view_layer.objects.active=candidate[0]
if not draft:
    bpy.ops.wm.obj_export(filepath=str(HERE/'bulkhead_lamp_after.obj'),export_selected_objects=True,forward_axis='NEGATIVE_Y',up_axis='Z',export_triangulated_mesh=True)
    bpy.ops.export_scene.gltf(filepath=str(HERE/'bulkhead_lamp_after.glb'),use_selection=True,export_format='GLB',export_yup=True,export_apply=True)

scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.device='CPU'
scene.cycles.samples=16 if draft else 40;scene.cycles.use_denoising=True
scene.cycles.max_bounces=8;scene.cycles.transmission_bounces=6
scene.render.threads_mode='FIXED';scene.render.threads=4
scene.render.resolution_x=1000 if draft else 1600;scene.render.resolution_y=850 if draft else 1360
scene.render.resolution_percentage=100;scene.render.image_settings.file_format='PNG'
scene.view_settings.view_transform='AgX';scene.view_settings.exposure=0
scene.world=scene.world or bpy.data.worlds.new('Same neutral ambient')
scene.world.use_nodes=True;scene.world.node_tree.nodes['Background'].inputs['Color'].default_value=(.31,.34,.39,1)
scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.32
wallmat=simple('Same neutral wall',(.19,.205,.22),.88)
wall=cube('Same neutral review wall',(0,.22,0),(100,.4,100),wallmat,.0);candidate.remove(wall)

for name,pos,power,size,col in [('Soft key',(-.4,-.55,.55),18,.6,(1,.92,.84)),('Cool fill',(.5,-.35,.2),11,.5,(.78,.88,1))]:
    data=bpy.data.lights.new(name,'AREA');data.energy=power;data.shape='DISK';data.size=size;data.color=col
    o=bpy.data.objects.new(name,data);bpy.context.collection.objects.link(o);o.location=pos
    o.rotation_euler=(Vector((0,-.05,0))-o.location).to_track_quat('-Z','Y').to_euler()
data=bpy.data.cameras.new('Matched 60 mm camera');camera=bpy.data.objects.new('Matched camera',data)
bpy.context.collection.objects.link(camera);scene.camera=camera;data.lens=60;data.clip_start=.005
eye=(.27,-.64,.22);target=(0,-.045,0)
camera.location=eye;camera.rotation_euler=(Vector(target)-camera.location).to_track_quat('-Z','Y').to_euler()
suffix='-draft' if draft else ''
report={'renderer':'Blender Cycles CPU','nativeEngineScreenshot':False,'generatedImage':False,
    'sameCameraLightingExposureScaleAndWall':True,'reviewOnly':True,'installed':False,
    'lens':data.lens,'cameraMetres':eye,'targetMetres':target,'exposure':0,'samples':scene.cycles.samples,
    'beforeTriangles':sum(len(o.data.polygons) for o in baseline),
    'afterTriangles':sum(sum(len(p.vertices)-2 for p in o.data.polygons) for o in candidate),
    'images':[]}
for variant in ('before','after'):
    for o in baseline:o.hide_render=variant!='before'
    for o in candidate:o.hide_render=variant!='after'
    path=OUT/(variant+suffix+'.png');scene.render.filepath=str(path)
    bpy.ops.render.render(write_still=True)
    report['images'].append({'variant':variant,'file':path.name,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
for o in baseline:o.hide_render=True;o.hide_set(True)
for o in candidate:o.hide_render=False

# Validate the actual candidate geometry and exact old files before delivering.
vs=[o.matrix_world@v.co for o in candidate for v in o.data.vertices]
lo=[min(v[i] for v in vs)/S for i in range(3)];hi=[max(v[i] for v in vs)/S for i in range(3)]
report['candidateBoundsInches']=[lo,hi]
assert lo[0]>=-5.001 and hi[0]<=5.001 and lo[2]>=-3.001 and hi[2]<=3.001 and lo[1]>=-4.201 and hi[1]<=.001,(lo,hi)
bad=[]
degenerate=[];open_parts=[]
for o in candidate:
    if any(not math.isfinite(c) for v in o.data.vertices for c in v.co):bad.append(o.name)
    o.data.calc_loop_triangles()
    if any(t.area<1e-14 for t in o.data.loop_triangles):degenerate.append(o.name)
    bm=bmesh.new();bm.from_mesh(o.data)
    boundary=sum(1 for e in bm.edges if e.is_boundary)
    if boundary:open_parts.append({'part':o.name,'boundaryEdges':boundary})
    bm.free()
assert not bad,bad
assert not degenerate,degenerate
assert all(p['part'] in ('Service identification plate','Localized edge nick') or p['part'].startswith('Localized edge nick.') for p in open_parts),open_parts
report['geometryQA']={'finite':True,'zeroAreaTriangles':0,'openParts':open_parts,'closedManufacturedParts':len(candidate)-len(open_parts)}
guard=json.loads((HERE/'source-guard.json').read_text())
assert all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h for p,h in guard.items()),'An original guarded file changed'
report['protectedGameFilesUnchanged']=len(guard)
if not draft:
    bpy.ops.file.pack_all()
    bpy.ops.wm.save_as_mainfile(filepath=str(HERE/'bulkhead_lamp_review.blend'))
(OUT/('render-report'+suffix+'.json')).write_text(json.dumps(report,indent=2))
print(json.dumps(report))
