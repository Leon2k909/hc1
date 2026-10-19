from pathlib import Path
import hashlib
import json
import os
import winreg

root = Path(__file__).resolve().parents[3]
engine = os.environ.get('FACEPUNCH_ENGINE')
if not engine:
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, 'Environment') as key:
        engine = winreg.QueryValueEx(key, 'FACEPUNCH_ENGINE')[0]
base = Path(engine) / 'core/shaders/foliage.shader'
original = base.read_bytes()
text = original.decode('utf-8').replace('\r\n', '\n')
old = '#include "common/utils/Material.CommonInputs.hlsl"'
assert text.count(old) == 1
text = text.replace(old, '#include "hc1_lowtide_foliage_inputs.hlsl"')
text = text.replace('Description = "Foliage shader for s&box";', 'Description = "Lowtide oak atlas: native foliage lighting with direct RGBA colour input";')
text = '// Based on the installed s&box foliage shader; provenance in Sources/Lowtide/foliage/shader-provenance.json.\n' + text
source = root / 'Sources/Lowtide/foliage'
target = source / 'hc1_lowtide_foliage.shader'
assert not target.exists()
target.write_text(text)
(source / 'shader-provenance.json').write_text(json.dumps({
    'source': 'Installed s&box core/shaders/foliage.shader',
    'source_sha256': hashlib.sha256(original).hexdigest(),
    'scope': 'Native vertex wind, cutout coverage and lighting retained. Only material-input include and header changed. Private input helper preserves generated RGBA alpha, uses sRGB colour and defaults to dielectric leaves with no duplicate standard transmission.',
    'candidate_shader_sha256': hashlib.sha256(target.read_bytes()).hexdigest()
}, indent=2) + '\n')
print('Private foliage shader staged from installed native shader; engine files unchanged.')
