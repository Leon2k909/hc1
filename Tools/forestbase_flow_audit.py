"""Verify emitted falling-water geometry, unchanged physics and native scene checks."""
import argparse,hashlib,importlib.util,json,shutil
from datetime import datetime,timezone
from pathlib import Path
import numpy as np
import forestbase_map as current
from forestbase_cascade_audit import physics

ROOT=current.K.ROOT
REPORT=ROOT/'output/forestbase'
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def geometry():
    vertices=[];uvs=[];groups={};material=None
    for line in (ROOT/'Assets/models/maps/forestbase/vista.obj').read_text().splitlines():
        if line.startswith('v '):vertices.append([float(x) for x in line.split()[1:]])
        elif line.startswith('vt '):uvs.append([float(x) for x in line.split()[1:]])
        elif line.startswith('usemtl '):material=line.split()[1]
        elif line.startswith('f ') and material in {f'waterfall_{i}' for i in range(4)}:
            groups.setdefault(material,set()).update(tuple(int(x)-1 for x in item.split('/')[:2]) for item in line.split()[1:])
    assert len(groups)==4
    report=[]
    for material,indices in sorted(groups.items()):
        rows={}
        for vi,ti in indices:
            # OBJ axes are west, up, north. UV v indexes the authored falling rows.
            west,z,n=vertices[vi]
            rows.setdefault(uvs[ti][1],[]).append((west,z,n))
        ordered=[np.array(rows[v]) for v in sorted(rows)]
        north=np.array([row[:,2].mean() for row in ordered])
        height=np.array([row[:,1].mean() for row in ordered])
        assert len(ordered)==73
        assert np.max(np.diff(north))<=.002,'A jet bends back into the cliff'
        assert np.max(np.diff(height))<0,'A jet climbs against gravity'
        assert height[-1]<-255,'Jet does not reach below the opaque pool'
        assert all(np.ptp(row[:,2])<.002 for row in ordered)
        impactNorth=float(np.interp(-255,height[::-1],north[::-1]))
        east=np.array([-row[:,0].mean() for row in ordered])
        impactEast=float(np.interp(-255,height[::-1],east[::-1]))
        basinRadius=((impactEast-430)/540)**2+((impactNorth-3370)/450)**2
        assert basinRadius<.80,'A jet impacts outside the plunge basin interior'
        report.append(dict(material=material,rows=len(rows),uniqueVertices=len(indices),
            topHeight=height[0],bottomHeight=height[-1],maximumBacktrack=float(np.max(np.diff(north))),
            impactPlan=[impactEast,impactNorth,-255],basinRadiusSquared=basinRadius,
            widthRange=[min(np.ptp(row[:,0]) for row in ordered),max(np.ptp(row[:,0]) for row in ordered)]))
    return report
