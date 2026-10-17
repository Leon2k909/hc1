"""Merge only new collider roots into Riverdale's saved editor scene; preserve all baked lighting."""
import json
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OLD = ROOT / 'Assets/scenes/maps/Riverdale/riverdale.scene'
STAGE = ROOT / 'output/riverdale/aaa/fix-stage/scenes/maps/Riverdale/riverdale.scene'
OUT = ROOT / 'output/riverdale/aaa/collision-merged.scene'

def main():
    old = json.loads(OLD.read_text(encoding='utf-8'))
    new = json.loads(STAGE.read_text(encoding='utf-8'))
    group_names = {'Pipe Solids', 'Yard Prop Solids'}
    roots = [g for g in new['GameObjects'] if g.get('Name') in group_names]
    assert len(roots)==2
    counts={g['Name']:len(g['Children']) for g in roots}
    assert counts['Pipe Solids']>10 and counts['Yard Prop Solids']>5, counts
    old['GameObjects'] = [g for g in old['GameObjects'] if g.get('Name') not in group_names] + roots
    world = next(g for g in old['GameObjects'] if g.get('Name') == 'Riverdale')
    count = 0
    for child in world['Children']:
        if not any(c.get('__type') == 'Sandbox.ModelRenderer' for c in child.get('Components', [])):
            continue
        if any(c.get('__type') == 'Facepunch.RiverdaleGratingStabilizer' for c in child['Components']):
            continue
        key = uuid.uuid5(uuid.UUID('5f1c9a72-8e34-4b6d-a2c7-91e0d4b36f85'), f"grating/fix/{child['__guid']}")
        child['Components'].append({'__type':'Facepunch.RiverdaleGratingStabilizer','__guid':str(key),'__enabled':True,'Flags':0})
        count += 1
    OUT.write_text(json.dumps(old, indent=2),encoding='utf-8')
    print(counts, f'grating components {count}', 'merged; saved GI/reflections preserved')

if __name__ == '__main__': main()
