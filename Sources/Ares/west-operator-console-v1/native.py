from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent
sys.path.insert(0,str(ROOT/'Sources/Ares/surface-finish-v2'));import native
text=(ROOT/'Sources/Ares/control-console-native-v1/import.cs.txt').read_text().replace('control-console-native-v1','west-operator-console-v1').replace('control_console_native_v1','west_operator_console_v1')
(HERE/'import.cs.txt').write_text(text)
if '--capture-only' not in sys.argv:
 print(native.script(HERE/'import.cs.txt'))
 for p in ('models/props/ares/west_operator_console_v1/after.vmdl','models/props/ares/west_operator_console_v1/preview.vmdl'):print(native.call('asset_compile',dict(path=p)))
text=(ROOT/'Sources/Ares/control-console-native-v1/capture.cs.txt').read_text().replace('control-console-native-v1','west-operator-console-v1').replace('control_console_native_v1','west_operator_console_v1').replace('console.vmdl','after.vmdl').replace('"models/maps/ares/ares_dressing.vmdl"','"models/maps/ares/ares_hall.vmdl"').replace('new Vector3(-440,-230,0)','new Vector3(240,1074,0)').replace('Console review','Operator console review')
text=text.replace('replacement.LodOverride=0;','replacement.LodOverride=0;replacement.WorldRotation=Rotation.From(0,90,0);')
text=text.replace('"Ares bounced lighting"','"Ares bounced lighting","Core Process Console","Lower Hall Bulkhead Lamp","West Control Room Display","West Stair Landing Rail","ARES transport cases"')
text=text.replace('var views=new[]{("player",new Vector3(-540,-290,64),new Vector3(-440,-230,38),50f),("detail",new Vector3(-494,-255,57),new Vector3(-438,-230,40),55f)};', 'var views=new[]{("player",new Vector3(195,974,64),new Vector3(240,1074,38),52f),("detail",new Vector3(214,1013,60),new Vector3(240,1074,39),60f)};')
text=text.replace('Triangles=info.Meshes.Sum(m=>m.Triangles),','LodTriangles=Enumerable.Range(0,info.LodCount).Select(l=>info.Meshes.Where(m=>(m.LodMask&(1<<l))!=0).Sum(m=>m.Triangles)).ToArray(),')
(HERE/'capture.cs.txt').write_text(text);print(native.script(HERE/'capture.cs.txt'))
