from pathlib import Path
import ast,collections,re
ROOT=Path(__file__).absolute().parents[3]
t=ast.parse((Path(__file__).parent/'build.py').read_text());n=next(n for n in t.body if isinstance(n,ast.FunctionDef) and n.name=='records');d={}
exec(compile(ast.Module(body=[n],type_ignores=[]),'records','exec'),d);rec=d['records']
_,faces=rec(ROOT/'output/riverside/water-tank-v1/legacy_absolute.obj');want=collections.Counter(k for _,k in faces)
print('Wanted:',collections.Counter(k[0] for k in want.elements()))
v=ROOT/'Assets/models/maps/riverside/riverside_backdrop.vmdl'
for ref in re.findall(r'filename\s*=\s*"([^"]+\.obj)"',v.read_text()):
    p=ROOT/'Assets'/ref
    if not p.exists():continue
    _,fs=rec(p);have=collections.Counter(k for _,k in fs);missing=want-have
    print('Source:',ref,'faces:',len(fs),'missing:',sum(missing.values()),collections.Counter(k[0] for k in missing.elements()))
    print('Missing examples:',list(missing)[:3]);print('Actual examples:',list(have)[:3])
    verts={p for mat,pts in want for p in pts};matched=[(i,k) for i,k in fs if k[0] in ('rs_tank','rs_paint_white') and all(p in verts for p in k[1])]
    print('Vertex-subset matches:',len(matched))
    for z in (1426.,1496.,1536.,1538.):
        actual={p for mat,pts in have if mat=='rs_tank' for p in pts if p[1]==z}
        expected={p for mat,pts in want if mat=='rs_tank' for p in pts if p[1]==z}
        print('Z',z,'actual',len(actual),'expected',len(expected),'actual-only',sorted(actual-expected)[:5],'expected-only',sorted(expected-actual)[:5])
