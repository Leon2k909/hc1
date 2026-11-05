from pathlib import Path
import sys,json,hashlib
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent
sys.path.insert(0,str(ROOT/'Tools'))
import map_kit as K
from model import model
OUT=ROOT/'output/riverdale/sand-bin-v3';STAGE=OUT/'stage';RES='models/maps/riverdale/sand-bin-v3';DEST=STAGE/'Assets'/RES
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
m=json.loads((OUT/'manifest.json').read_text());assert sha(ROOT/m['source'])==m['source_sha256']
m['triangles']=K.write_model(DEST,RES,'sand_bin',model())
m['files']={str(p.relative_to(STAGE)).replace('\\','/'):sha(p) for p in STAGE.rglob('*') if p.is_file()}
(OUT/'manifest.json').write_text(json.dumps(m,indent=2));print(m['triangles'])
