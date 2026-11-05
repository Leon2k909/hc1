"""Adapt the guarded single-prop install workflow to the approved shop steps."""
from pathlib import Path
ROOT=Path(__file__).absolute().parents[3];HERE=Path(__file__).absolute().parent;OLD=ROOT/'Sources/Riverside/tower-roof-v1'
for name in ('prepare_install.py','install.py','finish_install.py'):
 s=(OLD/name).read_text()
 for a,b in [('tower-roof-v1','store-timber-steps-v1'),('tower_roof_v1','store_timber_steps_v1'),('legacy_roof','legacy_steps'),('dressing_without_roof','store_without_steps'),('riverside_dressing','riverside_store'),("'dressing.vmdl'","'store.vmdl'"),('dressing_vmdl_before','store_vmdl_before'),('Guard Tower Roofs','Store Timber Steps'),('Guard Tower Roof','Lucky Stop Timber Steps'),('roof.vmdl','steps.vmdl'),('4676,3156,468','5132,4364,236'),('1600,530,628','490,-235,0'),('0,-163.3007557660064,0','0,0,0'),('len(cut)==4','len(cut)==36'),('removed_triangles=4','removed_triangles=36'),('RemovedOldTriangles=4','RemovedOldTriangles=36'),('OnlyOriginalRoofRemoved','OnlyOriginalStepsRemoved'),('Roofs=1','StepSets=1'),('OriginalDressingModelDocPreserved','OriginalStoreModelDocPreserved')]:s=s.replace(a,b)
 (HERE/name).write_text(s)
