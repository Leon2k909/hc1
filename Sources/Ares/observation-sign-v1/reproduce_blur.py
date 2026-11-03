from pathlib import Path
import json,numpy as np
from PIL import Image
from native import ROOT,OUT,script
HERE=Path(__file__).parent
target=OUT/'sharpness-fix';target.mkdir(exist_ok=True)
attachment=Path('C:/Users/leon2/AppData/Local/Temp/codex-clipboard-4a918cce-4c8c-4a48-bf7e-6f613add6432.png')
a=np.asarray(Image.open(attachment).convert('RGB')).astype(float)
for name in ('detail-installed.png','detail-after.png'):
 b=np.asarray(Image.open(OUT/name).convert('RGB')).astype(float)
 print(name,'difference from user image',float(np.abs(a-b).mean()),flush=True)
src=(HERE/'capture.cs.txt').read_text().replace('output/ares/observation-sign-v1','output/ares/observation-sign-v1/sharpness-fix')
src=src.replace('if(variants.Contains("after"))','if(true)')
src=src.replace('variant=="after"','variant=="separate"')
start=src.index(' foreach(var material in models.Distinct()')
end=src.index(' for(var frame=0;frame<40;frame++)',start)
src=src[:start]+src[end:]
src=src.replace('frame<12','frame<90')
(HERE/'natural-capture.cs.txt').write_text(src)
config=json.loads((OUT/'capture-config.json').read_text());config['variants']=['integrated','separate']
(target/'capture-config.json').write_text(json.dumps(config,indent=2))
print(json.dumps(script(HERE/'natural-capture.cs.txt'),indent=2))
