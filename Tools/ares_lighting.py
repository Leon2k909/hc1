"""Retain Ares's reviewed native indirect-light bake when regenerating its scene.

Rebake after changing facility geometry or lighting; this does not generate probe textures.
"""
import copy
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROFILE = ROOT / 'Sources/Rendering/photographic-look-v1/ares-indirect-light.json'


def apply_baked_lighting(scene):
    volume = json.loads(PROFILE.read_text(encoding='utf-8'))
    objects = scene['GameObjects']
    matches = [i for i, obj in enumerate(objects) if obj.get('__guid') == volume['__guid']]
    if matches:
        objects[matches[0]] = copy.deepcopy(volume)
    else:
        objects.append(copy.deepcopy(volume))
    return scene
