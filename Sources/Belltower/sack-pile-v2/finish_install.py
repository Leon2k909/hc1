"""Publish the approved piles through the existing editor and retire old review meshes."""
from pathlib import Path
import ast,json,subprocess,sys,tempfile
ROOT=Path(__file__).resolve().parents[3]
HERE=Path(__file__).parent
sys.path.insert(0,str(ROOT/'Sources/Belltower/terracotta-pot-v2'))
import native
OUT=Path(tempfile.gettempdir())/'belltower-sack-pile-v2'
native.OUT=OUT
tree=ast.parse((ROOT/'Sources/Belltower/terracotta-pot-v2/finish_install.py').read_text())
command=next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='command' for t in n.targets))
command=command.replace('AddSeconds(45)','AddSeconds(180)')
cleanup=subprocess.Popen(['powershell','-NoProfile','-Command',command],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,creationflags=subprocess.CREATE_NO_WINDOW)
try:
    status=native.call('editor_status');scenes=native.call('list_scenes')['Scenes']
    if not any(r['ResourcePath']=='scenes/maps/belltower/belltower.scene' for r in scenes):
        assert not status['IsPlaying']
        native.call('open_scene',{'path':'scenes/maps/belltower/belltower.scene'})
        native.call('switch_scene',{'scene':status['ActiveScenePath']})
    print('Mirrored sources:',native.script(HERE/'import-mirrored.cs.txt','import-mirrored'),flush=True)
    assert native.call('asset_compile',{'path':'models/maps/belltower/sack-pile-v2/sack_pile_mirrored.vmdl'},'compile-mirrored')['Success']
    print('Install:',native.script(HERE/'install.cs.txt','install'),flush=True)
    manifest=json.loads((OUT/'install-stage/manifest.json').read_text())
    for relative in manifest['compile_models']:
        path=relative.removeprefix('Assets/')
        result=native.call('asset_compile',{'path':path},'installed-compile-'+Path(path).stem)
        assert result['Success'],result
        print('Compiled:',path,flush=True)
    print('Retired:',native.script(HERE/'delete-old.cs.txt','delete-old'),flush=True)
finally:
    if cleanup.poll() is None:cleanup.terminate()
    cleanup.communicate(timeout=25)
