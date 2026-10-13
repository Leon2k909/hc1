"""Author Lowtide's quay crane in Blender, in map inches and (east, north, up).

rtk proxy "C:/Program Files/Blender Foundation/Blender 5.1/blender.exe" -b --python Tools/lowtide_crane_blender.py

Exports an editable .blend and a compact mesh with bevelled, weighted corner
normals. The map generator consumes that mesh; Blender is only needed to reauthor.
"""
import gzip
import json
import math
from pathlib import Path

import bpy
from mathutils import Vector, Matrix

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "Sources/Lowtide/crane"
OUT.mkdir(parents=True, exist_ok=True)
RED = "lt_crane_red"
STEEL = "lt_crane_machined"
DARK = "lt_crane_oily"
GLASS = "lt_crane_glass"
TRIM = "lt_crane_trim"
GRATE = "lt_crane_grate"
materials = {}
bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)


def material(name, colour, rough=.5, metal=.0):
    m = bpy.data.materials.new(name)
    m.diffuse_color = (*colour, 1)
    m.use_nodes = True
    bs = m.node_tree.nodes.get("Principled BSDF")
    bs.inputs["Base Color"].default_value = (*colour, 1)
    bs.inputs["Roughness"].default_value = rough
    bs.inputs["Metallic"].default_value = metal
    materials[name] = m
    return m


material(RED, (.28, .065, .035), .48)
material(STEEL, (.18, .21, .23), .38, .9)
material(DARK, (.032, .039, .043), .48, .7)
material(GLASS, (.025, .069, .086), .19, .25)
material(TRIM, (.34, .33, .29), .45, .75)
material(GRATE, (.08, .09, .095), .67, .8)
source = bpy.data.images.load(str(OUT / "oxide_red_source.png"))
nodes = materials[RED].node_tree.nodes
tex = nodes.new("ShaderNodeTexImage")
tex.image = source
materials[RED].node_tree.links.new(tex.outputs["Color"], nodes.get("Principled BSDF").inputs["Base Color"])
objects = []


def mesh_object(name, vertices, faces, paint, bevel=0, smooth=False):
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(materials[paint])
    for p in mesh.polygons:
        p.use_smooth = smooth or bevel > 0
    if bevel:
        mod = obj.modifiers.new("Fabricated edge radius", "BEVEL")
        mod.width = bevel
        mod.segments = 2
        mod.limit_method = "ANGLE"
        mod.angle_limit = .8
        mod.harden_normals = True
        mod = obj.modifiers.new("Weighted steel normals", "WEIGHTED_NORMAL")
        mod.keep_sharp = True
        mod.weight = 50
    obj["paint"] = paint
    objects.append(obj)
    return obj


def box(name, centre, size, paint=RED, bevel=.08, axes=None):
    c = Vector(centre)
    h = Vector(size) / 2
    axes = Matrix.Identity(3) if axes is None else axes
    vertices = [c + axes @ Vector((sx*h.x, sy*h.y, sz*h.z))
                for sx, sy, sz in ((-1,-1,-1),(1,-1,-1),(1,1,-1),(-1,1,-1),
                                  (-1,-1,1),(1,-1,1),(1,1,1),(-1,1,1))]
    faces = [(3,2,1,0),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)]
    return mesh_object(name, vertices, faces, paint, min(bevel, min(size)*.24))


def basis(axis):
    w = Vector(axis).normalized()
    u = Vector((0,0,1)).cross(w)
    if u.length < .01:
        u = Vector((1,0,0))
    u.normalize()
    v = w.cross(u).normalized()
    return u, v, w


def beam(name, a, b, width, depth=None, paint=RED, bevel=.08):
    a, b = Vector(a), Vector(b)
    u, v, w = basis(b-a)
    return box(name, (a+b)/2, (width, depth or width, (b-a).length), paint, bevel,
               Matrix((u,v,w)).transposed())


