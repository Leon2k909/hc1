"""Update only the repaired street bollard bands in Lowtide's existing dressing meshes.

The geometry in these large OBJ files includes independently polished map details;
never regenerate the entire dressing model to change the band material.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MARK = b'# Lowtide street bollards: sealed smooth caps, pavement contact'
OLD = b'usemtl rw_white_paint\n'
NEW = b'usemtl lt_bollard_diffuser\n'


def patch(side):
    base = ROOT / 'Assets/models/maps/lowtide' / f'lowtide_dress_{side}'
    obj = base.with_suffix('.obj')
    data = obj.read_bytes()
    assert data.count(MARK) == 1
    head, tail = data.split(MARK)
    if NEW not in tail:
        assert tail.count(OLD) == 1
        obj.write_bytes(head + MARK + tail.replace(OLD, NEW))
    else:
        assert tail.count(NEW) == 1

    mtl = base.with_suffix('.mtl')
    text = mtl.read_text(encoding='utf-8')
    if 'newmtl lt_bollard_diffuser' not in text:
        mtl.write_text(text.rstrip('\n') + '\nnewmtl lt_bollard_diffuser\nKd 1 1 1\nd 1\n', encoding='utf-8')

    vmdl = base.with_suffix('.vmdl')
    text = vmdl.read_text(encoding='utf-8')
    remap = '{ from = "lt_bollard_diffuser.vmat" to = "materials/lowtide/lt_bollard_diffuser.vmat" },'
    if remap not in text:
        anchor = '{ from = "rw_white_paint.vmat" to = "materials/railhead/rw_white_paint.vmat" },'
        assert text.count(anchor) == 1
        text = text.replace(anchor, anchor + '\n\t\t\t\t\t\t\t\t' + remap)
        vmdl.write_text(text, encoding='utf-8')
    print(f'{side}: isolated luminous band remapped')


if __name__ == '__main__':
    patch('east')
    patch('west')
