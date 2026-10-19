"""Compose offline window and shed-door candidates without overwriting either.

Both candidates touch the east/west OBJ files. This builds one compatible set
outside Assets and verifies the exact combined triangle/UV/normal delta. It does
not import assets, update model definitions, or modify the canonical map writer.
"""
import gc
import json
from pathlib import Path

import map_kit as K
import lowtide_window_construction as W

BASE = K.ROOT/'output/lowtide/quality-pass'
WINDOW = BASE/'window-construction'
DOOR = BASE/'door-construction'
OUT = BASE/'construction-integration'


def main():
    window = json.loads((WINDOW/'manifest.json').read_text())
    door = json.loads((DOOR/'manifest.json').read_text())
    checks = json.loads((DOOR/'verification.json').read_text())
    assert checks['status'] == 'offline_mesh_checks_passed'
    assert checks['revision'] == door['revision']
    assert checks['manifest_sha256'] == W.sha(DOOR/'manifest.json'), 'Door verification is stale'
    assert W.sha(W.__file__) == window['generator_sha256']
    assert all(W.sha(K.ROOT/p) == h for p, h in door['generator_sources'].items())
    protected = {**window['protected'], **door['protected']}
    assert all(W.sha(K.ROOT/p) == h for p, h in protected.items()), 'Live files changed; inspect before composing'
    report = dict(status='offline_combined_candidate_native_review_pending', production_changed=False,
                  canonical_map_writer_integrated=False, models={}, changes={},
                  protected=protected, new_material_slots=0,
                  source_manifests={str(p.relative_to(K.ROOT).as_posix()): W.sha(p)
                                    for p in (WINDOW/'manifest.json', DOOR/'manifest.json')},
                  generator_sha256=W.sha(__file__))
    for relative, change in window['changes'].items():
        name = Path(relative).stem
        assert W.sha(K.ASSETS/relative) == change['before']
        original = WINDOW/'stage'/relative
        assert W.sha(original) == change['after']
        text = original.read_text()
        if relative in door['changes']:
            assert door['changes'][relative]['before'] == change['before']
            old = (DOOR/f'{name}-old.obj').read_text()
            new = (DOOR/f'{name}-new.obj').read_text()
            merged, removed = W.replace_faces(text, old, new)
            prefix, suffix = merged.rsplit(f'# {W.REVISION}\n', 1)
            merged = prefix+f'# {door["revision"]}\n'+suffix
            expected = W.face_keys(text, attributes=True)-W.face_keys(old, attributes=True)+W.face_keys(new, attributes=True)
            assert W.face_keys(merged, attributes=True) == expected, 'Combined attributes differ'
            total = sum(expected.values())
            assert removed == door['models'][name]['removed_triangles']
            del expected
            door_delta = door['models'][name]['added_triangles']-removed
        else:
            merged = text
            total = sum(W.face_keys(text).values())
            door_delta = 0
        w = window['models'][name]
        assert total == w['preserved_triangles']+w['added_triangles']+door_delta
        target = OUT/'stage'/relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(merged.encode())
        report['changes'][relative] = dict(before=change['before'], after=W.sha(target))
        report['models'][name] = dict(triangles=total, windows=w['windows'],
                                     detailed_windows=w['detailed'],
                                     shed_door_pairs=door['models'].get(name, {}).get('doors', 0),
                                     delta_triangles=w['added_triangles']-w['removed_triangles']+door_delta)
        print(f'Composed {name}: {total:,} triangles, exact attributes retained outside both changes', flush=True)
        del text, merged
        gc.collect()
    report['delta_triangles'] = sum(v['delta_triangles'] for v in report['models'].values())
    assert all(W.sha(K.ROOT/p) == h for p, h in protected.items())
    (OUT/'manifest.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps({k: v for k, v in report.items() if k not in ('protected', 'changes', 'source_manifests')}, indent=2))


if __name__ == '__main__':
    main()
