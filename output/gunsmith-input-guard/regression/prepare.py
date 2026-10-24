"""Use production firing methods directly, without compiling rendering/ballistics."""
from pathlib import Path
import hashlib
import json

directory = Path(__file__).resolve().parent
root = directory.parents[2]
source_path = root/'Code/Weapons/Components/Shootable.cs'
text = source_path.read_text(encoding='utf-8')
methods = []
for signature in ('private void ClearBurst()', 'protected override void OnInputSuppressed()', 'protected override void OnInputUpdate()'):
    start = text.index(signature)
    opening = text.index('{', start)
    depth = 0
    for i in range(opening, len(text)):
        depth += (text[i] == '{') - (text[i] == '}')
        if depth == 0:
            methods.append(text[start:i+1])
            break
    else:
        raise ValueError('Unbalanced production method')
(directory/'GeneratedShootable.cs').write_text('namespace Facepunch;\npublic partial class Shootable\n{\n'+'\n'.join(methods)+'\n}\n')
paths = [source_path, root/'Code/Weapons/Components/WeaponInputAction.cs']
(directory/'production-inputs.json').write_text(json.dumps({str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}, indent=2))
print('Prepared actual production input/firing code for the standalone regression runner.')
