"""Real smooth lifebuoy, twisted grab rope and mounting hardware; matched saved-mesh review."""
from pathlib import Path
import math,json,hashlib,sys
import bpy,bmesh
from mathutils import Vector
ROOT=Path.cwd();HERE=ROOT/'Sources/Riverdale/lifebuoy-trial-v1';TEX=HERE/'textures';OUT=ROOT/'output/asset-improvement-20261031/riverdale-lifebuoy'
sys.path.insert(0,str(HERE));sys.path.insert(0,str(ROOT/'Tools'));import geometry as G;import belltower_render as R
S=G.S;draft='--draft' in sys.argv;validate_only='--validate-only' in sys.argv
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
def mat(name,color,rough=.6,metal=0,prefix=None):
    m=bpy.data.materials.new(name);m.use_nodes=True;n=m.node_tree.nodes;l=m.node_tree.links;p=n.get('Principled BSDF')
    p.inputs['Base Color'].default_value=(*color,1);p.inputs['Roughness'].default_value=rough;p.inputs['Metallic'].default_value=metal
    if prefix:
        for suffix,socket in [('color','Base Color'),('roughness','Roughness'),('metallic','Metallic')]:
            t=n.new('ShaderNodeTexImage');t.image=bpy.data.images.load(str(TEX/f'{prefix}_{suffix}.png'),check_existing=True)
            if suffix!='color':t.image.colorspace_settings.name='Non-Color'
            l.new(t.outputs['Color'],p.inputs[socket])
        t=n.new('ShaderNodeTexImage');t.image=bpy.data.images.load(str(TEX/f'{prefix}_normal.png'),check_existing=True);t.image.colorspace_settings.name='Non-Color'
        nm=n.new('ShaderNodeNormalMap');nm.inputs['Strength'].default_value=.6;l.new(t.outputs['Color'],nm.inputs['Color']);l.new(nm.outputs['Normal'],p.inputs['Normal'])
    return m
orange=mat('Moulded orange buoy shell',(.5,.06,.02),prefix='orange');white=mat('White reflective band fabric',(.7,.7,.65),prefix='white')
rope=mat('Three strand floating grab rope',(.4,.3,.17),prefix='rope');steel=mat('Brushed stainless mounting hardware',(.3,.33,.35),.44,.95,'steel')
rubber=mat('Neoprene contact pads and hook sleeve',(.012,.015,.017),prefix='rubber');webbing=mat('Woven rope retention loops',(.65,.63,.5),prefix='webbing')

# The body's radial and axial radii differ: a buoyant moulding with a true bore,
# rather than a faceted inner tube. White bands are separate thin volumes.
def torus_points(a,t,thickness=0):
    radial=11+(2.34+thickness)*math.cos(t)
    return (radial*math.cos(a),-3-(1.86+thickness)*math.sin(t),radial*math.sin(a))
N=192;M=24;vs=[];uv=[]
for i in range(N):
    for j in range(M):vs.append(torus_points(i*math.tau/N,j*math.tau/M));uv.append((i/N*3,j/M))
fs=[(i*M+j,((i+1)%N)*M+j,((i+1)%N)*M+(j+1)%M,i*M+(j+1)%M) for i in range(N) for j in range(M)]
G.mesh('Continuous smooth buoy moulding',vs,fs,orange,True,uv)
for k in range(4):
    a0=math.pi/4+k*math.pi/2;a1=a0+math.pi/4;steps=24;vs=[];uv=[]
    for layer in (0,.035):
        for i in range(steps+1):
            for j in range(M):
                a=a0+(a1-a0)*i/steps;vs.append(torus_points(a,j*math.tau/M,layer));uv.append((i/steps,j/M))
    size=(steps+1)*M;fs=[]
    for i in range(steps):
        for j in range(M):
            jj=(j+1)%M
            fs.append((size+i*M+j,size+(i+1)*M+j,size+(i+1)*M+jj,size+i*M+jj))
            fs.append((i*M+jj,(i+1)*M+jj,(i+1)*M+j,i*M+j))
    for i in (0,steps):
        for j in range(M):jj=(j+1)%M;fs.append((i*M+j,i*M+jj,size+i*M+jj,size+i*M+j))
    G.mesh('Thin fitted reflective quadrant band',vs,fs,white,True,uv)

