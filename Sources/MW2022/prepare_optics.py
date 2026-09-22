"""Replace Source stencil/RT lenses with one s&box aiming surface per optic."""
import json,re
from pathlib import Path
from optic_caps import clear_caps
HERE=Path(__file__).resolve().parent;A=HERE.parents[1]/'Assets'
models=json.loads((HERE/'conversion.json').read_text())['models']
materials=json.loads((HERE/'materials.json').read_text())['materials']
def write(path,text):
    if not path.exists() or path.read_text()!=text:path.write_text(text)
base=(A/'attachments/m4a1/optics/reflex_reticle.vmat').read_text()
base=re.sub(r'g_flUseReticleTexture\s+"[^"]*"','g_flUseReticleTexture "0"',base)
for m in materials.values():
    if m.get('optic_glass'):write(A/m['vmat'],(A/'attachments/m4a1/materials/hidden.vmat').read_text())
report=[]
for m in models:
    if m['category']!='Optic':continue
    path=(A/m['vmdl']).with_suffix('.obj')
    original=HERE/'optics_original'/path.name;original.parent.mkdir(exist_ok=True)
    if not original.exists():original.write_bytes(path.read_bytes())
    lines=original.read_text().splitlines();positions=[];uvlines=[];faces={};mat=None
    for li,line in enumerate(lines):
        f=line.split()
        if not f:continue
        if f[0]=='v':positions.append(tuple(float(v)for v in f[1:]))
        elif f[0]=='vt':uvlines.append(li)
        elif f[0]=='usemtl':mat=f[1]
        elif f[0]=='f':faces.setdefault(mat,[]).append([tuple(int(i)-1 for i in v.split('/'))for v in f[1:]])
    candidates=[k for k,v in m['materials'].items()if materials[v].get('optic_glass') and k in faces]
    def score(k):
        full=m['materials'][k]
        return (0 if '/ads_scope_lens' in full else 1 if '_lens_ads'in full and '_edge'not in full else 2 if '_edge'not in full else 3)
    selected=min(candidates,key=score)
    vertices={v for face in faces[selected]for v in face}
    lo=[min(positions[v[0]][i]for v in vertices)for i in (0,1)]
    hi=[max(positions[v[0]][i]for v in vertices)for i in (0,1)]
    center=next((b['head'][1:]for b in m['bones']if b['name']=='tag_reticle_attach'),[(lo[i]+hi[i])/2 for i in range(2)])
    for vi,ti,ni in vertices:
        uv=[(positions[vi][i]-center[i])/max(hi[i]-lo[i],.01)+.5 for i in range(2)]
        lines[uvlines[ti]]='vt %.7f %.7f'%tuple(uv)
    lines,caps=clear_caps(lines,m,materials,center,[lo,hi])
    write(path,'\n'.join(lines)+'\n')
    scope=any(t in m['key']for t in ('scope','4x','thermal','hybrid','2x'))and not m['key'].endswith('holo')
    lens=base.replace('g_flScopeReticle "0"','g_flScopeReticle "1"' if scope else 'g_flScopeReticle "0"')
    lenspath=path.with_name(path.stem+'_reticle.vmat');write(lenspath,lens)
    vmdl=path.with_suffix('.vmdl');data=vmdl.read_text()
    pattern=r'(from = "'+selected+r'\.vmat" to = ")[^"]*(")'
    data=re.sub(pattern,lambda x:x[1]+lenspath.relative_to(A).as_posix()+x[2],data)
    write(vmdl,data)
    report.append(dict(key=m['key'],surface=selected,material=m['materials'][selected],center=center,aperture=[lo,hi],removed_caps=caps))
write(HERE/'optics.json',json.dumps(report,indent=2))
print('OPTICS',len(report),'aiming surfaces')
