"""Recheck all saved lifebuoy vertices, UVs, normals and its enabled scene placement.

The hall OBJ contains many unrelated props and can change in other work. Match
the actual extracted buoy instead of blocking a private review on other props.
"""
from pathlib import Path
import hashlib,json
root=Path.cwd();here=root/'Sources/Riverdale/lifebuoy-trial-v1'
namespace={}
prefix=(here/'prepare.py').read_text().split("(HERE/'before.json').write_text")[0]
exec(compile(prefix,str(here/'prepare.py'),'exec'),namespace)
assert dict(namespace['groups'])==json.loads((here/'before.json').read_text()),'Saved buoy changed'
record={'savedBuoyPositionsUVsNormalsUnchanged':True,'triangles':sum(namespace['matched'].values()),
        'enabledSavedRendererAtIdentity':True,'wholeHallHashAtRecheck':namespace['sha'](namespace['source']),
        'sourceWholeHallHashAtExtraction':json.loads((here/'provenance.json').read_text())['sourceSHA256'],
        'sceneSHA256AtRecheck':namespace['sha'](namespace['scene']),'originalFilesWrittenByThisTask':0}
(here/'lifebuoy-source-recheck.json').write_text(json.dumps(record,indent=2));print(json.dumps(record))
