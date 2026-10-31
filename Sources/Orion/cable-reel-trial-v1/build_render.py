"""Real timber cable-reel rebuild, with matched renders of the actual saved before."""
from pathlib import Path
import math,json,hashlib,random,sys
import bpy,bmesh
from mathutils import Vector
HERE=Path(__file__).parent;ROOT=HERE.parents[2];TEX=HERE/'textures'
OUT=ROOT/'output/asset-improvement-20261030/orion-cable-reel'
sys.path.insert(0,str(HERE));sys.path.insert(0,str(ROOT/'Tools'))
import geometry as G
import belltower_render as R
S=G.S;draft='--draft' in sys.argv;validate_only='--validate-only' in sys.argv;after_only='--after-only' in sys.argv
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)

def mat(name,color,rough=.7,metal=0,prefix=None,normal_strength=.6):
    m=bpy.data.materials.new(name);m.use_nodes=True;n=m.node_tree.nodes;l=m.node_tree.links;p=n.get('Principled BSDF')
    p.inputs['Base Color'].default_value=(*color,1);p.inputs['Roughness'].default_value=rough;p.inputs['Metallic'].default_value=metal
    if prefix:
        for suffix,socket in [('color','Base Color'),('roughness','Roughness'),('metallic','Metallic')]:
            path=TEX/(prefix+'_'+suffix+'.png')
            if not path.exists():continue
            t=n.new('ShaderNodeTexImage');t.image=bpy.data.images.load(str(path),check_existing=True)
            if suffix!='color':t.image.colorspace_settings.name='Non-Color'
            l.new(t.outputs['Color'],p.inputs[socket])
        path=TEX/(prefix+'_normal.png')
        if path.exists():
            t=n.new('ShaderNodeTexImage');t.image=bpy.data.images.load(str(path),check_existing=True);t.image.colorspace_settings.name='Non-Color'
            nm=n.new('ShaderNodeNormalMap');nm.inputs['Strength'].default_value=normal_strength
            l.new(t.outputs['Color'],nm.inputs['Color']);l.new(nm.outputs['Normal'],p.inputs['Normal'])
    return m

wood=mat('Weathered timber - original photographic CC0 scan',(.25,.19,.12),prefix='wood',normal_strength=.38)
endgrain=mat('Exposed sawn board end grain',(.20,.18,.15),prefix='endgrain',normal_strength=.7)
cable=mat('Fine textured black cable jacket',(.018,.021,.022),prefix='cable',normal_strength=.55)
zinc=mat('Weathered galvanized hardware',(.3,.32,.33),.52,.92,'zinc')
oxide=mat('Localized oxidized steel',(.13,.10,.06),.7,.4,'oxide')
label=mat('Faded paper inventory label',(.60,.55,.4),.89)
t=label.node_tree.nodes.new('ShaderNodeTexImage');t.image=bpy.data.images.load(str(TEX/'inventory_label.png'))
label.node_tree.links.new(t.outputs['Color'],label.node_tree.nodes.get('Principled BSDF').inputs['Base Color'])

def ring(name,center,profile,material,sides=64):
    # Closed profile around Z produces an actual open bore, without a cap across it.
    cx,cy,cz=center;vs=[]
    for r,z in profile:
        for i in range(sides):
            a=i*math.tau/sides;vs.append((cx+r*math.cos(a),cy+r*math.sin(a),cz+z))
    fs=[]
    for j in range(len(profile)):
        k=(j+1)%len(profile)
        for i in range(sides):ii=(i+1)%sides;fs.append((j*sides+i,j*sides+ii,k*sides+ii,k*sides+i))
    return G.mesh(name,vs,fs,material,True)

def clip(poly,bound,keep_greater):
    result=[]
    for a,b in zip(poly,poly[1:]+poly[:1]):
        ia=(a[0]>=bound) if keep_greater else (a[0]<=bound)
        ib=(b[0]>=bound) if keep_greater else (b[0]<=bound)
        if ia:result.append(a)
        if ia!=ib:
            t=(bound-a[0])/(b[0]-a[0]);result.append((bound,a[1]+t*(b[1]-a[1])))
    return result

