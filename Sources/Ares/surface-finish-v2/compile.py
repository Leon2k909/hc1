from pathlib import Path
import json
from native import call,OUT
paths=['materials/ares/surface-finish-v2/'+x+'.vmat' for x in ('wall','floor','frame')]
paths+=['models/maps/ares/surface-finish-v2/ares_'+x+'_trial.vmdl' for x in ('hall','reactor')]
results=[]
for path in paths:
    r=call('asset_compile',{'path':path,'full':True});results.append(r)
    print(json.dumps(r),flush=True)
    assert r.get('Success'),r
(OUT/'compilation.json').write_text(json.dumps(results,indent=2))
