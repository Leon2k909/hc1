"""Prepare this prop's native import, geometry check and matching engine capture scripts."""
from pathlib import Path
HERE=Path(__file__).absolute().parent;ROOT=HERE.parents[2];OLD=HERE.parent/'tv-aerial-v1'
def rename(t):return t.replace('tv-aerial-v1','trailer-hitch-v1').replace('tv_aerial_v1','trailer_hitch_v1').replace('legacy_aerial','legacy_hitch').replace('aerial.vmdl','hitch.vmdl').replace('aerial_lod','hitch_lod').replace('low_without_aerial','low_without_hitch')
(HERE/'import.cs.txt').write_text(rename((OLD/'import.cs.txt').read_text()))
(HERE/'verify.py').write_text(rename((OLD/'verify.py').read_text()).replace('<6500','<10000'))
t=rename((OLD/'review.py').read_text()).replace('import-aerial','import-hitch').replace('capture-aerial','capture-hitch')
a=t.index('var key=new SceneLight');b=t.index('            var pixmap=',a)
t=t[:a]+'''var key=new SceneLight(world,new Vector3(50,60,80),250,Color.White*1.8f);
        var fill=new SceneLight(world,new Vector3(-70,30,45),250,new Color(.75f,.85f,1f)*.8f);
        foreach(var (name,eye) in new[]{("overview",new Vector3(68,100,68)),("detail",new Vector3(36,88,43))})
        {
            var aim=name=="detail"?new Vector3(0,43,15):new Vector3(0,27,15);
            var camera=new SceneCamera("Trailer hitch review") { World=world,Position=eye,Rotation=Rotation.LookAt(aim-eye),
                FieldOfView=name=="detail"?45:46,ZNear=.1f,ZFar=500,Size=new Vector2(1200,900),AmbientLightColor=Color.White*.2f,
                BackgroundColor=new Color(.055f,.065f,.075f),AntiAliasing=true,EnablePostProcessing=true};
'''+t[b:]
t=t.replace('var item=new SceneObject(world,model,Transform.Zero);','''var item=new SceneObject(world,model,Transform.Zero);
        foreach(var mat in model.Materials)
            foreach(var tex in new[]{"g_tColor","g_tNormal","g_tRoughness"}.Select(mat.GetTexture).Append(mat.FirstTexture).Where(t=>t is not null).Distinct())tex.MarkUsed(1024);
        await Task.Delay(500,cancellationToken);''')
t=t.replace("        assert r['SourceUnchanged'] and not r['ErrorModels']\n        (OUT/'context-capture.json').write_text(json.dumps(r,indent=2));print(json.dumps(r,indent=2))", "        (OUT/'context-capture.json').write_text(json.dumps(r,indent=2));print(json.dumps(r,indent=2))\n        assert r['SourceUnchanged'] and not r['ErrorModels']")
(HERE/'review.py').write_text(t)
code=rename((OLD/'context.cs.txt').read_text())
code=code.replace('"Street Lights"','"Streetlight Heads", "Roof TV Aerials", "Propane Cylinders", "Lawn Chairs", "Supply Crates", "Sandbags", "Speed-Limit Signs", "Porch Lights"')
a=code.index('var at=new Vector3');b=code.index('\nvar scene = ',a)
code=code[:a]+'''var at=new Vector3(1050f,1030f,0f);
var views=new (string Name,Vector3 Eye,Vector3 Target,float Fov,bool Cooler)[]
{
    ("close",at+new Vector3(44,90,44),at+new Vector3(0,35,15),52f,true),
    ("parked",at+new Vector3(95,120,62),at+new Vector3(0,26,12),48f,true)
};
'''+code[b:]
(HERE/'context.cs.txt').write_text(code)
print('Native review scripts prepared')
