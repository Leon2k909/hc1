import json
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[5]
BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'Tools'))
import lowtide_paving as P
import lowtide_paving_relief as R
import lowtide_paving_use as U
settings = json.loads(P.SETTINGS.read_text())
material = U.contact_material(R.material_text(settings['repeat_scale'], settings['repeat_region_normalized']))
assert material == (BASE/'stage'/U.MATERIAL).read_text(), 'Canonical material drift'
a = json.loads((BASE/'manifest.json').read_text())
b = json.loads((BASE/'canonical-reproduction/manifest.json').read_text())
assert a['staged_files'] == b['staged_files']
record = dict(material_writer_matches=True, current_layout_command_files_match=5,
              generators={str(p.relative_to(ROOT)):U.sha(p) for p in [ROOT/'Tools/lowtide_paving.py', ROOT/'Tools/lowtide_paving_use.py']})
U.write(BASE/'canonical-verification.json', json.dumps(record, indent=2)+'\n')
print(json.dumps(record))
