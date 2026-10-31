"""Editable enclosed generating set; exact saved baseline and matched CPU Cycles frames."""
from pathlib import Path
import hashlib,json,math,sys
import bpy,bmesh
from mathutils import Vector
HERE=Path(__file__).parent;ROOT=Path.cwd();TEX=HERE/'textures';OUT=ROOT/'output/asset-improvement-20261030/orion-generator'
sys.path.insert(0,str(HERE));sys.path.insert(0,str(ROOT/'Tools'))
import geometry as G
import belltower_render as R
S=G.S;draft='--draft' in sys.argv;validate_only='--validate-only' in sys.argv;export_only='--export-only' in sys.argv
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)

def mat(name,color,rough=.65,metal=0,prefix=None,image=None,emission=0):
    m=bpy.data.materials.new(name);m.use_nodes=True;n=m.node_tree.nodes;l=m.node_tree.links;p=n.get('Principled BSDF')
    p.inputs['Base Color'].default_value=(*color,1);p.inputs['Roughness'].default_value=rough;p.inputs['Metallic'].default_value=metal
    for suffix,socket in [('color','Base Color'),('roughness','Roughness'),('metallic','Metallic')]:
        path=TEX/(prefix+'_'+suffix+'.png') if prefix else TEX/(image or 'absent')
        if not path.exists() or (not prefix and suffix!='color'):continue
        t=n.new('ShaderNodeTexImage');t.image=bpy.data.images.load(str(path),check_existing=True)
        if suffix!='color':t.image.colorspace_settings.name='Non-Color'
        l.new(t.outputs['Color'],p.inputs[socket])
        if emission and suffix=='color':l.new(t.outputs['Color'],p.inputs['Emission Color']);p.inputs['Emission Strength'].default_value=emission
    if prefix:
        t=n.new('ShaderNodeTexImage');t.image=bpy.data.images.load(str(TEX/(prefix+'_normal.png')),check_existing=True);t.image.colorspace_settings.name='Non-Color'
        nm=n.new('ShaderNodeNormalMap');nm.inputs['Strength'].default_value=.5;l.new(t.outputs['Color'],nm.inputs['Color']);l.new(nm.outputs['Normal'],p.inputs['Normal'])
    return m

paint=mat('Weathered slate powder coating',(.08,.11,.10),prefix='paint')
skid=mat('Graphite chassis coating',(.025,.03,.035),prefix='skid')
rubber=mat('Acoustic liner and EPDM seals',(.013,.017,.02),prefix='rubber')
zinc=mat('Galvanized fasteners',(.42,.44,.42),.4,.95,'zinc')
steel=mat('Brushed stainless exhaust',(.2,.22,.24),.42,.96,'steel')
heat=mat('Heat tinted exhaust welds',(.13,.09,.06),.55,.7,'heat')
brand=mat('Original Orion equipment plate',(.15,.18,.18),.6,.15,image='brand.png')
warning=mat('Service warning label',(.5,.4,.08),.7,image='warning.png')
display=mat('Recessed LCD under glass',(.025,.07,.06),.27,image='display.png',emission=.45)
yellow=mat('Muted safety yellow',(.52,.36,.055),.57)
red=mat('Emergency stop red polymer',(.38,.022,.012),.56)
green=mat('Status green lens',(.025,.21,.10),.23)

def box(name,p,size,m=paint,r=.08):return G.box(name,p,size,m,r)
def move(o,p):o.location+=Vector(p)*S;return o
def bolt(p,axis=(0,-1,0),radius=.25):
    G.turn('Captive washer',p,axis,[(radius*1.5,0),(radius*1.5,.08)],zinc,16)
    o=G.turn('Hex head fastener',tuple(Vector(p)+Vector(axis)*.08),axis,[(radius,.0),(radius,.23),(radius*.86,.29)],zinc,6)
    for f in o.data.polygons:f.use_smooth=False
    G.bevel(o,.025,1)
def plate(name,x,y,z,w,h,m):
    return G.mesh(name,[(x-w/2,y,z-h/2),(x+w/2,y,z-h/2),(x+w/2,y,z+h/2),(x-w/2,y,z+h/2)],[(0,1,2,3)],m,uv=[(0,0),(1,0),(1,1),(0,1)])
def side_frame(name,x,z,w,h,material=paint,depth=(30.6,31.4)):
    return move(G.frame(name,depth,(w,h,.50),(w-2.0,h-2.0,.20),material),(x,0,z))
