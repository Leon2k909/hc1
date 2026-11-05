"""Refine the reused shed lock without editing the shared shed asset."""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent
old=ROOT/'Sources/sewage/gate-shed-lock-v1'
source=ROOT/'Tools/sewage_tunnel_gates.py'
assert not (HERE/'gate-before.py').exists()
(HERE/'gate-before.py').write_bytes(source.read_bytes())
lock=(ROOT/'Tools/belltower_padlock.py').read_text()
lock=lock.replace('"""Shed lock hardware, in the existing door frame; visual geometry only."""','"""Sewer lock refinement derived from belltower_padlock; shared sheds stay unchanged."""')
lock=lock.replace("BRASS = 'door_brass'","BRASS = 'sewer_lock_brass'")
lock=lock.replace('steps=8','steps=12')
start=lock.index('                mid=(a+b)/2-');end=lock.index('\n        cap(loops[0]',start)
lock=lock[:start]+'''                # Rounded outline normals follow the corner radius rather than
                # pointing from the centre of the case; smooth the bevel rings.
                def surface_normal(p, shrink):
                    r=max(.04,radius-shrink)
                    centre=np.array((cx,cz))
                    extent=np.array((width/2-shrink-r,height/2-shrink-r))
                    offset=p-centre-np.clip(p-centre,-extent,extent)
                    offset/=np.linalg.norm(offset)
                    n=np.array((offset[0],(sb-sa)/(yb-ya),offset[1]))
                    return n/np.linalg.norm(n)
                ns=[surface_normal(a,sa),surface_normal(b,sa),
                    surface_normal(c,sb),surface_normal(d,sb)]
                emit(paint,[(a[0],cy+ya,a[1]),(b[0],cy+ya,b[1]),
                            (c[0],cy+yb,c[1]),(d[0],cy+yb,d[1])],sum(ns),ns)''' +lock[end:]
lock=lock.replace('3.25,3.8,1.26,.55,BRASS,.15','3.4,3.95,1.55,.68,BRASS,.20')
lock=lock.replace('hole=(cx,cz-.65,.29,None)','hole=(cx,cz-.65,.39,None)')
lock=lock.replace('tube(shackle,.19,STEEL,(0,1,0))','''tube(shackle,.23,STEEL,(0,1,0),20)
    # Machined collars seat the two shackle legs into the top of the case.
    for x in (cx-1.05,cx+1.05):
        F.turned(model,at((x,cy,.04)),up,run,
                 [(.29,-.15),(.31,-.09),(.31,.04),(.26,.10)],STEEL,24,True)
    # Fine raised perimeter on the face defines the case construction seam.
    rim=outline(3.05,3.60,.54,cx,cz,16)
    rimpoints=[(p[0],cy+1.55/2-.02,p[1]) for p in rim]
    tube(rimpoints+[rimpoints[0]],.025,BRASS,(0,1,0),8)''')
lock=lock.replace('front=cy+1.26/2-.11','front=cy+1.55/2-.035')
lock=lock.replace('cx+.25*math.cos(a),keyz+.25*math.sin(a)','cx+.34*math.cos(a),keyz+.34*math.sin(a)')
lock=lock.replace('(cx,keyz,.052,.145)','(cx,keyz,.065,.19)')
(ROOT/'Tools/sewage_gate_lock.py').write_text(lock)
text=source.read_text().replace('import belltower_padlock as P','import sewage_gate_lock as P')
text=text.replace("'door_brass':'materials/belltower/fountain_bronze.vmat'","'sewer_lock_brass':'materials/sewage/gate-lock-v2/brass.vmat'")
text=text.replace("{'door_brass':32,'iron_black':32}","{'sewer_lock_brass':32,'iron_black':32}")
source.write_text(text)
# Reuse the guarded splice workflow, with a frozen previous gate module.
build=(old/'build.py').read_text()
start=build.index('source=ROOT/');end=build.index('import sewage_tunnel_gates as new',start)
build=build[:start]+'''frozen=HERE/'gate-before.py'
assert not (OUT/'plan.json').exists()
spec=importlib.util.spec_from_file_location('gate_before',frozen);old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)
'''+build[end:]
build=build.replace("if k not in old.MATERIALS","if f'newmtl {k}\\n' not in mtl")
build=build.replace('sewage/gate-shed-lock-v1','sewage/gate-lock-v2')
build=build.replace("reuse='Tools/belltower_padlock.py'","reuse='Tools/sewage_gate_lock.py (derived from belltower_padlock.py)'")
(HERE/'build.py').write_text(build)
for name in ('import.cs.txt','check.py'):
    text=(old/name).read_text().replace('sewage/gate-shed-lock-v1','sewage/gate-lock-v2').replace("'shed-'","'refined-'")
    (HERE/name).write_text(text)
material=HERE/'brass.vmat.txt'
material.write_text('''// Fine brass finish for the sewer padlock case.
"Layer0"
{
    shader "shaders/complex.shader"
    F_SPECULAR "1"
    TextureColor "materials/default/default_color.tga"
    TextureNormal "materials/default/default_normal.tga"
    TextureRoughness "materials/default/default_rough.tga"
    TextureAmbientOcclusion "materials/default/default_ao.tga"
    g_vColorTint "[.57 .34 .105 1]"
    g_flMetalness ".88"
    g_flRoughnessScaleFactor ".42"
    g_flModelTintAmount "1"
}
''')
install=(old/'install.cs.txt').read_text().replace('sewage/gate-shed-lock-v1','sewage/gate-lock-v2')
# Written after build, because build emits the generic install script.
(HERE/'install-material.cs.txt').write_text('''var root=Sandbox.Project.Current.GetRootPath();
var path=System.IO.Path.Combine(root,"Assets/materials/sewage/gate-lock-v2/brass.vmat");
if(System.IO.File.Exists(path))throw new Exception("Material already exists");
System.IO.Directory.CreateDirectory(System.IO.Path.GetDirectoryName(path));
System.IO.File.Copy(System.IO.Path.Combine(root,"Sources/sewage/gate-lock-v2/brass.vmat.txt"),path);
Editor.AssetSystem.RegisterFile(path);return new{Imported=true};
''')
print('Prepared independent sewer lock refinement and guarded splice builder')
