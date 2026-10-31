"""Actual Ares console model rebuild and matched offline geometry comparison."""
from pathlib import Path
import hashlib,json,math,sys,random
import bpy,bmesh
from mathutils import Vector
HERE=Path(__file__).parent;ROOT=HERE.parents[2];TEX=HERE/'textures'
OUT=ROOT/'output/asset-improvement-20261030/ares-control-console'
sys.path.insert(0,str(HERE));sys.path.insert(0,str(ROOT/'Tools'))
import geometry as G
import belltower_render as R
S=G.S;draft='--draft' in sys.argv;validate_only='--validate-only' in sys.argv
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)

def material(name,color,rough=.6,metal=0,prefix=None):
    m=bpy.data.materials.new(name);m.use_nodes=True;n=m.node_tree.nodes;l=m.node_tree.links;p=n.get('Principled BSDF')
    p.inputs['Base Color'].default_value=(*color,1);p.inputs['Roughness'].default_value=rough;p.inputs['Metallic'].default_value=metal
    if prefix:
        for suffix,socket in [('color','Base Color'),('roughness','Roughness'),('metallic','Metallic')]:
            tex=n.new('ShaderNodeTexImage');tex.image=bpy.data.images.load(str(TEX/(prefix+'_'+suffix+'.png')),check_existing=True)
            if suffix!='color':tex.image.colorspace_settings.name='Non-Color'
            l.new(tex.outputs['Color'],p.inputs[socket])
        tex=n.new('ShaderNodeTexImage');tex.image=bpy.data.images.load(str(TEX/(prefix+'_normal.png')),check_existing=True);tex.image.colorspace_settings.name='Non-Color'
        normal=n.new('ShaderNodeNormalMap');normal.inputs['Strength'].default_value=.6;l.new(tex.outputs['Color'],normal.inputs['Color']);l.new(normal.outputs['Normal'],p.inputs['Normal'])
    return m

paint=material('Coated warm grey folded steel',(.32,.34,.33),prefix='paint')
dark=material('Fine textured charcoal instrument panel',(.035,.04,.042),prefix='dark')
steel=material('Brushed stainless and machined fasteners',(.36,.39,.4),.4,.96,'steel')
rubber=material('EPDM seams and neoprene feet',(.012,.016,.016),.82)
keys=material('Moulded PBT keys',(.026,.031,.032),.53)
yellow=material('Faded safety yellow control collar',(.63,.42,.065),.61)
red=material('Red phenolic stop cap',(.28,.025,.017),.4)
track=material('Satin ceramic trackball',(.32,.35,.32),.28)
led=material('Cyan indicator lens',(.02,.18,.20),.21)
lp=led.node_tree.nodes.get('Principled BSDF');lp.inputs['Emission Color'].default_value=(.08,.6,.68,1);lp.inputs['Emission Strength'].default_value=1.4
amber=material('Amber status indicator',(.35,.13,.018),.24)
ap=amber.node_tree.nodes.get('Principled BSDF');ap.inputs['Emission Color'].default_value=(1,.32,.025,1);ap.inputs['Emission Strength'].default_value=1.5

def image_material(name,file,rough=.5):
    m=material(name,(1,1,1),rough);t=m.node_tree.nodes.new('ShaderNodeTexImage');t.image=bpy.data.images.load(str(TEX/file),check_existing=True)
    m.node_tree.links.new(t.outputs['Color'],m.node_tree.nodes.get('Principled BSDF').inputs['Base Color']);return m
labels=image_material('Engraved service and control labels','panel_labels.png',.64)
legends=image_material('Keycap legends','key_legends.png',.56)
screen=image_material('Original approved Ares display atlas','ar_screens_color.png',.65)
sp=screen.node_tree.nodes.get('Principled BSDF');sp.inputs['Specular IOR Level'].default_value=0
st=next(n for n in screen.node_tree.nodes if n.type=='TEX_IMAGE')
screen.node_tree.links.new(st.outputs['Color'],sp.inputs['Emission Color']);sp.inputs['Emission Strength'].default_value=.75

def screw(p,axis=(0,-1,0),r=.24):
    a=Vector(axis);p=Vector(p)
    G.turn('Contact washer',p,a,[(r*1.3,0),(r*1.3,.05)],steel,16)
    G.turn('Recessed socket cap',p+a*.05,a,[(r,0),(r,.10),(r*.78,.16),(r*.36,.16),(r*.36,.07)],steel,20)
    G.turn('Dark hex socket',p+a*.125,a,[(r*.36,0),(r*.36,.008)],rubber,6)

