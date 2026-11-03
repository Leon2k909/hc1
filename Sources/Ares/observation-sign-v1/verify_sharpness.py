from pathlib import Path
import json,hashlib
import numpy as np
from PIL import Image
from native import ROOT,OUT,call
HERE=Path(__file__).parent
# Request no artificial mip residency. Give normal camera streaming enough frames.
for filename in ('baseline.cs.txt','capture.cs.txt'):
    p=HERE/filename;s=p.read_text()
    start=s.index(' foreach(var material in models.Distinct()')
    end=s.index(' for(var frame=0;frame<40;frame++)',start)
    s=s[:start]+s[end:];s=s.replace('frame<12','frame<90');p.write_text(s)
fixed=OUT/'sharpness-fix'
a=np.asarray(Image.open(OUT/'detail-after.png').convert('RGB')).astype(float)
b=np.asarray(Image.open(fixed/'detail-integrated.png').convert('RGB')).astype(float)
bad=np.asarray(Image.open(OUT/'detail-installed.png').convert('RGB')).astype(float)
roi=(slice(405,550),slice(475,1200))
error=float(np.abs(a[roi]-b[roi]).mean())
baderror=float(np.abs(a[roi]-bad[roi]).mean())
edge=lambda x:float(np.abs(np.diff(x[roi].mean(axis=2),axis=1)).mean())
assert error<3,(error,'Installed lettering differs from approval')
assert edge(b)>.9*edge(a),(edge(b),edge(a))
assert edge(b)>1.5*edge(bad),(edge(b),edge(bad))
receipt=json.loads((fixed/'capture-integrated-separate.json').read_text())
assert receipt['UserStatePreserved'] and not receipt['ErrorModels']
for name in ('detail','context'):
    (fixed/f'{name}-installed-ready.png').write_bytes((fixed/f'{name}-integrated.png').read_bytes())
report=dict(installed=True,approved_lettering_mean_error=error,previous_blurred_lettering_mean_error=baderror,approved_edge_detail=edge(a),installed_edge_detail=edge(b),previous_blurred_edge_detail=edge(bad),forced_texture_residency=False,frames_per_view=90,user_state_preserved=True,error_models=[],reason='Previous installed capture ran before normal texture streaming settled')
(fixed/'verification.json').write_text(json.dumps(report,indent=2))
old=json.loads((OUT/'installed.json').read_text());old['sharpness_verification']=report;old['capture']=receipt;old['previous_capture_rejected']=True
(OUT/'installed.json').write_text(json.dumps(old,indent=2))
print(json.dumps(report,indent=2))
