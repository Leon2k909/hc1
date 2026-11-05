"""Native import and isolated review; no writes to the saved map."""
from pathlib import Path
import json,sys,hashlib
sys.dont_write_bytecode=True
ROOT=Path(__file__).absolute().parents[3];HERE=Path(__file__).absolute().parent
sys.path.insert(0,str(ROOT/'Sources/Spillway/hose-coil-v2'))
from native import Editor
OUT=ROOT/'output/riverside/still-here-board-v1';mode=sys.argv[1]
with Editor() as e:
    if mode=='import':
        m=json.loads((OUT/'manifest.json').read_text())
        sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
        scene='Assets/scenes/maps/Riverside/riverside.scene'
        # Other chats may save unrelated scene work. This import never writes the scene; geometry guards stay strict.
        assert all(sha(ROOT/p)==h for p,h in m['protected'].items() if p!=scene),'Store source changed; rebuild the review.'
        m['protected'][scene]=sha(ROOT/scene)
        (OUT/'manifest.json').write_text(json.dumps(m,indent=2))
        r=e.script((HERE/'import.cs.txt').read_text(),'import-ladder.cs')
        (OUT/'native-import.json').write_text(json.dumps(r,indent=2));print(json.dumps(r),flush=True)
        m=json.loads((OUT/'manifest.json').read_text())
        paths=[p[7:] for p in m['files'] if p.endswith('.vmat')]+[m['resource'],m['background'],'models/props/riverside/still_here_board_v1/legacy_board.vmdl']
        results=[dict(path=p,result=e.call('asset_compile',dict(path=p))) for p in paths]
        (OUT/'native-compile.json').write_text(json.dumps(results,indent=2))
        assert all(i['result']['Success'] for i in results)
        print(json.dumps(dict(Compiled=len(results),Success=True)))
    elif mode=='isolated':
        code=r'''
var session=Editor.SceneEditorSession.Active;var before=new{Id=session.Scene.Id,Dirty=session.HasUnsavedChanges,Game.IsPlaying};
var output=System.IO.Path.Combine(Sandbox.Project.Current.GetRootPath(),"output/riverside/still-here-board-v1");
var paths=new System.Collections.Generic.List<string>();
foreach(var variant in new[]{"before","after"})
{
    var model=Model.Load("models/props/riverside/still_here_board_v1/"+(variant=="before"?"legacy_board.vmdl":"board.vmdl"));
    if(model.IsError)throw new Exception("Fixture failed to load");
    var world=new SceneWorld();
    try
    {
        var item=new SceneObject(world,model,Transform.Zero);
        foreach(var mat in model.Materials)
            foreach(var tex in new[]{"g_tColor","g_tNormal","g_tRoughness"}.Select(mat.GetTexture).Append(mat.FirstTexture).Where(t=>t is not null).Distinct())tex.MarkUsed(1024);
        await Task.Delay(500,cancellationToken);
        var key=new SceneLight(world,new Vector3(-90,-80,100),500,Color.White*3f);
        var fill=new SceneLight(world,new Vector3(-40,100,-20),500,new Color(.75f,.85f,1f)*1.5f);
        foreach(var (name,eye) in new[]{("overview",new Vector3(-135,-85,45)),("detail",new Vector3(-100,-40,15)),("rear",new Vector3(110,80,35))})
        {
            var aim=Vector3.Zero;
            var camera=new SceneCamera("Reclaimed board review") { World=world,Position=eye,Rotation=Rotation.LookAt(aim-eye),
                FieldOfView=48,ZNear=.1f,ZFar=1500,Size=new Vector2(1200,900),AmbientLightColor=Color.White*.24f,
                BackgroundColor=new Color(.055f,.065f,.075f),AntiAliasing=true,EnablePostProcessing=true};
            var pixmap=new Editor.Pixmap(1200,900);Sandbox.SandboxToolExtensions.RenderToPixmap(camera,pixmap,false);
            var path=System.IO.Path.Combine(output,name+"-"+variant+".png");pixmap.SavePng(path);paths.Add(path);
        }
    }
    finally{world.Delete();}
}
return new{PreviewOnly=true,UserStatePreserved=session.Scene.Id==before.Id&&session.HasUnsavedChanges==before.Dirty&&Game.IsPlaying==before.IsPlaying,Images=paths};
'''
        r=e.script(code,'capture-ladder-isolated.cs')
        assert r['UserStatePreserved'];(OUT/'isolated-capture.json').write_text(json.dumps(r,indent=2));print(json.dumps(r,indent=2))
    elif mode=='context':
        r=e.script((HERE/'context.cs.txt').read_text(),'capture-ladder-context.cs')
        (OUT/'context-capture.json').write_text(json.dumps(r,indent=2));print(json.dumps(r,indent=2))
        assert r['SourceUnchanged'] and not r['ErrorModels']
