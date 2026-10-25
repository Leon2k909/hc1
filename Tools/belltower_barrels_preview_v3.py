"""Offline construction review of the v3 casks beside the old one (Blender Cycles).

python Tools/belltower_barrels_preview_v3.py writes the review OBJ; then
blender -b --factory-startup --python Tools/belltower_barrels_preview_v3.py -- render
renders output/belltower/barrels-v3/preview/*.png. Materials are approximations of the vmats (the same scan and
textures with their tints), lit by two area lights under a pale sky. Not an engine capture.
"""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
FOLDER = ROOT / 'output/belltower/barrels-v3/preview'
ASSETS = ROOT / 'Assets'
# Plan positions: three casks as the market keeps them, a pair, and the old cask for comparison.
LAYOUT = [((-1873., 1475.), 13, 36), ((-1873., 1506.), 13, 36), ((-1906., 1487.), 13, 36),
          ((-1840., 1440.), 13, 36), ((-1812., 1446.), 13, 36)]
OLD = (-1930., 1450.)


def write():
    sys.path.insert(0, str(ROOT / 'Tools'))
    import map_kit as K
    import belltower_barrels_v3 as V3
    import belltower_detail as D
    model = K.Model()
    for centre, r, h in LAYOUT:
        V3.build(model, centre, 0, r, h)
    D.barrel(model, OLD, 0, 13, 36)
    FOLDER.mkdir(parents=True, exist_ok=True)
    K.write_obj(FOLDER / 'review.obj', model, 'belltower_west')
    print(model.triangle_count())


