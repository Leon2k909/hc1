"""Independent source and native evidence checks for Collider's environment finish."""
from pathlib import Path
import argparse
import hashlib
import json
import numpy as np

ROOT=Path(__file__).resolve().parents[3]


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def obj(path):
    vertices=[];uv=[];normals=[];faces=[];paint=None;added=False
    with path.open(encoding='utf-8') as stream:
        for line in stream:
            if line.startswith('# Collider finish-v1:'):added=True
            if line.startswith('v '):vertices.append(tuple(map(float,line.split()[1:])))
            elif line.startswith('vt '):uv.append(tuple(map(float,line.split()[1:])))
            elif line.startswith('vn '):normals.append(tuple(map(float,line.split()[1:])))
            elif line.startswith('usemtl '):paint=line.split()[1]
            elif line.startswith('f '):faces.append((paint,[tuple(map(int,t.split('/'))) for t in line.split()[1:]],added))
    return np.array(vertices),np.array(uv),np.array(normals),faces


def validate(stage,installed=False,geometry_baseline=None):
    manifest=json.loads((stage/'manifest.json').read_text())
    relative=Path('models/maps/collider/collider_structure.obj')
    baseline=(geometry_baseline or stage/'before')/relative
    original=obj(baseline);candidate=obj(stage/'assets'/relative)
    for before,after in zip(original[:3],candidate[:3]):
        assert np.isfinite(after).all()
        assert np.array_equal(before,after[:len(before)]),'Original attribute table changed'
    vertices,uv,normals,faces=candidate
    retained=[f for p,f,added in faces if not added]
    old=[f for p,f,added in original[3]]
    removed={tuple(f) for f in old}-{tuple(f) for f in retained}
    assert len(removed)==1440
    assert len(retained)==len(old)-1440
    assert [f for f in old if tuple(f) not in removed]==retained
    assert len(faces)==manifest['geometry']['final_triangle_count']
    minimum=float('inf');wrong=0
    for paint,indices,added in faces:
        assert len(indices)==3
        for vi,ti,ni in indices:
            assert 1<=vi<=len(vertices) and 1<=ti<=len(uv) and 1<=ni<=len(normals)
        points=vertices[[i[0]-1 for i in indices]]
        cross=np.cross(points[1]-points[0],points[2]-points[0]);area=float(np.linalg.norm(cross)/2)
        if added:
            minimum=min(minimum,area)
            assert area>1e-8,(paint,indices,'Degenerate added face')
            dot=float(np.dot(cross,normals[indices[0][2]-1]))
            wrong+=dot < -1e-9
        if paint=='cf_floor':assert normals[indices[0][2]-1][1]>.8
        if paint=='cf_soffit':assert normals[indices[0][2]-1][1]<-.8
    assert wrong==0,wrong
    source_doc=((geometry_baseline or stage/'before')/relative.with_suffix('.vmdl')).read_bytes()
    after_doc=(stage/'assets'/relative.with_suffix('.vmdl')).read_bytes()
    marker=b'\t\t\t{\n\t\t\t\t_class = "PhysicsShapeList"'
    assert source_doc[source_doc.index(marker):]==after_doc[after_doc.index(marker):]
    for entry in manifest['files']:
        assert sha(stage/'assets'/entry['relative'])==entry['after']
        if installed:assert sha(ROOT/'Assets'/entry['relative'])==entry['after']
    if installed:
        publication=stage.parent/'published.json'
        for p,value in manifest['protected'].items():
            if p=='scenes/maps/Collider/collider.scene' and publication.is_file():
                # The asset import precedes the owned native GI/reflection save.
                # Accept that scene only when both native checks and captures
                # identify the exact saved file recorded by finalization.
                receipt=json.loads(publication.read_text())
                native=json.loads((stage.parent/'native-validation.json').read_text())
                capture=json.loads((stage.parent/'captures/capture-report.json').read_text())
                value=receipt['scene_sha256']
                assert native['SceneSha256']==capture['SavedSceneSha256']==value
                assert native['Checked']==68 and not native['Failed']
            assert sha(ROOT/'Assets'/p)==value,p
        for p,value in manifest['sources'].items():assert sha(ROOT/p)==value,p
    result={'revision':manifest['revision'],'stage':manifest['stage'],'files_verified':len(manifest['files']),
        'geometry_baseline':str(baseline.relative_to(ROOT)),
        'original_vertex_uv_normal_tables_preserved':True,'retained_faces_exact':True,
        'removed_flat_portal_triangles':1440,'new_triangles':manifest['geometry']['added_finish_triangles'],
        'final_triangles':len(faces),'smallest_added_triangle_area':minimum,
        'added_winding_failures':wrong,'physics_suffix_exact':True,'installed_sources_verified':installed}
    if installed:
        imported=json.loads((stage/'native-import.json').read_text())
        assert imported['PhysicsPreserved'] and imported['SceneSourcePreserved'] and imported['EditorStatePreserved']
    (stage/('installed-source-validation.json' if installed else 'source-validation.json')).write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stage',type=Path,default=ROOT/'output/depot-finish-20261027/stage-v8')
    parser.add_argument('--baseline',type=Path,default=ROOT/'output/depot-finish-20261027/stage-v4/before',
                        help='Original geometry directory retained by the first published stage')
    parser.add_argument('--installed',action='store_true');args=parser.parse_args()
    validate(args.stage.resolve(),args.installed,args.baseline.resolve() if args.baseline else None)
