"""Save the sack detail handoff after current comparisons are recorded."""
from pathlib import Path
import json

root = Path(__file__).resolve().parents[4]
status = json.loads((root/'Sources/Lowtide/sacks/lod-status.json').read_text())
assert status['geometry']['lower_triangles_per_sack'] == {'1':818, '2':288}
assert not status['native_switching_configured']
path = root/'CLAUDE.md'
before = path.read_bytes()
newline = b'\r\n' if b'\r\n' in before else b'\n'
marker = b'## Lowtide (multiplayer map, `Tools/lowtide_map.py`)' + newline
note = '''- Offline sack detail candidates (2026-10-15): `Sources/Lowtide/sacks/lod-status.json` records
  818- and 288-triangle alternatives to the unchanged 1,570-triangle close sack. They retain the
  close body's positions, UVs and normals, with extra samples around its pinched corners. The
  medium mesh retains simplified closed seam shells to preserve their visible lines.
  All 528 exported reduced bodies are closed; nine CPU comparison sheets cover 320/160/80-pixel
  features and approximate mip filtering. Six staged model alternatives include their unchanged
  material libraries. These are geometry candidates, not configured native LODs or FPS results:
  the dressing/fleet models aggregate many props, so grouping, transitions and budgets still need
  native review. `Tools/lowtide_sack_lods.py` changes no live assets or canonical generator.
'''.encode().replace(b'\n', newline)
assert before.count(marker) == 1
if b'- Offline sack detail candidates (2026-10-15)' not in before:
    temporary = path.with_name('.CLAUDE.lowtide-sack-lods-note.tmp')
    assert not temporary.exists()
    temporary.write_bytes(before.replace(marker, marker+note, 1))
    assert path.read_bytes() == before, 'Documentation changed concurrently'
    temporary.replace(path)
print('Sack distance-detail handoff recorded')
