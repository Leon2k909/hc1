"""Temporarily start the task-owned editor empty; restore the user's scene preferences afterwards."""
from pathlib import Path
import json,sys
ROOT=Path.cwd();OUT=ROOT/'output/orion-generator-installed-20261030';path=ROOT/'.sbox/project.json';backup=OUT/'editor-scene-preferences-before.json'
keys=('editor.openscenes','editor.activescene','editor.playmode');data=json.loads(path.read_text())
if sys.argv[1]=='prepare':
    assert not backup.exists(),'Scene preferences already staged'
    snapshot={key:data.get(key) for key in keys};backup.write_text(json.dumps(snapshot,indent=2))
    for key,value in zip(keys,('[]','null','false')):
        if key in data:data[key]['Value']=value
    for name in ('editor-owner.log','editor-protocol.jsonl'):
        old=OUT/name
        if old.exists():old.rename(OUT/(name+'.startup-attempt-1'))
else:
    snapshot=json.loads(backup.read_text())
    for key,value in snapshot.items():
        if value is None:data.pop(key,None)
        else:data[key]=value
path.write_text(json.dumps(data,indent=2));print(json.dumps({'restored':sys.argv[1]!='prepare','keys':keys}))