def ring(name,p,axis,inner,outer,thickness,material,sides=32):
    axis=Vector(axis).normalized();ref=Vector((0,0,1)) if abs(axis.z)<.9 else Vector((1,0,0));a=axis.cross(ref).normalized();b=axis.cross(a)
    vs=[tuple(Vector(p)+axis*d+r*(a*math.cos(i*math.tau/sides)+b*math.sin(i*math.tau/sides))) for r,d in [(inner,0),(outer,0),(outer,thickness),(inner,thickness)] for i in range(sides)]
    fs=[(j*sides+i,j*sides+(i+1)%sides,((j+1)%4)*sides+(i+1)%sides,((j+1)%4)*sides+i) for j in range(4) for i in range(sides)]
    return G.mesh(name,vs,fs,material,True)

# Welded skid with real fork pockets through both longitudinal rails.
for y in (-30.5,30.5):
    for z in (.70,6.30):box('Skid channel flange',(0,y,z),(128,5,.65),skid,.09)
    for a,b in [(-64,-45),(-27,25),(43,64)]:box('Skid web beside fork opening',((a+b)/2,y,3.50),(b-a,.75,5.0),skid,.08)
    for x in (-36,34):
        for edge in (x-9,x+9):box('Fork pocket side return',(edge,0,3.5),(.70,60,4.7),skid,.06)
        box('Fork pocket upper reinforcement',(x,y,6.7),(20,5.2,.35),steel,.035)
for x in (-54,0,54):box('Transverse chassis tie',(x,0,5.0),(4.0,59,3.2),skid,.12)
box('Bunded integral belly tank',(0,0,9.0),(120,58,5.4),skid,.23)
for x in (-54,54):
    for y in (-26,26):
        box('Mounting foot',(x,y,.24),(10,10,.48),skid,.10)
        G.turn('Elastomer vibration isolator',(x,y,6.5),(0,0,1),[(1.8,0),(1.8,2.9),(1.5,3.15)],rubber,24)
        G.turn('Isolator top washer',(x,y,9.6),(0,0,1),[(2.0,0),(2.0,.30)],zinc,24)
        bolt((x,y,9.92),(0,0,1),.38)

# Acoustic enclosure: separate rails, posts, floor, doors and real ventilation openings.
box('Enclosure lower tray',(0,0,11.6),(126,63.5,1.25),paint,.22)
box('Dark acoustic lining behind vents',(0,0,35.3),(112,48,44),rubber,.20)
for y in (-31.0,31.0):
    for z in (13.3,59.7):box('Folded longitudinal panel rail',(0,y,z),(125,2.0,2.1),paint,.17)
    for x in (-61.8,61.8):box('Enclosure corner post',(x,y,36.5),(2.6,2.9,47.8),paint,.22)
for x in (-61.8,61.8):
    for z in (13.3,59.7):box('Folded end frame',(x,0,z),(2.5,62,2.1),paint,.16)

# Left near-side intake bank. Thin inclined blades leave clear open air gaps.
for x,w in [(-44,28),(50,20)]:
    side_frame('Gasket behind intake frame',x,36,w+1,44,rubber,(30.05,30.6))
    side_frame('Intake perimeter frame',x,36,w,43)
    for i in range(13):
        z=17.6+i*3.0;o=box('Formed intake louvre',(x,-30.8,z),(w-2.3,2.8,.24),paint,.055);o.rotation_euler.x=math.radians(27)
    for z in (16.0,56.0):
        for xx in (x-w/2+1.3,x+w/2-1.3):bolt((xx,-31.6,z))

# Main service doors and their elastomer seams.
for x,w in [(-10.5,36),(24,28)]:
    box('Continuous door gasket',(x,-30.7,36),(w+1.0,1.1,44.8),rubber,.20)
    box('Folded removable service door',(x,-31.4,36),(w,.85,44),paint,.18)
    for z in (21,49):
        hx=x-w/2+1.3
        box('Hinge leaf',(hx,-32.0,z),(1.5,.25,4.6),zinc,.07)
        G.turn('Hinge barrel',(hx+.65,-32.4,z-2.2),(0,0,1),[(.33,0),(.33,4.4)],zinc,16)
        for zz in (z-1.4,z+1.4):bolt((hx-.35,-32.25,zz),radius=.16)
    xx=x+w/2-2.1
    box('Recessed latch cup',(xx,-32.0,32.0),(2.4,.45,6.8),skid,.33)
    G.tube('Return service handle',[(xx,-32.4,30),(xx,-33.3,30.5),(xx,-33.3,33.5),(xx,-32.4,34)],.24,zinc,12)
    for z in (15.5,56.5):
        for xx in (x-w/2+2,x+w/2-2):bolt((xx,-31.95,z),radius=.19)
