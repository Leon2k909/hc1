"""Stage only the separate shop display OBJ; keep town meshes and scene intact."""
from pathlib import Path
from collections import Counter
import hashlib
import importlib.util
import json
import numpy as np
import belltower_shop_displays_v2 as S
import map_kit as K

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'output/belltower/prop-edge-audit'


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def build(module, records):
    model = K.Model()
    for record in records:
        parameters = {k:record[k] for k in ('origin','outward','width','height')}
        module.build(model, **parameters)
        opposite = parameters.copy()
        opposite['origin'] = [-record['origin'][0], *record['origin'][1:]]
        opposite['outward'] = [-record['outward'][0], *record['outward'][1:]]
        module.build(model, **opposite)
    assert not model.boxes and not model.hulls and not model.props
    return model


def main():
    manifest_path = OUT/'stage/manifest.json'
    assert not manifest_path.exists()
    spec = importlib.util.spec_from_file_location('soft_props_previous', OUT/'before/belltower_shop_displays_v2.py')
    previous = importlib.util.module_from_spec(spec); spec.loader.exec_module(previous)
    installed_record = json.loads((ROOT/'output/belltower/shop-displays/stage-v10/manifest.json').read_text())
    records = installed_record['west_apertures']
    old, new = build(previous, records), build(S, records)
    relative = Path('Assets/models/maps/belltower/shop-display-v2/shop_displays.obj')
    live = ROOT/relative
    baseline = OUT/'before'/relative
    baseline.parent.mkdir(parents=True, exist_ok=True)
    K.write_obj(baseline, old, 'shop_displays_v2')
    assert sha(baseline) == sha(live), 'Current display geometry differs; preserve the newer revision.'
    candidate = OUT/'stage'/relative
    candidate.parent.mkdir(parents=True, exist_ok=True)
    K.write_obj(candidate, new, 'shop_displays_v2')
    assert sha(candidate.with_suffix('.mtl')) == sha(live.with_suffix('.mtl'))
    assert set(old.polygons) == set(new.polygons)
    minimum_area = float('inf'); triangles = 0; invalid = 0
    for paint, faces in new.polygons.items():
        for i,(points,normal) in enumerate(faces):
            assert np.isfinite(points).all() and np.isfinite(normal).all()
            uv = new.polygon_uvs.get((paint,i))
            if paint in ('shop2_labels','shop2_prices'):
                assert uv is not None and all(0 <= a <= 1 and 0 <= b <= 1 for a,b in uv)
            p = np.round(points,3)
            for j in range(1,len(p)-1):
                cross = np.cross(p[j]-p[0],p[j+1]-p[0])
                area = float(np.linalg.norm(cross)/2)
                if area < 1e-8:
                    invalid += 1
                else:
                    minimum_area = min(minimum_area,area)
                triangles += 1
                assert np.dot(cross,normal) >= -1e-7
    assert invalid == 0, ('Degenerate exported faces', invalid)
    protected = {relative.with_suffix(ext).as_posix():sha(live.with_suffix(ext)) for ext in ('.vmdl','.mtl')}
    for paint in new.polygons:
        path = ROOT/'Assets'/S.material_path(paint)
        protected[path.relative_to(ROOT).as_posix()] = sha(path)
    report = {'revision':'soft-shop-props-v1','displays':18,
        'features':['slight continuous bow in long timber shelves and their front rails',
                    'inward paper creases and uneven folded seams on parcels',
                    'gently curled price cards retaining their metal clips'],
        'files':{relative.as_posix():{'before':sha(live),'after':sha(candidate),
                 'source':candidate.relative_to(ROOT).as_posix(),'backup':baseline.relative_to(ROOT).as_posix()}},
        'source_sha256':{p:sha(ROOT/p) for p in ('Tools/belltower_shop_displays_v2.py','Tools/belltower_soft_props.py',
                                               'Tools/belltower_stage_soft_props.py')},
        'protected_sha256':protected,'before_triangles':old.triangle_count(),
        'after_triangles':new.triangle_count(),'export_triangles_checked':triangles,
        'minimum_export_triangle_area_square_inches':minimum_area,'degenerate_export_triangles':invalid,
        'new_colliders':0,'town_models_written':False,'scene_written':False,
        'material_and_texture_changes':False,'source_integration_applied':True,
        'native_import_verified':False,'native_visual_review_verified':False}
    manifest_path.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ('files','source_sha256','protected_sha256')}))


if __name__ == '__main__': main()
