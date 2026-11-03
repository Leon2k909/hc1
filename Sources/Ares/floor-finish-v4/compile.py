import json,time
from native import call,OUT
paths=['materials/ares/floor-finish-v4/plate.vmat','materials/ares/floor-finish-v4/grip.vmat','models/maps/ares/floor-finish-v4/ares_hall_trial.vmdl']
report=[]
for path in paths:
    try:
        result=call('asset_compile',dict(path=path));assert result.get('Success'),result
    except RuntimeError as e:
        if 'timed out' not in str(e):raise
        result=call('asset_info',dict(path=path))
        for i in range(12):
            if result.get('IsCompiledAndUpToDate') or result.get('IsCompileFailed'):break
            time.sleep(5);result=call('asset_info',dict(path=path))
        assert result.get('IsCompiledAndUpToDate') and not result.get('IsCompileFailed'),result
    report.append(dict(path=path,result=result));print(path,'OK',flush=True)
(OUT/'compilation.json').write_text(json.dumps(report,indent=2))
