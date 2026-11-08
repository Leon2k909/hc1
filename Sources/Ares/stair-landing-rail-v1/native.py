from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent
sys.path.insert(0,str(ROOT/'Sources/Ares/surface-finish-v2'));import native
text=(ROOT/'Sources/Ares/control-console-native-v1/import.cs.txt').read_text().replace('control-console-native-v1','stair-landing-rail-v1').replace('control_console_native_v1','stair_landing_rail_v1')
(HERE/'import.cs.txt').write_text(text);print(native.script(HERE/'import.cs.txt'))
for p in ('models/props/ares/stair_landing_rail_v1/rail.vmdl','models/props/ares/stair_landing_rail_v1/preview.vmdl'):print(native.call('asset_compile',dict(path=p)))
text=(ROOT/'Sources/Ares/control-console-native-v1/capture.cs.txt').read_text().replace('control-console-native-v1','stair-landing-rail-v1').replace('control_console_native_v1','stair_landing_rail_v1').replace('console.vmdl','rail.vmdl').replace('"models/maps/ares/ares_dressing.vmdl"','"models/maps/ares/ares_hall.vmdl"').replace('new Vector3(-440,-230,0)','Vector3.Zero').replace('Console review','Railing review')
text=text.replace('"Ares bounced lighting"','"Ares bounced lighting","Core Process Console","Lower Hall Bulkhead Lamp","West Control Room Display","ARES transport cases"')
text=text.replace('var views=new[]{("player",new Vector3(-540,-290,64),new Vector3(-440,-230,38),50f),("detail",new Vector3(-494,-255,57),new Vector3(-438,-230,40),55f)};', 'var views=new[]{("player",new Vector3(-190,865,265),new Vector3(-119,760,229),55f),("detail",new Vector3(-112,712,226),new Vector3(-82,760,227),55f)};')
(HERE/'capture.cs.txt').write_text(text);print(native.script(HERE/'capture.cs.txt'))
