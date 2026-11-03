from pathlib import Path
import sys,json,hashlib
HERE=Path(__file__).parent;sys.path.insert(0,str(HERE))
import build as B
wall=B.K.Model()
wall.box((-25,.03,-7),(25,2,9.5),'rv_hall_epoxy')
wall.box((-25,.03,9.5),(25,2,10.05),'rv_hall_joint')
wall.box((-25,.03,10.05),(25,2,25),'rv_wall_clean')
B.R.configure(wall);B.K.write_model(B.DEST,B.RESOURCE,'review_wall',wall)
priorities={'.png':0,'.obj':1,'.mtl':2,'.vmat':3,'.vmdl':4}
files=[dict(path=p.relative_to(B.STAGE).as_posix(),sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in sorted(B.STAGE.rglob('*'),key=lambda p:(priorities.get(p.suffix,9),str(p))) if p.is_file()]
(B.OUT/'publish.json').write_text(json.dumps(dict(files=files),indent=2)+'\n')
print('Riverdale-material review wall prepared; saved map untouched')