def main(prefix='flow'):
    spec=importlib.util.spec_from_file_location('pre_flow_physics',REPORT/'facade-before/forestbase_map.py')
    before=importlib.util.module_from_spec(spec);spec.loader.exec_module(before)
    old=physics(before.build(visual_chunks=[]));new=physics(current.build(visual_chunks=[]))
    assert old==new,'Backdrop change altered authored physics'
    qa=json.loads((REPORT/'engine-qa.json').read_text())
    if prefix=='turbulence':
        latest=max(p.stat().st_mtime for p in (ROOT/'Assets/models/maps/forestbase/vista.obj',
            ROOT/'Assets/shaders/forestbase_waterfall.shader',ROOT/'Assets/shaders/forestbase_mist.shader',
            ROOT/'Assets/shaders/forestbase_basin.shader'))
        assert (REPORT/'engine-qa.json').stat().st_mtime>latest,'Native QA predates the water revision'
    assert not qa['errors']
    spawns=[x for x in qa['results'] if x['kind'] in ('red','blue','dm')]
    boundaries=[x for x in qa['results'] if x['kind']=='boundary']
    vehicles=[x for x in qa['results'] if x['kind']=='vehicle-collision']
    assert len(spawns)==32 and all(x['floor'] and not x['blocked'] for x in spawns)
    assert len(boundaries)==6 and all(x['blocked'] for x in boundaries)
    assert len(vehicles)==4 and all(x['passed'] for x in vehicles)
    assert all(not x['visible'] for x in qa['exposure'])
    nav=json.loads((REPORT/'engine-nav.json').read_text())
    assert len(nav['results'])==24 and all(x['reachable'] and x['controllerClear'] and x['pathStatus']=='Complete' for x in nav['results'])
    assert len(nav['stairChecks'])==22 and all(x['clear'] for x in nav['stairChecks'])
    water=geometry()
    destination=REPORT/f'{prefix}-verified';destination.mkdir(exist_ok=True)
    paths=[REPORT/(v+'.png') for v in ('aerial','entrance','command','waterfall','waterfall-foot','gorge')]
    paths += [REPORT/p for p in ('engine-qa.json','engine-nav.json','layout.json')]
    paths += [ROOT/'Tools'/p for p in ('forestbase_cascade.py','forestbase_water.py','forestbase_map.py')]
    paths += [ROOT/'Tools/forestbase_flow_motion_audit.py',ROOT/'Editor/Hc1ForestBaseQa.cs']
    paths += [ROOT/'Assets/shaders'/p for p in ('forestbase_waterfall.shader','forestbase_mist.shader','forestbase_foam.shader','forestbase_cascade_rock.shader')]
    paths += list((ROOT/'Assets/materials/forestbase').glob('waterfall*.vmat'))
    if prefix in ('shore','turbulence'):
        paths += [ROOT/'Tools/forestbase_shore.py',ROOT/'Assets/shaders/forestbase_shore.shader']
        paths += list((ROOT/'Assets/materials/forestbase').glob('shore*.vmat'))
        paths += list((ROOT/'Assets/models/maps/forestbase').glob('shore*.vmdl'))
    if prefix=='turbulence':
        paths += [ROOT/'Assets/shaders/forestbase_basin.shader',ROOT/'Assets/materials/forestbase/plunge_basin.vmat']
    report=dict(createdUtc=datetime.now(timezone.utc).isoformat(),
        phase='Gravity-constrained falling jets, softer frayed flow and localized elliptical impact spray',
        engineQaUtc=datetime.fromtimestamp((REPORT/'engine-qa.json').stat().st_mtime,timezone.utc).isoformat(),
        physicsIdentical=True,collisionSha256=hashlib.sha256(json.dumps(new,sort_keys=True).encode()).hexdigest(),
        modelErrors=[],spawnChecks=32,boundarySamples=6,vehicleSamples=4,
        spawnExposureRays=sum(x['total'] for x in qa['exposure']),waterGeometry=water,
        nativeCompletePaths=24,stairDirections=22,
        navigationScope='Previous native navigation on identical authored collision.',
        limitations=['Visual fidelity and AAA finish remain incomplete.','Aerated water uses diffuse emission, not volumetric multiple scattering.','No physical fluid simulation or 10–15 remote-client verification.'])
    if prefix in ('shore','turbulence'):
        report['phase']='Scanned shoreline stones, smooth wet bank and sparse geometry-blade grass'
        report['shoreBoulders']=sum(x[0].startswith('Shore boulder') for x in current.INSTANCES)
        report['shoreGrassClumps']=sum(x[0].startswith('Shore grass') for x in current.INSTANCES)
        assert report['shoreBoulders']==6 and report['shoreGrassClumps']==24
        shore=json.loads((ROOT/'Assets/scenes/maps/ForestBase/forestbase.scene').read_text())
        forest=next(x for x in shore['GameObjects'] if x['Name']=='Forest Backdrop')
        assert all(len(x['Components'])==1 and x['Components'][0]['__type']=='Sandbox.ModelRenderer'
                   for x in forest['Children'] if x['Name'].startswith('Shore '))
        report['shoreHasNoColliderComponents']=True
    if prefix=='turbulence':
        report['phase']='Irregular wider jets, wispy impact mist and integrated rippled plunge water'
        material=(ROOT/'Assets/materials/forestbase/plunge_basin.vmat').read_text()
        import re
        centers=[(float(re.search(fr'ImpactEast{i} "([\d.-]+)"',material).group(1)),
                  float(re.search(fr'ImpactNorth{i} "([\d.-]+)"',material).group(1))) for i in range(4)]
        assert all(np.linalg.norm(np.array(center)-np.array(jet['impactPlan'][:2]))<2 for center,jet in zip(centers,water))
        report['basinImpactCentersMatchJets']=True
        report['assetRevisionHashes']={str(p.relative_to(ROOT)):sha(p) for p in (
            ROOT/'Assets/scenes/maps/ForestBase/forestbase.scene',ROOT/'Assets/models/maps/forestbase/vista.obj',
            ROOT/'Assets/models/maps/forestbase/vista.vmdl',ROOT/'Assets/materials/forestbase/plunge_basin.vmat',
            ROOT/'Assets/shaders/forestbase_basin.shader',ROOT/'Assets/shaders/forestbase_waterfall.shader',
            ROOT/'Assets/shaders/forestbase_mist.shader')}
    perfPath=REPORT/f'{prefix}-1080-performance-audit.json'
    if perfPath.exists():
        perf=json.loads(perfPath.read_text())
        assert all(sha(ROOT/path)==digest for path,digest in perf['assetRevisionHashes'].items()),'Stale performance evidence'
        report['runtimePerformance']=perf
        paths += list(REPORT.glob(f'{prefix}-1080-*'))
    motionPrefix=prefix if prefix=='turbulence' else 'flow'
    motionPath=REPORT/f'{motionPrefix}-motion-audit.json'
    if motionPath.exists():
        motion=json.loads(motionPath.read_text())
        assert motion['waterShaderSha256']==sha(ROOT/'Assets/shaders/forestbase_waterfall.shader'),'Stale motion evidence'
        report['waterMotion']=motion
        if prefix=='shore':report['waterMotionScope']='Earlier runtime captures verify animation of the unchanged jet shader; the new shore dressing is verified separately by current native images.'
        paths += [motionPath,REPORT/f'{motionPrefix}-runtime-captures.json']
        paths += [REPORT/f'{motionPrefix}-runtime-waterfall-{i}.png' for i in range(3)]
    for path in paths:shutil.copy2(path,destination/path.name)
    report['snapshotHashes']={p.name:sha(p) for p in destination.iterdir() if p.is_file()}
    (REPORT/f'{prefix}-integration-audit.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(physicsIdentical=True,waterGeometry=water,modelErrors=qa['errors']),indent=2))
if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--prefix',choices=('flow','shore','turbulence'),default='flow')
    args=parser.parse_args()
    main(args.prefix)