plate('Orion generating set data plate',-11,-31.86,49.5,27,6.75,brand)
for x in (-23.5,1.5):
    for z in (46.7,52.3):bolt((x,-31.9,z),radius=.12)
plate('Main service safety label',-11,-31.86,25,11,7.33,warning)

# Recessed controller with a protective raised bezel, key switch and tactile controls.
box('Controller dark inset',(23,-32.0,49),(22,1.0,18),skid,.40)
side_frame('Moulded controller bezel',23,49,21,17,skid,(32.25,33.1))
plate('Glazed LCD face',23,-32.8,49.6,17.0,12.75,display)
for x in (17,23,29):
    G.turn('Tactile button retaining ring',(x,-32.0,37.0),(0,-1,0),[(1.15,0),(1.15,.45)],zinc,24)
    G.turn('Tactile polymer button',(x,-32.5,37.0),(0,-1,0),[(.85,0),(.85,.50),(.69,.60)],green if x==29 else rubber,24)
G.turn('Emergency stop yellow collar',(23,-31.9,18),(0,-1,0),[(2.3,0),(2.3,.30)],yellow,32)
G.turn('Emergency stop stem',(23,-32.2,18),(0,-1,0),[(.78,0),(.78,.65)],rubber,24)
G.turn('Emergency stop mushroom',(23,-32.7,18),(0,-1,0),[(1.7,0),(1.8,.35),(1.65,.83),(1.35,1.02)],red,32)
G.turn('Belly tank filler surround',(-49,-31.5,13.6),(0,-1,0),[(1.7,0),(1.7,.25)],steel,32)
G.turn('Quarter turn fuel cap',(-49,-31.8,13.6),(0,-1,0),[(1.35,0),(1.35,.40),(1.15,.58)],skid,12)
box('Fuel cap grip',(-49,-32.45,13.6),(2.0,.35,.40),zinc,.07)

# End radiator: fan and fins behind a formed louvre pack and open diamond wire guard.
fan_x=56;fan_z=35
G.turn('Radiator fan motor',(fan_x,0,fan_z),(1,0,0),[(3.5,0),(3.5,3.4),(2.8,4.2)],skid,32)
ring('Fan shroud',(55,0,fan_z),(1,0,0),19.4,20.6,2.0,skid,64)
for i in range(8):
    a=i*math.tau/8;vs=[]
    for depth in (0,.18):
        for r,angle,dx in [(3,a,0),(18,a+.30,0),(18,a+.59,1.4),(4,a+.31,.5)]:vs.append((56+dx+depth,r*math.cos(angle),fan_z+r*math.sin(angle)))
    G.mesh('Pitched radiator fan blade',vs,[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)],skid)
for y in range(-26,27,2):box('Radiator cooling fin',(54.2,y,35),(1.0,.14,40),steel,.025)
o=G.frame('Radiator end opening',(61.2,62.2),(60,45,.6),(57,42,.4),paint)
G.transform(o,(0,0,36),((0,1,0),(-1,0,0),(0,0,1)))
for i in range(13):
    z=17.4+i*3.0;o=box('Radiator formed end louvre',(61.0,0,z),(3.0,56,.24),paint,.05);o.rotation_euler.y=math.radians(-28)
for sign in (-1,1):
    for offset in range(-38,81,4):
        pts=[]
        for i in range(81):
            y=-27+i*54/80;z=offset+sign*y*.75
            if 16<=z<=56:pts.append((62.5,y,z))
        if len(pts)>1:G.tube('Open diamond radiator guard',[pts[0],pts[-1]],.055,skid,6)
for y in (-28.4,28.4):
    for z in (16,36,56):bolt((62.7,y,z),(1,0,0),.23)

# Other service faces are fully built; no blank reverse side or open shell.
box('Rear panel gasket',(0,30.5,36),(119,1.0,44.6),rubber,.22)
for x in (-31,29):
    box('Rear acoustic service panel',(x,31.2,36),(58,.8,44),paint,.17)
    for z in (16,55):
        for xx in (x-26,x+26):bolt((xx,31.75,z),(0,1,0),.23)
    for z in (27,43):
        box('Rear hinge block',(x-27,31.8,z),(1.4,.6,4.3),zinc,.12)
    box('Rear service latch',(x+23,31.9,35),(2,.7,5),skid,.25)