def outer_radius(a):
    r=25.88+.045*math.sin(17*a)+.025*math.sin(37*a+.5)
    for at in (.51,2.14,4.42):
        delta=(a-at+math.pi)%math.tau-math.pi;r-=.16*math.exp(-(delta/.025)**2)
    return r

# True circular-sawn boards in two crossing layers, not a cylinder with a wood picture.
outline=[(outer_radius(a)*math.cos(a),outer_radius(a)*math.sin(a)) for a in [i*math.tau/192 for i in range(192)]]
rng=random.Random(209)
def cutter(center,r,height):
    bpy.ops.mesh.primitive_cylinder_add(vertices=64,radius=r*S,depth=height*S,location=tuple(c*S for c in center))
    return bpy.context.object
bore=cutter((0,0,23),3.20,52)
tail_hole=cutter((16,-14,43.4),.95,6)
def boolean(o,tool):
    bpy.context.view_layer.objects.active=o
    mod=o.modifiers.new('Real through bore','BOOLEAN');mod.operation='DIFFERENCE';mod.solver='EXACT';mod.object=tool
    bpy.ops.object.modifier_apply(modifier=mod.name)

def wood_uv(o,lo,hi,index,rotation):
    # Restrict each physical board to one seam-free plank of the unchanged scan.
    layer=o.data.uv_layers.active
    if layer is None:layer=o.data.uv_layers.new(name='UVMap')
    scan_boards=[(.008,.114),(.129,.236),(.255,.342),(.362,.448),(.471,.559),(.583,.659),(.684,.763),(.787,.878),(.901,.991)]
    start,end=scan_boards[index%len(scan_boards)];offset=(index*.173)%1
    # Boolean cuts may append an empty cutter-material slot. Bind it explicitly,
    # then use the actual end-grain slot instead of assuming a fixed index.
    for slot in range(len(o.data.materials)):
        if o.data.materials[slot] is None:o.data.materials[slot]=wood
    o.data.materials.append(endgrain);endgrain_index=len(o.data.materials)-1
    zmin=min(v.co.z for v in o.data.vertices)/S;zmax=max(v.co.z for v in o.data.vertices)/S
    for p in o.data.polygons:
        across_normal=-p.normal.x*math.sin(rotation)+p.normal.y*math.cos(rotation)
        is_end=abs(p.normal.z)<.5 and abs(across_normal)>.50
        if is_end:p.material_index=endgrain_index
        for li in p.loop_indices:
            v=o.data.vertices[o.data.loops[li].vertex_index].co/S
            x=v.x*math.cos(rotation)+v.y*math.sin(rotation);y=-v.x*math.sin(rotation)+v.y*math.cos(rotation)
            depth=(v.z-zmin)/(zmax-zmin)
            if is_end:layer.data[li].uv=((x-lo)/(hi-lo),depth)
            elif abs(p.normal.z)>.5:layer.data[li].uv=(start+(end-start)*(x-lo)/(hi-lo),(y+26)/52+offset)
            else:layer.data[li].uv=(start+(end-start)*depth,(y+26)/52+offset)

for flange,levels in [('Lower',[(0,1.20,0),(1.30,2.50,math.pi/2)]),('Upper',[(42.1,43.25,0),(43.35,44.5,math.pi/2)])]:
    for layer,(z0,z1,angle) in enumerate(levels):
        for index in range(-6,7):
            lo=index*4-1.96;hi=index*4+1.96
            poly=clip(clip(outline,lo,True),hi,False)
            if len(poly)<3:continue
            def rotate(p,z):return (p[0]*math.cos(angle)-p[1]*math.sin(angle),p[0]*math.sin(angle)+p[1]*math.cos(angle),z)
            vs=[rotate(p,z) for z in (z0,z1) for p in poly];n=len(poly)
            fs=[tuple(reversed(range(n))),tuple(range(n,2*n))]
            fs.extend((i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n))
            o=G.mesh(flange+' cross-laminated timber board',vs,fs,wood)
            if lo<3.2 and hi>-3.2:boolean(o,bore)
            tx=16*math.cos(angle)-14*math.sin(angle)
            if flange=='Upper' and lo<tx+.96 and hi>tx-.96:boolean(o,tail_hole)
            G.bevel(o,.035,2);wood_uv(o,lo,hi,index+6+layer*3,angle)
