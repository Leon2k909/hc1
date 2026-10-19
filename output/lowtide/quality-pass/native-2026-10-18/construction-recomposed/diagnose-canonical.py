from pathlib import Path
import sys,json
from collections import Counter
OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[4]
sys.path.insert(0,str(ROOT/'Tools'))
import lowtide_window_construction as W
before=W.face_keys((OUT/'canonical-verification/lowtide_east-before-windows.obj').read_text(),attributes=True)
after=W.face_keys((OUT/'canonical-verification/lowtide_east-after-windows.obj').read_text(),attributes=True)
base=ROOT/'output/lowtide/quality-pass/window-construction'
minus=W.face_keys((base/'lowtide_east-old.obj').read_text(),attributes=True)
plus=W.face_keys((base/'lowtide_east-new.obj').read_text(),attributes=True)
expected=before-minus+plus
missing=expected-after
extra=after-expected
print(json.dumps(dict(missing_materials=dict(Counter({paint:sum(v for k,v in missing.items() if k[0]==paint) for paint in {k[0] for k in missing}})),extra_materials=dict(Counter({paint:sum(v for k,v in extra.items() if k[0]==paint) for paint in {k[0] for k in extra}})),missing=list(missing.items())[:2],extra=list(extra.items())[:2]),indent=2))
