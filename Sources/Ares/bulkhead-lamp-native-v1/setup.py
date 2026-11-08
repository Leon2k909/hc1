from pathlib import Path
import json,sys
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent;OUT=ROOT/'output/ares/bulkhead-lamp-native-v1'
sys.path.insert(0,str(ROOT/'Sources/Ares/surface-finish-v2'));import native
text=(ROOT/'Sources/Ares/control-console-native-v1/import.cs.txt').read_text().replace('control-console-native-v1','bulkhead-lamp-native-v1').replace('control_console_native_v1','bulkhead_lamp_native_v1')
(HERE/'import.cs.txt').write_text(text)
print(native.script(HERE/'import.cs.txt'))
manifest=json.loads((OUT/'manifest.json').read_text())
for p in manifest['files']:
 if p.endswith(('.vmat','.vmdl')):print(p,native.call('asset_compile',dict(path=p)))
text=(ROOT/'Sources/Ares/control-console-native-v1/capture.cs.txt').read_text().replace('control-console-native-v1','bulkhead-lamp-native-v1').replace('control_console_native_v1','bulkhead_lamp_native_v1').replace('console.vmdl','lamp.vmdl').replace('Console review','Lamp review').replace('new Vector3(-440,-230,0)','new Vector3(-300,1100,120)')
text=text.replace('var views=new[]{("player",new Vector3(-540,-290,64),new Vector3(-440,-230,38),50f),("detail",new Vector3(-494,-255,57),new Vector3(-438,-230,40),55f)};', 'var views=new[]{("context",new Vector3(-330,1010,90),new Vector3(-300,1098,119),50f),("detail",new Vector3(-312,1070,119),new Vector3(-300,1098,120),40f)};')
(HERE/'capture.cs.txt').write_text(text)
print(native.script(HERE/'capture.cs.txt'))
