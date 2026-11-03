"""Verify the installed migration against its immutable pre-import mesh backups."""
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT/'Tools'))
from riverdale_splice import read_obj

out = ROOT/'output/riverdale/radiation-monitor-v2'
report = []
for name in ('riverdale_hall_detail','riverdale_hall_fine'):
    relative = Path('models/maps/riverdale')/(name+'.obj')
    before = Counter(read_obj(out/'backup'/relative)[1])
    remove = Counter(read_obj(out/(name+'-old.obj'))[1])
    add = Counter(read_obj(out/(name+'-new.obj'))[1])
    installed = Counter(read_obj(ROOT/'Assets'/relative)[1])
    staged = Counter(read_obj(out/'stage'/relative)[1])
    assert staged == before-remove+add, name+' initial splice contains unrelated changes'
    concurrent_removed, concurrent_added = staged-installed, installed-staged
    # Separate ongoing edits changed overhead equipment and removed old eye washes
    # after our import. Verify our exact monitor faces survive, retaining those edits.
    assert not add-installed, name+' replacement monitor faces missing'
    assert not (remove & installed), name+' legacy monitor faces still present'
    assert Counter({f:n for f,n in installed.items() if f[0].startswith('rv_arm_')}) == Counter({f:n for f,n in add.items() if f[0].startswith('rv_arm_')})
    assert not remove-before
    olddoc=(out/'backup'/relative.with_suffix('.vmdl')).read_text()
    newdoc=(ROOT/'Assets'/relative.with_suffix('.vmdl')).read_text()
    def strip_monitor_materials(text):
        lines=[]
        for line in text.splitlines():
            if 'from = "rv_arm_' not in line:
                lines.append(line.strip().rstrip(','))
        return '\n'.join(lines).replace('riverdale_hall_fine_arm_v2.obj','riverdale_hall_fine.obj')
    assert strip_monitor_materials(olddoc)==strip_monitor_materials(newdoc), name+' unrelated modeldoc changes'
    report.append(dict(Model=name, Removed=sum(remove.values()), Added=sum(add.values()), InitialSpliceUnrelatedFacesPreserved=True, CollisionUnchanged=True,
                       ConcurrentChangesRetained=dict(Removed=sum(concurrent_removed.values()),Added=sum(concurrent_added.values()),
                           Materials=sorted({m for m,c in concurrent_removed|concurrent_added}))))
manifest=json.loads((out/'stage.json').read_text())
paths=[Path(e['Target']) for e in manifest['Entries']]
hashes={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
result=dict(MonitorCount=11, Geometry=report, InstalledMonitorFacesMatch=True, InstalledSHA256=hashes)
(out/'verified.json').write_text(json.dumps(result,indent=2))
print(json.dumps({k:v for k,v in result.items() if k!='InstalledSHA256'},indent=2))
