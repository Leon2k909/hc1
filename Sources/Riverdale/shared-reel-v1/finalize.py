import json
from pathlib import Path
from native import ROOT,OUT
y=ROOT/'Tools/riverdale_yard.py';t=y.read_text();needle='    d = unit2( axis )' # exact helper insertion uses doc-free function start
start=t.index('def cable_reel(');i=t.index('\n',start)+1
hook='    if tuple(c)==(60,2420) and tuple(axis)==(1,0) and R==20. and width==26.:\n        # Approved shared resource is placed by riverdale_map.write_scene.\n        old_pipe=P.pipe\n        try:\n            P.pipe=lambda *a,**k:None\n            body=K.Model()\n        finally:P.pipe=old_pipe\n'
# Retain exactly the old tail by suppressing only turned body/hub calls for this location.
tail=t.index('    tail =',start) if '    tail =' in t[start:t.index('\ndef ',start+1)] else -1
begin=t.index('    turned( m, base, ax, profile,',start);end=t.index('    tail =',begin)
block=t[begin:end];hub='    hub = base + ax * ( width / 2 + 1.4 )\n';assert hub in block
block=block.replace(hub,'');t=t[:begin]+hub+'    if not (tuple(c)==(60,2420) and tuple(axis)==(1,0) and R==20. and width==26.):\n'+''.join('    '+l+'\n' for l in block.splitlines())+t[end:];y.write_text(t)
g=ROOT/'Tools/riverdale_map.py';s=g.read_text();line='    world["Children"].append( EMERGENCY_PHONES.scene_group( ids ) )';assert s.count(line)==1
s=s.replace(line,line+'\n    from riverdale_shared_reel import scene_object as approved_reel\n    world["Children"].append(approved_reel())');g.write_text(s)
(ROOT/'Tools/riverdale_shared_reel.py').write_text('''"""Approved shared reel; native serialization preserves its installed transform."""
import json
from pathlib import Path
def scene_object():
    return json.loads((Path(__file__).resolve().parents[1]/'Sources/Riverdale/shared-reel-v1/native-instance.json').read_text())
''')
