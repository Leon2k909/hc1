"""Native, matched in-map comparison; never save candidate objects."""
from pathlib import Path
import json,math,sys,tempfile,ast,subprocess
ROOT=Path(__file__).resolve().parents[3]
HERE=Path(__file__).parent
sys.path.insert(0,str(ROOT/'Sources/Belltower/terracotta-pot-v2'))
import native
OUT=Path(tempfile.gettempdir())/'belltower-menu-board-v2'
native.OUT=OUT

def helper():
    text=(ROOT/'Sources/Belltower/terracotta-pot-v2/capture.cs.txt').read_text()
    text=text.replace('terracotta-pot-v2','menu-board-v2').replace('terracotta_pot.vmdl','menu_board.vmdl').replace('west_without_one_pot.vmdl','west_without_menu_board.vmdl')
    text=text.replace('new Vector3(514,1862,0)','new Vector3(-218,628,0)')
    text=text.replace('Temporary terracotta pot comparison','Temporary menu board comparison')
    text=text.replace('GameObject trialPot=null;', 'GameObject trialFill=null;\nGameObject trialPot=null;')
    text=text.replace('if(candidate)\n        {', '''if(config["review_fill"]?.GetValue<bool>()==true)
        {
            trialFill=new GameObject(scene,false,"Temporary matched inspection light");
            trialFill.Flags|=GameObjectFlags.NotSaved|GameObjectFlags.EditorOnly;
            trialFill.WorldPosition=new Vector3(-270,550,72);
            var fill=trialFill.Components.Create<PointLight>();
            fill.LightColor=new Color(3.0f,2.8f,2.5f);
            fill.Radius=180f;
            fill.Shadows=false;
            trialFill.Enabled=true;
        }
        if(candidate)
        {''')
    text=text.replace('if(trialPot.IsValid()) {trialPot.Destroy();scene.ProcessDeletes();}', 'if(trialPot.IsValid())trialPot.Destroy();\n        if(trialFill.IsValid())trialFill.Destroy();\n        scene.ProcessDeletes();')
    text=text.replace('RequestedExposure = exposure, NativeEnabled', 'TemporaryMatchedInspectionLight=config["review_fill"]?.GetValue<bool>()==true, RequestedExposure = exposure, NativeEnabled')
    destination=HERE/'capture.cs.txt';destination.write_text(text);return destination

def capture(name,candidate,position=(-258,550,33),target=(-218,628,17),fov=44,exposure=1.5,fill=False):
    x,y,z=[b-a for a,b in zip(position,target)]
    angles=(math.degrees(math.atan2(-z,math.hypot(x,y))),math.degrees(math.atan2(y,x)),0)
    manifest=json.loads((OUT/'manifest.json').read_text())
    config={'directory':'review','name':name,'position':','.join(map(str,position)),'angles':','.join(map(str,angles)),'width':1280,'height':1024,'fov':fov,'exposure':exposure,'settle_ms':0,'candidate':candidate,'review_fill':fill,'expected_scene_sha256':manifest['guards']['Assets/scenes/maps/Belltower/belltower.scene']}
    (OUT/'capture.json').write_text(json.dumps(config))
    return native.script(helper(),name)

if __name__=='__main__':
    mode=sys.argv[1]
    if mode=='finalize':
        # The shared app repeatedly starts large read-only diff previews. Keep
        # only those verified previews out of the short native validation window.
        tree=ast.parse((ROOT/'Sources/Belltower/terracotta-pot-v2/finish_install.py').read_text())
        command=next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='command' for t in n.targets))
        cleanup=subprocess.Popen(['powershell','-NoProfile','-Command',command],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,creationflags=subprocess.CREATE_NO_WINDOW)
        try:
            print('Import:',json.dumps(native.script(HERE/'import.cs.txt','import')),flush=True)
            for name in ('menu_board','west_without_menu_board'):
                result=native.call('asset_compile',{'path':f'models/maps/belltower/menu-board-v2/{name}.vmdl'},'compile-'+name)
                print('Compile:',name,json.dumps(result),flush=True)
                if not result['Success']:raise RuntimeError('Native compilation failed: '+name)
            status=native.call('editor_status');scenes=native.call('list_scenes')['Scenes']
            if not any(s['ResourcePath']=='scenes/maps/belltower/belltower.scene' for s in scenes):
                if status['IsPlaying']:raise RuntimeError('Belltower document closed during another map play session.')
                native.call('open_scene',{'path':'scenes/maps/belltower/belltower.scene'})
                native.call('switch_scene',{'scene':status['ActiveScenePath']})
            print('Before:',json.dumps(capture('before',False)),flush=True)
            print('After:',json.dumps(capture('after',True)),flush=True)
        finally:
            if cleanup.poll() is None:cleanup.terminate()
            cleanup.communicate(timeout=25)
    elif mode=='import':print(json.dumps(native.script(HERE/'import.cs.txt','import'),indent=2))
    elif mode=='compile':
        for name in ('menu_board','west_without_menu_board'):
            print(name,json.dumps(native.call('asset_compile',{'path':f'models/maps/belltower/menu-board-v2/{name}.vmdl'},'compile-'+name)))
    elif mode in ('before','after'):print(json.dumps(capture(mode,mode=='after'),indent=2))
    else:raise ValueError(mode)