def label(index,center,w,h,right=(1,0,0),up=(0,0,1)):
    c=Vector(center);r=Vector(right)*w/2;u=Vector(up)*h/2
    col=index%2;row=index//2;u0=col/2;u1=(col+1)/2;v0=1-(row+1)/4;v1=1-row/4
    return G.mesh('Engraved panel label',[c-r-u,c+r-u,c+r+u,c-r+u],[(0,1,2,3)],labels,uv=[(u0,v0),(u1,v0),(u1,v1),(u0,v1)],fix=False)

# A cabinet assembled from closed folded panels, with a recessed front service bay.
G.box('Grounded recessed plinth',(0,1,1.6),(55,27.5,3.2),dark,.35)
for x in (-24.7,24.7):
    for y in (-10.8,12.8):G.box('Neoprene isolation foot',(x,y,.43),(5.1,4.6,.85),rubber,.24)
G.box('Cabinet lower folded tray',(0,1,4.3),(59.3,30.5,2.5),paint,.4)
for x in (-28.75,28.75):G.box('Folded side cheek',(x,1.1,18.8),(1.3,30.3,27.0),paint,.32)
G.box('Closed rear service wall',(0,15.6,18.8),(56.7,1.1,27.0),paint,.2)
G.box('Dark service recess',(0,-12.95,18.4),(56,.8,26),dark,.18)
G.box('Front service door gasket',(-7.5,-13.59,18.4),(39.8,.22,24.4),rubber,.15)
G.box('Inset front service door',(-7.5,-13.87,18.4),(39.3,.42,23.9),paint,.17)
G.box('Lower stainless kick plate',(-7.5,-14.12,8.8),(36.4,.12,3.4),steel,.06)
for x in (-24.9,9.9):
    for z in (8.4,28.4):screw((x,-14.12,z),r=.17)
for z in (11,25):
    G.box('Door hinge block',(-27.9,-14.02,z),(1.7,.7,3.0),steel,.12)
    G.turn('Hinge pin',(-27.9,-14.45,z-1.6),(0,0,1),[(.19,0),(.19,3.2)],steel,16)
G.box('Service latch surround',(8.2,-14.18,18.6),(1.9,.17,4.8),rubber,.24)
G.box('Recessed service latch',(8.2,-14.32,18.6),(1.35,.18,3.8),steel,.2)
G.turn('Latch key socket',(8.2,-14.45,18.8),(0,-1,0),[(.23,0),(.23,.04)],dark,12)
label(0,(-8,-14.15,25.3),20.8,4.0)
label(3,(-8,-14.16,15),20.8,2.4)

# Open individual louvres reveal a dark, physically recessed ventilation cavity.
G.box('Vent recessed interior',(21.0,-12.95,18.5),(12.5,1.3,24.0),rubber,.1)
for x in (14.5,27.5):G.box('Vent side flange',(x,-13.75,18.5),(.6,.8,24.2),paint,.09)
for z in (6.6,30.4):G.box('Vent end flange',(21,-13.75,z),(13.6,.8,.6),paint,.09)
for z in [8+i*1.43 for i in range(16)]:
    o=G.box('Formed open louvre',(21,-14.0,z),(12.4,.9,.58),paint,.11);o.rotation_euler.x=math.radians(20)
for x in (15,27):
    for z in (7.3,29.7):screw((x,-14.2,z),r=.15)

# Deck and a closed chamfered display housing. Existing screen content and aspect preserved.
G.box('Sealed operator deck',(0,-6.3,33.7),(59.5,18.0,2.0),dark,.52)
G.box('Folded front deck fascia',(0,-15.45,32.65),(59.1,.55,2.4),paint,.17)
G.box('Cabinet top rear closure',(0,9.55,33.0),(58.7,16.1,2.5),paint,.32)
L=math.hypot(10,28);up=Vector((0,10/L,28/L));inward=Vector((0,28/L,-10/L));normal=-inward
origin=Vector((0,8.54,48.7));axes=[(1,0,0),inward,up]
def panel(o):return G.transform(o,origin,axes)
panel(G.box('Closed angled display chassis',(0,1.35,0),(57.8,2.65,32.1),paint,.63))
panel(G.frame('Display compression seal',(-.14,.02),(56.2,31.45,.62),(52.45,29.96,.27),rubber))
panel(G.frame('Chamfered display bezel',(.02,.42),(56.5,31.55,.62),(52.03,29.76,.18),dark))
for x in (-27.4,27.4):
    for z in (-14.7,14.7):
        p=origin+Vector((x,0,0))+up*z+normal*.44;screw(p,normal,.18)
