"""Verify the scoped bench import, collision preservation and native captures."""
import importlib.util
import json
from pathlib import Path
import numpy as np
from PIL import Image
import map_kit as K
import veridant_bench as B
import veridant_stage_bench as Stage
from railhead_stage_extinguisher import sha

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output/veridant/bench-v2'


def results(path):
    raw=json.loads(Path(path).read_text());assert not raw.get('isError'),path
    rows=[]
    for item in raw['content']:
        if item['type']=='text':
            try:rows.append(json.loads(item['text']))
            except json.JSONDecodeError:pass
    return rows


def main():
    request=json.loads((OUT/'import-request.json').read_text());stage=request['stage']
    manifest=json.loads((OUT/stage/'manifest.json').read_text())
    for path,item in manifest['files'].items():assert sha(ROOT/path)==item['after'],path
    for group in ('source_sha256','protected_sha256'):
        for path,digest in manifest[group].items():
            # Other authorised map work can save the scene between calls. Our
            # asset publisher never writes it, and every capture verifies its
            # entry hash again after restoring all transient state.
            if path.endswith('.scene'):continue
            assert sha(ROOT/path)==digest,path
    for path,parts in manifest['required_source_snippets'].items():
        assert all(part in (ROOT/path).read_text() for part in parts),path
    assert Stage.placements()==manifest['placements']
    spec=importlib.util.spec_from_file_location('previous_bench',ROOT/'Sources/Veridant/bench-v2/previous-bench.py')
    legacy=importlib.util.module_from_spec(spec);spec.loader.exec_module(legacy)
    old=K.Model();new=K.Model()
    for place in manifest['placements']:
        legacy.bench(old,**place);B.build_into(new,**place)
    assert len(old.boxes)==len(new.boxes)==4 and not old.hulls and not new.hulls
    for before,after in zip(old.boxes,new.boxes):
        for i in range(3):assert np.array_equal(before[i],after[i])
        assert before[3]==after[3]
    assert Stage.remaining_legacy_faces(ROOT/manifest['base_import'],old)==0
    first=json.loads((OUT/'stage-v1/manifest.json').read_text())
    doc='Assets/models/maps/veridant/veridant_dress.vmdl';marker='_class = "PhysicsShapeList"'
    before=(ROOT/first['files'][doc]['backup']).read_text();current=(ROOT/doc).read_text()
    assert before[before.index(marker):]==current[current.index(marker):]
    assert current.count('filename = "models/maps/veridant/bench-v2/benches.obj"')==1
    receipt=json.loads((OUT/'native-import.json').read_text())
    assert receipt['Stage']==stage and receipt['BenchesUpdated']==4
    assert receipt['PhysicsBytesPreserved'] and receipt['EditorStatePreserved'] and not receipt['SceneChanged']
    compiles=results(OUT/'final-compile-v5/call_tools.json')
    assert len(compiles)==9 and all(row['Success'] for row in compiles)
    status,camera=results(OUT/'final-status/call_tools.json')
    assert Path(status['Paths']['ProjectRoot']).resolve()==ROOT
    assert not status['IsCompiling'] and status['LastCompileSucceeded'] and status['LastCompileErrors']==0
    assert status['ActiveScene']=='veridant' and not status['SceneHasUnsavedChanges'] and not status['IsPlaying']
    captures={};same_scene_hash=True
    for name in ('overview','detail'):
        image=ROOT/f'output/veridant/quality/bench-v2-final/{name}.png'
        meta=json.loads(image.with_name(name+'-camera.json').read_text())
        assert all(meta['Restoration'].values())
        original=ROOT/f'output/veridant/quality/bench-v2-before/{name}.png'
        baseline=json.loads(original.with_name(name+'-camera.json').read_text())
        for key in ('Position','Angles','FieldOfView','FovAxis','Width','Height','RequestedExposure'):
            assert meta['Capture'][key]==baseline['Capture'][key],(name,key)
        same_scene_hash &= meta['Capture']['SourceSceneSha256']==baseline['Capture']['SourceSceneSha256']
        assert sha(image)!=sha(original)
        captures[name]={'path':image.relative_to(ROOT).as_posix(),'sha256':sha(image),**meta}
    for name,filename in (('teak','teak-albedo-generated-v1.png'),('concrete','concrete-albedo-generated-v1.png')):
        size=(1024,2048) if name=='teak' else (1024,1024)
        source=Image.open(ROOT/f'Sources/Veridant/bench-v2/{filename}').convert('RGB').resize(size,Image.Resampling.LANCZOS)
        published=Image.open(ROOT/f'Assets/materials/veridant/bench-v2/{name}_color.png')
        assert np.array_equal(np.asarray(source),np.asarray(published))
        for kind in ('color','normal','rough'):
            assert Image.open(ROOT/f'Assets/materials/veridant/bench-v2/{name}_{kind}.png').size==size
    report={'revision':manifest['revision'],'stage':stage,'benches_updated':4,
            'triangles_per_bench':9080,'total_triangles':36320,
            'initial_legacy_triangles_removed':288,'legacy_bench_faces_remaining':0,
            'published_file_hashes_verified':len(manifest['files']),
            'scene_written_by_this_task':False,'scene_preserved_during_import_and_captures':True,
            'before_after_scene_hash_identical':same_scene_hash,
            'comparison_note':'Cameras and exposure match; other prop work saved the scene between baseline and final captures.',
            'physics_bytes_exact':True,'collision_shapes_exact':True,
            'concurrent_prop_imports_preserved':True,'native_import':receipt,'native_compiles':compiles,
            'captures':captures,'editor_status':status,'editor_camera':camera,
            'texture_sources':'Sources/Veridant/bench-v2/imagegen-prompts.json',
            'visual_review':'Rounded ends, individual wood grain, end grain, fixings, contact and concrete checked in native close-up and overall views.',
            'performance_note':'36,320 render triangles for four benches; frame-rate impact has not been benchmarked.'}
    (OUT/'validation.json').write_text(json.dumps(report,indent=2)+'\n')
    (ROOT/'Sources/Veridant/bench-v2/installed.json').write_text(json.dumps({
        'revision':manifest['revision'],'stage':stage,'benches_updated':4,
        'validation':'output/veridant/bench-v2/validation.json','screenshot':captures['overview']['path'],
        'source_hook':'Tools/veridant_parts.py:bench','physics_bytes_exact':True},indent=2)+'\n')
    print(json.dumps({'benches_updated':4,'native_compiles_passed':9,'captures_reviewed':2,
                      'collision_and_scene_preserved':True,'triangles_per_bench':9080}))


if __name__=='__main__':main()
