"""Native comparison of the complete wall fixture, with matched inspection lighting."""
from pathlib import Path
import ast,json,math,subprocess,sys,tempfile
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent
sys.path.insert(0,str(ROOT/'Sources/Belltower/terracotta-pot-v2'))
import native
OUT=Path(tempfile.gettempdir())/'belltower-wall-lantern-v2';native.OUT=OUT

def helper():
    text=(ROOT/'Sources/Belltower/bistro-table-v2/capture.cs.txt').read_text()
    text=text.replace('bistro-table-v2','wall-lantern-v2').replace('west_without_table.vmdl','west_without_lantern.vmdl').replace('bistro_table.vmdl','wall_lantern.vmdl')
    text=text.replace('new Vector3(-170,600,0)','new Vector3(475,1850,126)')
    text=text.replace('trialPot.WorldRotation=Rotation.Identity;','trialPot.WorldRotation=Rotation.From(Angles.Parse("0,180,0"));')
    text=text.replace('new Vector3(-230,520,75)','new Vector3(445,1910,140)').replace('Temporary bistro table comparison','Temporary wall lantern comparison')
    path=HERE/'capture.cs.txt';path.write_text(text);return path

def capture(name,candidate,position=(443,1915,127),target=(475,1858,116),fov=38):
    x,y,z=[b-a for a,b in zip(position,target)];angles=(math.degrees(math.atan2(-z,math.hypot(x,y))),math.degrees(math.atan2(y,x)),0)
    m=json.loads((OUT/'manifest.json').read_text())
    config={'directory':'review','name':name,'position':','.join(map(str,position)),'angles':','.join(map(str,angles)),'width':1280,'height':1024,'fov':fov,'exposure':1.5,'settle_ms':0,'candidate':candidate,'review_fill':True,'expected_scene_sha256':m['guards']['Assets/scenes/maps/Belltower/belltower.scene']}
    (OUT/'capture.json').write_text(json.dumps(config));return native.script(helper(),name)

def finalize():
    tree=ast.parse((ROOT/'Sources/Belltower/terracotta-pot-v2/finish_install.py').read_text())
    command=next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='command' for t in n.targets))
    cleanup=subprocess.Popen(['powershell','-NoProfile','-Command',command],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,creationflags=subprocess.CREATE_NO_WINDOW)
    try:
        print('Import:',native.script(HERE/'import.cs.txt','import'),flush=True)
        for name in ('wall_lantern','west_baseline','west_without_lantern'):
            result=native.call('asset_compile',{'path':f'models/maps/belltower/wall-lantern-v2/{name}.vmdl'},'compile-'+name)
            assert result['Success'],result;print('Compiled:',name,flush=True)
        status=native.call('editor_status');scenes=native.call('list_scenes')['Scenes']
        if not any(s['ResourcePath']=='scenes/maps/belltower/belltower.scene' for s in scenes):
            if status['IsPlaying']:raise RuntimeError('Belltower document closed while another map is playing.')
            native.call('open_scene',{'path':'scenes/maps/belltower/belltower.scene'});native.call('switch_scene',{'scene':status['ActiveScenePath']})
        for name,candidate in [('warm-baseline',False),('warm-trial',True),('before-final',False),('after-final',True)]:print(name,json.dumps(capture(name,candidate)['Restoration']),flush=True)
    finally:
        if cleanup.poll() is None:cleanup.terminate()
        cleanup.communicate(timeout=25)

if __name__=='__main__':finalize()
