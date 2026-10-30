"""Run sequential A/B measurements in the open Depot game view. No native calls during each sample."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import shutil
import sys
import time
import psutil

ROOT=Path.cwd()
sys.path.insert(0,str(ROOT/'Tools'))
from depot_performance import call, normalise
from photographic_look import engine_path

SOURCE=ROOT/'Sources/Depot/performance-v1'
OUTPUT=ROOT/'output/depot-performance-20261027'

def save(label,value):
    (OUTPUT/(label+'.json')).write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8')
    return value

def script(name,label):
    state=call('instance_status')
    target=Path(state['ExchangeDirectory'])/name
    target.parent.mkdir(parents=True,exist_ok=True)
    shutil.copyfile(SOURCE/name,target)
    return save(label,normalise(call('run_csharp',{'path':str(target)})))

def toggle(enabled,label):
    (SOURCE/'toggle.json').write_text(json.dumps({'enabled':enabled}),encoding='utf-8')
    return script('toggle.cs.txt',label)

def fingerprint():
    paths=list((ROOT/'Code').rglob('*.cs'))+list((ROOT/'Code').rglob('*.razor'))+list((ROOT/'Assets/shaders').glob('*.shader'))
    return {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}

def processes():
    result={}
    for proc in psutil.process_iter(['pid','name','cpu_times']):
        try:
            times=proc.info['cpu_times']
            result[str(proc.pid)]={'name':proc.info['name'],'seconds':times.user+times.system}
        except (psutil.NoSuchProcess,psutil.AccessDenied):
            pass
    return result

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prefix',default='paired')
    parser.add_argument('--warmup',type=int,default=3)
    parser.add_argument('--reverse',action='store_true')
    parser.add_argument('--views',nargs='+',choices=['pump','stair','upper'],default=['pump','stair','upper'])
    args=parser.parse_args()
    views=[('pump',{'position':'-1192,112,888.1','angles':'0,0,0'}),
           ('stair',{'position':'132,1060,888.1','angles':'0,-3,0'}),
           ('upper',{'position':'-16,-764,1056.1','angles':'12,90,0'})]
    results=[]
    try:
        for name,view in views:
            if name not in args.views: continue
            (SOURCE/'view.json').write_text(json.dumps(view),encoding='utf-8')
            script('move-view.cs.txt',name+'-fixed-position')
            for variant in (['after','before'] if args.reverse else ['before','after']):
                label=args.prefix+'-'+name+'-'+variant
                state=toggle(variant=='after',label+'-state')
                time.sleep(args.warmup)
                shot=call('camera_screenshot',{'width':1920,'height':1080,'includeUi':True})
                if isinstance(shot,str) and Path(shot).is_file():
                    shutil.copyfile(shot,OUTPUT/(label+'.png'))
                source_before=fingerprint()
                process_before=processes()
                log=engine_path()/'logs/sbox-dev.log'
                log_offset=log.stat().st_size
                started=time.monotonic()
                start=script('start-sample.cs.txt',label+'-start')
                print(json.dumps({'started':label,'state':state,'start':start}),flush=True)
                time.sleep(25)
                # Wait for the engine's own completion marker. Slow frames can make a fixed
                # wall-clock delay shorter than 900 frames; querying C# during that window
                # would contaminate the sample.
                deadline=started+100
                while True:
                    with log.open('rb') as log_file:
                        log_file.seek(log_offset)
                        sample_log=log_file.read().decode('utf-8',errors='replace')
                    if 'dev_perf over 900 frames' in sample_log:
                        break
                    if time.monotonic()>deadline:
                        raise RuntimeError('The engine did not complete 900 frames within 100 seconds.')
                    time.sleep(1)
                details=save(label+'-details',normalise(call('call_tools',{
                    'calls':[{'name':'perf_overview'},{'name':'perf_cpu','arguments':{'limit':80}},
                             {'name':'perf_gpu','arguments':{'limit':200}},{'name':'perf_rendering'}]})))
                if len(details.get('results',[]))!=4 or details.get('text'):
                    raise RuntimeError('Incomplete native performance detail for '+label)
                sample=script('read-sample.cs.txt',label)
                elapsed=time.monotonic()-started
                source_after=fingerprint()
                process_after=processes()
                changed=[p for p in source_before.keys()|source_after.keys() if source_before.get(p)!=source_after.get(p)]
                with log.open('rb') as log_file:
                    log_file.seek(log_offset)
                    lines=log_file.read().decode('utf-8',errors='replace').splitlines()
                compiler_activity=[line for line in lines if any(term in line.lower() for term in ['compiling','recompile','hotload'])]
                competing=sorted([{'name':p['name'],'pid':pid,'one_core_percent':round(100*(p['seconds']-process_before[pid]['seconds'])/elapsed,1)}
                    for pid,p in process_after.items() if pid in process_before],key=lambda p:p['one_core_percent'],reverse=True)[:15]
                save(label+'-source-revision',source_before)
                delta=lambda key:math.dist([float(v) for v in sample[key].split(',')],[float(v) for v in start[key].split(',')])
                if delta('PlayerPosition')>.5 or delta('CameraPosition')>.5:
                    raise RuntimeError('Camera or player moved during '+label)
                if sample['Screen']!=start['Screen'] or sample['MinBots']!=9 or sample['MaxBots']!=9:
                    raise RuntimeError('Resolution or bot count changed during '+label)
                assembly_changed=sample['GameAssembly']!=start['GameAssembly']
                compiler_processes=[p for p in competing if 'compiler' in p['name'].lower() and p['one_core_percent']>5]
                result={'name':name,'variant':variant,'FrameMs':sample['FrameMs'],'BotMs':sample['BotMs'],
                        'SourceChanges':changed,'CompilerActivity':compiler_activity,'GameAssemblyChanged':assembly_changed,
                        'CompilerProcesses':compiler_processes,'valid':not changed and not compiler_activity and not assembly_changed and not compiler_processes,
                        'ProcessActivity':competing,
                        'BytesPerFrame':sample['BytesPerFrame'],'state':state,'start':start,'end':{
                            k:sample[k] for k in ['Utc','Screen','CameraPosition','CameraAngles','PlayerPosition']}}
                results.append(result)
                save(args.prefix+'-progress',results)
                print(json.dumps({'completed':label,**result}),flush=True)
    finally:
        toggle(True,args.prefix+'-final-cleanup-state')
    save(args.prefix+'-results',results)

if __name__=='__main__':
    main()
