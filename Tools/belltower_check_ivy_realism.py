"""Verify the published ivy matches the reviewed candidate and preserves the town."""
from pathlib import Path
from collections import Counter
import hashlib
import json
import numpy as np
import map_kit as K
import belltower_map as B
import belltower_ivy_realism as I
import belltower_stage_ivy as S
import belltower_stage_ivy_realism as R

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output/belltower/ivy-realism-v3'


def sha(path):
    with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def main():
    preview=json.loads((OUT/'preview/stage/manifest.json').read_text())
    publication=json.loads((OUT/'publication/stage/manifest.json').read_text())
    for phase in (preview,publication):
        for relative,row in phase['files'].items():
            assert sha(ROOT/relative)==row['after'],relative
            assert sha(ROOT/row['source'])==row['after']
            if row['backup']:assert sha(ROOT/row['backup'])==row['before']
    for path,digest in publication['source_sha256'].items():assert sha(ROOT/path)==digest,path
    assert sha(ROOT/'Assets/scenes/maps/Belltower/belltower.scene')==publication['scene_sha256']
    for side in ('west','east'):
        model=publication['models'][side]
        assert model['all_non_ivy_obj_bytes_preserved'] and model['collision_exact'] and model['all_non_ivy_imports_exact']
        combined=Counter()
        for kind,targets in model['imports'].items():
            sources=preview['models'][side]['imports'][kind]
            assert len(sources)==len(targets)
            for source,target in zip(sources,targets):
                a,b=ROOT/'Assets'/source,ROOT/'Assets'/target
                assert sha(a)==sha(b),(source,target)
                count=sum(line.startswith(b'f ') for line in b.open('rb'))
                assert count<=R.LIMIT
                combined.update(S.source_counter(b,set(I.MATERIALS)))
        assert S.source_counter(ROOT/f'Assets/models/maps/belltower/belltower_{side}.obj',set(I.MATERIALS))==combined
        relative=f'Assets/models/maps/belltower/belltower_{side}.vmdl'
        original=(OUT/'publication/before'/relative).read_bytes()
        current=(ROOT/relative).read_bytes()
        marker=b'_class = "PhysicsShapeList"'
        if marker in original:assert original[original.index(marker):]==current[current.index(marker):]
        keep=lambda raw:[block for start,end,block in R.blocks(raw.decode()) if not any(k in block for k in ('ivy_climb','ivy_hang'))]
        assert keep(original)==keep(current)
    # Exercise the public map hook against the accepted candidate at the
    # photographed original clearance rectangle, including UVs and normals.
    m=K.Model();wall=K.Wall('n',(1400,1560),(-2380,-2300),(0,240),'+e')
    assert B.ivy(m,wall,1480,0,1.5,out=1.2)
    original=next((R.ORIGINAL/'Assets/models/maps/belltower/compiler-safe/west').glob('*ivy_climb.obj'))
    points,normal=next((p,n) for p,n in S.patches(original) if np.allclose(np.mean(p,axis=0),(-2298.8,1480,72)))
    reference=K.Model();I.build(reference,points,normal)
    def geometry(model):
        return {paint:[([np.round(p,9).tolist() for p in pts],np.round(n,9).tolist(),model.polygon_uvs.get((paint,k)))
            for k,(pts,n) in enumerate(rows)] for paint,rows in model.polygons.items()}
    assert geometry(m)==geometry(reference)
    assert not m.boxes and not m.hulls and not m.props
    resources=json.loads((OUT/'native-resources.json').read_text())
    assert resources['LeafMaterialValid'] and resources['TextureValid']
    assert all(not row['IsError'] and len(row['IvyMaterials'])==3 for row in resources['Models'])
    native=json.loads((OUT/'native-production-status/call_tools.json').read_text())
    items=[json.loads(item['text']) for item in native['content'] if item['type']=='text']
    assets=[row for row in items if 'IsCompiled' in row]
    assert len(assets)==5 and all(a['IsCompiledAndUpToDate'] and not a['IsCompileFailed'] for a in assets)
    views=[]
    for directory,names in [('ivy-realism-v3-preview',('front','oblique','sunlit','hanging')),
        ('ivy-realism-v3-installed',('front','oblique'))]:
        for name in names:
            base=ROOT/'output/belltower/quality'/directory
            data=json.loads((base/(name+'-camera.json')).read_text())
            assert data['EditorStatePreserved'] and data['ActiveGamePreserved'] and data['TemporarySceneDestroyed']
            assert (base/(name+'.png')).is_file()
            views.append((base/(name+'.png')).relative_to(ROOT).as_posix())
    result={'passed':True,'patches':50,'leaf_variants':8,
        'leaves':2*sum(p['leaves'] for p in preview['patches_per_half']),
        'triangles_per_half':publication['models']['west']['triangles'],
        'max_import_triangles':R.LIMIT,'non_ivy_town_geometry_exact':True,'collision_exact':True,'scene_file_unchanged':True,
        'canonical_generator_matches_candidate':True,'published_parts_match_rendered_candidate':True,
        'native_compilation_passed':True,'native_resources_loaded':True,'reviewed_views':views,
        'runtime_performance_measured':False,'user_visual_acceptance':'awaiting feedback'}
    (OUT/'verification.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result))


if __name__=='__main__':main()
