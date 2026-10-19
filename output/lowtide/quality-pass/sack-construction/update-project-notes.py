"""Add the scoped cargo-sack candidate note after verification, preserving other edits."""
from pathlib import Path
import json

root = Path(__file__).resolve().parents[4]
status = json.loads((root/'Sources/Lowtide/sacks/construction-status.json').read_text())
assert status['evidence']['byte_identical_reproduced_components'] == 3
path = root/'CLAUDE.md'
before = path.read_bytes()
newline = b'\r\n' if b'\r\n' in before else b'\n'
marker = b'## Lowtide (multiplayer map, `Tools/lowtide_map.py`)' + newline
note = '''- Offline sewn cargo sacks (2026-10-15): read `Sources/Lowtide/sacks/construction-status.json`.
  The separate candidate in `Tools/lowtide_sack_construction.py` replaces 264 rounded-block sacks
  with pinched sewn ends, a side hem, local gathers and finer continuous cloth UVs. Existing jute
  pixels, cover bounds, collision, materials, placements and unrelated prop faces remain intact.
  All exported bodies/thread shells are closed with valid normals/UVs; three components reproduce
  byte for byte. Six matched CPU views are in `output/lowtide/quality-pass/sack-construction/final-preview`.
  The preview's local shadow adapter fixes a half-pixel depth mismatch; sloped-plane checks verify it.
  These three dressing/fleet OBJ copies do not overlap the other construction/material candidates.
  They add 382,800 triangles: native appearance, textile filtering and measured gameplay cost remain
  open, including whether distance reduction or instancing is required. No live import or canonical
  generator change is applied. Keep the offline restriction; native acceptance is still required.
'''.encode().replace(b'\n', newline)
assert before.count(marker) == 1
if b'- Offline sewn cargo sacks (2026-10-15)' not in before:
    temporary = path.with_name('.CLAUDE.lowtide-sacks-note.tmp')
    assert not temporary.exists()
    temporary.write_bytes(before.replace(marker, marker+note, 1))
    assert path.read_bytes() == before, 'Documentation changed concurrently'
    temporary.replace(path)
print('Lowtide sack handoff recorded; unrelated documentation preserved')
