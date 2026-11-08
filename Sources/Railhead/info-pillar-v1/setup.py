from pathlib import Path
import json
ROOT=Path(__file__).absolute().parents[3];HERE=Path(__file__).parent;OUT=ROOT/'output/railhead/info-pillar-v1'
src=(ROOT/'Sources/Ares/control-console-native-v1/import.cs.txt').read_text().replace('output/ares/control-console-native-v1','output/railhead/info-pillar-v1').replace('models/props/ares/control_console_native_v1/','models/props/railhead/info_pillar_v1/').replace('materials/ares/control_console_native_v1/','models/props/railhead/info_pillar_v1/').replace('ExistingCandidateReused=true','NewGeometry=true')
(HERE/'import.cs.txt').write_text(src)
src=(ROOT/'Sources/Ares/control-console-native-v1/capture.cs.txt').read_text().replace('output/ares/control-console-native-v1/native','output/railhead/info-pillar-v1/native').replace('Assets/scenes/maps/Ares/ares.scene','Assets/scenes/maps/Railhead/railhead.scene').replace('models/maps/ares/ares_dressing.vmdl','models/maps/railhead/railhead_dress_centre.vmdl').replace('models/props/ares/control_console_native_v1/preview.vmdl','models/props/railhead/info_pillar_v1/preview.vmdl').replace('models/props/ares/control_console_native_v1/console.vmdl','models/props/railhead/info_pillar_v1/pillar.vmdl').replace('new Vector3(-440,-230,0)','new Vector3(1500,0,0)').replace('Console review','Information pillar review').replace('ReusedExistingCandidate=true','NewGeometry=true')
src=src.replace('"Ares","Lights","Reflection Probes","Ares bounced lighting"','"Station","Lights","Reflection Probes","Station Indirect Light","Volumetric Haze"')
start=src.index(' var views=');end=src.index('\n foreach(var after',start)
src=src[:start]+''' var views=new[]{("player",new Vector3(1620,-50,64),new Vector3(1500,0,51),55f),("detail",new Vector3(1550,-24,60),new Vector3(1500,0,53),45f)};'''+src[end:]
src=src.replace('new Vector3(-540,-290,64),new Vector3(-540,-290,-20)','new Vector3(1620,-50,64),new Vector3(1620,-50,-20)')
where=src.index(' var trace=');src=src[:where]+''' for(var lod=1;lod<3;lod++){using var bitmap=new Bitmap(1200,1000);using(scene.Push()){replacement.LodOverride=lod;scene.EditorTick(.016f,.016f);preRender?.Invoke(scene,null);preCamera?.Invoke(scene,null);camera.RenderToBitmap(bitmap,false);}System.IO.File.WriteAllBytes(System.IO.Path.Combine(output,"detail-lod"+lod+".png"),bitmap.ToPng());}
'''+src[where:]
src=src.replace('Triangles=info.Meshes.Sum(m=>m.Triangles)','LodTriangles=Enumerable.Range(0,info.LodCount).Select(l=>info.Meshes.Where(m=>(m.LodMask&(1<<l))!=0).Sum(m=>m.Triangles)).ToArray()')
(HERE/'capture.cs.txt').write_text(src)
plan=json.loads((OUT/'manifest.json').read_text());(OUT/'compile.json').write_text(json.dumps({'calls':[{'name':'asset_compile','arguments':{'path':p,'full':True}} for p in plan['files'] if p.endswith('.vmdl')]}))
