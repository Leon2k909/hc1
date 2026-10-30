"""Independent mesh, retained-import and publication checks for the ivy."""
from pathlib import Path
import argparse
import hashlib
import json
import re
import numpy as np

ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'output/veridant/ivy-v2'


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else None


def check(stage_name,installed=False):
    stage=OUT/stage_name;manifest=json.loads((stage/'manifest.json').read_text())
    for relative,item in manifest['files'].items():
        assert sha(ROOT/item['source'])==item['after'],relative
        if installed:assert sha(ROOT/relative)==item['after'],relative
    for group in ('source_sha256','protected_sha256'):
        for relative,value in manifest[group].items():assert sha(ROOT/relative)==value,relative
    leaf=stage/'Assets/models/maps/veridant/ivy-v2/ivy.obj'
    vertices=[];normals=[];uv=[];faces=[];paint=None
    for line in leaf.read_text().splitlines():
        if line.startswith('v '):vertices.append(list(map(float,line.split()[1:])))
        elif line.startswith('vn '):normals.append(list(map(float,line.split()[1:])))
        elif line.startswith('vt '):uv.append(list(map(float,line.split()[1:])))
        elif line.startswith('usemtl '):paint=line.split()[1]
        elif line.startswith('f '):faces.append((paint,[list(map(int,s.split('/'))) for s in line.split()[1:]]))
    vertices=np.array(vertices);normals=np.array(normals);uv=np.array(uv)
    assert np.isfinite(vertices).all() and np.isfinite(normals).all() and np.isfinite(uv).all()
    wrong=0;minimum=float('inf')
    for paint,indices in faces:
        assert len(indices)==3
        for v,t,n in indices:assert 1<=v<=len(vertices) and 1<=t<=len(uv) and 1<=n<=len(normals)
        p=vertices[[i[0]-1 for i in indices]]
        cross=np.cross(p[1]-p[0],p[2]-p[0]);area=float(np.linalg.norm(cross)/2)
        assert area>1e-9,(paint,indices,'Degenerate exported face')
        minimum=min(minimum,area)
        n=normals[[i[2]-1 for i in indices]].mean(axis=0)
        wrong+=np.dot(cross,n)<-1e-8
    assert wrong==0,wrong
    assert len(faces)==manifest['new_triangles']
    base=stage/'Assets/models/maps/veridant/ivy-v2/foliage-base.obj'
    assert sha(base)==manifest['retained_geometry_proof']['retained_bytes_sha256']
    doc='Assets/models/maps/veridant/veridant_foliage.vmdl'
    before=(ROOT/manifest['original_document'] if 'original_document' in manifest else stage/'before'/doc).read_text();after=(stage/doc).read_text()
    imports=lambda s:re.findall(r'filename\s*=\s*"([^"]+\.obj)"',s)
    old=imports(before);new=imports(after)
    previous=manifest['base_import'].removeprefix('Assets/')
    assert set(new)-set(old)=={'models/maps/veridant/ivy-v2/foliage-base.obj','models/maps/veridant/ivy-v2/ivy.obj'}
    assert set(old)-set(new)=={previous}
    assert 'PhysicsShape' not in before and 'PhysicsShape' not in after
    assert sha(stage/'Assets/materials/veridant/ivy-v2/leaf.png')==sha(ROOT/'Sources/Veridant/ivy-v2/leaf-source.png')
    if 'texture_packing' in manifest:
        assert sha(stage/'Assets/materials/veridant/ivy-v2/leaf-pot.png')==manifest['texture_packing']['PackedSha256']
    result=dict(success=True,installed=installed,files=len(manifest['files']),triangles=len(faces),
        minimum_exported_triangle_area=minimum,winding_errors=int(wrong),
        old_ivy_triangles_removed=manifest['retained_geometry_proof']['removed_triangles'],
        unrelated_imports_preserved=True,retained_obj_bytes_exact=True,physics_unchanged=True,
        generated_texture_bytes_preserved=True,planting=manifest['planting'])
    (stage/('installed-validation.json' if installed else 'source-validation.json')).write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--stage',default='stage-v2');p.add_argument('--installed',action='store_true');a=p.parse_args();check(a.stage,a.installed)
