"""Record the latest confirmed single-view 1080p cascade revision without rewriting older samples."""
import argparse,hashlib,json,re
from collections import defaultdict
from datetime import datetime,timedelta,timezone
from pathlib import Path
import map_kit as K

REPORT=K.ROOT/'output/forestbase'
LOG=Path('C:/Program Files (x86)/Steam/steamapps/common/sbox/logs/sbox-dev.log')

def main(prefix='cascade',audit_key='cascadeGraphics1080pRuntime'):
    log=LOG.read_text(encoding='utf-8-sig')
    pattern=r'(\d{4}/\d\d/\d\d [\d:.]+)\s+\[Generic\] dev_perf over (\d+) frames, bots alive (\d+)-(\d+), players (\d+), bot LOD (\w+)\r?\n(.*?GcPause[^\r\n]*)'
    match=list(re.finditer(pattern,log,re.S))[-1]
    preceding=list(re.finditer(r'(\d{4}/\d\d/\d\d [\d:.]+)\s+\[Generic\] dev_perf: sampling[^\r\n]*',log[:match.start()]))[-1]
    def stamp(value):return datetime.strptime(value,'%Y/%m/%d %H:%M:%S.%f').replace(tzinfo=timezone(timedelta(hours=2))).astimezone(timezone.utc)
    start,end=stamp(preceding.group(1)),stamp(match.group(1))
    interval=log[preceding.start():match.start()]
    gpuFenceWarnings=interval.count('GPU fence wait exceeded 250ms')
    presentWarnings=interval.count('without a present event')
    captureNotices=interval.count('Forest Base perf camera:')
    numbers=re.search(r'frame ms: avg ([\d.]+).*?p50 ([\d.]+)\s+p95 ([\d.]+)\s+p99 ([\d.]+)\s+max ([\d.]+)',match.group())
    before=json.loads((REPORT/f'{prefix}-1080-runtime-context-before.json').read_text())
    after=json.loads((REPORT/f'{prefix}-1080-runtime-context-after.json').read_text())
    assert before['scene']==after['scene']=='forestbase'
    assert before['screen']==after['screen']=='1920,1080'
    assert before['modelErrors']==after['modelErrors']==0
    assert before['ssrVolumes']==after['ssrVolumes']==1
    assert datetime.fromisoformat(before['utc'].replace('Z','+00:00'))<=start<end<=datetime.fromisoformat(after['utc'].replace('Z','+00:00'))
    views=json.loads((REPORT/f'{prefix}-1080-viewport-state.json').read_text())
    assert any(v.get('views') and all(not x['Visible'] for x in v['views']) for v in views['sessionViews'] if v['name']=='forestbase')
    assert int(match.group(2))==600
    samples=json.loads((REPORT/f'{prefix}-1080-runtime-gpu.json').read_text(encoding='utf-8-sig'))
    overlap=[x for x in samples if start<=datetime.fromisoformat(x['utc'].replace('Z','+00:00'))<=end]
    assert overlap,'No overlapping GPU telemetry'
    groups=defaultdict(list)
    for x in overlap:groups[(x['process'],x['processId'],x['engine'])].append(x['utilizationPercent'])
    gpu=[dict(process=p,processId=pid,engine=engine,samples=len(values),minPercent=min(values),maxPercent=max(values)) for (p,pid,engine),values in groups.items()]
    frame=dict(zip(('average','p50','p95','p99','max'),map(float,numbers.groups())))
    timings={name:dict(averageMs=float(avg),maxMs=float(maximum)) for name,avg,maximum in re.findall(r'^\s+(\w+)\s+avg ([\d.]+)\s+max ([\d.]+)',match.group(),re.M)}
    report=dict(fromUtc=start.isoformat(),toUtc=end.isoformat(),frames=600,resolution=[1920,1080],
        botsAlive=[int(match.group(3)),int(match.group(4))],playersAlive=int(match.group(5)),botLod=match.group(6),
        frameMs=frame,averageFpsApprox=round(1000/frame['average'],2),engineTimings=timings,
        modelRenderersBefore=before['modelRenderers'],modelRenderersAfter=after['modelRenderers'],modelErrors=0,ssrVolumes=1,
        gpuFenceWaitWarnings=gpuFenceWarnings,presentEventWarnings=presentWarnings,
        captureNoticesDuringSample=captureNotices,
        diagnosticOnly=bool(gpuFenceWarnings or presentWarnings or captureNotices),
        gpuTelemetryWindowUtc=[overlap[0]['utc'],overlap[-1]['utc']],
        singleVisibleGameView=True,gpuOverlap=gpu,
        contextEvidence=[f'{prefix}-1080-runtime-context-before.json',f'{prefix}-1080-runtime-context-after.json'],
        viewportEvidence=f'{prefix}-1080-viewport-state.json',gpuEvidence=f'{prefix}-1080-runtime-gpu.json',
        imageEvidence=f'{prefix}-1080-runtime-yard.png',
        limitations=['One fixed yard view in the editor; not an unloaded multi-view standalone benchmark.','Local bots and one local player; no remote-client test.','Other GPU processes are recorded, not assumed absent.','The earlier two-visible-view diagnostic is excluded from this sample.'])
    sources=[K.ROOT/'Assets/scenes/maps/ForestBase/forestbase.scene',K.ROOT/'Assets/materials/forestbase/waterfall_froth_v2.png']
    sources += list((K.ROOT/'Assets/shaders').glob('forestbase_*.shader'))
    sources += list((K.ROOT/'Assets/models/maps/forestbase').glob('*.vmdl'))
    sources += list((K.ROOT/'Assets/models/maps/forestbase').glob('*.obj'))
    sources += list((K.ROOT/'Assets/materials/forestbase').glob('*.vmat'))
    sources += list((K.ROOT/'Assets/materials/forestbase/scans').glob('*.vmat'))
    for kind in ('fir','sapling'):
        for pattern in ('*.obj','*.vmdl','*.vmat','impostor*.png'):
            sources += list((K.ROOT/f'Assets/models/maps/forestbase/{kind}').glob(pattern))
    # Hash the model/material dependencies used by the complete backdrop,
    # including shared geometry grass, rather than only top-level model files.
    for folder in ('Assets/models/maps/forestbase','Assets/materials/forestbase','Assets/models/grass'):
        sources += [p for p in (K.ROOT/folder).rglob('*') if p.is_file() and p.suffix in ('.obj','.vmdl','.vmat','.png','.jpg')]
    sources += [K.ROOT/'Assets/shaders/hc1grass.shader']
    sources=sorted(set(sources))
    report['assetRevisionHashes']={str(p.relative_to(K.ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}
    (REPORT/f'{prefix}-1080-performance-log.txt').write_text(preceding.group()+'\n'+match.group()+'\n')
    (REPORT/f'{prefix}-1080-performance-audit.json').write_text(json.dumps(report,indent=2)+'\n')
    audit=json.loads((REPORT/'performance-audit.json').read_text())
    audit[audit_key]=report
    (REPORT/'performance-audit.json').write_text(json.dumps(audit,indent=2)+'\n')
    print(json.dumps(dict(frameMs=frame,fps=report['averageFpsApprox'],bots=report['botsAlive']),indent=2))

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--prefix',default='cascade')
    parser.add_argument('--key',default='cascadeGraphics1080pRuntime')
    args=parser.parse_args()
    main(args.prefix,args.key)
