from pathlib import Path
import ast
ROOT=Path('C:/sbox-projects/hc1/forked-shooter-main');HERE=Path(__file__).parent
s=(HERE/'build.py').read_text();tree=ast.parse(s);node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='model');function=ast.get_source_segment(s,node)
helper='''"""Approved L1 roof ladder, reusing the retained quay-ladder design and materials."""
import inspect
import numpy as np
import map_kit as K
import riverdale_parts as G
import lowtide_quay_ladders as A
H=220.0
'''+function+'''

def append_to(target,foot):
    m=model(0);offset=np.asarray(foot,float)
    for paint,faces in m.polygons.items():
        alias='roof_ladder_'+paint
        target.material_overrides[alias]=m.material_overrides[paint]
        target.tile_overrides[alias]=m.tile_overrides[paint]
        for i,(points,normal) in enumerate(faces):
            target.polygon(alias,[p+offset for p in points],normal,uv=m.polygon_uvs.get((paint,i)),normals=m.polygon_normals.get((paint,i)))
'''
(ROOT/'Tools/riverside_roof_ladder.py').write_text(helper,encoding='utf-8')
p=ROOT/'Tools/riverside_map.py';s=p.read_text(encoding='utf-8');a=s.index('        for dy in ( -9, 9 ):',s.index('foot = v( -hx - 40'));b=s.index('        # Junk up',a)
s=s[:a]+'''        from riverside_roof_ladder import append_to as append_approved_roof_ladder
        append_approved_roof_ladder( part, foot )
'''+s[b:];compile(s,str(p),'exec');p.write_text(s,encoding='utf-8')
s=(HERE/'runtime-review.cs.txt').read_text();a=s.index('  item=new GameObject');b=s.index('  foreach(var view',a);s=s[:a]+s[b:]
s=s.replace('new[]{"before","after"}','new[]{"installed"}').replace('    dressing.Model=variant=="before"?original:without;renderer.Enabled=variant=="after";','').replace('PreviewOnly=true','Installed=true').replace('report.PreviewOnly','report.Installed').replace('Candidate=candidate.MeshInfo','PublicModel=original.MeshInfo').replace('"runtime-review.json"','"installed-runtime.json"')
(HERE/'runtime-installed.cs.txt').write_text(s,encoding='utf-8')
s=(HERE/'capture.py').read_text().replace('runtime-review.cs.txt','runtime-installed.cs.txt').replace('state-restored.json','installed-state-restored.json').replace('scene-unchanged.json','installed-scene-unchanged.json');(HERE/'capture_installed.py').write_text(s,encoding='utf-8')
print('Authoring uses the approved new ladder; old reusable model retained.')
