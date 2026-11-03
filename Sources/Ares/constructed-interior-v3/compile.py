import json,time
from native import call,OUT
paths=['materials/ares/constructed-v3/'+n+'.vmat' for n in ('paint','dark','steel','red','rubber','copper','ceiling','floor','skin')]
paths+=['models/maps/ares/constructed-v3/ares_'+n+'_trial.vmdl' for n in ('hall','reactor')]
report=[]
for p in paths:
    try:
        r=call('asset_compile',dict(path=p));assert r.get('Success'),r
    except RuntimeError as e:
        # Compilation can finish after the MCP call's timeout. Inspect it before
        # doing anything else; never dispatch the same mutation twice.
        if 'timed out' not in str(e):raise
        r=call('asset_info',dict(path=p))
        for i in range(12):
            if r.get('IsCompiledAndUpToDate') or r.get('IsCompileFailed'):break
            time.sleep(5);r=call('asset_info',dict(path=p))
        assert r.get('IsCompiledAndUpToDate') and not r.get('IsCompileFailed'),r
    report.append(dict(path=p,result=r));print(p,'OK',flush=True)
(OUT/'compilation.json').write_text(json.dumps(report,indent=2))