box('Alternator end service cover',(-62.1,0,36),(1.1,60,44),paint,.24)
for y in (-27,27):
    for z in (16,56):bolt((-62.8,y,z),(-1,0,0),.26)
for y in range(-21,22,4):box('Alternator cooling recess',(-62.8,y,35),(.22,1.2,29),skid,.13)

# Folded roof, rain edges, lifting eyes, short silencer and retained rain flap.
for x in (-31.8,31.8):box('Folded roof skin',(x,0,62.0),(63.3,66,1.40),paint,.30)
box('Roof centre seam cap',(0,0,62.8),(1.2,65,.28),steel,.08)
for y in (-33.1,33.1):box('Downturned roof rain edge',(0,y,61.3),(127,.65,2.2),paint,.14)
for x in (-47,47):
    for y in (-24,24):
        box('Lifting lug welded foot',(x,y,63.0),(6.8,3.0,.40),steel,.13)
        ring('Open lifting eye',(x,y-.3,65.0),(0,1,0),.95,2.05,.6,steel,32)
        G.tube('Lifting foot weld bead',[(x-3.0,y-1.4,63.1),(x+3.0,y-1.4,63.1)],.10,heat,8)
        for xx in (x-2.6,x+2.6):bolt((xx,y,63.25),(0,0,1),.25)
ring('Exhaust roof boot',(-48,12,62.75),(0,0,1),1.05,2.25,.38,heat,40)
G.tube('Exhaust formed inlet',[(-48,12,62.8),(-48,12,64.3),(-47.6,12,65.5),(-46,12,66.4),(-42,12,66.4)],1.0,steel,24)
G.turn('Closed cylindrical exhaust silencer',(-42,12,66.4),(1,0,0),[(1.1,0),(2.1,1),(2.35,2),(2.35,27),(2.1,28),(1.1,29)],steel,48)
for x in (-38,-18):
    box('Exhaust saddle foot',(x,12,63.3),(2,8,.5),heat,.12)
    ring('Exhaust retaining strap',(x,12,66.4),(1,0,0),2.35,2.55,.8,heat,40)
for x in (-40,-15):ring('Silencer rolled end seam',(x,12,66.4),(1,0,0),2.3,2.46,.22,heat,48)
G.tube('Upturned exhaust outlet',[(-13,12,66.4),(-9,12,66.4),(-7,12,67.2),(-6.4,12,69.0)],.82,heat,24)
o=box('Hinged exhaust rain flap',(-6.4,12,69.55),(2.3,2.3,.16),steel,.08);o.rotation_euler.y=math.radians(-6)
G.turn('Rain flap hinge',(-7.6,10.9,69.45),(0,1,0),[(.22,0),(.22,2.2)],zinc,16)

candidate=list(G.parts);bpy.context.view_layer.update()
baseline=[]
for material,faces in json.loads((HERE/'before.json').read_text()).items():
    shader,kv=R.parse_vmat('materials/orion/'+material+'.vmat');m=R.standard_material('Installed '+material,kv)
    # The shared converter defaults to .7 for constants. Preserve this saved
    # material's actual .55 instead of changing the baseline's reflection.
    if kv.get('TextureRoughness','').startswith('['):
        next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED').inputs['Roughness'].default_value=R.floats(kv['TextureRoughness'])[0]
    vs=[];uv=[];ns=[];fs=[]
    for f in faces:fs.append(tuple(range(len(vs),len(vs)+3)));vs+=f['vertices'];uv+=f['uv'];ns+=f['normals']
    o=G.mesh('Exact saved generator box',vs,fs,m,True,uv,False);o.data.normals_split_custom_set_from_vertices(ns);baseline.append(o)

for o in candidate:
    bm=bmesh.new();bm.from_mesh(o.data);bmesh.ops.triangulate(bm,faces=list(bm.faces));bmesh.ops.dissolve_degenerate(bm,dist=1e-8,edges=list(bm.edges));bm.to_mesh(o.data);bm.free();o.data.update()
    assert all(math.isfinite(v) for p in o.data.vertices for v in p.co),o.name
    assert all(p.material_index<len(o.data.materials) and o.data.materials[p.material_index] is not None for p in o.data.polygons),o.name
    o.data.calc_loop_triangles();assert all(t.area>1e-14 for t in o.data.loop_triangles),o.name