# A fine mould parting bead at the outside edge. It follows the existing shell,
# and takes the same material instead of an artificial black dirt outline.
G.tube('Mould parting bead',[(13.365*math.cos(i*math.tau/192),-3,13.365*math.sin(i*math.tau/192)) for i in range(193)],.018,orange,6)

# The grab line is a continuous three-strand twisted rope, with smooth sagging
# loops and no open joins at the retention points.
steps=512;centres=[]
for i in range(steps):
    t=i/128;k=int(t);f=t-k;a=math.pi/4+math.pi/2*t;sag=1.30*math.sin(math.pi*f)
    r=13.75+sag;centres.append(Vector((r*math.cos(a),-3,r*math.sin(a)-sag*.6)))
dist=[0.]
for a,b in zip(centres,centres[1:]+centres[:1]):dist.append(dist[-1]+(b-a).length)
turns=round(dist[-1]/1.60)
for strand in range(3):
    path=[]
    for i,c in enumerate(centres):
        tangent=(centres[(i+1)%steps]-centres[(i-1)%steps]).normalized();normal=Vector((0,1,0));across=tangent.cross(normal).normalized()
        phase=math.tau*(turns*dist[i]/dist[-1]+strand/3);path.append(c+.175*(normal*math.cos(phase)+across*math.sin(phase)))
    vs=[];uv=[];sides=6
    for i,p in enumerate(path):
        tangent=(path[(i+1)%steps]-path[(i-1)%steps]).normalized();a=Vector((0,1,0));a=(a-tangent*a.dot(tangent)).normalized();b=tangent.cross(a)
        for j in range(sides):
            v=p+.115*(a*math.cos(j*math.tau/sides)+b*math.sin(j*math.tau/sides));vs.append(tuple(v));uv.append((dist[i]/2,j/sides))
    fs=[(i*sides+j,((i+1)%steps)*sides+j,((i+1)%steps)*sides+(j+1)%sides,i*sides+(j+1)%sides) for i in range(steps) for j in range(sides)]
    G.mesh('Continuous twisted rope strand',vs,fs,rope,True,uv)

# Four broad woven retention loops actually enclose the grab rope.
for k in range(4):
    angle=math.pi/4+k*math.pi/2;radial=Vector((math.cos(angle),0,math.sin(angle)));tangent=Vector((-math.sin(angle),0,math.cos(angle)))
    profile=[(12.45,-4.04),(13.3,-4.0),(13.9,-3.75),(14.16,-3.35),(14.16,-2.65),(13.9,-2.25),(13.3,-2.0),(12.45,-1.96)]
    vs=[]
    for r,y in profile:
        for across,depth in ((-.36,-.045),(.36,-.045),(.36,.045),(-.36,.045)):
            vs.append(tuple(radial*(r+depth)+Vector((0,y,0))+tangent*across))
    fs=[(3,2,1,0),tuple(range(len(vs)-4,len(vs)))]
    for i in range(len(profile)-1):
        for j in range(4):fs.append((i*4+j,i*4+(j+1)%4,(i+1)*4+(j+1)%4,(i+1)*4+j))
    G.mesh('Woven grab rope retention loop',vs,fs,webbing)
    for edge in (-.28,.28):
        line=[tuple(radial*(r+.05)+Vector((0,y,0))+tangent*edge) for r,y in profile]
        G.tube('Retention loop edge stitching',line,.012,white,5)

