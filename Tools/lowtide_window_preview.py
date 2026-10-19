"""Prepare or render an offline, matched-lighting window construction review.

Python creates the exact map-kit prototype. Blender renders its OBJ geometry
and writes an editable .blend. No editor or live asset writes are performed.
The room shader is represented by a neutral pane to isolate frame construction.
"""
import argparse
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'output/lowtide/quality-pass/window-construction/preview'


def prepare():
    import map_kit as K
    import lowtide_map as L
    import lowtide_masonry as M
    import lowtide_window_construction as W
    OUT.mkdir(parents=True, exist_ok=True)
    wall = K.Wall('e', (-58, 58), (0, 20), (0, 196), '-n')
    opening = wall.add(0, 44, 64, 150, 'glass_arch')
    common = K.Model()
    wall.build(common, 'brick', None, 'brick', None, None)
    L.courses(common, wall, L.EAST, (176,))
    M.sill(common, L, wall, opening)
    M.arch(common, L, wall, opening)
    old = K.Model().extend(common)
    L.window(old, wall, opening, L.EAST)
    new = K.Model()
    for paint, faces in old.polygons.items():
        if paint == L.EAST.frame:
            continue
        for i, (points, normal) in enumerate(faces):
            new.polygon(paint, points, normal, uv=old.polygon_uvs.get((paint, i)),
                        normals=old.polygon_normals.get((paint, i)))
    W.frame(new, L, wall, opening, L.EAST)
    W.validate_model(new)
    for label, model in (('before', old), ('candidate', new)):
        L.configure(model)
        K.write_obj(OUT / f'{label}.obj', model, 'lowtide_east')
    materials = {}
    for paint, resource in old.material_overrides.items():
        text = (K.ASSETS / resource).read_text()
        materials[paint] = dict(resource=resource,
                               inputs=dict(re.findall(r'^\s*(\w+)\s+"([^"\r\n]*)"', text, re.M)))
    (OUT / 'materials.json').write_text(json.dumps(materials, indent=2) + '\n')
    (OUT / 'scope.json').write_text(json.dumps(dict(
        purpose='Matched geometry comparison, not an in-engine lighting or glass preview',
        opening_inches=[44, 86], outer_wall_inches=[116, 196],
        before_triangles=old.triangle_count(), candidate_triangles=new.triangle_count(),
        room_shader='Neutral pane for construction visibility',
        texture_sources='Current production textures, read only'), indent=2) + '\n')
    print('Prepared exact before/candidate geometry for Blender')


