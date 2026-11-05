from native import call,OUT
import json
p=json.loads((OUT/'preview-plan.json').read_text())
paths=[r[7:] for r in p['files'] if r.endswith('.vmat')]
paths+=['models/maps/riverside/discarded-tyres-v1/'+s+'.vmdl' for s in ('before','tyre')]
report=[]
for path in paths:
    try:
        result=call('asset_compile',{'path':path})
        if not result.get('Success'):raise RuntimeError(str(result))
    except Exception:
        state=call('asset_info',{'path':path})
        if not state.get('IsCompiledAndUpToDate') or state.get('IsCompileFailed'):raise
        result={'Success':True,'Path':path,'ConfirmedAfterTimeout':True}
    report.append(result)
(OUT/'preview-compilation.json').write_text(json.dumps(report,indent=2))
print(json.dumps({'Compiled':len(report),'Success':True}))
