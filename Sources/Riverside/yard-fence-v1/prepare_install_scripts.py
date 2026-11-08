from pathlib import Path
ROOT=Path(__file__).absolute().parents[3];HERE=Path(__file__).absolute().parent;OLD=ROOT/'Sources/Riverside/tower-roof-v1'
for name in ('prepare_install.py','install.py','finish_install.py'):
 s=(OLD/name).read_text()
 for a,b in [('tower-roof-v1','yard-fence-v1'),('tower_roof_v1','yard_fence_v1'),('legacy_roof','legacy_fence'),('dressing_without_roof','dressing_without_fence'),('Guard Tower Roofs','West Yard Fences'),('Guard Tower Roof','West Yard Privacy Fence'),('roof.vmdl','fence.vmdl'),('4676,3156,468','11048,7648,1284'),('1600,530,628','960,1400,0'),('0,-163.3007557660064,0','0,90,0'),('len(cut)==4','len(cut)==1044'),('removed_triangles=4','removed_triangles=1044'),('RemovedOldTriangles=4','RemovedOldTriangles=1044'),('OnlyOriginalRoofRemoved','OnlyOriginalFenceRemoved'),('Roofs=1','Fences=1')]:s=s.replace(a,b)
 (HERE/name).write_text(s)
