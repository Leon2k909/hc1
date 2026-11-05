from pathlib import Path
import json,sys,runpy
from native import ROOT,call,script
HERE=Path(__file__).parent
status=call('editor_status')
assert Path(status['Paths']['ProjectRoot']).resolve()==ROOT
if '--capture-only' not in sys.argv:
 print(json.dumps(script(HERE/'import.cs.txt')),flush=True)
 for name in ('yard_without_cone',):
  result=call('asset_compile',dict(path=f'models/maps/riverdale/shared-cone-v1/{name}.vmdl',full=False))
  print(json.dumps(result),flush=True);assert result['Success']
sys.argv=[str(HERE/'capture.py')];runpy.run_path(str(HERE/'capture.py'),run_name='__main__')
