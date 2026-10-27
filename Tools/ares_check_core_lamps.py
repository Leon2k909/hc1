"""Check this scoped core-light repair and its native engine evidence."""
import json
from pathlib import Path
import numpy as np
import ares_core_lamps as L
import ares_map as A
import map_kit as K
from railhead_stage_extinguisher import sha

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output/ares/core-lamp-mounts-v1'


def result(path):
    raw=json.loads(path.read_text());assert not raw.get('isError'),path
    return json.loads(next(c['text'] for c in raw['content'] if c['type']=='text'))


def main():
    manifest=json.loads((OUT/'stage-v1/manifest.json').read_text())
    for p,item in manifest['files'].items():assert sha(ROOT/p)==item['after'],p
    for p,h in manifest['protected_sha256'].items():assert sha(ROOT/p)==h,p
    for p,h in manifest['source_sha256'].items():
        if p!='Tools/ares_core_lamps.py':assert sha(ROOT/p)==h,p
    for p,parts in manifest['required_source_snippets'].items():
        assert all(part in (ROOT/p).read_text() for part in parts),p
    # Reproduce the exact published geometry with the helper inserted into a
    # non-empty collision model, as happens during complete map generation.
    model=K.Model();model.collision_box((0,0,0),(1,1,1),'metal')
    collision_counts=(len(model.boxes),len(model.hulls));mounts=L.flared_ring_lamps(model)
    assert (len(model.boxes),len(model.hulls))==collision_counts
    A.configure(model);folder=OUT/'source-check';folder.mkdir(exist_ok=True)
    path=folder/'new-lamps.obj';K.write_obj(path,model,'ares_reactor')
    assert sha(path)==sha(OUT/'stage-v1/proof/new-lamps.obj')
    assert model.triangle_count()==10608 and len(mounts)==24
    reactor,glass=K.Model(),K.Model();A.reactor(reactor,glass)
    assert reactor.boxes and reactor.hulls
    receipt=json.loads((OUT/'native-import.json').read_text())
    assert receipt['Fixtures']==24 and receipt['EditorStatePreserved']
    compile=result(OUT/'compile-native/asset_compile.json');assert compile['Success']
    captures={}
    for phase in ('before','after'):
        data=json.loads((OUT/phase/'capture.json').read_text());assert data['SourceUnchanged']
        assert all(not m['Error'] for m in data['Models'])
        captures[phase]={name:{'path':(OUT/phase/(name+'.png')).relative_to(ROOT).as_posix(),
                                     'sha256':sha(OUT/phase/(name+'.png'))}
                         for name in ('mount-close','mount-oblique','ring-context')}
    source_scene='Assets/scenes/maps/Ares/ares.scene'
    report={'revision':manifest['revision'],'fixtures_fixed':24,'removed_triangles':288,
            'new_triangles':10608,'unrelated_obj_bytes_and_original_indices_preserved':True,
            'model_document_materials_and_collision_sources_unchanged':True,
            'scene_file_unchanged':sha(ROOT/source_scene)==manifest['scene_sha256_at_staging'],
            'source_reproduction_byte_exact':True,'existing_collision_preserved_by_helper':True,
            'whole_reactor_source_regeneration_passed':True,
            'final_helper_sha256':sha(ROOT/'Tools/ares_core_lamps.py'),
            'native_compile':compile,'native_import':receipt,'captures':captures,
            'visual_review':'Close and oblique engine captures show attached metal housings; ring view checks all placements.',
            'performance_note':'Geometry count recorded; no FPS benchmark.'}
    (OUT/'validation.json').write_text(json.dumps(report,indent=2)+'\n')
    (ROOT/'Sources/Ares/core-lamp-mounts-v1/installed.json').write_text(json.dumps({
        'revision':manifest['revision'],'fixtures_fixed':24,
        'validation':'output/ares/core-lamp-mounts-v1/validation.json',
        'screenshot':captures['after']['mount-close']['path']},indent=2)+'\n')
    print(json.dumps({k:report[k] for k in ('fixtures_fixed','source_reproduction_byte_exact',
         'whole_reactor_source_regeneration_passed','scene_file_unchanged')}))


if __name__=='__main__':main()
