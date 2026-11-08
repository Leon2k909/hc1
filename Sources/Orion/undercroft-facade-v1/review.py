from pathlib import Path
import sys,json
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent;OUT=ROOT/'output/orion/undercroft-facade-v1';base=ROOT/'Sources/Railhead/help-point-v1'
(HERE/'native.py').write_text((base/'native.py').read_text().replace('railhead/help-point-v1','orion/undercroft-facade-v1').replace('railhead-help-point','orion-facade-review'))
sys.path.insert(0,str(HERE));import native
text=(base/'import.cs.txt').read_text().replace('output/railhead/help-point-v1','output/orion/undercroft-facade-v1').replace('Assets/models/props/railhead/help_point_v1/','Assets/models/props/orion/undercroft_facade_v1/').replace('Assets/materials/railhead/help_point_v1/','Assets/materials/orion/undercroft_facade_v1/')
(HERE/'import.cs.txt').write_text(text);print(native.script(HERE/'import.cs.txt'))
print(native.call('asset_compile',dict(path='materials/orion/undercroft_facade_v1/label.vmat')))
for name in ('facade','preview'):print(native.call('asset_compile',dict(path=f'models/props/orion/undercroft_facade_v1/{name}.vmdl')))
text=(base/'capture.cs.txt').read_text().replace('output/railhead/help-point-v1/native','output/orion/undercroft-facade-v1/native').replace('Assets/scenes/maps/Railhead/railhead.scene','Assets/scenes/maps/Orion/orion.scene')
start=text.index('var names=');end=text.index('\nvar roots=',start)
text=text[:start]+'var names=new[]{"Sun","Sky","Fog","Look","Orion","Lights","Volumetric Fog","Reflection Probes","Operator Chair","Orion Launch Vehicle"}.ToHashSet(StringComparer.OrdinalIgnoreCase);'+text[end:]
text=text.replace('models/maps/railhead/railhead_dress_west.vmdl','models/maps/orion/orion_launch_deck.vmdl').replace('models/props/railhead/help_point_v1/preview.vmdl','models/props/orion/undercroft_facade_v1/preview.vmdl').replace('models/props/railhead/help_point_v1/help_point.vmdl','models/props/orion/undercroft_facade_v1/facade.vmdl')
text=text.replace('  scene.Deserialize(data);','''  scene.Deserialize(data);
  // Identical light sources in both variants. Before: the original concrete
  // face occludes them. After: they illuminate the two constructed interiors.
  foreach(var y in new[]{380f,130f}){var holder=new GameObject(true,"Utility room ceiling light");holder.WorldPosition=new Vector3(926,y,90);var light=holder.AddComponent<PointLight>();light.Radius=90;light.LightColor=new Color(.9f,.82f,.65f);light.Shadows=true;}
''')
start=text.index(' var views=');end=text.index('\n foreach(var after',start)
text=text[:start]+''' var views=new[]{("context",new Vector3(710,315,64),new Vector3(900,315,60),105f),("detail",new Vector3(775,400,74),new Vector3(907,315,57),78f)};'''+text[end:]
text=text.replace('new Bitmap(view.Item1=="detail"?1000:900,1200)','new Bitmap(1800,1000)').replace('ExistingMaterialsReused=true','AcceptedFinishesReused=true,InteriorLights=2')
(HERE/'capture.cs.txt').write_text(text);print(native.script(HERE/'capture.cs.txt'))
