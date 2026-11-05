"""Stage an additive warning-board upgrade, retaining every published signage triangle."""
from pathlib import Path
from collections import Counter
import hashlib,json,sys
ROOT=Path(__file__).resolve().parents[3]
HERE=Path(__file__).resolve().parent
OUT=ROOT/'output/sewage/warning-sign-v1'
STAGE=OUT/'stage'
sys.path.insert(0,str(ROOT/'Tools'))
import map_kit as K,riverdale_splice as S,sewage_warning_sign as W

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    baseline=OUT/'baseline';baseline.mkdir(exist_ok=True)
    pub=ROOT/'Assets/models/maps/sewage/sewage_signage.obj'
    for suffix in ('.obj','.mtl','.vmdl'):
        source=pub.with_suffix(suffix);target=baseline/source.name
        if target.exists():assert target.read_bytes()==source.read_bytes(),'Published model changed; inspect before rebuilding'
        else:target.write_bytes(source.read_bytes())
    header,old=S.read_obj(pub)
    assert len([f for f in old if f[0]=='warning'])==4,'Warning face changed'
    hardware=W.emit(K.Model())
    K.write_obj(OUT/'hardware.obj',hardware,'sewage_signage')
    _,added=S.read_obj(OUT/'hardware.obj')
    modeldir=STAGE/'Assets/models/maps/sewage/warning-sign-v1';modeldir.mkdir(parents=True,exist_ok=True)
    S.write_obj(modeldir/'after.obj',['mtllib after.mtl\n','o after\n'],old+added)
    (modeldir/'before.obj').write_bytes(pub.read_bytes().replace(b'sewage_signage.mtl',b'before.mtl'))
    original_mtl=pub.with_suffix('.mtl').read_text()
    new_mtl=original_mtl+''.join(f'newmtl {p}\nKd 1 1 1\nd 1\n' for p in sorted(W.MATERIALS))
    (modeldir/'before.mtl').write_text(original_mtl)
    (modeldir/'after.mtl').write_text(new_mtl)
    original_doc=pub.with_suffix('.vmdl').read_text()
    marker='{ from = "warning.vmat" to = "materials/sewage/warning.vmat" }'
    assert original_doc.count(marker)==1
    remaps=',\n'.join(f'                            {{ from = "{k}.vmat" to = "{v}" }}' for k,v in W.MATERIALS.items())
    new_doc=original_doc.replace(marker,marker+',\n'+remaps)
    for variant,doc in (('before',original_doc),('after',new_doc)):
        (modeldir/f'{variant}.vmdl').write_text(doc.replace('models/maps/sewage/sewage_signage.obj',f'models/maps/sewage/warning-sign-v1/{variant}.obj'))
    install=OUT/'install';install.mkdir(exist_ok=True)
    S.write_obj(install/'sewage_signage.obj',header,old+added)
    (install/'sewage_signage.mtl').write_text(new_mtl)
    (install/'sewage_signage.vmdl').write_text(new_doc)
    _,result=S.read_obj(install/'sewage_signage.obj')
    assert not Counter(old)-Counter(result),'Existing faces changed'
    assert Counter(result)-Counter(old)==Counter(added),'Unexpected geometry change'
    # A finite mesh, without zero-area triangles or generated collision.
    import numpy as np
    for _,corners in added:
        p=[np.array([float(t) for t in c[0].split()]) for c in corners]
        assert all(np.isfinite(v).all() for v in p)
        assert np.linalg.norm(np.cross(p[1]-p[0],p[2]-p[0]))>1e-5
    report=dict(old_triangles=len(old),added_triangles=len(added),new_triangles=len(result),existing_faces_exact=True,
        collision_changed=False,scene_changed=False,
        baseline={p.name:sha(p) for p in baseline.iterdir() if p.is_file()},
        preview_files={p.relative_to(STAGE).as_posix():sha(p) for p in STAGE.rglob('*') if p.is_file()},
        install_files={p.name:sha(p) for p in install.iterdir() if p.is_file()})
    (OUT/'plan.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))

if __name__=='__main__':main()
