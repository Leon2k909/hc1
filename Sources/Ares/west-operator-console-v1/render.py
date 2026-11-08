from pathlib import Path
import subprocess,os,sys
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent;OUT=ROOT/'output/ares/west-operator-console-v1'
text=(ROOT/'Sources/Collider/monitor-trial-v1/render.py').read_text().replace("output/asset-improvement-20261029/monitor","output/ares/west-operator-console-v1").replace("models/props/collider/monitor-trial-v1","models/props/ares/west_operator_console_v1").replace("ASSETS=ROOT/'Assets'","ASSETS=OUT/'stage/Assets'")
text=text.replace("scene.cycles.samples=32","scene.cycles.samples=24").replace("location=(0,0,-.26)","location=(0,0,-.025)")
text=text.replace("views=[('main',(3.3,-4.8,2.9),(0,.1,.86)),('rear',(3.3,4.8,2.9),(0,.1,.86))]","views=[('main',(2.6,-4.1,2.7),(0,0,.80))]")
text=text.replace("    material_cache[path]=mat","    if keys.get('F_SPECULAR')=='0':\n        for node in mat.node_tree.nodes:\n            if node.type=='BSDF_PRINCIPLED':node.inputs['Specular IOR Level'].default_value=0\n    material_cache[path]=mat")
script=HERE/'render_blender.py';script.write_text(text)
env=dict(os.environ)
for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):env[k]='1'
with (OUT/'render.log').open('w') as log:
 p=subprocess.Popen(['C:/Program Files/Blender Foundation/Blender 5.1/blender.exe','-b','--factory-startup','--threads','4','--python-exit-code','1','--python',str(script)],cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW|subprocess.IDLE_PRIORITY_CLASS)
 try:
  import psutil
  psutil.Process(p.pid).cpu_affinity(psutil.Process().cpu_affinity()[-4:])
  result=p.wait(timeout=240);assert result==0,(OUT/'render.log').read_text()[-6000:]
 finally:
  if p.poll() is None:p.terminate();p.wait(timeout=15)
print('Matched offline renders complete; owned renderer exited')
