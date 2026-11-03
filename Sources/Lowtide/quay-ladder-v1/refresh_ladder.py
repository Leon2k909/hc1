from pathlib import Path
import json,sys,runpy
from native import call,script
HERE=Path(__file__).parent
print(json.dumps(script(HERE/'import.cs.txt')),flush=True)
result=call('asset_compile',dict(path='models/maps/lowtide/quay-ladder-v1/quay_ladder.vmdl',full=True))
print(json.dumps(result),flush=True);assert result['Success']
sys.argv=[str(HERE/'review.py'),'--capture-only'];runpy.run_path(str(HERE/'review.py'),run_name='__main__')
