"""Verify the overlap check detects the captured v1 defect and accepts v2."""
import ast
import json
from pathlib import Path
import platform
import runpy
import sys
platform._wmi=None
sys.path.insert(0,'Tools')
import numpy as np
import belltower_gardens as G
from map_kit import Model

quality=Path('output/belltower/quality')
tree=ast.parse((quality/'check-garden-geometry.py').read_text())
function=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='check_cladding_planes')
scope={'np':np,'G':G,'surface_checks':[]}
exec(compile(ast.Module(body=[function],type_ignores=[]),'<trim-check>','exec'),scope)
old=runpy.run_path(str(quality/'garden-v2-before/source/belltower_gardens.py'))
records=[]
for name,args in [
    ('large-west',(-1840,-1720,-1440,-1340,-48,'+n',False)),
    ('large-east',(-420,-300,-1440,-1360,-48,'+n',False)),
    ('small-terrace',(-1440,-1380,-1090,-1030,-48,'+e',True)),
]:
    walls=((args[0],args[1]),(args[2],args[3]))
    previous,current=Model(),Model()
    old['shed'](previous,*args)
    G.shed(current,*args)
    try:
        scope['check_cladding_planes'](name,previous,walls)
    except AssertionError as error:
        old_defect=str(error)
    else:
        raise AssertionError('The check missed the captured v1 defect: '+name)
    scope['check_cladding_planes'](name,current,walls)
    records.append({'prop':name,'v1_overlap_detected':old_defect,'v2_overlap_absent':True})
(quality/'garden-v2-trim-regression.json').write_text(json.dumps(records,indent=2)+'\n')
print(json.dumps(records,indent=2))