def rod(name, a, b, radius, paint=STEEL, sides=12, bevel=.04):
    a, b = Vector(a), Vector(b)
    u, v, w = basis(b-a)
    vertices = [p + radius * (u*math.cos(t) + v*math.sin(t))
                for p in (a,b) for t in (2*math.pi*i/sides for i in range(sides))]
    faces = [tuple(reversed(range(sides))), tuple(range(sides, sides*2))]
    faces.extend((i,(i+1)%sides,(i+1)%sides+sides,i+sides) for i in range(sides))
    # Small fittings use smooth cylinders. Only large machined parts need a
    # geometric end bevel; keep the repeated crane inexpensive at map scale.
    edge = min(bevel,radius*.15) if radius >= 2 else 0
    obj = mesh_object(name, vertices, faces, paint, edge, smooth=True)
    if edge:
        obj.modifiers["Fabricated edge radius"].segments = 1
    obj.data.polygons[0].use_smooth = obj.data.polygons[1].use_smooth = False
    return obj


def bolt(name, centre, axis=(0,1,0), radius=.46, paint=STEEL):
    c, d = Vector(centre), Vector(axis).normalized()
    rod(name+" washer", c-d*.05, c+d*.09, radius*1.36, DARK, 12, .015)
    rod(name+" hex head", c+d*.07, c+d*.36, radius, paint, 6, .025)


def plate(name, outline, axis, thickness=.7, paint=RED):
    # Extruded planar polygon, authored in outward counterclockwise order.
    d = Vector(axis).normalized()*thickness/2
    pts = [Vector(p) for p in outline]
    if (pts[1]-pts[0]).cross(pts[2]-pts[0]).dot(d) < 0:
        pts.reverse()
    count = len(pts)
    vertices = [p+s*d for s in (-1,1) for p in pts]
    faces = [tuple(reversed(range(count))), tuple(range(count,count*2))]
    faces.extend((i,(i+1)%count,(i+1)%count+count,i+count) for i in range(count))
    return mesh_object(name, vertices, faces, paint, .065)


def ibeam(name, a, b, width, depth, flange=1.0, web=.75):
    a, b = Vector(a), Vector(b)
    u, v, w = basis(b-a)
    rot = Matrix((u,v,w)).transposed()
    centre = (a+b)/2
    length = (b-a).length
    for side in (-1,1):
        box(name+" flange", centre+v*side*(depth-flange)/2, (width,flange,length), RED,.1,rot)
    box(name+" web", centre, (web,depth-2*flange,length), RED,.08,rot)


def railing(name, a, b, height=39, posts=4):
    a,b = Vector(a),Vector(b)
    for k in range(posts):
        p = a+(b-a)*k/(posts-1)
        rod(name+" upright",p,p+Vector((0,0,height)),.67,RED,10)
        box(name+" post foot",p+Vector((0,0,.2)),(3.5,3.5,.4),DARK,.05)
    for z in (height/2,height):
        rod(name+" handrail",a+Vector((0,0,z)),b+Vector((0,0,z)),.64,RED,10)
    beam(name+" toe plate",a+Vector((0,0,2.5)),b+Vector((0,0,2.5)),.22,5,RED,.035)