vs=[o.matrix_world@v.co for o in candidate for v in o.data.vertices]
lo=[min(p[i] for p in vs)/S for i in range(3)];hi=[max(p[i] for p in vs)/S for i in range(3)]
assert all(a>=b-.001 for a,b in zip(lo,(-65,-35,0))) and all(a<=b+.001 for a,b in zip(hi,(65,35,70))),(lo,hi)
guard=json.loads((HERE/'source-guard.json').read_text());assert all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h for p,h in guard.items())
report={'asset':'Orion launch-deck enclosed generator','renderer':'Blender Cycles CPU','nativeEngineScreenshot':False,'installed':False,
 'sameCameraScaleLightingExposure':True,'beforeTriangles':12,'afterTriangles':sum(len(o.data.polygons) for o in candidate),
 'boundsInches':[lo,hi],'zeroAreaTriangles':0,'finiteGeometry':True,'protectedOriginalsUnchanged':len(guard),'images':[]}
if not draft and not validate_only:
    bpy.ops.object.select_all(action='DESELECT');copies=[]
    for o in candidate:
        c=o.copy();c.data=o.data.copy();bpy.context.collection.objects.link(c);c.select_set(True);copies.append(c)
    bpy.context.view_layer.objects.active=copies[0];bpy.ops.object.join();joined=bpy.context.object;joined.name='Orion generator review mesh'
    # Keep the export pivot at the footprint centre on the floor, independent
    # of which individually positioned part happens to be the active mesh.
    bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
    bpy.ops.wm.obj_export(filepath=str(HERE/'generator_after.obj'),export_selected_objects=True,forward_axis='NEGATIVE_Y',up_axis='Z',export_triangulated_mesh=True)
    bpy.ops.export_scene.gltf(filepath=str(HERE/'generator_after.glb'),use_selection=True,export_format='GLB',export_apply=True)
    bpy.data.objects.remove(joined,do_unlink=True)
if export_only:
    report['exportPivotMetres']=[0,0,0];(OUT/'export-rebuild.json').write_text(json.dumps(report,indent=2));print(json.dumps(report));sys.exit(0)
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.cycles.samples=12 if draft else 32;scene.cycles.use_denoising=True;scene.cycles.max_bounces=5
scene.render.threads_mode='FIXED';scene.render.threads=4;scene.render.resolution_x=1050 if draft else 1600;scene.render.resolution_y=760 if draft else 1160;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG';scene.view_settings.view_transform='AgX';scene.view_settings.exposure=0
scene.world=scene.world or bpy.data.worlds.new('Same studio ambient');scene.world.use_nodes=True
scene.world.node_tree.nodes['Background'].inputs['Color'].default_value=(.34,.37,.42,1);scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.34
G.box('Same neutral floor',(0,0,-.4),(2000,2000,.8),mat('Neutral studio floor',(.14,.155,.17),.85),0)
for name,pos,power,size,color in [('Soft key',(-3.5,-5,6.5),1400,5,(1,.94,.86)),('Cool fill',(5.5,-1.5,3.8),950,4,(.81,.89,1)),('Edge light',(-.4,4.5,5.0),1400,4,(.93,.97,1))]:
    d=bpy.data.lights.new(name,'AREA');d.energy=power;d.shape='DISK';d.size=size;d.color=color
    o=bpy.data.objects.new(name,d);bpy.context.collection.objects.link(o);o.location=pos;o.rotation_euler=(Vector((0,0,.8))-o.location).to_track_quat('-Z','Y').to_euler()
d=bpy.data.cameras.new('Matched 60 mm camera');cam=bpy.data.objects.new('Matched camera',d);bpy.context.collection.objects.link(cam);scene.camera=cam
eye=(4.3,-6.5,3.6);target=(0,0,.85);d.lens=60;cam.location=eye;cam.rotation_euler=(Vector(target)-cam.location).to_track_quat('-Z','Y').to_euler()
report.update({'cameraMetres':eye,'targetMetres':target,'lens':60,'samples':scene.cycles.samples})
suffix='-draft' if draft else ''
for variant in (() if validate_only else ('before','after')):
    for o in baseline:o.hide_render=variant!='before'
    for o in candidate:o.hide_render=variant!='after'
    path=OUT/(variant+suffix+'.png');scene.render.filepath=str(path);bpy.ops.render.render(write_still=True)
    report['images'].append({'variant':variant,'file':path.name,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
for o in baseline:o.hide_render=True;o.hide_set(True)
for o in candidate:o.hide_render=False
if not draft and not validate_only:bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(HERE/'generator_review.blend'))
(OUT/('geometry-validation.json' if validate_only else 'render-report'+suffix+'.json')).write_text(json.dumps(report,indent=2));print(json.dumps(report))
