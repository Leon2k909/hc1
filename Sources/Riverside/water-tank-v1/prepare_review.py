"""Create tank-specific native import and isolated capture scripts."""
from pathlib import Path
HERE=Path(__file__).absolute().parent;ROOT=HERE.parents[2];OLD=HERE.parent/'trailer-hitch-v1'
def rename(t):
    return t.replace('trailer-hitch-v1','water-tank-v1').replace('trailer_hitch_v1','water_tank_v1').replace('legacy_hitch','legacy_tank').replace('low_without_hitch','backdrop_without_tank').replace('hitch.vmdl','tank.vmdl').replace('hitch_lod','tank_lod')
(HERE/'import.cs.txt').write_text(rename((OLD/'import.cs.txt').read_text()))
(HERE/'verify.py').write_text(rename((OLD/'verify.py').read_text()).replace('<10000','<15000'))
t=rename((OLD/'review.py').read_text()).replace('import-hitch','import-tank').replace('capture-hitch','capture-tank')
a=t.index('var key=new SceneLight');b=t.index('            var pixmap=',a)
t=t[:a]+'''var key=new SceneLight(world,new Vector3(-400,650,700),2200,Color.White*60f);
        var fill=new SceneLight(world,new Vector3(700,-400,400),2200,new Color(.75f,.85f,1f)*25f);
        foreach(var (name,eye) in new[]{("overview",new Vector3(-650,750,700)),("detail",new Vector3(-350,480,650))})
        {
            var aim=name=="detail"?new Vector3(0,0,190):new Vector3(0,0,145);
            var camera=new SceneCamera("Water tower vessel review") { World=world,Position=eye,Rotation=Rotation.LookAt(aim-eye),
                FieldOfView=name=="detail"?50:46,ZNear=.1f,ZFar=5000,Size=new Vector2(1200,900),AmbientLightColor=Color.White*.2f,
                BackgroundColor=new Color(.055f,.065f,.075f),AntiAliasing=true,EnablePostProcessing=true};
'''+t[b:]
(HERE/'review.py').write_text(t)
code=rename((OLD/'context.cs.txt').read_text()).replace('models/maps/riverside/riverside_low.vmdl','models/maps/riverside/riverside_backdrop.vmdl')
code=code.replace('"Roof TV Aerials"','"Roof TV Aerials", "Trailer Hitches", "Trailer Entry Doors", "Campers"')
a=code.index('var at=new Vector3');b=code.index('\nvar scene = ',a)
code=code[:a]+'''var at=new Vector3(3600f,-1688f,1196f);
var views=new (string Name,Vector3 Eye,Vector3 Target,float Fov,bool Cooler)[]
{
    ("tank",at+new Vector3(-700,820,600),at+Vector3.Up*120,50f,true),
    ("landmark",at+new Vector3(-1900,2100,350),at-Vector3.Up*360,45f,true)
};
'''+code[b:]
(HERE/'context.cs.txt').write_text(code)
print('Tank native review scripts prepared')