# Rail bogies and portal: actual rolled sections, wheel flanges and bolted knees.
for x in (-70,70):
    for y in (-90,90):
        label = f"Portal {x} {y}"
        box(label+" bogie chassis",(x,y,13),(58,17,12),DARK,.8)
        box(label+" removable cover",(x,y,21),(55,18,2),RED,.22)
        for offset in (-20,20):
            xx=x+offset
            rod(label+" rail wheel",(xx,y-6.8,7.5),(xx,y+6.8,7.5),7.4,STEEL,24,.16)
            for side in (-1,1):
                rod(label+" wheel flange",(xx,y+side*6.1,7.5),(xx,y+side*7.1,7.5),8,DARK,24,.07)
                rod(label+" axle hub",(xx,y+side*7.1,7.5),(xx,y+side*8.5,7.5),2.5,STEEL,16,.1)
        box(label+" column shoe",(x,y,26),(20,18,8),RED,.4)
        ibeam(label+" rolled column",(x,y,30),(x,y,200),16,16,1.1,1)
        for z in (38,114,192):
            box(label+" splice plate",(x,y+8.15,z),(14,.7,11),RED,.1)
            for dx in (-4.5,4.5):
                for dz in (-3.2,3.2):
                    bolt(label+" splice",(x+dx,y+8.55,z+dz))
        # The heavy welded haunch tapers into the girder rather than forming a cube.
        for side in (-1,1):
            plate(label+" knee",[(x-side*7,y-8,177),(x-side*7,y-8,222),(x-side*29,y-8,222)],(0,-1,0),1.1)
        for dx in (-5.5,5.5):
            for dy in (-5.5,5.5):
                bolt(label+" shoe anchor",(x+dx,y+dy,30),(0,0,1),.66)

for y in (-90,90):
    ibeam("Portal cross girder",(-82,y,214),(82,y,214),20,28,1.4,1.2)
    # Keep the existing diagonals and the same gameplay opening.
    beam("Portal diagonal",(-70,y,39),(70,y,190),4,3.2,RED,.12)
    for x,z in ((-63,48),(63,180)):
        plate("Diagonal connection",[(x-9,y+3,z-8),(x+9,y+3,z-8),(x+9,y+3,z+8),(x-9,y+3,z+8)],(0,1,0),.6)
        for dx in (-4,4):
            bolt("Brace connection bolt",(x+dx,y+3.35,z))
for x in (-70,70):
    ibeam("Portal longitudinal girder",(x,-100,214),(x,100,214),20,28,1.4,1.2)
    beam("Portal side brace",(x,-90,42),(x,90,190),4,3.2,RED,.12)
    for y in (-54,0,54):
        box("Girder web stiffener",(x,y,214),(16,.55,25),RED,.08)

# Open maintenance deck and a recognisable two-piece slewing bearing.
box("Slew deck",(0,0,228),(151,190,2.2),DARK,.35)
for y in (-77,77):
    beam("Deck edge",(-76,y,231),(76,y,231),1.3,4,RED,.08)
for z,r,d in ((233,60,6),(239,57,3),(242,60,2)):
    rod("Slewing bearing race",(0,0,z-d/2),(0,0,z+d/2),r,DARK if z==239 else STEEL,64,.16)
for k in range(36):
    t=math.tau*k/36
    bolt("Bearing retaining bolt",(54*math.cos(t),54*math.sin(t),243.1),(0,0,1),.62)
for k in range(64):
    t=math.tau*k/64
    box("Slew gear tooth",(60*math.cos(t),60*math.sin(t),237),(2.5,2.4,2.5),STEEL,.07,
        Matrix.Rotation(t,3,"Z"))

# Shaped machinery house. Cladding is real geometry, with distinct edge radii.
box("Machinery house shell",(0,0,280),(116,152,74),RED,2.2)
box("House lower sill",(0,0,245),(121,162,4),DARK,.4)
box("Roof gutter",(0,0,319),(120,160,3),DARK,.55)
box("Shallow rounded roof",(0,0,321.5),(122,164,5),RED,1.7)
for side in (-1,1):
    x=side*58.7
    # A louver bank, access cover, and a smaller electrical cabinet on both sides.
    box("Louver surround",(x,-27,282),(1.5,55,48),DARK,.35)
    for k in range(12):
        box("Folded ventilation louvre",(x+side*.9,-27,261+k*3.55),(1.1,51,1.6),RED,.12,
            Matrix.Rotation(math.radians(-18)*side,3,"Y"))
    box("Engine access cover",(x,36,280),(1.4,55,63),RED,.45)
    for yy in (12,60):
        for zz in (252,280,308):
            bolt("Engine cover fastener",(x+side*.85,yy,zz),(side,0,0),.44,RED)
    rod("Cover handle",(x+side*1.7,47,276),(x+side*1.7,47,284),.38,STEEL,10)
    for yy in (44,48):
        rod("Handle stem",(x+side*.8,yy,276),(x+side*1.8,yy,276),.28,STEEL,8)
    box("Side rubbing strip",(side*60,0,249),(1,150,2.3),TRIM,.16)