# Real wall mount with countersunk screws, a formed J hook and a soft sleeve.
G.box('Closed stainless wall plate',(0,-.22,10.5),(4,.4,5),steel,.18)
for x in (-1.25,1.25):
    for z in (9.0,12.0):
        G.turn('Countersunk plate fastener',(x,-.43,z),(0,-1,0),[(.25,0),(.25,.05),(.20,.12)],steel,20)
        G.box('Fastener driver slot',(x,-.558,z),(.25,.014,.048),rubber,.006)
hook=[(0,-.42,9),(0,-3.5,9),(0,-5.0,9),(0,-5.4,9.1),(0,-5.60,9.4),(0,-5.65,10.1),(0,-5.65,11.05)]
G.tube('Formed stainless J hook',hook,.31,steel,16)
G.tube('Protective hook sleeve',[(0,-5.65,9.65),(0,-5.65,10.9)],.35,rubber,16)
for x in (-7.5,7.5):G.box('Wall contact bumper',(x,-.60,-7.5),(1.5,1.0,2.2),rubber,.24)
candidate=list(G.parts);bpy.context.view_layer.update()

baseline=[]
for paint,faces in json.loads((HERE/'before.json').read_text()).items():
    shader,kv=R.parse_vmat('materials/riverdale/'+paint+'.vmat');m=R.standard_material('Installed '+paint,kv)
    p=next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
    # Constant VMAT UI colour values need sRGB-to-linear conversion for Cycles.
    # Textured inputs already receive it from Blender's image colour space.
    if not p.inputs['Base Color'].is_linked:
        tint=R.floats(kv.get('g_vColorTint','[1 1 1 1]'))[:3]
        p.inputs['Base Color'].default_value=(*(c/12.92 if c<=.04045 else ((c+.055)/1.055)**2.4 for c in tint),1)
    if kv.get('TextureRoughness','').startswith('['):p.inputs['Roughness'].default_value=R.floats(kv['TextureRoughness'])[0]
    if kv.get('F_METALNESS_TEXTURE')=='1':
        path=ROOT/'Assets'/kv['TextureMetalness'];t=m.node_tree.nodes.new('ShaderNodeTexImage');t.image=bpy.data.images.load(str(path));t.image.colorspace_settings.name='Non-Color';m.node_tree.links.new(t.outputs['Color'],p.inputs['Metallic'])
    vs=[];uv=[];ns=[];fs=[]
    for f in faces:fs.append(tuple(range(len(vs),len(vs)+3)));vs+=f['vertices'];uv+=f['uv'];ns+=f['normals']
    o=G.mesh('Exact saved lifebuoy before',vs,fs,m,True,uv,False);o.data.normals_split_custom_set_from_vertices(ns);baseline.append(o)

for o in candidate:
    bm=bmesh.new();bm.from_mesh(o.data);bmesh.ops.triangulate(bm,faces=list(bm.faces));bmesh.ops.dissolve_degenerate(bm,dist=1e-8,edges=list(bm.edges));bm.to_mesh(o.data);bm.free();o.data.update();o.data.calc_loop_triangles()
    assert all(math.isfinite(c) for v in o.data.vertices for c in v.co),o.name
    assert all(t.area>1e-14 for t in o.data.loop_triangles),o.name
    assert all(p.material_index<len(o.data.materials) and o.data.materials[p.material_index] is not None for p in o.data.polygons),o.name
vs=[o.matrix_world@v.co/S for o in candidate for v in o.data.vertices];lo=[min(v[i] for v in vs) for i in range(3)];hi=[max(v[i] for v in vs) for i in range(3)]
assert lo[1]>=-6.06 and hi[1]<=.001 and lo[0]>=-16 and hi[0]<=16 and lo[2]>=-17 and hi[2]<=16,(lo,hi)
guard=json.loads((HERE/'source-guard.json').read_text());assert all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h for p,h in guard.items())
report={'asset':'Riverdale reactor-hall lifebuoy','renderer':'Blender Cycles CPU','nativeEngineScreenshot':False,'installed':False,'sameCameraScaleLightingExposure':True,'constantVMATColoursConvertedFromSRGB':True,
 'beforeTriangles':sum(len(f) for f in json.loads((HERE/'before.json').read_text()).values()),'afterTriangles':sum(len(o.data.polygons) for o in candidate),
 'boundsInches':[lo,hi],'zeroAreaTriangles':0,'finiteGeometry':True,'protectedOriginalsUnchanged':len(guard),'images':[]}