bpy.data.objects.remove(bore,do_unlink=True);bpy.data.objects.remove(tail_hole,do_unlink=True)

# Timber barrel with a clear centre cavity; top and bottom arbor holes remain open.
for i in range(20):
    a0=i*math.tau/20+.004;a1=(i+1)*math.tau/20-.004
    vs=[(r*math.cos(a),r*math.sin(a),z) for z in (2.40,42.20) for r,a in ((11.5,a0),(12.6,a0),(12.6,a1),(11.5,a1))]
    o=G.mesh('Vertical barrel stave',vs,[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)],wood)
    G.bevel(o,.035,2)
    u=o.data.uv_layers.active
    for loop in o.data.loops:
        p=o.data.vertices[loop.vertex_index].co/S
        u.data[loop.index].uv=((i%8+.45)/8+(math.atan2(p.y,p.x)-a0)/math.tau,p.z/45)

# A closed annular inner winding volume, covered by a continuous visible cable helix.
ring('Inner wound cable layers',(0,0,0),[(12.65,2.95),(19.55,2.95),(19.55,41.75),(12.65,41.75)],cable,96)
turns=33;steps=turns*80;pitch=1.155;start=-turns*math.tau-math.pi/4
points=[]
for i in range(steps+1):
    t=i/80;a=start+t*math.tau;r=20.1+.027*math.sin(a*3)+.015*math.sin(a*9)
    points.append((r*math.cos(a),r*math.sin(a),3.0+t*pitch))
G.tube('Continuous 33-turn outer cable winding',points,.535,cable,8)
end=Vector(points[-1])
tail=[end,(15.5,-14.0,41.7),(16,-14,42.5),(16,-14,44.2),(16.5,-13.5,44.9),(18,-12,45.05),(21,-9,45.05)]
# Smooth the lead-out with a Catmull-Rom spline so it has credible cable bend radii.
def catmull(points,steps=8):
    p=[Vector(points[0])]+[Vector(x) for x in points]+[Vector(points[-1])];out=[]
    for i in range(1,len(p)-2):
        for j in range(steps):
            t=j/steps
            out.append(tuple(.5*((2*p[i])+(-p[i-1]+p[i+1])*t+(2*p[i-1]-5*p[i]+4*p[i+1]-p[i+2])*t*t+(-p[i-1]+3*p[i]-3*p[i+1]+p[i+2])*t*t*t)))
    out.append(tuple(p[-2]));return out
G.tube('Clamped cable lead-out',catmull(tail),.535,cable,12)

# Real arbor reinforcing rings and eight long threaded tie rods.
for z in (2.51,44.51):ring('Galvanized open arbor reinforcing ring',(0,0,z),[(3.18,0),(4.65,0),(4.65,.13),(3.18,.13)],zinc,64)
for i in range(8):
    a=i*math.tau/8+.19;x=9.35*math.cos(a);y=9.35*math.sin(a)
    G.turn('Tie rod',(x,y,1.75),(0,0,1),[(.22,0),(.22,43.75)],oxide,12)
    for z in (.12,44.51):
        ring('Contact-stained washer',(x,y,z),[(.235,0),(.70,0),(.70,.085),(.235,.085)],oxide if i%3==0 else zinc,24)
    ring('Hexagonal tension nut',(x,y,44.59),[(.235,0),(.48,0),(.53,.06),(.53,.39),(.46,.46),(.235,.46)],zinc,6)
    G.turn('Protruding thread core',(x,y,44.98),(0,0,1),[(.215,0),(.215,.40)],oxide,12)
    thread=[]
    for j in range(121):
        angle=j*math.tau/24;thread.append((x+.23*math.cos(angle),y+.23*math.sin(angle),44.98+.4*j/120))
    G.tube('Visible helical tie-rod thread',thread,.028,zinc,5)

