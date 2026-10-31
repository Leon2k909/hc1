"""Run a single background render at idle priority, confined to two logical CPUs."""
from pathlib import Path
import json,os,subprocess,sys,time
import psutil
ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'output/asset-improvement-20261030/pump-skid/clean-finish-review'
BLENDER=Path('C:/Program Files/Blender Foundation/Blender 5.1/blender.exe')
p=psutil.Process();p.nice(psutil.IDLE_PRIORITY_CLASS);cpus=p.cpu_affinity()[-2:];p.cpu_affinity(cpus)
env=dict(os.environ)
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):env[key]='1'
command=[str(BLENDER),'-b','--factory-startup','--threads','2','--python-exit-code','1',
         '--python',str(Path(__file__).parent/'render_clean_finish.py')]
if '--after-only' in sys.argv:command+=['--','--after-only']
if '--draft' in sys.argv:command+=['--','--draft']
if '--surface-review' in sys.argv:command+=['--','--surface-review']
if '--surface-first' in sys.argv:command+=['--','--surface-first']
start=time.monotonic()
with (OUT/'render.log').open('w',encoding='utf-8') as log:
    child=subprocess.Popen(command,cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT,
                           creationflags=subprocess.CREATE_NO_WINDOW|subprocess.IDLE_PRIORITY_CLASS)
    childproc=psutil.Process(child.pid);childproc.cpu_affinity(cpus)
    assert childproc.cpu_affinity()==cpus
    assert childproc.nice()==psutil.IDLE_PRIORITY_CLASS
    print(json.dumps({'renderPID':child.pid,'priority':'idle','cpuAffinity':cpus,'gpuRendering':False}),flush=True)
    try:
        code=child.wait(timeout=3600)
    except BaseException:
        if child.poll() is None:child.terminate();child.wait(timeout=30)
        raise
report={'exitCode':code,'elapsedSeconds':round(time.monotonic()-start,2),'renderProcessStopped':True,
        'priority':'idle','cpuAffinity':cpus,'threads':2,'gpuRendering':False}
(OUT/'render-process.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
sys.exit(code)