face=json.loads((HERE/'before.json').read_text())['ar_screens']
vs=[];uv=[];fs=[]
shift=up*(-1.38)
for f in face:
    fs.append(tuple(range(len(vs),len(vs)+3)))
    vs.extend([Vector(p)+shift for p in f['vertices']]);uv.extend(f['uv'])
G.mesh('Original full screen artwork',vs,fs,screen,uv=uv,fix=False)

# Side display trunnions and visible rear heat-dissipation rails.
for sign in (-1,1):
    G.turn('Display pivot washer',(sign*28.9,9.0,40.3),(sign,0,0),[(1.8,0),(1.8,.45)],rubber,32)
    G.turn('Display pivot cap',(sign*29.20,9.0,40.3),(sign,0,0),[(1.55,0),(1.48,.45),(1.2,.6)],steel,32)
    G.box('Display support foot',(sign*26.8,9.1,35.2),(3.4,7.4,4.0),paint,.5)
for x in range(-24,25,3):
    o=G.box('Rear cooling rib',(x,2.9,0),(.38,.62,23.5),dark,.10);panel(o)

# Rugged keyboard with individually modelled sculpted caps and actual legend UVs.
G.box('Keyboard mounting seal',(-8.5,-7.2,34.79),(23.6,10.3,.18),rubber,.32)
G.box('Keyboard chassis',(-8.5,-7.2,35.12),(23.1,9.8,.50),steel,.34)
G.box('Keyboard inset tray',(-8.5,-7.2,35.40),(22.3,9.0,.18),dark,.22)
def key(x,y,w,index):
    G.box('Sculpted PBT keycap',(x,y,35.88),(w,.85,.64),keys,.15)
    i=index%60;u0=(i%8)/8;u1=(i%8+1)/8;v1=1-(i//8)/8;v0=v1-1/8
    G.mesh('Laser key legend',[(x-w*.32,y-.30,36.208),(x+w*.32,y-.30,36.208),(x+w*.32,y+.30,36.208),(x-w*.32,y+.30,36.208)],[(0,1,2,3)],legends,uv=[(u0,v0),(u1,v0),(u1,v1),(u0,v1)],fix=False)
for row in range(4):
    for col in range(15):key(-18.1+col*1.04,-9.2+row*1.15,.88,row*12+col)
for col in range(12):key(-18.1+col*1.04,-3.9,.83,52+col)
for x,w,i in [(-17.6,1.8,47),(-15.2,1.8,48),(-9.3,7.8,51),(-3.5,1.8,46)]:key(x,-10.65,w,i)
for row in range(4):
    for col in range(3):key(.0+col*1.04,-9.2+row*1.15,.88,row*3+col)

# Physical trackball, command buttons, selector and guarded stop control.
G.turn('Trackball mounting ring',(10.1,-7.5,34.8),(0,0,1),[(2.25,0),(2.25,.32),(1.63,.53)],steel,48)
bpy.ops.mesh.primitive_uv_sphere_add(segments=40,ring_count=20,radius=1.47*S,location=(10.1*S,-7.5*S,35.18*S))
o=bpy.context.object;o.name='Ceramic trackball';o.data.materials.append(track)
for p in o.data.polygons:p.use_smooth=True
G.parts.append(o)
for x in (7.5,12.7):G.box('Trackball tactile switch',(x,-11.25,35.0),(2.5,1.1,.7),keys,.22)
for i,x in enumerate((18.3,22.2,26.1)):
    G.turn('Pushbutton threaded collar',(x,-9.7,34.8),(0,0,1),[(1.03,0),(1.03,.32),(.89,.47)],steel,32)
    G.turn('Illuminated command cap',(x,-9.7,35.2),(0,0,1),[(.74,0),(.74,.30),(.62,.40)],led if i<2 else amber,32)
label(5,(21.7,-12.5,34.73),12.2,1.0,up=(0,1,0))
G.turn('Stop switch warning collar',(24.3,-3.5,34.8),(0,0,1),[(1.8,0),(1.8,.14)],yellow,40)
G.turn('Stop switch barrel',(24.3,-3.5,34.95),(0,0,1),[(.75,0),(.75,.75)],dark,32)
G.turn('Mushroom stop cap',(24.3,-3.5,35.55),(0,0,1),[(1.21,0),(1.28,.16),(1.28,.49),(1.06,.66)],red,40)
label(7,(22.8,-.45,34.73),12.5,1.0,up=(0,1,0))
G.turn('Selector mounting escutcheon',(-25.5,-6.8,34.85),(0,0,1),[(1.65,0),(1.65,.16)],steel,32)
G.turn('Rotary selector base',(-25.5,-6.8,35.02),(0,0,1),[(1.17,0),(1.17,.42),(.98,.55)],keys,32)
G.box('Glove grip selector handle',(-25.5,-6.8,35.75),(.60,2.05,.75),keys,.19)
for z in (0,1,2):G.turn('Power status lens',(-25.5,-1.3-z*1.45,34.85),(0,0,1),[(.29,0),(.29,.18)],led if z<2 else amber,20)
label(4,(-24.4,-11.3,34.73),7.7,1.1,up=(0,1,0))
label(1,(-21.7,-15.76,32.7),12.3,1.3)

# Side service handles, recessed access covers and retained cable routing.
for sign in (-1,1):
    for y in (-5,8):G.box('Handle mounting boss',(sign*29.49,y,23.4),(.72,1.8,2.0),dark,.18)
    G.tube('Side service grab handle',[(sign*29.7,-5,23.4),(sign*29.7,-4.3,24.6),(sign*29.7,7.3,24.6),(sign*29.7,8,23.4)],.24,steel,12)
G.box('Rear maintenance cover',(0,16.24,19.1),(38,.22,20.4),dark,.14)
for x in (-17.8,17.8):
    for z in (10.2,28):screw((x,16.4,z),(0,1,0),.18)
for x in (-8,8):
    G.turn('Rear cable compression gland',(x,16.6,6.8),(0,1,0),[(.72,0),(.72,.45),(.56,.85)],dark,12)
    G.tube('Retained short power cable',[(x,17.2,6.8),(x,17.6,5.7),(x+1,17.6,3.2),(x+3,16.0,2.8)],.28,rubber,10)

candidate=list(G.parts)
# Exact installed baseline, with its original split normals, UVs and materials.
baseline=[]
for name,faces in json.loads((HERE/'before.json').read_text()).items():
    shader,kv=R.parse_vmat('materials/ares/'+name+'.vmat');m=R.standard_material('Installed '+name,kv)
    for p in m.node_tree.nodes:
        if p.type=='BSDF_PRINCIPLED':
            if name=='ar_screens':p.inputs['Specular IOR Level'].default_value=0
            if kv.get('TextureRoughness','').startswith('['):p.inputs['Roughness'].default_value=R.floats(kv['TextureRoughness'])[0]
            if kv.get('F_SELF_ILLUM')=='1' and not p.inputs['Emission Color'].is_linked:
                p.inputs['Emission Color'].default_value=(*R.floats(kv.get('g_vColorTint','1 1 1 1'))[:3],1)
    vs=[];uv=[];ns=[];fs=[]
    for f in faces:fs.append(tuple(range(len(vs),len(vs)+3)));vs+=f['vertices'];uv+=f['uv'];ns+=f['normals']
    o=G.mesh('Installed '+name,vs,fs,m,True,uv,False);o.data.normals_split_custom_set_from_vertices(ns);baseline.append(o)

# Export a single combined candidate mesh for material batching, retaining editable parts in .blend.
if not draft and not validate_only:
    bpy.ops.object.select_all(action='DESELECT');copies=[]
    for o in candidate:
        c=o.copy();c.data=o.data.copy();bpy.context.collection.objects.link(c);c.select_set(True);copies.append(c)
    bpy.context.view_layer.objects.active=copies[0];bpy.ops.object.join();joined=bpy.context.object;joined.name='Ares control console review mesh'
    bpy.ops.wm.obj_export(filepath=str(HERE/'control_console_after.obj'),export_selected_objects=True,forward_axis='NEGATIVE_Y',up_axis='Z',export_triangulated_mesh=True)
    bpy.ops.export_scene.gltf(filepath=str(HERE/'control_console_after.glb'),use_selection=True,export_format='GLB',export_apply=True)
    bpy.data.objects.remove(joined,do_unlink=True)

scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.device='CPU'
scene.cycles.samples=12 if draft else 24;scene.cycles.use_denoising=True;scene.cycles.max_bounces=5
scene.render.threads_mode='FIXED';scene.render.threads=4
scene.render.resolution_x=950 if draft else 1400;scene.render.resolution_y=1050 if draft else 1540
scene.render.resolution_percentage=100;scene.render.image_settings.file_format='PNG'
scene.view_settings.view_transform='AgX';scene.view_settings.exposure=0
scene.world=scene.world or bpy.data.worlds.new('Same studio ambient');scene.world.use_nodes=True
scene.world.node_tree.nodes['Background'].inputs['Color'].default_value=(.34,.37,.42,1);scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.34
floor=G.box('Same neutral studio floor',(0,0,-.4),(2000,2000,.8),material('Neutral matte floor',(.13,.145,.16),.84),0)
for name,pos,power,size,color in [('Soft key',(-3.5,-4.2,5.2),950,4.5,(1,.93,.85)),('Cool fill',(3.8,-1.8,3.1),680,3.7,(.80,.88,1)),('Edge light',(-1.5,3,4.3),1050,3.1,(.92,.96,1))]:
    d=bpy.data.lights.new(name,'AREA');d.energy=power;d.shape='DISK';d.size=size;d.color=color
    o=bpy.data.objects.new(name,d);bpy.context.collection.objects.link(o);o.location=pos;o.rotation_euler=(Vector((0,0,.85))-o.location).to_track_quat('-Z','Y').to_euler()
d=bpy.data.cameras.new('Matched 60 mm camera');cam=bpy.data.objects.new('Matched camera',d);bpy.context.collection.objects.link(cam);scene.camera=cam
d.lens=60;eye=(2.385,-3.735,2.6);target=(0,0,.80);cam.location=eye;cam.rotation_euler=(Vector(target)-cam.location).to_track_quat('-Z','Y').to_euler()
suffix='-draft' if draft else '';report={'renderer':'Blender Cycles CPU','nativeEngineScreenshot':False,'installed':False,
    'sameCameraScaleLightingExposure':True,'screenArtwork':'Original approved Ares atlas and original saved UVs',
    'cameraMetres':eye,'targetMetres':target,'lens':60,'samples':scene.cycles.samples,
    'beforeTriangles':40,'afterTriangles':sum(sum(len(p.vertices)-2 for p in o.data.polygons) for o in candidate),'images':[]}
for variant in (() if validate_only else ('before','after')):
    for o in baseline:o.hide_render=variant!='before'
    for o in candidate:o.hide_render=variant!='after'
    path=OUT/(variant+suffix+'.png');scene.render.filepath=str(path);bpy.ops.render.render(write_still=True)
    report['images'].append({'variant':variant,'file':path.name,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})

bad=[];degenerate=[]
for o in candidate:
    if any(not math.isfinite(c) for v in o.data.vertices for c in v.co):bad.append(o.name)
    o.data.calc_loop_triangles()
    if any(t.area<1e-14 for t in o.data.loop_triangles):degenerate.append(o.name)
assert not bad,bad
assert not degenerate,degenerate
vs=[o.matrix_world@v.co for o in candidate for v in o.data.vertices]
lo=[min(v[i] for v in vs)/S for i in range(3)];hi=[max(v[i] for v in vs)/S for i in range(3)]
report['boundsInches']=[lo,hi]
assert lo[0]>=-30.01 and hi[0]<=30.01 and lo[1]>=-16.01 and hi[1]<=18.01 and lo[2]>=-.001 and hi[2]<=64.01,(lo,hi)
guard=json.loads((HERE/'source-guard.json').read_text());assert all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h for p,h in guard.items())
report['protectedOriginalFilesUnchanged']=len(guard);report['finiteGeometry']=True;report['zeroAreaTriangles']=0
for o in baseline:o.hide_render=True;o.hide_set(True)
for o in candidate:o.hide_render=False
if not draft and not validate_only:
    bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(HERE/'control_console_review.blend'))
(OUT/('geometry-validation.json' if validate_only else 'render-report'+suffix+'.json')).write_text(json.dumps(report,indent=2))
print(json.dumps(report))
