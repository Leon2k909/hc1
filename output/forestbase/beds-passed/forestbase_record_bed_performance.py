"""Record the completed 1080p bedding-revision runtime sample without discarding history."""
import hashlib, json, re
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
import map_kit as K

REPORT=K.ROOT/'output/forestbase'
LOG=Path('C:/Program Files (x86)/Steam/steamapps/common/sbox/logs/sbox-dev.log')

def main():
    log=LOG.read_text(encoding='utf-8-sig')
    matches=list(re.finditer(r'(2026/10/09 [\d:.]+)\s+\[Generic\] dev_perf over (\d+) frames, bots alive (\d+)-(\d+), players (\d+), bot LOD (\w+)\r?\n(.*?GcPause[^\r\n]*)',log,re.S))
    match=matches[-1]
    preceding=list(re.finditer(r'(2026/10/09 [\d:.]+)\s+\[Generic\] dev_perf: sampling[^\r\n]*',log[:match.start()]))[-1]
    start=datetime.strptime(preceding.group(1),'%Y/%m/%d %H:%M:%S.%f').replace(tzinfo=timezone(timedelta(hours=2))).astimezone(timezone.utc)
    end=datetime.strptime(match.group(1),'%Y/%m/%d %H:%M:%S.%f').replace(tzinfo=timezone(timedelta(hours=2))).astimezone(timezone.utc)
    numbers=re.search(r'frame ms: avg ([\d.]+).*?p50 ([\d.]+)\s+p95 ([\d.]+)\s+p99 ([\d.]+)\s+max ([\d.]+)',match.group())
    timings={name:dict(averageMs=float(avg),maxMs=float(maximum)) for name,avg,maximum in re.findall(r'^\s+(\w+)\s+avg ([\d.]+)\s+max ([\d.]+)',match.group(),re.M)}
    before=json.loads((REPORT/'bed-1080-runtime-context-before.json').read_text())
    after=json.loads((REPORT/'bed-1080-runtime-context-after.json').read_text())
    assert before['scene']==after['scene']=='forestbase'
    assert before['screen']==after['screen']=='1920,1080'
    assert before['modelErrors']==after['modelErrors']==0
    assert before['ssrVolumes']==after['ssrVolumes']==1
    samples=json.loads((REPORT/'bed-1080-runtime-gpu.json').read_text(encoding='utf-8-sig'))
    overlap=[x for x in samples if start<=datetime.fromisoformat(x['utc'].replace('Z','+00:00'))<=end]
    groups=defaultdict(list)
    for x in overlap: groups[(x['process'],x['processId'],x['engine'])].append(x['utilizationPercent'])
    gpu=[dict(process=p,processId=pid,engine=engine,samples=len(values),minPercent=min(values),maxPercent=max(values))
         for (p,pid,engine),values in groups.items()]
    assert overlap,'Missing overlapping GPU telemetry'
    camera=[x for x in before['cameras'] if x['name']=='Forest Base performance camera'][0]
    report=dict(date='2026-10-09',fromUtc=start.isoformat(),toUtc=end.isoformat(),
        frames=int(match.group(2)),botsAlive=[int(match.group(3)),int(match.group(4))],playersAlive=int(match.group(5)),
        botLod=match.group(6),frameMs=dict(zip(('average','p50','p95','p99','max'),map(float,numbers.groups()))),
        engineTimings=timings,resolution=[1920,1080],camera=camera,
        modelRenderersBefore=before['modelRenderers'],modelRenderersAfter=after['modelRenderers'],
        modelErrors=0,ssrVolumes=1,gpuOverlap=gpu,
        logEvidence='bed-1080-performance-log.txt',contextEvidence=['bed-1080-runtime-context-before.json','bed-1080-runtime-context-after.json'],
        gpuEvidence='bed-1080-runtime-gpu.json',imageEvidence='bed-1080-runtime-view.png',
        limitations=['Local bots and one local player; not 10–15 remote clients.',
            'Other processes including SteelSeries and desktop compositor use GPU engines during this sample; not an unloaded baseline.',
            'Single fixed yard view, editor runtime, aged match with dynamic model count; not a fresh-load multi-view comparison.',
            'No GPU-isolated attribution of all frame cost to the map; current average remains below a 60 FPS target.'])
    assert report['frameMs']['average']==28.36,'The intended 1080p run is no longer the latest sample'
    (REPORT/'bed-1080-performance-log.txt').write_text(preceding.group()+'\n'+match.group()+'\n')
    audit=json.loads((REPORT/'performance-audit.json').read_text())
    audit['bedLightingGround1080pRuntime']=report
    (REPORT/'performance-audit.json').write_text(json.dumps(audit,indent=2)+'\n')
    (REPORT/'bed-1080-performance-audit.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(frameMs=report['frameMs'],bots=report['botsAlive'],gpuOverlap=[dict(process=x['process'],min=x['minPercent'],max=x['maxPercent']) for x in gpu]),indent=2))

if __name__=='__main__': main()
