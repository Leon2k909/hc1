"""Render an unlit albedo-response study, not a native s&box screenshot.

Each pair uses the original atlas, identical UVs, camera, alpha cutoff and
sampled canopy colour. Only the accepted/trial detail response changes.
"""
import hashlib
import json
from pathlib import Path

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'output/belltower/quality/forest-detail-v1'
data = json.loads((OUT / 'calibration.json').read_text(encoding='utf-8'))
atlas = ROOT / 'Sources/Belltower/generated/forest-trees-v1.png'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def study_material(variant, candidate):
    material = bpy.data.materials.new('Original atlas albedo study')
    material.use_nodes = True
    nodes, links = material.node_tree.nodes, material.node_tree.links
    nodes.clear()

    def math(operation, a, b=None):
        node = nodes.new('ShaderNodeMath')
        node.operation = operation
        for index, value in enumerate((a, b)):
            if value is None:
                continue
            if isinstance(value, (int, float)):
                node.inputs[index].default_value = value
            else:
                links.new(value, node.inputs[index])
        return node.outputs[0]

    texture = nodes.new('ShaderNodeTexImage')
    texture.image = bpy.data.images.load(str(atlas), check_existing=True)
    texture.image.colorspace_settings.name = 'sRGB'
    texture.image.alpha_mode = 'STRAIGHT'
    texture.interpolation = 'Linear'
    texture.extension = 'CLIP'
    luma = nodes.new('ShaderNodeVectorMath')
    luma.operation = 'DOT_PRODUCT'
    luma.inputs[1].default_value = (.2126, .7152, .0722)
    links.new(texture.outputs['Color'], luma.inputs[0])
    luminance = luma.outputs['Value']
    if candidate:
        signal = math('MULTIPLY', luminance, luminance)
        fraction = math('DIVIDE', signal, math('ADD', signal, data['coefficients'][variant]))
        factor = math('ADD', .5125, math('MULTIPLY', 1.1375, fraction))
        chroma = nodes.new('ShaderNodeVectorMath')
        chroma.operation = 'DIVIDE'
        links.new(texture.outputs['Color'], chroma.inputs[0])
        links.new(math('MAXIMUM', luminance, .005), chroma.inputs[1])
        lower = nodes.new('ShaderNodeVectorMath')
        lower.operation = 'MAXIMUM'
        lower.inputs[1].default_value = (.2, .2, .2)
        links.new(chroma.outputs['Vector'], lower.inputs[0])
        upper = nodes.new('ShaderNodeVectorMath')
        upper.operation = 'MINIMUM'
        upper.inputs[1].default_value = (3, 3, 3)
        links.new(lower.outputs['Vector'], upper.inputs[0])
        confidence = math('MINIMUM', 1., math('MAXIMUM', 0., math('DIVIDE', math('SUBTRACT', texture.outputs['Alpha'], .65), .3)))
        confidence = math('MULTIPLY', math('MULTIPLY', confidence, confidence), math('SUBTRACT', 3., math('MULTIPLY', 2., confidence)))
        normalise = nodes.new('ShaderNodeVectorMath')
        normalise.operation = 'DIVIDE'
        links.new(upper.outputs['Vector'], normalise.inputs[0])
        normalise.inputs[1].default_value = data['chroma_means'][variant]
        strength = nodes.new('ShaderNodeMixRGB')
        links.new(math('MULTIPLY', confidence, data['chroma_strength']), strength.inputs[0])
        strength.inputs[1].default_value = (1, 1, 1, 1)
        links.new(normalise.outputs['Vector'], strength.inputs[2])
        detailed = nodes.new('ShaderNodeVectorMath')
        detailed.operation = 'MULTIPLY'
        links.new(factor, detailed.inputs[0])
        links.new(strength.outputs[0], detailed.inputs[1])
        factor = detailed.outputs['Vector']
    else:
        detail = math('MINIMUM', 2., math('MAXIMUM', .25, math('DIVIDE', luminance, .08)))
        factor = math('ADD', .35, math('MULTIPLY', .65, detail))
    canopy = nodes.new('ShaderNodeVectorMath')
    canopy.operation = 'MULTIPLY'
    canopy.inputs[0].default_value = data['preview_colour']['linear_rgb']
    links.new(factor, canopy.inputs[1])
    emission = nodes.new('ShaderNodeEmission')
    links.new(canopy.outputs['Vector'], emission.inputs['Color'])
    emission.inputs['Strength'].default_value = 1
    alpha = math('GREATER_THAN', texture.outputs['Alpha'], .35)
    transparent = nodes.new('ShaderNodeBsdfTransparent')
    mix = nodes.new('ShaderNodeMixShader')
    links.new(alpha, mix.inputs[0])
    links.new(transparent.outputs[0], mix.inputs[1])
    links.new(emission.outputs[0], mix.inputs[2])
    output = nodes.new('ShaderNodeOutputMaterial')
    links.new(mix.outputs[0], output.inputs['Surface'])
    return material


