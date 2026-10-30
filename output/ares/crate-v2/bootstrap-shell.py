"""Pin and adapt the project's authored equipment-shell topology for Ares."""
import hashlib
from pathlib import Path

root = Path(__file__).resolve().parents[3]
source = (root / 'Tools/veridant_case_detail.py').read_text()
reference = root / 'Sources/Ares/crate-v2/reference-case-detail.py.txt'
assert not reference.exists()
reference.write_text(source)
core = source[:source.index('\ndef write_materials(')]
core = core.replace('materials/veridant/cases-v4', 'materials/ares/crate-v2')
core = core.replace('vr_transport_', 'ar_cargo_').replace("paint='vr_case_black'", "paint='ar_case_black'")
core = core.replace('surface=\'plastic\', seed=0):', "surface='plastic', seed=0, marked=False, quality=0):")
assert 'marked=False, quality=0' in core
start = core.index('    # UVs use the actual OBJ')
end = core.index('    # Carry the exact authored transform', start)
core = core[:start] + core[end:]
core = core.replace('    front=face(-Y,X,W/2,L/2)', '    front=face(-Y,X,W/2,L/2,not marked)')
start = core.index('def build_into(')
head, body = core[:start], core[start:]
body = body.replace('rounded_rect(', 'rounded(')
body = body.replace('    local = K.Model(); L, W, H = map(float, size)',
    '    steps=4 if quality==0 else 2; count=steps+1\n'
    '    def rounded(w,h,r):return rounded_rect(w,h,r,steps)\n'
    '    local = K.Model(); L, W, H = map(float, size)')
body = body.replace('range(corner*5, corner*5+4)', 'range(corner*count, corner*count+steps)')
body = body.replace('range(corner*5,corner*5+4)', 'range(corner*count,corner*count+steps)')
body = body.replace('corner*5:corner*5+5', 'corner*count:corner*count+count')
body = body.replace('            mask=(0.,.8,1.,1.,1.,.8,0.)',
    '            mask=[0.]+[1.]*count+[0.];mask[1]=mask[-2]=.8')
body = body.replace('for i in range(6):', 'for i in range(len(mask)-1):')
body = body.replace('    def screw(at, normal, right=X, r=.115):',
    '    def screw(at, normal, right=X, r=.115):\n        if quality:return')
core = head + body
core = '# Ares shell topology, pinned from the authored project equipment case.\n' + core
assert 'corner*5' not in core and 'vr_transport_' not in core
target = root / 'Tools/ares_case_shell.py'
assert not target.exists()
target.write_text(core)
print({'reference_sha256': hashlib.sha256(source.encode()).hexdigest(), 'core_lines': len(core.splitlines())})
