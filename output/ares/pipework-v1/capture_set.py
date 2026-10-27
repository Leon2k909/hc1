import argparse
from pathlib import Path
import subprocess
import sys

ap=argparse.ArgumentParser();ap.add_argument('--phase',required=True)
ap.add_argument('--trial',action='store_true');ap.add_argument('--stage',default='stage-v5')
ap.add_argument('views',nargs='+');args=ap.parse_args()
root=Path(__file__).resolve().parents[3]
for view in args.views:
    command=['rtk','proxy',sys.executable,'-X','utf8','Tools/ares_pipework_capture.py',
        '--phase',args.phase,'--view',view,'--stage',args.stage]
    if args.trial:command.append('--trial')
    subprocess.run(command,cwd=root,check=True)
    subprocess.run(['rtk','proxy',sys.executable,'-X','utf8','output/knife-throw/editor_check.py',
        '--script','Sources/Ares/pipework-v1/capture.cs.txt',
        '--output-dir',f'output/ares/pipework-v1/capture-{args.phase}-{view}',
        '--timeout','45','--direct-call','--cleanup-exchange'],cwd=root,check=True)
