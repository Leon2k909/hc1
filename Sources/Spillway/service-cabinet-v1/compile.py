from pathlib import Path
import json
from native import call,ROOT,OUT
plan=json.loads((OUT/'install-plan.json').read_text())
resources=[r[7:] for r in plan['files'] if r.startswith('Assets/materials/spillway/service-cabinet-v1/') and r.endswith('.vmat')]
resources+=['models/maps/spillway/service-cabinet-v1/'+n+'.vmdl' for n in ['before','cabinet','review_floor']]
results=[]
for path in resources:
    try:
        result=call('asset_compile',{'path':path})
        if not result.get('Success'):raise RuntimeError(str(result))
    except Exception:
        state=call('asset_info',{'path':path})
        if not state.get('IsCompiledAndUpToDate') or state.get('IsCompileFailed'):raise
        result={'Success':True,'Path':path,'CompletedAfterTimeout':True}
    results.append(result)
(OUT/'compilation.json').write_text(json.dumps(results,indent=2))
print(json.dumps({'Compiled':len(results),'Success':True}))
