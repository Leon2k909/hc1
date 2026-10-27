"""Preserve native evidence and exact physics parity for the facade/forest revision."""
import hashlib,importlib.util,json,shutil
from datetime import datetime,timezone
from pathlib import Path
import forestbase_map as current
from forestbase_cascade_audit import physics

ROOT=current.K.ROOT
REPORT=ROOT/'output/forestbase'
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def main():
    spec=importlib.util.spec_from_file_location('pre_facade',REPORT/'facade-before/forestbase_map.py')
    before=importlib.util.module_from_spec(spec);spec.loader.exec_module(before)
    old=physics(before.build(visual_chunks=[]));new=physics(current.build(visual_chunks=[]))
    assert old==new,'Visual facade work changed authored collision'
    collisionSha=hashlib.sha256(json.dumps(new,sort_keys=True).encode()).hexdigest()
    qa=json.loads((REPORT/'engine-qa.json').read_text())
    assert not qa['errors']
    spawn=[x for x in qa['results'] if x['kind'] in ('red','blue','dm')]
    boundaries=[x for x in qa['results'] if x['kind']=='boundary']
    vehicles=[x for x in qa['results'] if x['kind']=='vehicle-collision']
    assert len(spawn)==32 and all(x['floor'] and not x['blocked'] for x in spawn)
    assert len(boundaries)==6 and all(x['blocked'] for x in boundaries)
    assert len(vehicles)==4 and all(x['passed'] for x in vehicles)
    assert all(not x['visible'] for x in qa['exposure'])
    nav=json.loads((REPORT/'engine-nav.json').read_text())
    assert len(nav['results'])==24 and all(x['reachable'] and x['controllerClear'] and x['pathStatus']=='Complete' for x in nav['results'])
    assert len(nav['stairChecks'])==22 and all(x['clear'] for x in nav['stairChecks'])
    for folder in ('fir','sapling'):
        for path in (ROOT/f'Assets/models/maps/forestbase/{folder}').glob('*.vmat'):
            assert 'TextureMetalness "[0 0 0 0]"' in path.read_text(),path
    assert not any('/pine/' in item[1] for item in current.INSTANCES)
    treeCounts={name:sum(item[0].startswith(prefix) for item in current.INSTANCES) for name,prefix in
                (('matureNear','Fir '),('young','Young fir'),('middle','Forest middle'),('far','Far fir'))}
    geometry=json.loads((REPORT/'distant-fir-geometry.json').read_text())
    assert all(x['uvLayers'] and x['triangles']<22000 for x in geometry)
    destination=REPORT/'facade-verified';destination.mkdir(exist_ok=True)
    paths=[REPORT/(v+'.png') for v in ('aerial','entrance','command','barracks','barracks-upper','catwalk','roof-detail','workshop','waterfall','waterfall-foot')]
    paths += [REPORT/p for p in ('engine-qa.json','engine-nav.json','layout.json','distant-fir-geometry.json')]
    paths += [ROOT/'Tools'/p for p in ('forestbase_map.py','forestbase_import_fir.py','forestbase_distant_fir_blender.py','forestbase_import_surfaces.py')]
    paths += [ROOT/'Assets/shaders/forestbase_facade.shader']
    perfPath=REPORT/'facade-1080-performance-audit.json'
    perf=None
    if perfPath.exists():
        perf=json.loads(perfPath.read_text())
        assert all(sha(ROOT/path)==digest for path,digest in perf['assetRevisionHashes'].items()),'Performance belongs to a different asset revision'
        paths += list(REPORT.glob('facade-1080-*'))
    for path in paths: shutil.copy2(path,destination/path.name)
    report=dict(createdUtc=datetime.now(timezone.utc).isoformat(),
        phase='Scanned neutral mineral facades, panel joints/anchors, dimensional denser forest and explicit dielectric inputs',
        engineQaUtc=datetime.fromtimestamp((REPORT/'engine-qa.json').stat().st_mtime,timezone.utc).isoformat(),
        nativeNavigationUtc=datetime.fromtimestamp((REPORT/'engine-nav.json').stat().st_mtime,timezone.utc).isoformat(),
        physicsIdentical=True,collisionSha256=collisionSha,modelErrors=[],spawnChecks=32,
        boundarySamples=6,vehicleSamples=4,spawnExposureRays=sum(x['total'] for x in qa['exposure']),
        nativeCompletePaths=24,stairDirections=22,treeCounts=treeCounts,distantTreeGeometry=geometry,
        navigationScope='Navigation was previously verified on identical authored collision; no geometry expansion of the playable area.',
        limitations=['Visual fidelity and AAA finish remain incomplete.','No 10–15 remote-client verification.','Performance is a single local editor view when attached.'],
        snapshotHashes={p.name:sha(p) for p in destination.iterdir() if p.is_file()})
    if perf: report['runtimePerformance']=perf
    (REPORT/'facade-integration-audit.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(physicsIdentical=True,trees=treeCounts,modelErrors=qa['errors']),indent=2))
if __name__=='__main__': main()
