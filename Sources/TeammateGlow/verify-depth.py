"""Assert the actual rendered depth mask, including fully exposed geometry."""
import json
from pathlib import Path
import numpy as np
from PIL import Image

root=Path(__file__).resolve().parents[2]
folder=root/'output/teammate-glow/verified'
read=lambda name:np.asarray(Image.open(folder/f'{name}.png').convert('RGB')).astype(np.int16)
partial=np.abs(read('covered-on')-read('covered-off'))
visible=np.abs(read('visible-on')-read('visible-off'))
regions={'hidden_torso':(slice(260,400),slice(410,550)),
         'exposed_arm':(slice(200,240),slice(130,220)),
         'unoccupied_wall':(slice(430,500),slice(290,330))}
report={name:{'mean_channel_delta':float(partial[region].mean()),
              'maximum_channel_delta':int(partial[region].max())} for name,region in regions.items()}
report['fully_visible_maximum_channel_delta']=int(visible.max())
report['fully_visible_changed_pixels']=int(np.any(visible,axis=2).sum())
native=json.loads((folder/'native-result.json').read_text())
assert native['EditorStatePreserved']
assert 2<report['hidden_torso']['mean_channel_delta']<60
assert report['exposed_arm']['maximum_channel_delta']==0
assert report['unoccupied_wall']['maximum_channel_delta']==0
assert report['fully_visible_maximum_channel_delta']==0
assert native['Style']['VisibleEdge']=='0,0,0,0' and native['Style']['VisibleFill']=='0,0,0,0'
report['style']=native['Style'];report['editor_state_preserved']=True
(folder/'verification.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
