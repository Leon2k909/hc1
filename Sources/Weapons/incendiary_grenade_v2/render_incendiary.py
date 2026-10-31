"""Matched Cycles renders of the old incendiary grenade and v2's exported files: same camera, light and exposure. Not engine screenshots.

blender -b --factory-startup -t 4 --python render_incendiary.py -- <project root> <work dir> <out dir> <width> <samples> <views> [old,new] [lod]
"""
import os
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import adapt  # noqa: E402

adapt.run(
    "render_smoke.py",
    [
        ("Weapons/Throwable/M18_Smoke_Grenade/smoke_grenade_v2", adapt.FOLDER),
        ("smoke_grenade_color.png", "incendiary_grenade_color.png"),
        ("smoke_grenade_rough.png", "incendiary_grenade_rough.png"),
        ("smoke_grenade_metal.png", "incendiary_grenade_metal.png"),
        ("smoke_grenade_normal.png", "incendiary_grenade_normal.png"),
        ('f"smoke_grenade_{g}_lod', 'f"incendiary_grenade_{g}_lod'),
        # The camera sees a plain backdrop, so a bright building isn't behind the grenade. The light is unchanged, for both models.
        (
            "bg.inputs[1].default_value = 0.8\nscene.world = world",
            "bg.inputs[1].default_value = 0.8\n"
            'seen = nt.nodes.new("ShaderNodeBackground")\n'
            "seen.inputs[0].default_value = (0.06, 0.062, 0.068, 1)\n"
            'path = nt.nodes.new("ShaderNodeLightPath")\n'
            'choose = nt.nodes.new("ShaderNodeMixShader")\n'
            'nt.links.new(path.outputs["Is Camera Ray"], choose.inputs[0])\n'
            "nt.links.new(bg.outputs[0], choose.inputs[1])\n"
            "nt.links.new(seen.outputs[0], choose.inputs[2])\n"
            'nt.links.new(choose.outputs[0], nt.nodes["World Output"].inputs[0])\n'
            "scene.world = world",
        ),
    ],
    os.path.abspath(__file__),
)
