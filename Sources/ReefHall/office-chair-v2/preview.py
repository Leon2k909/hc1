"""Offscreen Blender preview (not a game capture) of office-chair v1 and v2 side by side, same camera and light.
Run: blender -b --factory-startup --python Sources/ReefHall/office-chair-v2/preview.py -- <out.png>"""
import bpy, sys, math
from pathlib import Path
from mathutils import Vector
ROOT = Path(__file__).resolve().parents[3]
A = ROOT / 'Assets'
out = sys.argv[sys.argv.index('--') + 1]
bpy.ops.wm.read_factory_settings(use_empty=True)
MATS = {'v1': {'polymer': 'materials/reefhall/office-chair-v1/polymer', 'steel': 'materials/reefhall/office-chair-v1/steel',
               'rubber': 'materials/reefhall/office-chair-v1/rubber', 'upholstery': 'materials/reefhall/rh_pad_dark'},
        'v2': {p: f'materials/collider/chair-realism-v2/{p}' for p in ('cloth', 'welt', 'polymer', 'alloy', 'rubber', 'steel')}}


def vmat_values(path):
    text = (A / (path + '.vmat')).read_text()
    get = lambda key: next((l.split('"')[-2] for l in text.splitlines() if l.strip().startswith(key)), None)
    return get('TextureColor'), get('TextureRoughness'), get('TextureNormal'), get('g_flMetalness')


def material(name, path):
    mat = bpy.data.materials.new(name); mat.use_nodes = True
    nt = mat.node_tree; bsdf = nt.nodes['Principled BSDF']
    col, rough, nrm, metal = vmat_values(path)
    coord = nt.nodes.new('ShaderNodeTexCoord')
    def tex(spec, noncolor):
        if spec and spec.endswith(('.png', '.tga')) and (A / spec).exists():
            n = nt.nodes.new('ShaderNodeTexImage'); n.image = bpy.data.images.load(str(A / spec))
            if noncolor: n.image.colorspace_settings.name = 'Non-Color'
            nt.links.new(coord.outputs['UV'], n.inputs[0]); return n
        return None
    c = tex(col, False)
    if c: nt.links.new(c.outputs[0], bsdf.inputs['Base Color'])
    elif col: v = [float(x) for x in col.strip('[]').split()[:3]]; bsdf.inputs['Base Color'].default_value = (*v, 1)
    r = tex(rough, True)
    if r: nt.links.new(r.outputs[0], bsdf.inputs['Roughness'])
    elif rough: bsdf.inputs['Roughness'].default_value = float(rough.strip('[]').split()[0])
    n = tex(nrm, True)
    if n and 'default' not in nrm:
        nm = nt.nodes.new('ShaderNodeNormalMap'); nt.links.new(n.outputs[0], nm.inputs['Color']); nt.links.new(nm.outputs[0], bsdf.inputs['Normal'])
    bsdf.inputs['Metallic'].default_value = float(metal) if metal else (1.0 if any(k in name for k in ('steel', 'alloy')) else 0.0)
    return mat


for i, (ver, obj) in enumerate([('v1', 'models/maps/reefhall/office-chair-v1/office_chair.obj'),
                                ('v2', 'models/maps/reefhall/office-chair-v2/office_chair.obj')]):
    before = set(bpy.data.objects)
    bpy.ops.wm.obj_import(filepath=str(A / obj))
    for ob in set(bpy.data.objects) - before:
        for slot in ob.material_slots:
            key = slot.material.name.split('.')[0]
            slot.material = material(f'{ver}_{key}', MATS[ver][key])
        ob.data.transform(__import__('mathutils').Matrix.Scale(0.0254, 4))
        vs = [ob.matrix_world @ v.co for v in ob.data.vertices]  # bound_box is stale after data.transform
        cx = (min(v.x for v in vs) + max(v.x for v in vs))/2; cy = (min(v.y for v in vs) + max(v.y for v in vs))/2
        z0 = min(v.z for v in vs)
        ob.data.transform(__import__('mathutils').Matrix.Translation((-cx, -cy, -z0)))
        if ver == 'v1': ob.rotation_euler.z = math.pi / 2  # v1 was built facing -Y in the map; turn it to face +X like v2
        ob.location.x = 0; ob.location.y = -0.5 + 1.0 * i
sc = bpy.context.scene
sc.render.engine = 'CYCLES'; sc.cycles.samples = 24; sc.cycles.device = 'CPU'
sc.render.resolution_x = 1600; sc.render.resolution_y = 900
w = bpy.data.worlds.new('w'); sc.world = w; w.use_nodes = True; w.node_tree.nodes['Background'].inputs[1].default_value = .35
for loc, e in [((3, -2, 4), 600), ((-2, 3, 2.5), 200)]:
    l = bpy.data.objects.new('l', bpy.data.lights.new('l', 'AREA')); l.data.energy = e; l.data.size = 2
    l.location = loc; l.rotation_euler = (Vector((0, 0, .5)) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler(); sc.collection.objects.link(l)
floor = bpy.data.meshes.new('f'); floor.from_pydata([(-5, -5, 0), (5, -5, 0), (5, 5, 0), (-5, 5, 0)], [], [(0, 1, 2, 3)])
fo = bpy.data.objects.new('f', floor); sc.collection.objects.link(fo)
cam = bpy.data.objects.new('c', bpy.data.cameras.new('c')); cam.data.lens = 50; sc.collection.objects.link(cam); sc.camera = cam
cam.location = tuple(float(v) for v in (sys.argv[sys.argv.index('--') + 2].split(',') if len(sys.argv) > sys.argv.index('--') + 2 else (2.6, -1.3, 1.25))); cam.rotation_euler = (Vector((0, 0, .5)) - cam.location).to_track_quat('-Z', 'Y').to_euler()
sc.render.filepath = out
bpy.ops.render.render(write_still=True)
