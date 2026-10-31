"""One owned, idle-priority Blender process on four CPUs; no render or UI."""
from pathlib import Path
import json,os,subprocess,time,psutil,sys
HERE=Path(__file__).parent;ROOT=HERE.resolve().parents[2];OUT=ROOT/'output/orion-cable-reel-installed-20261030';OUT.mkdir(parents=True,exist_ok=True)
p=psutil.Process();p.nice(psutil.IDLE_PRIORITY_CLASS);cpus=p.cpu_affinity()[-4:];p.cpu_affinity(cpus)
cmd=['C:/Program Files/Blender Foundation/Blender 5.1/blender.exe','-b','--factory-startup','--threads','4','--python-exit-code','1','--python',str(HERE/'export_lods.py')]
started=time.monotonic()
with (OUT/'lod-export.log').open('w') as log:
    child=subprocess.Popen(cmd,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW|subprocess.IDLE_PRIORITY_CLASS)
    psutil.Process(child.pid).cpu_affinity(cpus);print(json.dumps({'ownedBlenderPID':child.pid,'cpuAffinity':cpus}),flush=True)
    try:code=child.wait(timeout=600)
    except BaseException:
        if child.poll() is None:child.terminate();child.wait(timeout=30)
        raise
print(json.dumps({'exitCode':code,'seconds':round(time.monotonic()-started,1)}));sys.exit(code)
