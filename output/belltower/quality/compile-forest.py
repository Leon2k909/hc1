"""Compile the reviewed source candidate through the attached native editor.

Each result is saved separately. A failed/timed-out call stops the queue; inspect
the engine and output before explicitly resuming with --start.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

root=Path(__file__).resolve().parents[3]
stage=root/'output/belltower/quality/forest-v1-staging'
destination=root/'output/belltower/quality/forest-v3-native'
destination.mkdir(parents=True,exist_ok=True)
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--start',type=int,default=0)
args=parser.parse_args()
records=json.loads((stage/'import.json').read_text())
fingerprint=hashlib.sha256((stage/'manifest.json').read_bytes()).hexdigest()
for record in records:
    for path in (root/record['source'],root/'Assets'/record['path']):
        assert hashlib.sha256(path.read_bytes()).hexdigest()==record['sha256'], path
paths=['materials/belltower/forest/forest_trees.vmat']+[
    record['path'] for record in records if record['path'].endswith('.vmdl')]
assert 0<=args.start<len(paths)

def invoke(tool,out,arguments=None):
    command=[sys.executable,'-X','utf8',str(root/'output/knife-throw/editor_check.py'),
        '--tool',tool,'--output-dir',str(out),'--timeout','180']
    if arguments is not None:
        out.mkdir(parents=True,exist_ok=True)
        argument_file=out/'arguments.json'
        argument_file.write_text(json.dumps(arguments))
        command+=['--args-file',str(argument_file)]
    subprocess.run(command,cwd=root,check=True)
    result=json.loads((out/(tool+'.json')).read_text())
    assert not result.get('isError'), result
    if 'structuredContent' in result:
        return result['structuredContent']
    return json.loads(next(item['text'] for item in result['content'] if item['type']=='text'))

before=invoke('editor_status',destination/'before')
assert Path(before['Paths']['ProjectRoot']).resolve()==root
assert not before['IsCompiling'], 'Wait for the current code compilation.'
assert not (before['IsPlaying'] and 'belltower' in (before.get('ActiveScenePath') or '').lower())
for index,path in enumerate(paths[args.start:],start=args.start):
    print(f'[{index+1}/{len(paths)}] {path}',flush=True)
    out=destination/f'{index:03}-{Path(path).stem}'
    (out).mkdir(parents=True,exist_ok=True)
    (out/'candidate.json').write_text(json.dumps({'manifest_sha256':fingerprint,'path':path}))
    result=invoke('asset_compile',out,{'path':path,'full':False})
    assert result.get('Success') is True, result

after=invoke('editor_status',destination/'after')
for key in ('ActiveScenePath','SceneHasUnsavedChanges','IsPlaying','IsPaused'):
    assert before[key]==after[key], f'Editor state changed during compilation: {key}'
print('Forest native compilation queue completed; model-load verification remains required.',flush=True)
