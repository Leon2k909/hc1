"""Write texture dependencies through native editor tools, then compile sequentially."""
from pathlib import Path
import json
import native_cli as cli

report=json.loads((cli.OUT/'texture-import-remaining.json').read_text())
results=[]
for change in report['Changes']:
    args=json.loads(Path(change['NativeWriteRequest']).read_text())
    result=cli.call('write_file',args)
    assert result.get('written') is True,result
    compiled=cli.call('asset_compile',{'path':change['Material'],'full':True})
    assert compiled.get('Success') is True,compiled
    results.append(compiled)
    print(change['Material']+': compiled successfully',flush=True)
(cli.OUT/'native-material-compilation.json').write_text(json.dumps(results,indent=2))
