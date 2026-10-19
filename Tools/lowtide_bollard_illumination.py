"""Install a unique lit band and low-intensity local light on Lowtide street bollards.

Only the repaired bollard geometry after its sentinel is modified; the original
white paint elsewhere in each large dressing mesh is left untouched.
"""
import json
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / 'Assets'
MARK = '# Lowtide street bollards: sealed smooth caps, pavement contact'
SOURCE = 'rw_white_paint'
TARGET = 'lt_bollard_diffuser'
STREET_E = range(1050, 2200, 160)


def patch_dressing(side):
    base = ASSETS / 'models/maps/lowtide' / f'lowtide_dress_{side}'
    obj = base.with_suffix('.obj')
    content = obj.read_text(encoding='utf-8')
    assert content.count(MARK) == 1, f'{obj}: bollard sentinel missing'
    head, tail = content.split(MARK)
    marker = f'usemtl {SOURCE}\n'
    replacement = f'usemtl {TARGET}\n'
    if tail.count(replacement) != 1:
        assert tail.count(marker) == 1, f'{obj}: expected one isolated bollard band'
        content = head + MARK + tail.replace(marker, replacement)
        obj.write_text(content, encoding='utf-8', newline='\n')

    mtl = base.with_suffix('.mtl')
    content = mtl.read_text(encoding='utf-8')
    if f'newmtl {TARGET}\n' not in content:
        content += f'newmtl {TARGET}\nKd 1 1 1\nd 1\n'
        mtl.write_text(content, encoding='utf-8', newline='\n')

    vmdl = base.with_suffix('.vmdl')
    content = vmdl.read_text(encoding='utf-8')
    remap = f'{{ from = "{TARGET}.vmat" to = "materials/lowtide/{TARGET}.vmat" }},'
    if remap not in content:
        anchor = '{ from = "rw_white_paint.vmat" to = "materials/railhead/rw_white_paint.vmat" },'
        assert content.count(anchor) == 1, f'{vmdl}: remap anchor not unique'
        content = content.replace(anchor, anchor + '\n\t\t\t\t\t\t\t\t' + remap)
        vmdl.write_text(content, encoding='utf-8', newline='\n')
    return str(obj)


def light_object(side, e):
    # map_kit's source coordinates: world X = north, world Y = -east.
    east = e if side == 'east' else -e
    name = f'Bollard diffuser {side} {e}'
    key = lambda what: str(uuid.uuid5(uuid.NAMESPACE_URL, f'lowtide/{name}/{what}'))
    return {
        '__guid': key('object'), '__version': 2, 'Flags': 0,
        'Name': name, 'Position': f'1193,{-east},38',
        'Rotation': '0,0,0,1', 'Scale': '1,1,1',
        'Tags': 'light_point,light', 'Enabled': True,
        'NetworkMode': 2, 'NetworkFlags': 0, 'NetworkOrphaned': 0,
        'NetworkTransmit': True, 'OwnerTransfer': 1,
        'Components': [{
            '__type': 'Sandbox.PointLight', '__guid': key('light'),
            '__enabled': True, 'Flags': 0, 'Attenuation': 1,
            'Contribution': 'Diffuse, Specular', 'FogMode': 'Disabled',
            'FogStrength': 0, 'LightColor': '0.4,0.43,0.5,1',
            'OnComponentDestroy': None, 'OnComponentDisabled': None,
            'OnComponentEnabled': None, 'OnComponentFixedUpdate': None,
            'OnComponentStart': None, 'OnComponentUpdate': None,
            'Radius': 48, 'ShadowBias': 0, 'ShadowHardness': 0,
            'Shadows': False,
        }], 'Children': []
    }


def patch_scene():
    scene = ASSETS / 'scenes/maps/Lowtide/lowtide.scene'
    content = scene.read_text(encoding='utf-8')
    existing = json.loads(content)
    previous = {obj.get('Name') for obj in existing['GameObjects']}
    lights = [light_object(side, e) for side in ('east', 'west') for e in STREET_E]
    missing = [obj for obj in lights if obj['Name'] not in previous]
    if missing:
        # Preserve formatting and unrelated editor-authored data in the scene.
        anchor = '  "GameObjects": [\n'
        assert content.count(anchor) == 1
        fragment = ''.join(json.dumps(obj, indent=2).replace('\n', '\n    ') + ',\n' for obj in missing)
        fragment = ''.join('    ' + line if i == 0 else line for i, line in enumerate(fragment.splitlines(keepends=True)))
        content = content.replace(anchor, anchor + fragment, 1)
        parsed = json.loads(content)
        assert len(parsed['GameObjects']) == len(existing['GameObjects']) + len(missing)
        scene.write_text(content, encoding='utf-8', newline='\n')
    return len(missing)


if __name__ == '__main__':
    for side in ('east', 'west'):
        print('Updated', patch_dressing(side))
    print('Added point lights:', patch_scene())
