"""Blender-side CC0 fir export: UV-preserving mesh LODs and transparent crowns."""
import json
import math
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector

ROOT = Path(__file__).resolve().parent.parent
ASSET = sys.argv[sys.argv.index('--') + 1]
KIND = 'fir' if ASSET == 'fir_tree_01' else 'sapling'
FOLDER = ROOT / f'Assets/models/maps/forestbase/{KIND}'
SPECS = json.loads((FOLDER / 'texture-specs.json').read_text())
SCENE = bpy.context.scene


def export(obj, filename):
    bpy.ops.object.select_all(action='DESELECT')
    obj.hide_set(False)
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.wm.obj_export(filepath=str(FOLDER / filename), export_selected_objects=True,
        apply_modifiers=True, export_materials=True, export_triangulated_mesh=True,
        global_scale=39.37007874, forward_axis='Z', up_axis='Y')
    # Reject a material-bound mesh without texture coordinates. Blender can
    # retain a Geometry Nodes UVMap as a generic vector attribute, which the
    # OBJ exporter does not recognize as a UV layer.
    lines = (FOLDER / filename).read_text().splitlines()
    if not any(line.startswith('vt ') for line in lines):
        raise ValueError(f'Export has no texture coordinates: {filename}')
    if any('//' in vertex or '/' not in vertex for line in lines if line.startswith('f ')
           for vertex in line.split()[1:]):
        raise ValueError(f'Export contains an untextured face: {filename}')
    mtl = (FOLDER / filename).with_suffix('.mtl')
    mtl.write_text('\n'.join(line for line in mtl.read_text().splitlines()
                             if not line.startswith('map_')) + '\n')


def bake_materials():
    # Bake source albedo, with real atlas alpha. Lighting is applied once by
    # the engine; baking directional lights here would lock their direction.
    for name, textures in SPECS.items():
        material = bpy.data.materials.get(f'{ASSET}_{name}')
        if material is None:
            raise ValueError(f'Missing source material: {ASSET}_{name}')
        material.use_nodes = True
        nodes = material.node_tree.nodes
        nodes.clear()
        links = material.node_tree.links
        output = nodes.new('ShaderNodeOutputMaterial')
        emission = nodes.new('ShaderNodeEmission')
        color = nodes.new('ShaderNodeTexImage')
        color.image = bpy.data.images.load(str(FOLDER / textures['Color']), check_existing=True)
        ao = nodes.new('ShaderNodeAmbientOcclusion')
        ao.inputs['Distance'].default_value = 1.4 if KIND == 'fir' else .15
        ao.samples = 16
        contrast = nodes.new('ShaderNodeMixRGB')
        contrast.blend_type = 'MULTIPLY'
        contrast.inputs[0].default_value = .65
        links.new(color.outputs['Color'], contrast.inputs[1])
        links.new(ao.outputs['Color'], contrast.inputs[2])
        links.new(contrast.outputs['Color'], emission.inputs['Color'])
        if 'Translucency' in textures:
            alpha = nodes.new('ShaderNodeTexImage')
            alpha.image = bpy.data.images.load(str(FOLDER / textures['Translucency']), check_existing=True)
            alpha.image.colorspace_settings.name = 'Non-Color'
            transparent = nodes.new('ShaderNodeBsdfTransparent')
            mix = nodes.new('ShaderNodeMixShader')
            links.new(alpha.outputs['Color'], mix.inputs[0])
            links.new(transparent.outputs[0], mix.inputs[1])
            links.new(emission.outputs[0], mix.inputs[2])
            links.new(mix.outputs[0], output.inputs['Surface'])
        else:
            links.new(emission.outputs[0], output.inputs['Surface'])


def cards(variant, center, height, width):
    verts, faces, indices = [], [], []
    # Three crossed cards keep the far crown visible from every azimuth.
    for angle, material in ((0, 0), (60, 1), (120, 1)):
        direction = Vector((math.cos(math.radians(angle)), math.sin(math.radians(angle)), 0))
        bottom = center - Vector((0, 0, height / 2))
        top = center + Vector((0, 0, height / 2))
        start = len(verts)
        verts += [bottom - direction * width / 2, bottom + direction * width / 2,
                  top + direction * width / 2, top - direction * width / 2]
        faces.append(tuple(start + i for i in range(4)))
        indices.append(material)
    mesh = bpy.data.meshes.new(f'{KIND}_{variant}_lod2')
    mesh.from_pydata(verts, [], faces)
    for angle in (0, 90):
        mesh.materials.append(bpy.data.materials.new(f'impostor_{variant}_{angle}'))
    uv = mesh.uv_layers.new(name='UVMap')
    for poly, index in zip(mesh.polygons, indices):
        poly.material_index = index
        for loop, coord in zip(poly.loop_indices, ((0, 0), (1, 0), (1, 1), (0, 1))):
            uv.data[loop].uv = coord
    obj = bpy.data.objects.new(mesh.name, mesh)
    SCENE.collection.objects.link(obj)
    export(obj, obj.name + '.obj')
    bpy.data.objects.remove(obj, do_unlink=True)
    bpy.data.meshes.remove(mesh)


originals = {variant: bpy.data.objects.get(f'{ASSET}_{variant}' + ('_LOD2' if KIND == 'fir' else ''))
             for variant in 'abc'}
