"""One owned Blender process, idle priority, four logical CPUs, CPU rendering."""
from pathlib import Path
import json,os,subprocess,sys,time
import psutil
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent
OUT=ROOT/'output/asset-improvement-20261030/bulkhead-lamp'
blender=Path('C:/Program Files/Blender Foundation/Blender 5.1/blender.exe')
proc=psutil.Process();proc.nice(psutil.IDLE_PRIORITY_CLASS);cpus=proc.cpu_affinity()[-4:];proc.cpu_affinity(cpus)
env=dict(os.environ)
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):env[key]='1'
cmd=[str(blender),'-b','--factory-startup','--threads','4','--python-exit-code','1','--python',str(HERE/'build_render.py')]
if '--draft' in sys.argv:cmd+=['--','--draft']
started=time.monotonic()
with (OUT/'render.log').open('w',encoding='utf-8') as log:
    child=subprocess.Popen(cmd,cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW|subprocess.IDLE_PRIORITY_CLASS)
    psutil.Process(child.pid).cpu_affinity(cpus)
    print(json.dumps({'ownedRenderPID':child.pid,'priority':'idle','cpuAffinity':cpus,'gpuRendering':False}),flush=True)
    try:code=child.wait(timeout=1800)
    except BaseException:
        if child.poll() is None:child.terminate();child.wait(timeout=30)
        raise
print(json.dumps({'exitCode':code,'seconds':round(time.monotonic()-started,1)}))
sys.exit(code)
