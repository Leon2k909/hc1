from pathlib import Path
import ast
ROOT=Path('C:/sbox-projects/hc1/forked-shooter-main');HERE=Path(__file__).parent;s=(HERE/'build.py').read_text();tree=ast.parse(s)
functions='\n\n'.join(ast.get_source_segment(s,n) for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ('roof','sheet','normal','model'))
helper='''"""Approved folded rooftop tarp; reuse original dimensions and roof pitch."""
import math
import numpy as np
import map_kit as K
import riverdale_parts as G
MAT='materials/riverside/folded-tarp-v1'
Z=np.array((0.,0.,1.))
'''+functions+'''

def append_to(target,position):
    m=model(0);offset=np.asarray(position,float)
    for paint,faces in m.polygons.items():
        alias='rf_tarp_'+paint
        target.material_overrides[alias]=m.material_overrides[paint]
        target.tile_overrides[alias]=m.tile_overrides[paint]
        for i,(points,normal) in enumerate(faces):
            target.polygon(alias,[p+offset for p in points],normal,uv=m.polygon_uvs.get((paint,i)),normals=m.polygon_normals.get((paint,i)))
'''
(ROOT/'Tools/riverside_folded_tarp.py').write_text(helper,encoding='utf-8')
p=ROOT/'Tools/riverside_map.py';s=p.read_text(encoding='utf-8');old='        box( part, -hx + 120, -hx + 200, -40, 40, roof + 4, roof + 7, "rs_tarp_blue" )';assert s.count(old)==1
s=s.replace(old,'        from riverside_folded_tarp import append_to as append_approved_folded_tarp\n        append_approved_folded_tarp( part, v( -hx + 160, 0, roof + 4 ) )');compile(s,str(p),'exec');p.write_text(s,encoding='utf-8')
s=(HERE/'runtime-review.cs.txt').read_text();a=s.index('  item=new GameObject');b=s.index('  foreach(var view',a);s=s[:a]+s[b:];s=s.replace('new[]{"before","after"}','new[]{"installed"}').replace('    dressing.Model=variant=="before"?original:without;renderer.Enabled=variant=="after";','').replace('PreviewOnly=true','Installed=true').replace('report.PreviewOnly','report.Installed').replace('Candidate=candidate.MeshInfo','PublicModel=original.MeshInfo').replace('"runtime-review.json"','"installed-runtime.json"');(HERE/'runtime-installed.cs.txt').write_text(s,encoding='utf-8')
s=(HERE/'capture.py').read_text().replace('runtime-review.cs.txt','runtime-installed.cs.txt').replace('state-restored.json','installed-state-restored.json').replace('scene-unchanged.json','installed-scene-unchanged.json');(HERE/'capture_installed.py').write_text(s,encoding='utf-8')
p=ROOT/'CLAUDE.md';s=p.read_text(encoding='utf-8');rule='- Model upgrade priority: choose props visible at player eye level on main routes or frequently used interaction points. Avoid spending upgrades on hidden rooftop/background details unless requested (user preference, 2026-11-04).'
if rule not in s:
    with p.open('a',encoding='utf-8') as f:f.write('\n'+rule+'\n')
print('Generator updated and player-visible upgrade priority recorded.')
