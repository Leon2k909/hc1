from pathlib import Path
import json
import native

paths = [f'materials/riverdale/cctv_v2/rv_cam_{name}.vmat'
         for name in ('paint','seal','metal','glass','inner','label')]
paths += [f'models/maps/riverdale/cctv_v2_review/riverdale_hall_{name}.vmdl' for name in ('detail','fine')]
results = []
for path in paths:
    result = native.call('asset_compile', dict(path=path, full=False))
    results.append(result)
    print(json.dumps(result), flush=True)
    assert result.get('Success'), result
(native.OUT/'compilation.json').write_text(json.dumps(results,indent=2)+'\n')
