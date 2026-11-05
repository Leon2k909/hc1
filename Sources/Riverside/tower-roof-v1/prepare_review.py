from pathlib import Path
HERE=Path(__file__).absolute().parent;OLD=HERE.parent/'still-here-board-v1'
def rename(t):return t.replace('still-here-board-v1','tower-roof-v1').replace('still_here_board_v1','tower_roof_v1').replace('dressing_without_board','dressing_without_roof').replace('legacy_board','legacy_roof').replace('board_lod','roof_lod').replace('board.vmdl','roof.vmdl')
for f in ('import.cs.txt','verify.py'):(HERE/f).write_text(rename((OLD/f).read_text()))
t=rename((OLD/'review.py').read_text());a=t.index('var key=new SceneLight');b=t.index('            var pixmap=',a)
t=t[:a]+'''var key=new SceneLight(world,new Vector3(-100,-120,180),900,Color.White*7f);
        var fill=new SceneLight(world,new Vector3(130,100,-70),900,new Color(.75f,.85f,1f)*3f);
        foreach(var (name,eye) in new[]{("overview",new Vector3(-160,-190,150)),("detail",new Vector3(-100,-100,65)),("rear",new Vector3(130,150,-90))})
        {
            var aim=Vector3.Zero;
            var camera=new SceneCamera("Corrugated tower roof review") { World=world,Position=eye,Rotation=Rotation.LookAt(aim-eye),
                FieldOfView=48,ZNear=.1f,ZFar=2000,Size=new Vector2(1200,900),AmbientLightColor=Color.White*.24f,
                BackgroundColor=new Color(.055f,.065f,.075f),AntiAliasing=true,EnablePostProcessing=true};
'''+t[b:];(HERE/'review.py').write_text(t)
code=rename((OLD/'context.cs.txt').read_text());a=code.index('var views=new');b=code.index('\nvar scene = ',a)
code=code[:a]+'''var views=new (string Name,Vector3 Eye,Vector3 Target,float Fov,bool Cooler)[]
{
    ("close",Local(-210,-200,150),at,50f,true),
    ("underside",Local(-170,-200,-85),Local(0,0,-4),55f,true)
};
'''+code[b:];(HERE/'context.cs.txt').write_text(code)
t=rename((OLD/'compose.py').read_text()).replace('STILL HERE BOARD - RECLAIMED PLANK REBUILD','GUARD TOWER - CORRUGATED ROOF CANOPY').replace('same sign, camera','same tower, camera');(HERE/'compose.py').write_text(t)
