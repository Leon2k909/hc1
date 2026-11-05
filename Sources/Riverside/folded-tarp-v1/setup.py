from pathlib import Path
ROOT=Path('C:/sbox-projects/hc1/forked-shooter-main');HERE=Path(__file__).parent
for name in ('native.py','import.cs.txt','capture.py'):
    s=(ROOT/f'Sources/Riverside/roof-ladder-v1/{name}').read_text(encoding='utf-8').replace('roof-ladder-review','folded-tarp-review').replace('roof-ladder-v1','folded-tarp-v1');(HERE/name).write_text(s,encoding='utf-8')
s=(ROOT/'Sources/Riverside/roof-ladder-v1/runtime-review.cs.txt').read_text(encoding='utf-8').replace('roof-ladder-review','folded-tarp-review').replace('roof-ladder-v1','folded-tarp-v1').replace('levee_without_ladder','levee_without_tarp').replace('/ladder.vmdl','/tarp.vmdl').replace('407,-697,96','607,-737,314').replace('new[]{"whole","detail"}','new[]{"whole"}')
a=s.index('   camera.WorldPosition=');b=s.index('   foreach(var variant',a);s=s[:a]+'''   camera.WorldPosition=new Vector3(700,-850,425);
   camera.WorldRotation=Rotation.LookAt(new Vector3(607,-737,317)-camera.WorldPosition);camera.FieldOfView=46;
'''+s[b:];(HERE/'runtime-review.cs.txt').write_text(s,encoding='utf-8')
s=(ROOT/'Sources/Riverside/roof-ladder-v1/studio.cs.txt').read_text(encoding='utf-8').replace('roof-ladder-review','folded-tarp-review').replace('roof-ladder-v1','folded-tarp-v1').replace('legacy_ladder.vmdl','legacy_tarp.vmdl').replace('"ladder.vmdl"','"tarp.vmdl"').replace('(-80,130,270)','(-70,-30,140)').replace('(200,-200,100)','(90,100,100)')
a=s.index('   var eye=');b=s.index('   var pix=',a);s=s[:a]+'''   var eye=view=="whole"?new Vector3(105,-120,105):new Vector3(65,-70,35);var target=view=="whole"?new Vector3(0,0,1):new Vector3(31,-31,4);
   var camera=new SceneCamera("Folded tarp studio") {World=world,Position=eye,Rotation=Rotation.LookAt(target-eye),FieldOfView=view=="whole"?42:40,ZNear=2,ZFar=1500,Size=new Vector2(1200,1000),AmbientLightColor=new Color(.12f,.14f,.17f),BackgroundColor=new Color(.04f,.05f,.065f),AntiAliasing=true,EnablePostProcessing=true};
'''+s[b:];(HERE/'studio.cs.txt').write_text(s,encoding='utf-8')
s=(ROOT/'Sources/Riverside/roof-ladder-v1/check_geometry.py').read_text().replace('roof-ladder-v1','folded-tarp-v1').replace('ladder_lod','tarp_lod').replace('np.max(abs(v[:,0]))<55','np.max(abs(v[:,0]))<41').replace('v[:,1].min()>=0','v[:,1].min()>-4').replace('v[:,1].max()<243','v[:,1].max()<9').replace('np.max(abs(v[:,2]))<13','np.max(abs(v[:,2]))<41');(HERE/'check_geometry.py').write_text(s)
