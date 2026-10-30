"""Prepare the proven exact-scope installer for this approved machine-hall unit."""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
s=(ROOT/'Sources/Collider/console-trial-v1/install_accepted.py').read_text()
for old,new in (
    ('approved console','approved cooling unit'),('collider_console as CM','collider_cooling_unit as CM'),
    ('collider-console-accepted-20261030','collider-cooling-unit-accepted-20261030'),
    ('console-trial-v1','cooling-unit-trial-v1'),('Console already installed','Cooling unit already installed'),
    ('927da7b805e678c2e5ad53882540449f19d81ea2d88ba4b03718922d81d46af3','58810b5ef523d2f5c3f4f238e3ce28562c9550b06ba8f47b0400d07d3ce7f76f'),
    ('collider_structure','collider_machine'),('len(removed)==688','len(removed)==170'),('count-688+','count-170+'),
    ('Accepted control console','Accepted cooling unit'),('collider_approved_console','collider_approved_cooling_unit'),
    ("p.startswith('cp_')","p.startswith('cu_')"),('.console-incoming','.cooling-unit-incoming'),
    ("'placementPlan':[1755.,-55.,256.]","'placementPlan':[-1470.,1702.,20.]"),
    ("'removedOldTriangles':688","'removedOldTriangles':170"),
    ('structureTrianglesBefore','machineTrianglesBefore'),('structureTrianglesAfter','machineTrianglesAfter'),
    ('Tools/collider_console.py; collider_map.control_desk selected console','Tools/collider_cooling_unit.py; collider_map.cooling_unit selected placement')):
    assert old in s,old;s=s.replace(old,new)
s=s.replace("marker='PhysicsShapeList';assert new_doc[new_doc.index(marker):]==old_doc[old_doc.index(marker):]",
    "marker='PhysicsShapeList'\n    assert (marker in new_doc)==(marker in old_doc)\n    if marker in old_doc:assert new_doc[new_doc.index(marker):]==old_doc[old_doc.index(marker):]")
s=s.replace('from pathlib import Path',"import os\nfor key in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS'):os.environ[key]='1'\nimport psutil\nproc=psutil.Process();proc.nice(psutil.IDLE_PRIORITY_CLASS);proc.cpu_affinity(proc.cpu_affinity()[-2:])\nfrom pathlib import Path",1)
s=s.replace("print(json.dumps({k:v for k,v in result.items() if k!='removedFaceLines'}))",
    "print(json.dumps({k:v for k,v in result.items() if k not in ('removedFaceLines','protectedOtherFiles')}))")
(Path(__file__).parent/'install_accepted.py').write_text(s)
print('Prepared guarded cooling-unit installer.')
