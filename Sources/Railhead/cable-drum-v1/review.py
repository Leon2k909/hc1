from pathlib import Path
import json,runpy,sys
from native import call,script
HERE=Path(__file__).parent
if '--capture-only' not in sys.argv:
 print(json.dumps(script(HERE/'import.cs.txt')),flush=True)
 for name in ('timber_a','timber_b','timber_c','cable','steel','recess'):
  result=call('asset_compile',dict(path=f'materials/railhead/cable-drum-v1/{name}.vmat',full=False));print(json.dumps(result),flush=True);assert result['Success']
 for name in ('cable_drum','east_without_drum'):
  result=call('asset_compile',dict(path=f'models/maps/railhead/cable-drum-v1/{name}.vmdl',full=False));print(json.dumps(result),flush=True);assert result['Success']
sys.argv=[str(HERE/'capture.py')];runpy.run_path(str(HERE/'capture.py'),run_name='__main__')