# A formed retention cleat seats on the wood, with the lead-out held below it.
G.tube('Formed cable retention cleat',[(17.7,-9.7,44.65),(17.7,-9.7,45.77),(20.3,-12.3,45.77),(20.3,-12.3,44.65)],.11,zinc,10)
for x,y in ((17.7,-9.7),(20.3,-12.3)):
    G.box('Cleat foot',(x,y,44.60),(1.1,1.1,.14),zinc,.045)
    G.turn('Cleat fastener',(x,y,44.67),(0,0,1),[(.26,0),(.26,.16),(.20,.22)],zinc,6)

# Physical paper label with clipped corners, laid on the upper flange.
G.mesh('Orion inventory label',[(1.8,-19.8,44.555),(11.7,-19.8,44.555),(12.1,-19.4,44.555),(12.1,-15.0,44.555),(1.8,-15.0,44.555)],[(0,1,2,3,4)],label,
    uv=[(0,0),(.96,0),(1,.08),(1,1),(0,1)],fix=False)
candidate=list(G.parts)

# Copy the exact saved before, including its intentionally open single-sided shell.
baseline=[]
for paint,faces in json.loads((HERE/'before.json').read_text()).items():
    shader,kv=R.parse_vmat('materials/orion/'+paint+'.vmat');m=R.standard_material('Installed '+paint,kv)
    vs=[];uv=[];ns=[];fs=[]
    for f in faces:fs.append(tuple(range(len(vs),len(vs)+3)));vs+=f['vertices'];uv+=f['uv'];ns+=f['normals']
    o=G.mesh('Actual installed placeholder reel',vs,fs,m,True,uv,False);o.data.normals_split_custom_set_from_vertices(ns);baseline.append(o)

# Verify before spending time on final frames.
degenerate=[]
for o in candidate:
    # Boolean cap intersections can retain collinear vertices. Triangulate and
    # dissolve zero-area remnants at a sub-micron tolerance before export.
    bm=bmesh.new();bm.from_mesh(o.data)
    bmesh.ops.triangulate(bm,faces=list(bm.faces),quad_method='BEAUTY',ngon_method='BEAUTY')
    bmesh.ops.dissolve_degenerate(bm,dist=1e-8,edges=list(bm.edges));bm.to_mesh(o.data);bm.free();o.data.update()
    assert all(math.isfinite(v) for p in o.data.vertices for v in p.co),o.name
    assert all(p.material_index<len(o.data.materials) and o.data.materials[p.material_index] is not None for p in o.data.polygons),('Unbound material',o.name)
    o.data.calc_loop_triangles()
    if any(t.area<1e-14 for t in o.data.loop_triangles):degenerate.append(o.name)
assert not degenerate,degenerate
vs=[o.matrix_world@v.co for o in candidate for v in o.data.vertices]
lo=[min(v[i] for v in vs)/S for i in range(3)];hi=[max(v[i] for v in vs)/S for i in range(3)]
assert lo[2]>=-.001 and hi[2]<=46.001,(lo,hi)
assert max(math.hypot(p.x,p.y)/S for p in vs)<=26.01,(lo,hi)
guard=json.loads((HERE/'source-guard.json').read_text());assert all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h for p,h in guard.items())
report={'asset':'Orion launch-deck cable reel','renderer':'Blender Cycles CPU','nativeEngineScreenshot':False,
    'installed':False,'sameCameraScaleLightingExposure':True,'beforeTriangles':28,
    'afterTriangles':sum(sum(len(p.vertices)-2 for p in o.data.polygons) for o in candidate),
    'boundsInches':[lo,hi],'zeroAreaTriangles':0,'finiteGeometry':True,'protectedOriginalsUnchanged':len(guard),'images':[]}