def render():
    import bpy
    from mathutils import Vector
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    scene = bpy.context.scene
    scene.render.engine = 'CYCLES'
    scene.cycles.device = 'CPU'
    scene.cycles.samples = 32
    scene.cycles.use_denoising = True
    scene.render.threads_mode = 'FIXED'
    scene.render.threads = 6
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    scene.view_settings.view_transform = 'AgX'
    scene.view_settings.look = 'AgX - Medium High Contrast'
    scene.view_settings.exposure = 0
    scene.world.use_nodes = True
    scene.world.node_tree.nodes['Background'].inputs['Color'].default_value = (.39, .48, .63, 1)
    scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value = .45
    source = json.loads((OUT / 'materials.json').read_text())
    materials = {}

    def array(value, fallback):
        try: return [float(v) for v in value.strip('[]').split()]
        except (AttributeError, ValueError): return fallback

    def material(paint):
        if paint in materials:
            return materials[paint]
        m = bpy.data.materials.new(paint)
        m.use_nodes = True
        nodes, links = m.node_tree.nodes, m.node_tree.links
        bsdf = nodes.get('Principled BSDF')
        bsdf.inputs['Roughness'].default_value = .75
        params = source.get(paint, {}).get('inputs', {})
        if paint == 'rw_window_dark':
            bsdf.inputs['Base Color'].default_value = (.022, .041, .052, 1)
            bsdf.inputs['Roughness'].default_value = .24
            bsdf.inputs['Metallic'].default_value = .25
            materials[paint] = m
            return m
        uv = nodes.new('ShaderNodeTexCoord')
        scale = array(params.get('g_vBrickScale'), [1, 1, 0, 0])[:2]
        if 'g_flEnamelScale' in params:
            scale = [float(params['g_flEnamelScale'])] * 2
        mapping = nodes.new('ShaderNodeVectorMath')
        mapping.operation = 'MULTIPLY'
        mapping.inputs[1].default_value = (*scale, 1)
        links.new(uv.outputs['UV'], mapping.inputs[0])

        def texture(key, color_space):
            value = params.get(key)
            if not value or value.startswith('['):
                return None
            path = ROOT / 'Assets' / value
            if not path.exists():
                return None
            tex = nodes.new('ShaderNodeTexImage')
            tex.image = bpy.data.images.load(str(path), check_existing=True)
            tex.image.colorspace_settings.name = color_space
            tex.extension = 'REPEAT'
            links.new(mapping.outputs['Vector'], tex.inputs['Vector'])
            return tex

        color = texture('TextureColor', 'sRGB')
        if color:
            tint = array(params.get('g_flTintColor'), [1, 1, 1])[:3]
            if 'g_vEnamelTint' in params:
                tint = [v / .285 for v in array(params['g_vEnamelTint'], [1, 1, 1])[:3]]
            mix = nodes.new('ShaderNodeMixRGB')
            mix.blend_type = 'MULTIPLY'
            mix.inputs[0].default_value = 1
            mix.inputs[2].default_value = (*tint, 1)
            links.new(color.outputs['Color'], mix.inputs[1])
            links.new(mix.outputs['Color'], bsdf.inputs['Base Color'])
        else:
            c = array(params.get('TextureColor'), [.18, .14, .10])[:3]
            bsdf.inputs['Base Color'].default_value = (*c, 1)
        rough = texture('TextureRoughness', 'Non-Color')
        if rough:
            links.new(rough.outputs['Color'], bsdf.inputs['Roughness'])
        else:
            bsdf.inputs['Roughness'].default_value = array(params.get('TextureRoughness'), [.75])[0]
        normal = texture('TextureNormal', 'Non-Color')
        if normal:
            convert = nodes.new('ShaderNodeNormalMap')
            links.new(normal.outputs['Color'], convert.inputs['Color'])
            links.new(convert.outputs['Normal'], bsdf.inputs['Normal'])
        materials[paint] = m
        return m

    def obj(label):
        vertices, uvs, normals, faces, face_uvs, face_normals, paints = [], [], [], [], [], [], []
        active = None
        for line in (OUT / f'{label}.obj').read_text().splitlines():
            fields = line.split()
            if not fields: continue
            if fields[0] in ('v', 'vn'):
                x, y, z = map(float, fields[1:])
                # OBJ (-east, up, north) to Blender (east, north, up).
                value = (-x, z, y)
                if fields[0] == 'v': vertices.append(tuple(v * .0254 for v in value))
                else: normals.append(value)
            elif fields[0] == 'vt': uvs.append(tuple(map(float, fields[1:])))
            elif fields[0] == 'usemtl': active = fields[1]
            elif fields[0] == 'f':
                refs = [tuple(int(v) - 1 for v in p.split('/')) for p in fields[1:]]
                faces.append([p[0] for p in refs])
                face_uvs.append([uvs[p[1]] for p in refs])
                face_normals.extend(normals[p[2]] for p in refs)
                paints.append(active)
        mesh = bpy.data.meshes.new(label)
        mesh.from_pydata(vertices, [], faces)
        mesh.update()
        mesh.normals_split_custom_set(face_normals)
        layer = mesh.uv_layers.new(name='UVMap')
        slots = list(dict.fromkeys(paints))
        for paint in slots: mesh.materials.append(material(paint))
        for poly, coords, paint in zip(mesh.polygons, face_uvs, paints):
            poly.material_index = slots.index(paint)
            poly.use_smooth = True
            for i, uv in zip(poly.loop_indices, coords): layer.data[i].uv = uv
        model = bpy.data.objects.new(label, mesh)
        bpy.context.collection.objects.link(model)
        return model

    before, candidate = obj('before'), obj('candidate')
    sun_data = bpy.data.lights.new('Grazing daylight', 'SUN')
    sun_data.energy = 2.4
    sun_data.angle = .06
    sun = bpy.data.objects.new('Grazing daylight', sun_data)
    bpy.context.collection.objects.link(sun)
    sun.rotation_euler = Vector((.5, .6, -1)).to_track_quat('-Z', 'Y').to_euler()
    light_data = bpy.data.lights.new('Broad sky fill', 'AREA')
    light_data.energy = 180
    light_data.shape = 'DISK'
    light_data.size = 5
    light = bpy.data.objects.new('Broad sky fill', light_data)
    bpy.context.collection.objects.link(light)
    light.location = (-3, -4, 5)
    light.rotation_euler = (Vector((0, 0, 2.5)) - light.location).to_track_quat('-Z', 'Y').to_euler()
    camera_data = bpy.data.cameras.new('Construction review')
    camera = bpy.data.objects.new('Construction review', camera_data)
    bpy.context.collection.objects.link(camera)
    scene.camera = camera
    camera_data.type = 'ORTHO'
    views = {
        'oblique': dict(location=(3.0, -7, 3.4), target=(0, 0, 2.75), scale=3.75, size=(1100, 1100)),
        'head': dict(location=(1.8, -5, 4.1), target=(0, -.05, 3.35), scale=1.9, size=(1280, 900)),
        'joint': dict(location=(1.5, -3, 2.9), target=(.17, -.08, 2.63), scale=.75, size=(1000, 1000)),
    }
    for view, spec in views.items():
        camera.location = spec['location']
        camera.rotation_euler = (Vector(spec['target']) - camera.location).to_track_quat('-Z', 'Y').to_euler()
        camera_data.ortho_scale = spec['scale']
        scene.render.resolution_x, scene.render.resolution_y = spec['size']
        for label in ('before', 'candidate'):
            before.hide_render = label != 'before'
            candidate.hide_render = label != 'candidate'
            scene.render.filepath = str(OUT / f'{view}-{label}.png')
            bpy.ops.render.render(write_still=True)
    before.hide_render = before.hide_viewport = True
    candidate.hide_render = candidate.hide_viewport = False
    camera.location = views['oblique']['location']
    camera.rotation_euler = (Vector(views['oblique']['target']) - camera.location).to_track_quat('-Z', 'Y').to_euler()
    camera_data.ortho_scale = views['oblique']['scale']
    scene.render.resolution_x, scene.render.resolution_y = views['oblique']['size']
    scene['review_scope'] = 'Offline construction prototype. Lighting/glass are illustrative, not s&box validation.'
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT / 'window-construction.blend'))
    print('Completed six matched construction renders and editable blend')


if __name__ == '__main__':
    args = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else sys.argv[1:]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--render', action='store_true')
    parsed = parser.parse_args(args)
    render() if parsed.render else prepare()
