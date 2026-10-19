"""Add only the Lowtide floor handoff note, preserving concurrent documentation edits."""
from pathlib import Path

root=Path(__file__).resolve().parents[4]
path=root/'CLAUDE.md'
before=path.read_bytes()
newline=b'\r\n' if b'\r\n' in before else b'\n'
marker=b'## Lowtide (multiplayer map, `Tools/lowtide_map.py`)'+newline
note='''- Offline warehouse floor (2026-10-15): read `Sources/Lowtide/floor/floor-status.json`.
  `Tools/lowtide_warehouse_floor.py` stages a separate worn pine material for both mezzanines.
  Eight generated board scans remain unchanged; 25.4 cm boards run across the joists, with
  staggered ends and small nails on their 110-inch grid. Shallow grain normals, dry roughness,
  filtered joints and a muted tint replace the domestic-looking floor finish. The candidate
  remaps only the existing floorboards slot: no added triangles, collision or scene changes.
  Six matched CPU views, 100,000 layout samples, UV-derivative/mirror checks and 14 byte-identical
  regenerated files pass; 560 protected live files are unchanged. This is an offline candidate,
  not a native compilation or performance result. The staged VMDLs are review snapshots; after
  native acceptance apply only their material remap, preserving any later LOD/material changes.
  The canonical interior generator and warehouse DDGI bake still need integration after acceptance.
  Keep the user's offline restriction. This pass does not complete the overall visual goal.
'''.encode().replace(b'\n',newline)
assert before.count(marker)==1
if b'- Offline warehouse floor (2026-10-15)' not in before:
    temporary=path.with_name('.CLAUDE.lowtide-floor-note.tmp')
    assert not temporary.exists()
    temporary.write_bytes(before.replace(marker,marker+note,1))
    assert path.read_bytes()==before,'Documentation changed concurrently; review before replacing'
    temporary.replace(path)
print('Lowtide floor handoff recorded; other documentation preserved')
