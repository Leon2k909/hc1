from pathlib import Path
import json
import shutil
import sys
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
sys.path.insert(0,str(ROOT/'Tools'))
import veridant_inland_vista as vista
stage=ROOT/'output/veridant/inland-vista-v1/distance-fix/stage-v24'
vista.write_materials(stage/'Assets/materials/veridant')
old=stage/'Assets/shaders/hc1_veridant_horizon_v2.shader'
if old.exists(): old.unlink()
shutil.copy2(HERE/'hc1_veridant_horizon.shader.txt',stage/'Assets/shaders/hc1_veridant_horizon_v3.shader')
manifest=json.loads((stage/'manifest.json').read_text())
manifest['files']=[p.relative_to(stage).as_posix() for p in sorted((stage/'Assets').rglob('*')) if p.is_file()]
(stage/'manifest.json').write_text(json.dumps(manifest,indent=2))
(HERE/'compile-distance.cs.txt').write_text((HERE/'compile-shaders.cs.txt').read_text().replace(', "hc1_veridant_scrub_v3"',''),encoding='utf-8')