if any(obj is None for obj in originals.values()):
    raise ValueError('Missing authored tree variant')
for obj in list(bpy.data.objects):
    if obj not in originals.values():
        data = obj.data
        bpy.data.objects.remove(obj, do_unlink=True)
        if isinstance(data, bpy.types.Mesh) and data.users == 0:
            bpy.data.meshes.remove(data)
for collection in bpy.data.collections:
    collection.hide_render = False
    collection.hide_viewport = False
for obj in originals.values():
    mesh = obj.data
    if not mesh.uv_layers:
        attribute = mesh.attributes.get('UVMap')
        if attribute is None or attribute.domain != 'CORNER' or attribute.data_type != 'FLOAT_VECTOR':
            raise ValueError(f'Missing convertible authored UV map: {obj.name}')
        values = np.empty((len(attribute.data), 3), dtype=np.float32)
        attribute.data.foreach_get('vector', values.ravel())
        if len(values) != len(mesh.loops) or not np.isfinite(values).all():
            raise ValueError(f'Invalid authored UV map: {obj.name}')
        mesh.attributes.remove(attribute)
        uv = mesh.uv_layers.new(name='UVMap')
        uv.data.foreach_set('uv', values[:, :2].copy().ravel())
        mesh.uv_layers.active = uv
        uv.active_render = True
        print(f'{obj.name}: converted {len(values)} corner UV vectors to an exportable UV layer', flush=True)
    obj.hide_set(False)
    obj.hide_viewport = False
    obj.hide_render = True
    obj.location = (0, 0, 0)
    # One source variant contains an empty slot. Give any faces in it the
    # bark scan explicitly so the game never falls back to an error material.
    for slot in obj.material_slots:
        if slot.material is None:
            slot.material = bpy.data.materials[f'{ASSET}_bark']

SCENE.render.engine = 'CYCLES'
SCENE.cycles.device = 'CPU'
SCENE.cycles.samples = 16
SCENE.cycles.transparent_max_bounces = 32
SCENE.render.resolution_x = 512
SCENE.render.resolution_y = 1024
SCENE.render.resolution_percentage = 100
SCENE.render.film_transparent = True
SCENE.render.image_settings.file_format = 'PNG'
SCENE.render.image_settings.color_mode = 'RGBA'
SCENE.view_settings.view_transform = 'Standard'
SCENE.view_settings.look = 'None'
SCENE.view_settings.exposure = 0
SCENE.view_settings.gamma = 1
camera_data = bpy.data.cameras.new('Impostor camera')
camera = bpy.data.objects.new('Impostor camera', camera_data)
SCENE.collection.objects.link(camera)
SCENE.camera = camera
camera_data.type = 'ORTHO'
camera_data.clip_end = 500
bake_materials()
statistics = []
for variant, original in originals.items():
    bpy.context.view_layer.update()
    original.data.calc_loop_triangles()
    source_triangles = len(original.data.loop_triangles)
    bounds = [original.matrix_world @ Vector(point) for point in original.bound_box]
    minimum = Vector(tuple(min(point[axis] for point in bounds) for axis in range(3)))
    maximum = Vector(tuple(max(point[axis] for point in bounds) for axis in range(3)))
    center = (minimum + maximum) / 2
    height = max((maximum.z - minimum.z) * 1.04, (maximum - minimum).xy.length * 2.05)
    width = height / 2
    camera_data.ortho_scale = height
    original.hide_render = False
    for angle in (0, 90):
        direction = Vector((math.sin(math.radians(angle)), -math.cos(math.radians(angle)), 0))
        camera.location = center + direction * 40
        camera.rotation_euler = (center - camera.location).to_track_quat('-Z', 'Y').to_euler()
        SCENE.render.filepath = str(FOLDER / f'impostor_{variant}_{angle}.png')
        bpy.ops.render.render(write_still=True)
    original.hide_render = True
    for lod, target in enumerate((55000, 22000) if KIND == 'fir' else (10000, 4000)):
        obj = original.copy()
        obj.data = original.data.copy()
        SCENE.collection.objects.link(obj)
        obj.name = f'{KIND}_{variant}_lod{lod}'
        obj.hide_render = True
        bpy.context.view_layer.objects.active = obj
        if source_triangles > target:
            mod = obj.modifiers.new('Game LOD', 'DECIMATE')
            mod.ratio = target / source_triangles
            mod.use_collapse_triangulate = True
            bpy.ops.object.modifier_apply(modifier=mod.name)
        obj.data.calc_loop_triangles()
        statistics.append(dict(name=obj.name, triangles=len(obj.data.loop_triangles), sourceTriangles=source_triangles,
                               uvLayers=[layer.name for layer in obj.data.uv_layers]))
        export(obj, obj.name + '.obj')
        data = obj.data
        bpy.data.objects.remove(obj, do_unlink=True)
        bpy.data.meshes.remove(data)
    cards(variant, center, height, width)
    statistics.append(dict(name=f'{KIND}_{variant}_lod2', triangles=6,
                           cardCenter=list(center), cardHeight=height, cardWidth=width))
    print(f'{ASSET} {variant}: exported mesh LODs and cutout crowns', flush=True)
(ROOT / f'output/forestbase/{KIND}-lods.json').write_text(json.dumps(statistics, indent=2))
