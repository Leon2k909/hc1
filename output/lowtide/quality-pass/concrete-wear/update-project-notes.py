"""Record only this Lowtide candidate while preserving concurrent project notes."""
from pathlib import Path

root = Path(__file__).resolve().parents[4]
path = root / 'CLAUDE.md'
before = path.read_bytes()
newline = b'\r\n' if b'\r\n' in before else b'\n'
marker = b'## Lowtide (multiplayer map, `Tools/lowtide_map.py`)' + newline
note = '''- Offline warehouse concrete use (2026-10-15): read `Sources/Lowtide/concrete/wear-status.json`.
  `Tools/lowtide_concrete_wear.py` stages collision-aware dust, short rubber deposits and traffic
  polishing for both ground floors. Twelve layout routes avoid the saved cargo/column footprints;
  colour images, geometry, collision and live resources remain unchanged. The v2 mask replaces
  the first review's continuous tire lines. Checks cover 3,474 route samples, 8,192 atlas samples,
  36 excluded-surface cases and 32 untouched floor cases. Eight files reproduce byte for byte,
  with 561 protected live files unchanged. The six CPU material views and two layout diagrams
  have been reviewed; this modest candidate still needs native shader, lighting, filtering and
  performance checks. `Tools/lowtide_material_stage.py` combines it with the timber floor in
  `output/lowtide/quality-pass/material-integration/manifest.json`: 20 files, four existing-slot
  remaps across two models. Independent VMDL copies overwrite each other; apply only the four
  remaps after native acceptance, preserving later model/LOD edits. Canonical generation and
  a refreshed warehouse DDGI bake remain pending. Keep the user's offline restriction.
'''.encode().replace(b'\n', newline)
assert before.count(marker) == 1
if b'- Offline warehouse concrete use (2026-10-15)' not in before:
    temporary = path.with_name('.CLAUDE.lowtide-concrete-note.tmp')
    assert not temporary.exists()
    temporary.write_bytes(before.replace(marker, marker + note, 1))
    assert path.read_bytes() == before, 'Documentation changed concurrently; review before replacing'
    temporary.replace(path)
print('Lowtide concrete handoff recorded; other documentation preserved')
