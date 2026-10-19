"""Record the completed offline construction review without editor writes."""
import json
from pathlib import Path
import re

root = Path(__file__).resolve().parents[3]
path = root/'CLAUDE.md'
before = path.read_bytes()
text = before.decode('utf-8')
newline = '\r\n' if b'\r\n' in before else '\n'
note = '''- Offline combined construction set (2026-10-15): read Sources/Lowtide/construction/offline-status.json.
  Tools/lowtide_door_construction.py stages bevelled boards, tapered straps, fixed hinge brackets,
  pull handles and an open hasp staple for twelve closed door pairs on the four nearby sheds.
  Generated green/red colour pixels are unchanged; explicit UVs fit complete boards to the geometry.
  The doors add 39,988 triangles and no material slots. Exported coverage/clearance rays (18,568),
  two byte-identical regenerations and 556 protected live-file hashes pass. Exact face replacement
  preserves all other attributes, upper doors, open passages, thresholds, collision and scene data.
  CPU before/after views are offline construction previews; native compilation/visual/performance
  checks have not run. Sources/Lowtide/doors/construction-status.json records the evidence.
  The door and window candidates both change the east/west OBJ files. Do not copy both independent
  stages over each other: Tools/lowtide_construction_stage.py composes them into one verified set
  under output/lowtide/quality-pass/construction-integration (175,112 extra triangles overall).
  No canonical writer hook or live promotion is applied. Keep the user's offline restriction;
  native review and the separate foliage persistence work remain pending.
- Rejected offline brick relief (2026-10-15): Sources/Lowtide/brick/relief-status.json records the
  fitted-mortar-v4 experiment. Even with denser tracing, grazing views stretch bright mortar edges
  and rare first intersections are missed by up to 7.65 mm. Do not import it. Production brick,
  colour images and weathering remain intact; the research and comparisons are retained in output.
'''.replace('\n', newline)
if '- Offline combined construction set (2026-10-15):' not in text:
    match = re.search(r'(?m)^## Lowtide \([^\r\n]*\r?\n', text)
    assert match
    updated = text[:match.end()]+note+text[match.end():]
    assert path.read_bytes() == before, 'Project notes changed during edit'
    temporary = path.with_name(path.name+'.lowtide-offline.tmp')
    temporary.write_bytes(updated.encode('utf-8'))
    temporary.replace(path)
path = root/'Sources/Lowtide/windows/construction-status.json'
data = json.loads(path.read_text())
data['combined_integration_manifest'] = 'output/lowtide/quality-pass/construction-integration/manifest.json'
data['combined_integration_note'] = 'The shed-door candidate shares the east/west OBJ paths. Use the verified combined set after native acceptance; separate copies would overwrite each other.'
path.write_text(json.dumps(data, indent=2)+'\n')
print('Recorded offline construction handoff and rejected brick research')