if not draft and not validate_only:
    bpy.ops.object.select_all(action='DESELECT');copies=[]
    for o in candidate:
        c=o.copy();c.data=o.data.copy();bpy.context.collection.objects.link(c);c.select_set(True);copies.append(c)
    bpy.context.view_layer.objects.active=copies[0];bpy.ops.object.join();joined=bpy.context.object;joined.name='Riverdale lifebuoy review mesh';bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
    bpy.ops.wm.obj_export(filepath=str(HERE/'lifebuoy_after.obj'),export_selected_objects=True,forward_axis='NEGATIVE_Y',up_axis='Z',export_triangulated_mesh=True)
    bpy.ops.export_scene.gltf(filepath=str(HERE/'lifebuoy_after.glb'),use_selection=True,export_format='GLB',export_apply=True);bpy.data.objects.remove(joined,do_unlink=True)

scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.cycles.samples=10 if draft else 24;scene.cycles.use_denoising=True;scene.cycles.max_bounces=5
scene.render.threads_mode='FIXED';scene.render.threads=4;scene.render.resolution_x=950 if draft else 1400;scene.render.resolution_y=950 if draft else 1400;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG';scene.view_settings.view_transform='AgX';scene.view_settings.exposure=0
scene.world=scene.world or bpy.data.worlds.new('Same studio ambient');scene.world.use_nodes=True;scene.world.node_tree.nodes['Background'].inputs['Color'].default_value=(.34,.37,.42,1);scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.34
wall=mat('Same neutral upper wall',(.22,.235,.24),.88);blue=mat('Same blue lower wall',(.025,.095,.145),.82)
G.box('Same upper wall',(0,.35,45),(180,.7,105),wall,0);G.box('Same blue wall base',(0,.35,-52.5),(180,.7,90),blue,0)
for name,pos,power,size,color in [('Soft key',(-1.7,-2.3,2.6),450,2.4,(1,.94,.87)),('Cool fill',(2.0,-1.0,.5),170,1.8,(.82,.90,1))]:
    d=bpy.data.lights.new(name,'AREA');d.energy=power;d.shape='DISK';d.size=size;d.color=color;o=bpy.data.objects.new(name,d);bpy.context.collection.objects.link(o);o.location=pos;o.rotation_euler=(Vector((0,-.07,0))-o.location).to_track_quat('-Z','Y').to_euler()
d=bpy.data.cameras.new('Matched camera');cam=bpy.data.objects.new('Matched camera',d);bpy.context.collection.objects.link(cam);scene.camera=cam
eye=(.52,-1.70,.25);target=(0,-.07,-.015);d.lens=65;cam.location=eye;cam.rotation_euler=(Vector(target)-cam.location).to_track_quat('-Z','Y').to_euler();report.update({'cameraMetres':eye,'targetMetres':target,'lens':65,'samples':scene.cycles.samples})
for variant in (() if validate_only else ('before','after')):
    for o in baseline:o.hide_render=variant!='before'
    for o in candidate:o.hide_render=variant!='after'
    path=OUT/(variant+('-draft' if draft else '')+'.png');scene.render.filepath=str(path);bpy.ops.render.render(write_still=True);report['images'].append({'variant':variant,'file':path.name,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
for o in baseline:o.hide_render=True;o.hide_set(True)
for o in candidate:o.hide_render=False
if not draft and not validate_only:bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(HERE/'lifebuoy_review.blend'))
(OUT/('geometry-validation.json' if validate_only else 'render-report'+('-draft' if draft else '')+'.json')).write_text(json.dumps(report,indent=2));print(json.dumps(report))
