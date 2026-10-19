"""Append the accepted facade results, preserving unrelated subsystem notes."""
from pathlib import Path

path=Path('CLAUDE.md')
original=path.read_bytes()
newline='\r\n' if b'\r\n' in original else '\n'
text=original.decode('utf-8').replace('\r\n','\n')
marker='  - Facade profiles v1 (2026-10-15)'
if marker in text:
    print('Facade acceptance is already documented')
    raise SystemExit(0)
anchor='  - `belltower_interiors.py` replaces the hall\'s box furniture'
assert text.count(anchor)==1
addition='''  - Facade profiles v1 (2026-10-15) replaces box cornices and window heads with three profiled variants,
    bevels the surrounds, slopes the sills, varies some upper shutter angles, and divides wall coping into
    individual bevelled stones. Ground-floor shutters and original collision bounds are preserved.
    The centre now has 247,036 authored triangles; each half has 969,171. All 94 spot/reachability checks,
    35 detail-geometry cases, and convex-hull/physics comparisons passed. Only the three visible OBJ files changed.
    `Sources/Belltower/facades/manifest.json` records the accepted sources, checksums, compiled resources and six
    same-camera comparisons in `facades-v1-before/` and `facades-v1-saved/`. The scene file, v9 indirect lighting
    and v7 reflections are unchanged. Runtime performance has not been measured for this pass.
    `import-facades.cs.txt` verifies backups and hashes and can resume a checked partial import. A Git status scan
    temporarily denied replacement of an OBJ; it cleared naturally. Inspect the current hashes and locking process
    before retrying. `verify-facades.cs.txt` uses the off-editor `source-geometry.json` count report and validates
    loaded resources: this running engine's GetIndexCountForLod reports the first material's indices, not the total.
    The full source triangle totals are independently counted and tied to the imported OBJ hashes.
'''
updated=text.replace(anchor,addition+anchor)
assert path.read_bytes()==original, 'Notes changed during preparation; re-read before writing'
incoming=path.with_name('CLAUDE.md.facades-incoming')
incoming.write_bytes(updated.replace('\n',newline).encode('utf-8'))
incoming.replace(path)
print('Documented the accepted native facade pass')
