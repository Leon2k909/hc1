import json
from pathlib import Path
import re

root = Path(__file__).resolve().parents[4]
path = root/'Sources/Lowtide/construction/offline-status.json'
data = json.loads(path.read_text())
data['reduced_detail_candidates'] = 'Sources/Lowtide/construction/lod-status.json'
path.write_text(json.dumps(data, indent=2)+'\n')
path = root/'CLAUDE.md'
before = path.read_bytes()
text = before.decode('utf-8')
newline = '\r\n' if b'\r\n' in before else '\n'
note = '''- Offline construction detail levels (2026-10-15): Tools/lowtide_construction_lods.py prepares
  two geometry alternatives for the combined window/door candidate without altering the close
  version or live resources. The three affected models total 500,413 triangles at close detail,
  411,421 at level 1 and 381,861 at level 2 (17.8% and 23.7% less geometry). All unrelated triangle
  attributes are retained. Six component reproductions, 7,155 coverage/joint/clearance rays and
  556 protected live-file hashes pass. Eighteen matched CPU views cover 300/160/80-pixel features.
  Read Sources/Lowtide/construction/lod-status.json: these are profiling candidates, not configured
  native LODs. ModelDoc switches, temporal appearance and gameplay cost remain unverified. The
  warehouse halves are large aggregate models, so per-feature review sizes cannot be translated
  blindly into one distance threshold. Profile full detail before choosing switching/grouping.
'''.replace('\n', newline)
if '- Offline construction detail levels (2026-10-15):' not in text:
    match = re.search(r'(?m)^## Lowtide \([^\r\n]*\r?\n', text)
    assert match and path.read_bytes() == before
    updated = text[:match.end()]+note+text[match.end():]
    temporary = path.with_name(path.name+'.lowtide-lods.tmp')
    temporary.write_bytes(updated.encode('utf-8'))
    temporary.replace(path)
print('Recorded offline detail-level candidates and native limits')
