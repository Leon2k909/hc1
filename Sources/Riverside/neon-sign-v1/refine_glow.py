from pathlib import Path
import json,hashlib
HERE=Path(__file__).parent;REVIEW=HERE.parents[2];OUT=REVIEW/'output/riverside/neon-sign-v1'
source=HERE/'build.py';s=source.read_text(encoding='utf-8');assert 'g_flSelfIllumBrightness "3.8"' in s
source.write_text(s.replace('g_flSelfIllumBrightness "3.8"','g_flSelfIllumBrightness "18.0"'),encoding='utf-8')
p=REVIEW/'Assets/materials/riverside/neon-sign-v1/tube_glow.vmat';s=p.read_text(encoding='utf-8');assert 'g_flSelfIllumBrightness "3.8"' in s;p.write_text(s.replace('g_flSelfIllumBrightness "3.8"','g_flSelfIllumBrightness "18.0"'),encoding='utf-8')
plan=OUT/'manifest.json';m=json.loads(plan.read_text());m['files'][p.relative_to(REVIEW).as_posix()]=hashlib.sha256(p.read_bytes()).hexdigest();plan.write_text(json.dumps(m,indent=2),encoding='utf-8')
