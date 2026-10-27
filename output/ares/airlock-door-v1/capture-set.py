import argparse
import json
from pathlib import Path
import subprocess
import sys

ap=argparse.ArgumentParser();ap.add_argument('--phase',required=True)
ap.add_argument('--trial',action='store_true');ap.add_argument('views',nargs='+');args=ap.parse_args()
root=Path(__file__).resolve().parents[3]
for view in args.views:
    subprocess.run(['rtk','proxy',sys.executable,'-X','utf8','Tools/ares_pressure_capture.py',
                    '--phase',args.phase,'--view',view],cwd=root,check=True)
    p=root/'output/ares/airlock-door-v1/capture-request.json';j=json.loads(p.read_text())
    j['preserve_unsaved']=True
    if args.trial:j['trial_model']='models/maps/ares/pressure-doors-v2/trial_hall.vmdl'
    p.write_text(json.dumps(j))
    subprocess.run(['rtk','proxy',sys.executable,'-X','utf8','output/knife-throw/editor_check.py',
                    '--script','Sources/Ares/pressure-doors-v2/capture.cs.txt',
                    '--output-dir',f'output/ares/airlock-door-v1/capture-{args.phase}-{view}',
                    '--timeout','45','--direct-call','--cleanup-exchange'],cwd=root,check=True)
