"""Use the existing native connection helper against the canonical checkout."""
from pathlib import Path
import importlib.util,json,sys
ROOT=Path('C:/sbox-projects/hc1/forked-shooter-main')
OUT=Path(__file__).resolve().parents[3]/'output/riverside/shop-sign-v1'
spec=importlib.util.spec_from_file_location('shared_native',ROOT/'Sources/Riverside/drinks-fridge-v1/native.py')
native=importlib.util.module_from_spec(spec);spec.loader.exec_module(native);native.OUT=OUT
call=native.call;script=native.script
if __name__=='__main__':
    if sys.argv[1]=='script':result=script(sys.argv[2])
    else:result=call(sys.argv[1],json.loads(sys.argv[2]) if len(sys.argv)>2 else {})
    print(json.dumps(result,indent=2))
