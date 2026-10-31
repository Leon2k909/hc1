"""Prepare a native, read-only location capture using the existing Orion workflow."""
from pathlib import Path
import json
ROOT=Path.cwd()
assert any(ROOT.glob('*.sbproj')),ROOT
HERE=ROOT/'output/asset-improvement-20261030/orion-cable-reel/location'
source=(ROOT/'Sources/Orion/v2/editor/capture.cs.txt').read_text()
source=source.replace('"output/orion/v2/captures"','"output/asset-improvement-20261030/orion-cable-reel/location"')
source=source.replace('texture.MarkUsed(4096)','texture.MarkUsed(1024)')
# This private workflow never has a menu-image or asset-writing branch.
begin=source.index('        if (view["art"]?.GetValue<bool>() == true)')
end=source.index('\n    }\n    var missing',begin)
source=source[:begin]+source[end:]
(HERE/'capture.cs.txt').write_text(source,encoding='utf-8')
config={'scene':'Assets/scenes/maps/Orion/orion.scene','fixed_exposure':1.2,
    'width':1600,'height':1100,'stream_frames':18,'settle_frames':18,
    'views':[
        {'name':'original-location-close','eye':[560,1120,385],'target':[380,1320,262],'fov':55},
        {'name':'original-location-wide','eye':[900,650,560],'target':[300,1260,250],'fov':62}
    ]}
(HERE/'config.json').write_text(json.dumps(config,indent=2))
(HERE/'exchange-args.json').write_text(json.dumps({'code':'return exchangeDirectory;'}))
print('Prepared two native views of the original saved Orion scene; no game writes.')
