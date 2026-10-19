"""Run one bounded CPU-only studio renderer, retaining its detailed log."""
import os
import argparse
from pathlib import Path
import shutil
import subprocess
import sys

blender=shutil.which('blender')
if not blender:
    installed=sorted((Path(os.environ.get('ProgramFiles','C:/Program Files'))/'Blender Foundation').glob('*/blender.exe'))
    if not installed:
        raise RuntimeError('Blender is not installed')
    blender=str(installed[-1])
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--revision',choices=('garden-v1','garden-v2','garden-v3'),default='garden-v3')
parser.add_argument('--directory',help='A staged studio folder directly under output/belltower/quality.')
parser.add_argument('--exposure',type=float,default=0.0)
parser.add_argument('views',nargs='*')
options=parser.parse_args()
quality=Path('output/belltower/quality').resolve()
folder=(quality/(options.directory or f'{options.revision}-studio')).resolve()
if folder.parent != quality:
    raise ValueError('The studio directory must be directly under the quality output folder')
views=options.views
render_errors=[]
with (folder/'render.log').open('w',encoding='utf-8') as log:
    command=[blender,'--background','--factory-startup','--threads','2','--python-exit-code','1','--python','Tools/belltower_garden_preview.py']
    command+=['--','--revision',options.revision,'--exposure',str(options.exposure)]
    if options.directory:
        command+=['--directory',options.directory]
    if views:
        command+=['--views',*views]
    process=subprocess.Popen(command,
        stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,encoding='utf-8',errors='replace',
        creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
    print('Studio renderer PID',process.pid,flush=True)
    try:
        for line in process.stdout:
            log.write(line)
            log.flush()
            if 'GARDEN_REVIEW' in line or 'Error' in line or 'Traceback' in line or 'Exception' in line:
                print(line.strip(),flush=True)
            if 'Error:' in line or 'Traceback' in line:
                render_errors.append(line.strip())
        code=process.wait()
    finally:
        process.stdout.close()
        if process.poll() is None:
            process.terminate()
            process.wait(timeout=10)
    print('Studio renderer exit',code,flush=True)
    sys.exit(code or (1 if render_errors else 0))
