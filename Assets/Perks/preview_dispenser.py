"""Render the five dispensers side by side: blender -b perk_dispenser.blend -P preview_dispenser.py

Colours match ZombiesRoundSystem.CreatePerkDispenser (cabinet) and ZombiesBuyStation.PerkColor (lamps).
"""
import bpy
from mathutils import Vector
from pathlib import Path

folder = Path(__file__).resolve().parent
# perk: (cabinet enamel, lamp glow)
PERKS = {
    'secondwind': ((.16,.30,.58), (.3,.6,1)),
    'irontonic': ((.60,.10,.09), (.85,.15,.15)),
    'boltsoda': ((.12,.40,.20), (.2,.85,.3)),
    'hotshot': ((.30,.09,.07), (.95,.65,.1)),
    'fleetfoot': ((.78,.38,.10), (1,.55,.15)),
}

def srgb(c): return tuple(x ** 2.2 for x in c) + (1,)

def material(name, colour=(1,1,1), texture=None, metallic=.1, roughness=.5, emit=None, emit_mask=None, strength=3):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    bsdf = nodes.get('Principled BSDF')
    bsdf.inputs['Base Color'].default_value = srgb(colour)
    bsdf.inputs['Metallic'].default_value = metallic
    bsdf.inputs['Roughness'].default_value = roughness
    base = None
    if texture:
        tex = nodes.new('ShaderNodeTexImage')
        tex.image = bpy.data.images.load(str(folder / texture))
        mix = nodes.new('ShaderNodeMix')
        mix.data_type, mix.blend_type = 'RGBA', 'MULTIPLY'
        mix.inputs['Factor'].default_value = 1
        links.new(tex.outputs['Color'], mix.inputs['A'])
        mix.inputs['B'].default_value = srgb(colour)
        base = mix.outputs['Result']
        links.new(base, bsdf.inputs['Base Color'])
    if emit is not None:
        bsdf.inputs['Emission Strength'].default_value = strength
        if emit_mask:
            mask = nodes.new('ShaderNodeTexImage')
            mask.image = bpy.data.images.load(str(folder / emit_mask))
            mask.image.colorspace_settings.name = 'Non-Color'
            mul = nodes.new('ShaderNodeMix')
            mul.data_type, mul.blend_type = 'RGBA', 'MULTIPLY'
            mul.inputs['Factor'].default_value = 1
            links.new(base, mul.inputs['A'])
            links.new(mask.outputs['Color'], mul.inputs['B'])
            links.new(mul.outputs['Result'], bsdf.inputs['Emission Color'])
        else:
            bsdf.inputs['Emission Color'].default_value = srgb(emit)
    return mat

parts = {g: bpy.data.objects['perk_' + g] for g in ('enamel', 'metal', 'dark', 'accent', 'card', 'sign')}
metal = material('metal', (.54,.53,.46), metallic=.55, roughness=.3)
dark = material('dark', (.055,.065,.058), roughness=.6)

for i, (perk, (cabinet, glow)) in enumerate(PERKS.items()):
    offset = Vector((0, (i - 2) * 80, 0))
    mats = {
        'enamel': material(perk + ' enamel', cabinet, 'aged_enamel_neutral.png', .25, .45),
        'metal': metal, 'dark': dark,
        'accent': material(perk + ' lamp', glow, emit=glow, strength=6),
        'card': material(perk + ' poster', texture=f'{perk}_poster.png', roughness=.85),
        'sign': material(perk + ' sign', texture=f'{perk}_sign.png', roughness=.3, emit=True, emit_mask=f'{perk}_sign_glow.png', strength=4),
    }
    for group, obj in parts.items():
        copy = obj.copy()
        copy.data = obj.data.copy()
        copy.location = obj.location + offset
        copy.data.materials.clear()
        copy.data.materials.append(mats[group])
        bpy.context.collection.objects.link(copy)
    bpy.ops.object.light_add(type='POINT', location=offset + Vector((30, 0, 73.6)))
    lamp = bpy.context.object
    lamp.data.color = glow
    lamp.data.energy = 30000
    lamp.data.shadow_soft_size = 4
for obj in parts.values():
    obj.hide_render = True

bpy.ops.mesh.primitive_plane_add(size=2000, location=(0, 0, 0))

def aim(obj, point): obj.rotation_euler = (Vector(point) - obj.location).to_track_quat('-Z', 'Y').to_euler()
bpy.ops.object.camera_add(location=(330, -120, 110))
camera = bpy.context.object
aim(camera, (0, 0, 50))
camera.data.lens = 38
bpy.context.scene.camera = camera
bpy.ops.object.light_add(type='AREA', location=(160, -120, 240))
key = bpy.context.object
key.data.energy, key.data.size = 60000, 200
aim(key, (0, 0, 40))
scene = bpy.context.scene
scene.world.color = (.02, .022, .025)
scene.render.engine = 'CYCLES'
scene.cycles.samples = 48
scene.view_settings.view_transform = 'AgX'
scene.render.resolution_x, scene.render.resolution_y = 1600, 900
scene.render.filepath = str(folder / 'perk_dispenser_preview.png')
bpy.ops.render.render(write_still=True)
