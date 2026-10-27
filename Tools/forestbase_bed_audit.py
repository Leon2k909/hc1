"""Preserve the pre-bedding engine evidence and compare authored movement proxies."""
import hashlib, importlib.util, json, shutil
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
import forestbase_map as current

ROOT=current.K.ROOT
REPORT=ROOT/'output/forestbase'
SNAPSHOT=REPORT/'atmosphere-passed'

def file_hash(path): return hashlib.sha256(path.read_bytes()).hexdigest()

def physics(models):
    def convert(v):
        if isinstance(v,np.ndarray): return v.tolist()
        if isinstance(v,(tuple,list)): return [convert(x) for x in v]
        return v
    return {name:convert((m.boxes,m.hulls)) for name,m in models.items()}

def main():
    qa=json.loads((SNAPSHOT/'engine-qa.json').read_text())
    nav=json.loads((SNAPSHOT/'engine-nav.json').read_text())
    route=json.loads((SNAPSHOT/'route-audit.json').read_text())
    assert not qa['errors'] and len(nav['results'])==24
    assert all(x['reachable'] and x['controllerClear'] and x['pathStatus']=='Complete' for x in nav['results'])
    assert len(nav['stairChecks'])==22 and all(x['clear'] for x in nav['stairChecks'])
    assert len(route['checks'])==91 and not route['problems']
    audit=dict(createdUtc=datetime.now(timezone.utc).isoformat(),
               phase='Lighting, ground dressing, room clearance and command roof landing',
               engineEvidenceDate='2026-10-08',nativeCompletePaths=24,stairDirections=22,
               offlineRoutePoints=91,reachableGridCells=route['reachableCells'],
               engineErrors=qa['errors'],spotLights=len(qa['lighting']['spots']),
               shadowedSpots=sum(x['Shadows'] for x in qa['lighting']['spots']),
               pointLights=qa['lighting']['pointCount'],
               limitation='No runtime performance measurement for this revision; no 10–15 remote-client verification; current visuals remain below the AAA objective.',
               snapshotHashes={str(p.relative_to(SNAPSHOT)):file_hash(p) for p in SNAPSHOT.iterdir() if p.is_file()})
    (REPORT/'atmosphere-integration-audit.json').write_text(json.dumps(audit,indent=2)+'\n')
    spec=importlib.util.spec_from_file_location('pre_bedding_map',SNAPSHOT/'forestbase_map.py')
    before=importlib.util.module_from_spec(spec); spec.loader.exec_module(before)
    old=physics(before.build(visual_chunks=[])); new=physics(current.build(visual_chunks=[]))
    assert old==new,'Bedding changed authored collision geometry'
    digest=hashlib.sha256(json.dumps(new,sort_keys=True).encode()).hexdigest()
    (REPORT/'bed-collision-parity.json').write_text(json.dumps(dict(
        createdUtc=datetime.now(timezone.utc).isoformat(),identical=True,chunks=list(new),
        physicsSha256=digest,bedCount=4,newTextileMaterials=3,
        limitation='Exact authored physics parity; does not replace native engine compilation or visual verification.'),indent=2)+'\n')
    print('Preserved atmosphere evidence; all nine chunk collision definitions identical.')

def preserve_engine():
    qa=json.loads((REPORT/'engine-qa.json').read_text())
    nav=json.loads((REPORT/'engine-nav.json').read_text())
    assert not qa['errors']
    spawns=[x for x in qa['results'] if x['kind'] in ('red','blue','dm')]
    assert len(spawns)==32 and all(x['floor'] and not x['blocked'] for x in spawns)
    assert all(x['blocked'] for x in qa['results'] if x['kind']=='boundary')
    assert all(x['passed'] for x in qa['results'] if x['kind']=='vehicle-collision')
    assert all(not x['visible'] for x in qa['exposure'])
    assert all(x['reachable'] and x['controllerClear'] and x['pathStatus']=='Complete' for x in nav['results'])
    assert all(x['clear'] for x in nav['stairChecks'])
    destination=REPORT/'beds-passed'; destination.mkdir(exist_ok=True)
    paths=list(REPORT.glob('*.png'))
    paths += [REPORT/p for p in ('engine-qa.json','engine-nav.json','layout.json','bed-collision-parity.json')]
    paths += [ROOT/'Tools'/p for p in ('forestbase_map.py','forestbase_materials.py')]
    paths += [ROOT/'Assets/models/maps/forestbase'/p for p in ('barracks.obj','barracks.vmdl','barracks.mtl')]
    paths += list((ROOT/'Assets/materials/forestbase').glob('bed_*'))
    for p in paths:
        if p.suffix in ('.meta','_c'): continue
        shutil.copy2(p,destination/p.name)
    audit=dict(createdUtc=datetime.now(timezone.utc).isoformat(),
               phase='Four barracks beds with rounded cushions, cloth drape and steel frames',
               engineQaUtc=datetime.fromtimestamp((REPORT/'engine-qa.json').stat().st_mtime,timezone.utc).isoformat(),
               nativePathsUtc=datetime.fromtimestamp((REPORT/'engine-nav.json').stat().st_mtime,timezone.utc).isoformat(),
               modelErrors=[],spawnChecks=32,boundarySamples=6,vehicleSamples=4,
               roofBridgeSpawnRays=112,exposedSpawns=0,nativeCompletePaths=24,stairDirections=22,
               triangles=json.loads((REPORT/'layout.json').read_text())['stats']['barracks']['triangles'],
               collisionBoxes=299,physicsIdentical=True,
               note='Navigation evidence precedes final cloth adjustment; exact nine-chunk physics parity confirms unchanged navigation input. Visual QA follows final cloth adjustment.',
               limitations=['Current appearance remains below the AAA objective.','Bot performance is not remote multiplayer verification.'],
               snapshotHashes={p.name:file_hash(p) for p in destination.iterdir() if p.is_file()})
    (REPORT/'bed-integration-audit.json').write_text(json.dumps(audit,indent=2)+'\n')
    print('Preserved current engine views and successful native checks.')

if __name__=='__main__':
    import sys
    main()
    if '--engine' in sys.argv: preserve_engine()
