from pathlib import Path
ROOT=Path('C:/sbox-projects/hc1/forked-shooter-main');HERE=Path(__file__).parent
for name in ('native.py','import.cs.txt','capture.py'):
    s=(ROOT/f'Sources/Riverside/neon-sign-v1/{name}').read_text(encoding='utf-8').replace('neon-sign-review','roof-ladder-review').replace('neon-sign-v1','roof-ladder-v1');(HERE/name).write_text(s,encoding='utf-8')
s=(ROOT/'Sources/Riverside/neon-sign-v1/runtime-review.cs.txt').read_text(encoding='utf-8').replace('neon-sign-review','roof-ladder-review').replace('neon-sign-v1','roof-ladder-v1').replace('riverside_dressing.vmdl','riverside_levee.vmdl').replace('dressing_without_neon.vmdl','levee_without_ladder.vmdl').replace('neon_sign.vmdl','ladder.vmdl').replace('1150,60,0','407,-697,96').replace('Rotation.FromYaw(2.8624052f)','Rotation.FromYaw(90f)').replace('foreach(var view in new[]{"front"})','foreach(var view in new[]{"whole","detail"})')
a=s.index('var lightSettings=');b=s.index('var gameplay=',a);s=s[:a]+s[b:]
a=s.index('   camera.WorldPosition=');b=s.index('   foreach(var variant',a)
s=s[:a]+'''   camera.WorldPosition=view=="whole"?new Vector3(300,-850,210):new Vector3(392,-750,310);
   var target=view=="whole"?new Vector3(427,-697,215):new Vector3(443,-697,320);
   camera.WorldRotation=Rotation.LookAt(target-camera.WorldPosition);camera.FieldOfView=view=="whole"?72:52;
'''+s[b:]
a=s.index(' var afterLights=');b=s.index(' var errors=',a);s=s[:a]+s[b:];s=s.replace('ExistingNeonLightsUnchanged=true,','').replace(',Lights=lightSettings','')
(HERE/'runtime-review.cs.txt').write_text(s,encoding='utf-8')
s=(ROOT/'Sources/Riverside/neon-sign-v1/check_geometry.py').read_text().replace('neon-sign-v1','roof-ladder-v1').replace('neon_lod','ladder_lod');s=s.replace('np.max(abs(v[:,0]))<=57.001','np.max(abs(v[:,0]))<13').replace('v[:,1].max()<476','v[:,1].max()<243').replace('np.max(abs(v[:,2]))<9','np.max(abs(v[:,2]))<55');(HERE/'check_geometry.py').write_text(s)
