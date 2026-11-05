"""The same approved body/pin, without a tie where no cable exists."""
import json,runpy,sys
from pathlib import Path
ns=runpy.run_path(str(Path(__file__).with_name('build.py')),run_name='insulator_source')
counts=[]
for k in range(3):counts.append(ns['K'].write_obj(ns['OUT']/f'bare_lod{k}.obj',ns['make'](k,wire_tie=False),'pole_insulator_bare'))
ns['modeldoc']('pole_insulator_bare','bare')
(ns['REPORT']/'bare-mesh-report.json').write_text(json.dumps(dict(triangles=counts,same_approved_body=True,wire_tie=False),indent=2))
print('Bare variant LOD triangles:',counts)
