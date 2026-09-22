"""Call the project's running local s&box editor bridge."""
import json,sys,tempfile,time,uuid
from pathlib import Path
folder=Path(tempfile.gettempdir())/'sbox-bridge-ipc'
request='mw22-'+uuid.uuid4().hex
path=folder/('req_'+request+'.json');reply=folder/('res_'+request+'.json')
command='console_run';params=dict(command=' '.join(sys.argv[1:]))
if sys.argv[1]=='--asset':command='recompile_asset';params=dict(path=sys.argv[2])
path.write_text(json.dumps(dict(id=request,command=command,params=params)))
print('REQUEST',request,flush=True)
for _ in range(450):
    if reply.exists():
        print(reply.read_text(encoding='utf8'));reply.unlink();break
    time.sleep(.1)
else:raise TimeoutError('Editor bridge did not answer within 45 seconds')