def render():
    import bpy
    from mathutils import Vector
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.engine = 'CYCLES'; scene.cycles.samples = 48; scene.cycles.use_denoising = True
    scene.render.threads_mode = 'FIXED'; scene.render.threads = 4
    scene.render.resolution_x = 1400; scene.render.resolution_y = 900
    scene.view_settings.view_transform = 'AgX'

    def texture(nodes, path, colour=False):
        n = nodes.new('ShaderNodeTexImage'); n.image = bpy.data.images.load(str(path), check_existing=True)
        if not colour: n.image.colorspace_settings.name = 'Non-Color'
        return n

    scan = ASSETS / 'materials/belltower/scans/brown_planks_03'
    sys.path.insert(0, str(ROOT / 'Tools'))
    import belltower_barrels_v3 as V3
    tints = {name: tint for name, (textures, tint, _) in V3.SOURCES.items() if textures is V3.SCAN}
    tints.update({'furniture_wood_dark': (.83, .73, .6), 'planks': (1.08, .97, .82), 'planks_dark': (.83, .73, .6)})

    def material(name):
        m = bpy.data.materials.new(name + '-review'); m.use_nodes = True
        nodes, links = m.node_tree.nodes, m.node_tree.links; s = nodes.get('Principled BSDF')
        if name in tints:
            tex = texture(nodes, str(scan) + '_diffuse_4k.png', True)
            tint = nodes.new('ShaderNodeMixRGB'); tint.blend_type = 'MULTIPLY'; tint.inputs[0].default_value = 1
            tint.inputs[2].default_value = (*tints[name], 1)
            links.new(tex.outputs['Color'], tint.inputs[1]); links.new(tint.outputs[0], s.inputs['Base Color'])
            nm = nodes.new('ShaderNodeNormalMap'); links.new(texture(nodes, str(scan) + '_nor_gl_4k.png').outputs[0], nm.inputs['Color'])
            links.new(nm.outputs[0], s.inputs['Normal'])
            links.new(texture(nodes, str(scan) + '_rough_4k.png').outputs[0], s.inputs['Roughness'])
        elif name == 'sh_hoop':
            links.new(texture(nodes, ASSETS / 'materials/stillhouse/sh_hoop_color.png', True).outputs[0], s.inputs['Base Color'])
            links.new(texture(nodes, ASSETS / 'materials/stillhouse/hoop_rough.png').outputs[0], s.inputs['Roughness'])
            s.inputs['Metallic'].default_value = .4
        elif name in V3.SOURCES:
            textures, tint, _ = V3.SOURCES[name]
            tex = texture(nodes, ASSETS / textures['TextureColor'], True)
            mix = nodes.new('ShaderNodeMixRGB'); mix.blend_type = 'MULTIPLY'; mix.inputs[0].default_value = 1
            mix.inputs[2].default_value = (*tint, 1)
            links.new(tex.outputs['Color'], mix.inputs[1]); links.new(mix.outputs[0], s.inputs['Base Color'])
            s.inputs['Roughness'].default_value = .85
        elif name == 'iron_black':
            links.new(texture(nodes, ASSETS / 'materials/buildings/iron_black_color.png', True).outputs[0], s.inputs['Base Color'])
            s.inputs['Roughness'].default_value = .6
        else:
            s.inputs['Base Color'].default_value = (.5, 0, .5, 1)
        return m

    def aim(o, p): o.rotation_euler = (Vector(p) - o.location).to_track_quat('-Z', 'Y').to_euler()

    bpy.ops.wm.obj_import(filepath=str(FOLDER / 'review.obj'), forward_axis='NEGATIVE_Z', up_axis='Y')
    objects = [o for o in scene.objects if o.type == 'MESH']
    made = {}
    for o in objects:
        o.scale = (.0254,) * 3
        for slot in o.material_slots:
            key = slot.material.name.split('.')[0]
            slot.material = made.setdefault(key, material(key))
    bpy.context.view_layer.update()
    points = [o.matrix_world @ Vector(p) for o in objects for p in o.bound_box]
    lo = Vector(tuple(min(p[k] for p in points) for k in range(3))); hi = Vector(tuple(max(p[k] for p in points) for k in range(3)))
    centre = (lo + hi) * .5
    bpy.ops.mesh.primitive_plane_add(size=60, location=(centre.x, centre.y, lo.z + .003))
    floor = bpy.data.materials.new('studio-floor'); floor.use_nodes = True
    floor.node_tree.nodes.get('Principled BSDF').inputs['Base Color'].default_value = (.16, .16, .17, 1)
    bpy.context.object.data.materials.append(floor)
    world = bpy.data.worlds.new('review-world'); world.use_nodes = True; scene.world = world
    world.node_tree.nodes.get('Background').inputs[0].default_value = (.55, .63, .78, 1)
    world.node_tree.nodes.get('Background').inputs[1].default_value = .6
    bpy.ops.object.light_add(type='SUN', location=centre + Vector((0, 0, 5)))
    sun = bpy.context.object; sun.data.energy = 3.5; sun.rotation_euler = (0.85, 0.2, 2.2)
    # Offsets from the group's centre in metres (Blender's x is the plan's -x after the OBJ import).
    views = {'eye': (Vector((1.6, -3.6, 1.15)), Vector((0, 0, -.05)), 38),
             'close': (Vector((-.2, -1.6, 1.0)), Vector((-.15, .1, -.1)), 45),
             'top': (Vector((.6, -1.4, 1.9)), Vector((0, .1, -.2)), 40)}
    which = sys.argv[sys.argv.index('--') + 2:] if len(sys.argv) > sys.argv.index('--') + 2 else list(views)
    for name in which:
        offset, target, lens = views[name]
        bpy.ops.object.camera_add(location=centre + offset)
        cam = bpy.context.object; cam.data.lens = lens; aim(cam, centre + target); scene.camera = cam
        scene.render.filepath = str(FOLDER / f'{name}.png'); bpy.ops.render.render(write_still=True)
        print('REVIEW ' + scene.render.filepath, flush=True)


if __name__ == '__main__':
    if '--' in sys.argv and sys.argv[sys.argv.index('--') + 1] == 'render':
        render()
    else:
        write()
