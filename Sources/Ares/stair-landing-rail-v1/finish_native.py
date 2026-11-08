from pathlib import Path
import sys,json
ROOT=Path(__file__).resolve().parents[3];OUT=ROOT/'output/ares/stair-landing-rail-v1'
sys.path.insert(0,str(ROOT/'Sources/Ares/surface-finish-v2'));import native
result=native.call('asset_compile',dict(path='models/maps/ares/ares_hall.vmdl'));assert result.get('Success'),result;print(result)
result=native.script(Path(__file__).with_name('capture_installed.cs.txt'));assert result['Installed'] and result['ModelsValid'] and result['AddedColliders']==0 and result['PlayerFloorHit'] and abs(result['PlayerFloorZ']-208)<.01,result;print(result)
receipt=json.loads((OUT/'installed.json').read_text());receipt['PublicHallRecompile']='complete';receipt['NativeInstalledCapture']=True;(OUT/'installed.json').write_text(json.dumps(receipt,indent=2))
