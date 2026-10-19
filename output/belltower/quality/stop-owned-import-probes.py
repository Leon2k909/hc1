import psutil
import json

stopped=[]
for process in psutil.process_iter(['name','cmdline']):
    if process.info['name']!='python.exe':
        continue
    args=process.info['cmdline'] or []
    builder=process.pid==21516 and 'Tools/belltower_quality_forest.py' in args
    import_probe=args[1:3]==['-X','importtime'] and args[-1:]==["import numba;print('Numba imported')"]
    optional_installer=args[-3:]==['--target','output/tools/python-diagnostics','py-spy']
    if builder or import_probe or optional_installer:
        process.terminate()
        process.wait(timeout=10)
        stopped.append(process.pid)
print(json.dumps({'stopped_task_owned_helpers':stopped}))
