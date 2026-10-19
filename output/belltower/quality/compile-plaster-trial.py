from pathlib import Path
import argparse
import json
import subprocess
import sys

quality=Path('output/belltower/quality')
records=json.loads((quality/'plaster-v1-materials.json').read_text())
parser=argparse.ArgumentParser()
parser.add_argument('--start',type=int,default=0)
start=parser.parse_args().start
for item in records[start:]:
    args=quality/'plaster-v1-import/compile-args.json'
    args.write_text(json.dumps({'path':item['path'],'full':False}))
    subprocess.run([sys.executable,'-X','utf8','output/knife-throw/editor_check.py',
                    '--tool','asset_compile','--args-file',str(args),
                    '--output-dir',str(quality/'plaster-v1-import'/Path(item['path']).stem),
                    '--timeout','180'],check=True)
