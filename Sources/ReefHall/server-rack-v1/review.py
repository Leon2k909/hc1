from pathlib import Path
import json,sys,runpy
from native import call,script
HERE=Path(__file__).parent
if '--capture-only' not in sys.argv:
 print(json.dumps(script(HERE/'import.cs.txt')),flush=True)
 for name in ('frame','panel','rail','black','port'):
  result=call('asset_compile',dict(path=f'materials/reefhall/server-rack-v1/{name}.vmat',full=False));print(json.dumps(result),flush=True);assert result['Success']
 for name in ('server_racks','control_without_racks'):
  result=call('asset_compile',dict(path=f'models/maps/reefhall/server-rack-v1/{name}.vmdl',full=False));print(json.dumps(result),flush=True);assert result['Success']
sys.argv=[str(HERE/'capture.py')];runpy.run_path(str(HERE/'capture.py'),run_name='__main__')
