import json,sys
import native
paths=[f'materials/ares/interior-v1/{name}.vmat' for name in ('panel','frame','red','alloy','dark','floor')]
paths+=[f'models/maps/ares/interior-v1/{name}_preview.vmdl' for name in ('ares_hall','ares_reactor')]
if '--installed' in sys.argv:paths=[f'models/maps/ares/{name}.vmdl' for name in ('ares_hall','ares_reactor')]
results=[]
for path in paths:
    result=native.call('asset_compile',dict(path=path,full=False))
    results.append(result);print(json.dumps(result),flush=True)
    assert result.get('Success'),result
(native.OUT/('installed-compilation.json' if '--installed' in sys.argv else 'preview-compilation.json')).write_text(json.dumps(results,indent=2)+'\n')
