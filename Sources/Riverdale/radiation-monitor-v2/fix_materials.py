"""Stage the complex shader's supported self-illumination parameters."""
from pathlib import Path
import hashlib
import json

root = Path(__file__).resolve().parents[3]
out = root / 'output/riverdale/radiation-monitor-v2'
entries = []
for name in ('lcd', 'amber', 'green'):
    rel = Path('materials/riverdale/radiation_monitor_v2') / ('rv_arm_'+name+'.vmat')
    target = root / 'Assets' / rel
    text = target.read_text()
    text = text.replace('g_flSelfIllumScale', 'g_flSelfIllumBrightness')
    text = text.replace('    g_vSelfIllumTint', '    g_flSelfIllumAlbedoFactor "1"\n    g_vSelfIllumTint')
    text = text.replace('materials/default/default_white.tga', '[1 1 1 0]')
    source = out / 'material-fix' / rel
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_text(text)
    entries.append(dict(Source=str(source), Target=str(target), ExpectedSHA256=hashlib.sha256(target.read_bytes()).hexdigest(), SHA256=hashlib.sha256(source.read_bytes()).hexdigest()))
(out/'material-fix.json').write_text(json.dumps(dict(Entries=entries), indent=2))
installer = (Path(__file__).parent/'install.cs.txt').read_text().replace('"stage.json"', '"material-fix.json"')
(Path(__file__).parent/'install-material-fix.cs.txt').write_text(installer)