# Rear service door, seams, hinges, handle and inset nameplate.
box("Rear service door recess",(-16,76.6,279),(34,1.7,65),DARK,.5)
box("Rear service door",(-16,77.6,279),(32,.9,63),RED,.5)
for z in (258,299):
    rod("Door hinge",(-31,78.5,z-2),(-31,78.5,z+2),.6,STEEL,10)
rod("Door lever",(-4,79,278),(-4,79,284),.42,STEEL,12)
box("Rear equipment panel",(27,77.4,282),(43,1.2,60),RED,.5)
for x in (8,46):
    for z in (255,280,309):
        bolt("Rear panel screw",(x,78.15,z),radius=.38,paint=RED)
box("Manufacturer plate",(27,78.2,299),(13,.25,5),TRIM,.1)
for x in (21.5,32.5):
    bolt("Plate screw",(x,78.4,299),radius=.16)
box("Rear panel bottom grille",(27,78.2,263),(32,.5,11),DARK,.2)
for k in range(4):
    box("Rear grille slat",(27,78.6,259+k*2.5),(30,.5,1.1),RED,.08)

# The operator cabin has actual glazing with steel mullions and a sloped front.
box("Cab floor",(0,-102,253),(62,47,6),DARK,.6)
box("Cab lower body",(0,-102,264),(60,45,20),RED,1.1)
box("Cab rear bulkhead",(0,-82,291),(59,2,58),RED,.4)
for x in (-29,29):
    box("Cab side glass",(x,-103,294),(1,39,39),GLASS,.16)
    for z in (274,314):
        box("Cab window rail",(x,-103,z),(2.6,43,2.5),RED,.22)
    for y in (-123,-83):
        beam("Cab window pillar",(x,y,271),(x,y,317),2.4,2.4,RED,.22)
    box("Window centre mullion",(x,-104,294),(2,1.5,38),RED,.12)
for x in (-15,15):
    box("Cab front glazing",(x,-123.7,294),(27,1,38),GLASS,.15)
for x in (-29,0,29):
    beam("Front mullion",(x,-124.5,273),(x,-120.5,317),1.8,2.2,RED,.15)
for z in (274,315):
    box("Front window sill",(0,-123.5,z),(62,3,2.4),RED,.2)
box("Cab canopy",(0,-103,320),(65,50,5),RED,1.1)
rod("Cab windscreen wiper",(14,-125,286),(-4,-125,307),.24,DARK,8)
rod("Cab wiper blade",(-8,-125.1,301),(7,-125.1,310),.35,DARK,8)

# Walkway deck strips preserve the big open area under the portal.
for x in (-68,68):
    box("Side catwalk grating",(x,1,246),(17,160,1.2),GRATE,.12)
    railing("Side access railing",(x*1.15,-76,247),(x*1.15,84,247),38,5)
box("Rear catwalk grating",(0,90,246),(156,20,1.2),GRATE,.12)
railing("Rear access railing",(-78,100,247),(78,100,247),38,5)
# Slim permanently mounted ladder on the outer rear column, complete with hooks.
for x in (-75,-63):
    rod("Ladder stile",(x,104,24),(x,104,288),.72,DARK,12)
for z in range(30,248,12):
    rod("Ladder rung",(-75,104,z),(-63,104,z),.58,STEEL,10)
