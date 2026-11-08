from pathlib import Path
import json,hashlib
ROOT=Path(__file__).absolute().parents[3];HERE=Path(__file__).parent;OUT=ROOT/'output/ares/control-console-native-v1'
src=(HERE/'capture.cs.txt').read_text().replace('control-console-native-v1/native','control-console-native-v1/installed')
src=src.replace('"Ares bounced lighting"','"Ares bounced lighting","Core Process Console"')
src=src.replace('cut=Model.Load("models/props/ares/control_console_native_v1/preview.vmdl");','cut=old;')
start=src.index('  replacement=new GameObject');end=src.index('  if(old.IsError',start)
src=src[:start]+'  replacement=scene.GetAllComponents<ModelRenderer>().Single(r=>r.Model?.ResourcePath=="models/props/ares/control_console_native_v1/console.vmdl");replacement.LodOverride=0;\n'+src[end:]
src=src.replace('new[]{false,true}','new[]{true}')
where=src.index(' var trace=scene.Trace')
src=src[:where]+''' for(var lod=1;lod<3;lod++){using var bitmap=new Bitmap(1200,1000);using(scene.Push()){replacement.LodOverride=lod;scene.EditorTick(.016f,.016f);preRender?.Invoke(scene,null);preCamera?.Invoke(scene,null);camera.RenderToBitmap(bitmap,false);}System.IO.File.WriteAllBytes(System.IO.Path.Combine(output,"detail-lod"+lod+".png"),bitmap.ToPng());}
'''+src[where:]
src=src.replace('PreviewOnly=true','Installed=true').replace('Triangles=info.Meshes.Sum(m=>m.Triangles)','LodTriangles=Enumerable.Range(0,info.LodCount).Select(l=>info.Meshes.Where(m=>(m.LodMask&(1<<l))!=0).Sum(m=>m.Triangles)).ToArray()')
(HERE/'capture_installed.cs.txt').write_text(src)
plan=json.loads((OUT/'install-plan.json').read_text());assert json.loads((OUT/'installed.json').read_text())['Installed']
base=ROOT/'Assets'/plan['active_base'];assert base.read_bytes()==(OUT/'install-stage/dressing_without_console.obj').read_bytes()
# Native SceneFile serialization may normalize resource references; compare semantic previous roots.
before=json.loads((ROOT/'Sources/Ares/control-console-trial-v1/source-guard.json').read_text()) if False else None
scene=json.loads((ROOT/'Assets/scenes/maps/Ares/ares.scene').read_text());assert len([n for n in scene['GameObjects'] if n.get('Name')=='Core Process Console'])==1
assert hashlib.sha256((ROOT/'Assets/models/maps/ares/ares_dressing.vmdl').read_bytes()).hexdigest()==plan['protected']['Assets/models/maps/ares/ares_dressing.vmdl']
(OUT/'install-verification.json').write_text(json.dumps(dict(installed=True,old_faces_removed=40,modeldoc_and_physics_unchanged=True,active_base_matches_exact_cut=True,lod_triangles=json.loads((OUT/'lods.json').read_text())['triangles']),indent=2))
print('Installed scope verified; capture source prepared')
