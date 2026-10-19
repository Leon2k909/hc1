import json
from pathlib import Path
p=Path('Assets/scenes/maps/Riverdale/riverdale.scene')
data=json.loads(p.read_text(encoding='utf-8'))
root=next(x for x in data['GameObjects'] if x['Name']=='Riverdale')
before=len(root['Children'])
root['Children']=[x for x in root['Children'] if x['Name']!='Cooling Tower Vapor']
assert before-len(root['Children'])==1
backup=Path('output/riverdale/aaa/vapor/before-remove-vapor.scene')
backup.write_bytes(p.read_bytes())
p.write_text(json.dumps(data,indent=2),encoding='utf-8')
print('Removed one unsatisfactory vapor scene model; retained all other scene objects')