for z in (53,130,202,245):
    for x in (-75,-63):
        beam("Ladder fixing",(x,96,z),(x,104,z),1.1,1.1,DARK,.08)

# Four legs of the A-frame, with flanges, pin bosses and cross-bracing.
head = Vector((0,0,560))
for x in (-40,40):
    for y in (-50,70):
        a=Vector((x,y,324))
        b=Vector((x*.3,0,560))
        ibeam("A-frame rolled leg",a,b,8,9,.65,.58)
        box("A-frame deck shoe",a+Vector((0,0,2)),(15,16,5),RED,.3)
        for dx in (-5,5):
            bolt("A-frame anchor",a+Vector((dx,4,5)),(0,0,1),.55)
        rod("A-frame head boss",b+Vector((-3,0,0)),b+Vector((3,0,0)),4.4,RED,20,.1)
        rod("A-frame head pin",b+Vector((-4,0,0)),b+Vector((4,0,0)),2,STEEL,16,.07)
for z in (405,481,545):
    f=(z-324)/236
    xx=40*(1-f)+12*f
    for y0 in (-50,70):
        yy=y0*(1-f)
        beam("A-frame cross tie",(-xx,yy,z),(xx,yy,z),2.2,2.8,RED,.09)
for k in range(3):
    za,zb=338+k*67,405+k*67
    fa,fb=(za-324)/236,(zb-324)/236
    xa,xb=40*(1-fa)+12*fa,40*(1-fb)+12*fb
    beam("A-frame diagonal",(-xa,-50*(1-fa),za),(xb,-50*(1-fb),zb),2,2,RED,.08)

# A four-chord lattice jib: side Warren trusses and transverse diagonals.
root,tip=Vector((0,-60,340)),Vector((0,-1140,860))
def section(t):
    p=root+(tip-root)*t
    width=17*(1-t)+7*t
    height=40*(1-t)+18*t
    return [p+Vector((sx*width,0,dz)) for sx,dz in ((-1,0),(1,0),(-1,-height),(1,-height))]
for k in range(4):
    a,b=section(0)[k],section(1)[k]
    beam("Jib main chord",a,b,4.2,4.2,RED,.2)
for k in range(14):
    a,b=section(k/14),section((k+1)/14)
    for i,j in ((0,2),(1,3)):
        beam("Jib side diagonal",a[i if k%2==0 else j],b[j if k%2==0 else i],1.9,1.9,RED,.08)
        beam("Jib transverse tie",a[i],a[j],1.7,1.7,RED,.06)
    for i,j in ((0,1),(2,3)):
        beam("Jib cross bar",a[i],a[j],1.6,1.6,RED,.07)
    beam("Jib under diagonal",a[2 if k%2==0 else 3],b[3 if k%2==0 else 2],1.6,1.6,RED,.07)
# Genuine paired suspension cables and boom pivot bearings.
for x in (-8,8):
    rod("Luffing wire",head+Vector((x,0,0)),tip+Vector((x*.6,0,9)),.65,DARK,8,0)
    rod("Cable socket",head+Vector((x,0,0)),head+Vector((x,-14,4)),1.5,STEEL,12,.1)
rod("Boom pivot shaft",(-23,-60,330),(23,-60,330),3.4,STEEL,24,.12)
for x in (-22,22):
    rod("Boom pivot bearing",(x-1.5,-60,330),(x+1.5,-60,330),6,RED,24,.16)

# Sheave cheek plates, hauling ropes and a hook instead of a square jib nose.
for x in (-9,9):
    box("Nose sheave cheek",(x,-1140,851),(1.7,31,30),RED,1)
rod("Nose sheave",(-7,-1140,851),(7,-1140,851),11,STEEL,32,.14)
rod("Sheave axle",(-11,-1140,851),(11,-1140,851),2.2,STEEL,20,.08)
for x in (-3.3,3.3):
    rod("Hoist wire",(x,-1149,846),(x,-1149,16),.46,DARK,8,0)
