"""Blender construction review of the actual staged sculpt meshes, not a game capture."""
import argparse
import math
from pathlib import Path
import sys
import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument('--revision', default='revision1')
parser.add_argument('--source-revision')
parser.add_argument('--lion-cache')
parser.add_argument('--only-lion', action='store_true')
args = parser.parse_args(sys.argv[sys.argv.index('--')+1:])
OUT = ROOT/'output/belltower/fountain-ornaments-v2'/args.revision/'construction-preview'
OUT.mkdir(parents=True, exist_ok=True)
SOURCE = ROOT/'output/belltower/fountain-ornaments-v2'/(args.source_revision or args.revision)/'stage/ornaments.obj'
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.render.engine = 'CYCLES'; scene.cycles.samples = 24; scene.cycles.use_denoising = True
scene.render.threads_mode = 'FIXED'; scene.render.threads = 2
scene.render.resolution_x = 960; scene.render.resolution_y = 960; scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = 'PNG'; scene.view_settings.view_transform = 'AgX'
scene.world = bpy.data.worlds.new('Soft sky'); scene.world.use_nodes = True
scene.world.node_tree.nodes['Background'].inputs[0].default_value = (.68, .76, .88, 1)
scene.world.node_tree.nodes['Background'].inputs[1].default_value = .55


def material(name, metal=0):
    mat = bpy.data.materials.new(name); mat.use_nodes = True
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    bsdf = nodes.get('Principled BSDF'); bsdf.inputs['Metallic'].default_value = metal
    for suffix, socket, noncolor in [('color', 'Base Color', False), ('rough', 'Roughness', True), ('normal', None, True)]:
        node = nodes.new('ShaderNodeTexImage')
        node.image = bpy.data.images.load(str(ROOT/f'Assets/materials/belltower/{name}_{suffix}.png'), check_existing=True)
        if noncolor: node.image.colorspace_settings.name = 'Non-Color'
        if socket: links.new(node.outputs['Color'], bsdf.inputs[socket])
        else:
            decode = nodes.new('ShaderNodeNormalMap'); decode.inputs['Strength'].default_value = .5
            links.new(node.outputs['Color'], decode.inputs['Color']); links.new(decode.outputs['Normal'], bsdf.inputs['Normal'])
    return mat


materials = {'fountain_limestone': material('fountain_limestone'), 'fountain_bronze': material('fountain_bronze', .8)}
positions = [None]; uvs = [None]; normals = [None]; faces = []; paints = []; loop_uvs = []; loop_normals = []; paint = None
for line in SOURCE.open():
    values = line.split()
    if not values: continue
    if values[0] == 'v':
        x, y, z = map(float, values[1:]); positions.append((z-130, x+27, y))
    elif values[0] == 'vt': uvs.append(tuple(map(float, values[1:3])))
    elif values[0] == 'vn':
        x, y, z = map(float, values[1:]); normals.append((z, x, y))
    elif values[0] == 'usemtl': paint = values[1]
    elif values[0] == 'f':
        indices = [list(map(int, value.split('/'))) for value in values[1:]]
        centre = [sum(positions[i[0]][k] for i in indices)/len(indices) for k in range(3)]
        if abs(centre[0]) > 16 or centre[1] > 1 or not (30 < centre[2] < 106): continue
        if args.lion_cache and centre[2] < 65 and paint == 'fountain_limestone': continue
        faces.append([i[0]-1 for i in indices]); paints.append(paint)
        loop_uvs.extend(uvs[i[1]] for i in indices); loop_normals.extend(normals[i[2]] for i in indices)
if args.lion_cache:
    import numpy as np
    with np.load(args.lion_cache) as sculpt:
        v, f, n = sculpt['vertices'], sculpt['faces'][:, [0, 2, 1]], sculpt['normals']
    offset = len(positions)-1
    positions.extend((float(x), -float(d), float(z)+47) for x, d, z in v)
    for face in f:
        faces.append((face+offset).tolist()); paints.append('fountain_limestone')
        loop_uvs.extend((float(v[i, 0])/48+.17, (float(v[i, 2])+47)/48+.29) for i in face)
        loop_normals.extend((float(n[i, 0]), -float(n[i, 1]), float(n[i, 2])) for i in face)
mesh = bpy.data.meshes.new('Actual staged ornament mesh'); mesh.from_pydata(positions[1:], [], faces); mesh.update()
obj = bpy.data.objects.new('Limestone carvings and bronze outlet', mesh); scene.collection.objects.link(obj)
slots = list(materials)
for paint in slots: mesh.materials.append(materials[paint])
for poly, paint in zip(mesh.polygons, paints): poly.material_index = slots.index(paint); poly.use_smooth = True
layer = mesh.uv_layers.new(name='Authored stone UVs')
for loop, uv in zip(layer.data, loop_uvs): loop.uv = uv
mesh.normals_split_custom_set(loop_normals)

bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 3, 68))
block = bpy.context.object; block.name = 'Review support stone'; block.dimensions = (48, 6, 86)
bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
block.data.materials.append(materials['fountain_limestone'])
bevel = block.modifiers.new('Soft stone edges', 'BEVEL'); bevel.width = .16; bevel.segments = 3

sun = bpy.data.lights.new('Afternoon sun', 'SUN'); sun.energy = 2.6; sun.angle = math.radians(6)
lamp = bpy.data.objects.new('Afternoon sun', sun); scene.collection.objects.link(lamp)
lamp.rotation_euler = Vector((-.65, .9, -1.15)).to_track_quat('-Z', 'Y').to_euler()
camera = bpy.data.cameras.new('Review lens'); cam = bpy.data.objects.new('Review lens', camera)
scene.collection.objects.link(cam); scene.camera = cam; camera.clip_end = 2000
for name, position, target, lens in [
    ('lion', (15, -83, 60), (0, -4, 47), 70),
    ('lily', (12, -66, 96), (0, -1, 88), 70),
]:
    if args.only_lion and name != 'lion': continue
    cam.location = position; cam.rotation_euler = (Vector(target)-cam.location).to_track_quat('-Z', 'Y').to_euler()
    camera.lens = lens; scene.render.filepath = str(OUT/(name+'.png'))
    bpy.ops.render.render(write_still=True)
    print('ORNAMENT_REVIEW '+name, flush=True)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'ornament-review.blend'))