records = []
for variant in (0, 1, 3):
    for candidate in (False, True):
        bpy.ops.wm.read_factory_settings(use_empty=True)
        scene = bpy.context.scene
        scene.render.engine = 'CYCLES'
        scene.cycles.device = 'CPU'
        scene.cycles.samples = 8
        scene.cycles.seed = 1234
        scene.cycles.use_denoising = False
        scene.cycles.max_bounces = 2
        scene.render.threads_mode = 'FIXED'
        scene.render.threads = 2
        scene.render.resolution_x = 800
        scene.render.resolution_y = 800
        scene.render.resolution_percentage = 100
        scene.view_settings.view_transform = 'Standard'
        scene.view_settings.look = 'None'
        scene.view_settings.exposure = 0
        scene.view_settings.gamma = 1
        world = bpy.data.worlds.new('Neutral diagnostic background')
        world.use_nodes = True
        world.node_tree.nodes.get('Background').inputs[0].default_value = (.14, .14, .14, 1)
        world.node_tree.nodes.get('Background').inputs[1].default_value = 1
        scene.world = world
        u0, top, u1, bottom = data['rectangles'][variant]
        height = 4.
        width = height * (u1 - u0) / (bottom - top)
        vertices = [(-width / 2, 0, 0), (width / 2, 0, 0), (width / 2, 0, height), (-width / 2, 0, height)]
        mesh = bpy.data.meshes.new('Unchanged forest atlas card')
        mesh.from_pydata(vertices, [], [(0, 1, 2, 3)])
        uv = mesh.uv_layers.new(name='UVMap')
        for loop, coord in zip(uv.data, ((u0, 1 - bottom), (u1, 1 - bottom), (u1, 1 - top), (u0, 1 - top))):
            loop.uv = coord
        mesh.materials.append(study_material(variant, candidate))
        obj = bpy.data.objects.new('Atlas card', mesh)
        scene.collection.objects.link(obj)
        bpy.ops.object.camera_add(location=(0, -12, height / 2))
        camera = bpy.context.object
        target = Vector((0, 0, height / 2))
        camera.rotation_euler = (target - camera.location).to_track_quat('-Z', 'Y').to_euler()
        camera.data.type = 'ORTHO'
        camera.data.ortho_scale = max(width, height) * 1.08
        scene.camera = camera
        name = f'variant-{variant}-' + ('candidate' if candidate else 'baseline')
        scene.render.image_settings.file_format = 'PNG'
        scene.render.image_settings.color_mode = 'RGB'
        scene.render.filepath = str(OUT / (name + '.png'))
        bpy.ops.render.render(write_still=True)
        record = dict(name=name, variant=variant, candidate=candidate,
                      scope='Unlit source albedo-response study, not native lighting, BC7 or a game screenshot.',
                      image_sha256=sha(OUT / (name + '.png')), atlas_sha256=sha(atlas),
                      calibration_sha256=sha(OUT / 'calibration.json'), preview_source_sha256=sha(Path(__file__)),
                      camera_position=list(camera.location), camera_rotation=list(camera.rotation_euler),
                      ortho_scale=camera.data.ortho_scale, geometry=vertices,
                      size=[800, 800], view_transform='Standard', exposure=0,
                      engine='Cycles', blender=bpy.app.version_string, device='CPU', threads=2, samples=8)
        (OUT / (name + '.json')).write_text(json.dumps(record, indent=2) + '\n', encoding='utf-8')
        records.append(record)
        print('FOREST_DETAIL_REVIEW ' + name, flush=True)
(OUT / 'rendered-views.json').write_text(json.dumps(records, indent=2) + '\n', encoding='utf-8')