for x in (-5.8,5.8):
    box("Hook block cheek",(x,-1149,13),(1.4,18,22),RED,.8)
rod("Hook block sheave",(-5,-1149,17),(5,-1149,17),6.8,STEEL,24,.1)
rod("Hook swivel",(0,-1149,3),(0,-1149,-4),1.6,STEEL,16,.1)
hook=[Vector((0,-1149+5*math.sin(t),-7-5*math.cos(t))) for t in [i*math.pi*1.55/14 for i in range(15)]]
for a,b in zip(hook,hook[1:]):
    rod("Forged lifting hook",a,b,1.4,DARK,10,.04)

# Distinct cast counterweight slabs and the winch drum on the roof.
for x in (-10,10):
    beam("Counterweight suspension",head+Vector((x,0,0)),(x,130,520),5,5,RED,.15)
for z in (478,489,500,511):
    box("Counterweight slab",(0,130,z),(59,56,10),DARK,.6)
for x in (-23,23):
    box("Counterweight retaining strap",(x,158.5,497),(3,2,45),STEEL,.14)
rod("Luffing winch drum",(-20,45,336),(20,45,336),9,DARK,32,.2)
for x in (-21,21):
    rod("Winch end flange",(x-1,45,336),(x+1,45,336),11,RED,32,.15)
for x in range(-18,20,3):
    rod("Wound winch cable",(x-.6,45,336),(x+.6,45,336),9.3,STEEL,24,.06)

# Evaluate bevels and preserve the actual corner normals in the map interchange.
bpy.context.view_layer.update()
depsgraph=bpy.context.evaluated_depsgraph_get()
faces=[]
for obj in objects:
    ev=obj.evaluated_get(depsgraph)
    mesh=ev.to_mesh()
    paint=obj["paint"]
    for poly in mesh.polygons:
        points=[list(mesh.vertices[mesh.loops[i].vertex_index].co) for i in poly.loop_indices]
        normals=[list(mesh.corner_normals[i].vector) for i in poly.loop_indices]
        # Dominant-axis UV projection has consistent physical scale, with a stable
        # offset per component so repeated covers do not repeat the same paint chips.
        n=poly.normal
        dominant=max(range(3),key=lambda k:abs(n[k]))
        axes=[k for k in range(3) if k!=dominant]
        # A diagonal bevel can be nearly edge-on to an axis projection: use its
        # own orthogonal basis to retain non-degenerate tangents in Source 2.
        u,v,_=basis(n)
        tile=40.0 if paint==RED else 32.0
        shift=(sum(ord(c) for c in obj.name)%113)/113
        uv=[[(Vector(p).dot(u)/tile)+shift,(Vector(p).dot(v)/tile)+shift*.47] for p in points]
        faces.append([paint,points,normals,uv])
    ev.to_mesh_clear()
with gzip.open(OUT/"lowtide_quay_crane.mesh.json.gz","wt",encoding="utf8") as f:
    json.dump({"version":2,"units":"inches","axes":"east,north,up","faces":faces},f,separators=(",",":"))
# Add portable UVs to the editable source. The interchange already has final UVs.
for obj in objects:
    uv=obj.data.uv_layers.new(name="Steel inches")
    for poly in obj.data.polygons:
        u,v,_=basis(poly.normal)
        for i in poly.loop_indices:
            p=obj.data.vertices[obj.data.loops[i].vertex_index].co
            uv.data[i].uv=(p.dot(u)/40,p.dot(v)/40)
bpy.context.scene.unit_settings.system="IMPERIAL"
bpy.context.scene.unit_settings.scale_length=.0254
source.filepath="//oxide_red_source.png"
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/"lowtide_quay_crane.blend"))
triangles=sum(len(face[1])-2 for face in faces)
print(f"LOWTIDE CRANE: {len(objects)} editable parts, {len(faces)} polygons, {triangles} triangles")
