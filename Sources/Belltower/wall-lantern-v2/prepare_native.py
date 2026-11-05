"""Build guarded native scripts for the approved installation; there is no delete step."""
from pathlib import Path
import json,tempfile
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent
stage=Path(tempfile.gettempdir())/'belltower-wall-lantern-v2/install-stage'
p=stage/'manifest.json';m=json.loads(p.read_text());m['protected'].update(m['retained_original_files']);p.write_text(json.dumps(m,indent=2)+'\n')
s=(ROOT/'Sources/Belltower/bistro-table-v2/install.cs.txt').read_text()
s=s.replace('bistro-table-v2','wall-lantern-v2').replace('bistro_table.vmdl','wall_lantern.vmdl').replace('Bistro tables','Wall lanterns')
s=s.replace('tables','lanterns').replace('Tables','Lanterns').replace('table','lantern').replace('Table','Lantern')
s=s.replace('!=7','!=24').replace('all 7','all 24').replace('Installed=7','Installed=24').replace('3038','23040')
s=s.replace('var plan=new System.Collections.Generic.List', '''var original=Model.Load("models/maps/belltower/wall-lantern-original/wall_lantern_original.vmdl");
if(original is null || original.IsError)throw new InvalidOperationException("Retained original failed to load.");
var plan=new System.Collections.Generic.List''')
s=s.replace('User approved the cafe lantern. Preserve all 24 existing placements.','User approved the wall lantern. Preserve all 24 placements and retain the original asset.')
(HERE/'install.cs.txt').write_text(s)
s=(ROOT/'Sources/Belltower/bistro-table-v2/finish_install.py').read_text().replace('bistro-table-v2','wall-lantern-v2')
s=s.replace("    print('Install:',native.script(HERE/'install.cs.txt','install'),flush=True)","""    print('Original:',native.script(HERE/'preserve-original.cs.txt','preserve-original'),flush=True)
    result=native.call('asset_compile',{'path':'models/maps/belltower/wall-lantern-original/wall_lantern_original.vmdl'},'compile-retained-original')
    assert result['Success'],result
    print('Install:',native.script(HERE/'install.cs.txt','install'),flush=True)""")
s=s.replace("    print('Retired:',native.script(HERE/'delete-old.cs.txt','delete-old'),flush=True)","    print('Original assets retained; no deletion phase.',flush=True)")
(HERE/'finish_install.py').write_text(s)
assert 'LanternsInstalled=24' in (HERE/'install.cs.txt').read_text()
assert 'delete-old' not in s
print('Prepared native install for 24 lanterns; preserve original and delete nothing.')
