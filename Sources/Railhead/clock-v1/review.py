from pathlib import Path
import json,sys,runpy
from native import ROOT,OUT,call,script
HERE=Path(__file__).parent
if '--capture-only' not in sys.argv:
 print(json.dumps(script(HERE/'import.cs.txt')),flush=True)
 for name in ('housing','dial','ink','steel','seal'):
  result=call('asset_compile',dict(path=f'materials/railhead/clock-v1/{name}.vmat',full=True));print(json.dumps(result),flush=True);assert result['Success']
 for name in ('station_clock','dressing_without_clock'):
  result=call('asset_compile',dict(path=f'models/maps/railhead/clock-v1/{name}.vmdl',full=True));print(json.dumps(result),flush=True);assert result['Success']
sys.argv=[str(HERE/'capture.py')];runpy.run_path(str(HERE/'capture.py'),run_name='__main__')
