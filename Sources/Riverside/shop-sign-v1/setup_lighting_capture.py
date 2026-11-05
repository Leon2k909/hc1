from pathlib import Path
HERE=Path(__file__).parent
s=(HERE/'capture.py').read_text(encoding='utf-8').replace("'runtime-review.cs.txt'","'runtime-lighting.cs.txt'").replace("'state-restored.json'","'lighting-state-restored.json'")
s=s.replace('import json','import json,hashlib',1).replace('from native import call,script,OUT','from native import call,script,OUT,ROOT',1)
s=s.replace("status=call('editor_status')","status=call('editor_status')\nscene_file=ROOT/'Assets/scenes/maps/Riverside/riverside.scene'\nscene_before=hashlib.sha256(scene_file.read_bytes()).hexdigest()",1)
s=s.replace("    final=call('editor_status')","    final=call('editor_status')\n    scene_after=hashlib.sha256(scene_file.read_bytes()).hexdigest()\n    (OUT/'lighting-saved-scene.json').write_text(json.dumps(dict(before=scene_before,after=scene_after,unchanged=scene_before==scene_after),indent=2),encoding='utf-8')",1)
(HERE/'capture_lighting.py').write_text(s,encoding='utf-8')