if not draft and not validate_only:
    bpy.ops.object.select_all(action='DESELECT');copies=[]
    for o in candidate:
        c=o.copy();c.data=o.data.copy();bpy.context.collection.objects.link(c);c.select_set(True);copies.append(c)
    bpy.context.view_layer.objects.active=copies[0];bpy.ops.object.join();joined=bpy.context.object;joined.name='Orion cable reel review mesh'
    bpy.ops.wm.obj_export(filepath=str(HERE/'cable_reel_after.obj'),export_selected_objects=True,forward_axis='NEGATIVE_Y',up_axis='Z',export_triangulated_mesh=True)
    bpy.ops.export_scene.gltf(filepath=str(HERE/'cable_reel_after.glb'),use_selection=True,export_format='GLB',export_apply=True)
    bpy.data.objects.remove(joined,do_unlink=True)

scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.cycles.samples=12 if draft else 24
scene.cycles.use_denoising=True;scene.cycles.max_bounces=5;scene.render.threads_mode='FIXED';scene.render.threads=4
scene.render.resolution_x=1050 if draft else 1400;scene.render.resolution_y=1000 if draft else 1333;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG';scene.view_settings.view_transform='AgX';scene.view_settings.exposure=0
scene.world=scene.world or bpy.data.worlds.new('Same studio ambient');scene.world.use_nodes=True
scene.world.node_tree.nodes['Background'].inputs['Color'].default_value=(.34,.37,.42,1);scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.34
G.box('Same neutral floor',(0,0,-.4),(2000,2000,.8),mat('Neutral matte studio floor',(.14,.155,.17),.85),0)
for name,pos,power,size,color in [('Soft key',(-3.5,-4.0,5.0),900,4.0,(1,.94,.86)),('Cool fill',(3.6,-1.5,2.9),550,3.4,(.81,.89,1)),('Edge light',(-.4,3.5,4.0),1000,3.0,(.93,.97,1))]:
    d=bpy.data.lights.new(name,'AREA');d.energy=power;d.shape='DISK';d.size=size;d.color=color
    o=bpy.data.objects.new(name,d);bpy.context.collection.objects.link(o);o.location=pos;o.rotation_euler=(Vector((0,0,.6))-o.location).to_track_quat('-Z','Y').to_euler()
d=bpy.data.cameras.new('Matched 60 mm camera');cam=bpy.data.objects.new('Matched camera',d);bpy.context.collection.objects.link(cam);scene.camera=cam
eye=(1.935,-2.655,2.258);target=(0,0,.53);d.lens=60;cam.location=eye;cam.rotation_euler=(Vector(target)-cam.location).to_track_quat('-Z','Y').to_euler()
report.update({'cameraMetres':eye,'targetMetres':target,'lens':60,'samples':scene.cycles.samples})
suffix='-draft' if draft else ''
if after_only:
    path=OUT/'before.png';assert path.exists()
    existing=bpy.data.images.load(str(path));assert tuple(existing.size)==(1400,1333);bpy.data.images.remove(existing)
    report['images'].append({'variant':'before','file':path.name,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'reusedUnchangedBefore':True})
for variant in (() if validate_only else ('after',) if after_only else ('before','after')):
    for o in baseline:o.hide_render=variant!='before'
    for o in candidate:o.hide_render=variant!='after'
    path=OUT/(variant+suffix+'.png');scene.render.filepath=str(path);bpy.ops.render.render(write_still=True)
    report['images'].append({'variant':variant,'file':path.name,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
for o in baseline:o.hide_render=True;o.hide_set(True)
for o in candidate:o.hide_render=False
if not draft and not validate_only:bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(HERE/'cable_reel_review.blend'))
(OUT/('geometry-validation.json' if validate_only else 'render-report'+suffix+'.json')).write_text(json.dumps(report,indent=2))
print(json.dumps(report))
