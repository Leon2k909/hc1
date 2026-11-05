from pathlib import Path
HERE=Path(__file__).absolute().parent;OLD=HERE.parent/'tower-ladder-v1'
def rename(t):return t.replace('tower-ladder-v1','still-here-board-v1').replace('tower_ladder_v1','still_here_board_v1').replace('dressing_without_ladder','dressing_without_board').replace('legacy_ladder','legacy_board').replace('ladder_lod','board_lod').replace('ladder.vmdl','board.vmdl')
for f in ('import.cs.txt','verify.py'):
 t=rename((OLD/f).read_text());t='\n'.join(l for l in t.splitlines() if "assert sha(ROOT/manifest['reused_approved_design'])" not in l);(HERE/f).write_text(t)
t=rename((OLD/'review.py').read_text());a=t.index('var key=new SceneLight');b=t.index('            var pixmap=',a)
t=t[:a]+'''var key=new SceneLight(world,new Vector3(-90,-80,100),500,Color.White*3f);
        var fill=new SceneLight(world,new Vector3(-40,100,-20),500,new Color(.75f,.85f,1f)*1.5f);
        foreach(var (name,eye) in new[]{("overview",new Vector3(-135,-85,45)),("detail",new Vector3(-100,-40,15)),("rear",new Vector3(110,80,35))})
        {
            var aim=Vector3.Zero;
            var camera=new SceneCamera("Reclaimed board review") { World=world,Position=eye,Rotation=Rotation.LookAt(aim-eye),
                FieldOfView=48,ZNear=.1f,ZFar=1500,Size=new Vector2(1200,900),AmbientLightColor=Color.White*.24f,
                BackgroundColor=new Color(.055f,.065f,.075f),AntiAliasing=true,EnablePostProcessing=true};
'''+t[b:];(HERE/'review.py').write_text(t)
code=rename((OLD/'context.cs.txt').read_text());a=code.index('var views=new');b=code.index('\nvar scene = ',a)
code=code[:a]+'''var views=new (string Name,Vector3 Eye,Vector3 Target,float Fov,bool Cooler)[]
{
    ("close",Local(-130,-85,55),at,48f,true),
    ("sign",Local(-450,-130,65),Local(0,0,25),60f,true)
};
'''+code[b:];(HERE/'context.cs.txt').write_text(code)
t=rename((OLD/'compose.py').read_text()).replace("f'detail-{version}.png'","f'overview-{version}.png'").replace("f'tower-{version}.png'","f'close-{version}.png'").replace('GUARD-TOWER LADDER - APPROVED LOWTIDE DESIGN FITTED TO RIVERSIDE','STILL HERE BOARD - RECLAIMED PLANK REBUILD');(HERE/'compose.py').write_text(t)
