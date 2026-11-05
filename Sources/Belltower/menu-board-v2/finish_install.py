"""Install the user's approved replacement, compile, then retire verified old files."""
from pathlib import Path
import ast,json,subprocess,tempfile,sys
ROOT=Path(__file__).resolve().parents[3]
HERE=Path(__file__).parent
sys.path.insert(0,str(ROOT/'Sources/Belltower/terracotta-pot-v2'))
import native
OUT=Path(tempfile.gettempdir())/'belltower-menu-board-v2'
native.OUT=OUT
tree=ast.parse((ROOT/'Sources/Belltower/terracotta-pot-v2/finish_install.py').read_text())
command=next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='command' for t in n.targets))
cleanup=subprocess.Popen(['powershell','-NoProfile','-Command',command],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,creationflags=subprocess.CREATE_NO_WINDOW)
try:
    print('Prepare:',native.script(HERE/'prepare-new.cs.txt','prepare-variant'),flush=True)
    result=native.call('asset_compile',{'path':'models/maps/belltower/menu-board-v2/menu_board_b.vmdl'},'compile-variant-b')
    assert result['Success'],result
    print('Install:',native.script(HERE/'install.cs.txt','install'),flush=True)
    manifest=json.loads((OUT/'install-stage/manifest.json').read_text())
    for relative in manifest['files']:
        if not relative.endswith('.vmdl'):continue
        path=relative.removeprefix('Assets/')
        result=native.call('asset_compile',{'path':path},'compile-installed-'+Path(path).stem)
        assert result['Success'],(path,result)
        print('Compiled:',path,flush=True)
    print('Delete:',native.script(HERE/'delete-old.cs.txt','delete-old'),flush=True)
finally:
    if cleanup.poll() is None:cleanup.terminate()
    cleanup.communicate(timeout=25)
