"""Adapt the proven scoped installer to this console's approved transform and materials."""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
s=(ROOT/'Sources/Collider/monitor-trial-v1/install_accepted.py').read_text()
for old,new in (
    ('approved monitor','approved console'),('collider_monitor as CM','collider_console as CM'),
    ('collider-monitor-accepted-20261029','collider-console-accepted-20261030'),
    ('monitor-trial-v1','console-trial-v1'),('Monitor already installed','Console already installed'),
    ('len(removed)==26','len(removed)==688'),('count-26+','count-688+'),
    ('Accepted control-room monitor','Accepted control console'),('collider_approved_monitor','collider_approved_console'),
    ("p.startswith('mm_')","p.startswith('cp_')"),('len(remaps)==7','len(remaps)==14'),
    ('.monitor-incoming','.console-incoming'),("'placementPlan':[1880.,-190.,381.]","'placementPlan':[1755.,-55.,256.]"),
    ("'removedOldTriangles':26","'removedOldTriangles':688"),
    ('Tools/collider_monitor.py; collider_map.monitor selected placement','Tools/collider_console.py; collider_map.control_desk selected console')):
    assert old in s,old;s=s.replace(old,new)
s=s.replace("    candidate=json.loads((Path(__file__).parent/'candidate.json').read_text())",
    "    candidate=json.loads((Path(__file__).parent/'candidate.json').read_text())\n"
    "    review=json.loads((Path(__file__).parent/'review.json').read_text())\n"
    "    for path,h in review['proposalSourceSHA256'].items():assert sha(ROOT/path)==h,path\n"
    "    assert candidate['models']['after']['meshSHA256']=='927da7b805e678c2e5ad53882540449f19d81ea2d88ba4b03718922d81d46af3'")
(Path(__file__).parent/'install_accepted.py').write_text(s)
print('Prepared guarded console installer.')
