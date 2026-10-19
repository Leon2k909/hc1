"""Recompose reviewed window/door/pipe components over current saved meshes.

Archived full OBJ snapshots are never promoted. Their exact scoped component
changes must first reconstruct the archived result, then match current faces
including UVs and normals. This preserves newer work such as the grate wells.
Only output/lowtide is written. Native appearance and budgets remain separate.
"""
import argparse
import gc
import json
from pathlib import Path
import shutil

import map_kit as K
import lowtide_window_construction as W

BASE = K.ROOT/'output/lowtide/quality-pass'


def load(name):
    folder=BASE/name
    return folder,json.loads((folder/'manifest.json').read_text())


def checked_component(folder, stem, manifest):
    paths=[folder/f'{stem}-{suffix}.obj' for suffix in ('old','new')]
    for p in paths:
        if p.name in manifest.get('components',{}):
            assert W.sha(p)==manifest['components'][p.name],f'Changed reviewed component: {p}'
    return tuple(p.read_text() for p in paths)


def compose(text, old, new):
    current=W.face_keys(text,attributes=True)
    old_keys=W.face_keys(old,attributes=True)
    new_keys=W.face_keys(new,attributes=True)
    assert not old_keys-current,'The scoped component has changed in the current mesh'
    merged,removed=W.replace_faces(text,old,new)
    assert W.face_keys(merged,attributes=True)==current-old_keys+new_keys
    assert removed==sum(old_keys.values())
    return merged,dict(removed=removed,added=sum(new_keys.values()),
                       retained=sum(current.values())-removed)


def baseline(folder, relative, expected):
    p=folder/'before'/Path(relative).name
    assert W.sha(p)==expected,f'Changed archived baseline: {p}'
    return p.read_text()


def prove_archive(before, after, old, new):
    # The old component may share positions with later authored surfaces, so
    # compare full corner attributes, not only positions or triangle totals.
    rebuilt,_=compose(before,old,new)
    assert W.face_keys(rebuilt,attributes=True)==W.face_keys(after,attributes=True)


def main(out):
    out=Path(out).resolve()
    assert out.is_relative_to((K.ROOT/'output/lowtide').resolve())
    out.mkdir(parents=True,exist_ok=True)
    wf,w=load('window-construction')
    df,d=load('door-construction')
    pf,p=load('drain-construction')
    jf,j=load('drain-junctions')
    assert W.sha(W.__file__)==w['generator_sha256']
    assert all(W.sha(K.ROOT/path)==h for path,h in d['generator_sources'].items())
    report=dict(status='scoped_components_recomposed_native_review_pending',
        project_root=str(K.ROOT),production_changed=False,native_accepted=False,
        models={},staged_files={},live_before={},materials={},
        source_manifests={str((folder/'manifest.json').relative_to(K.ROOT)):W.sha(folder/'manifest.json') for folder in (wf,df,pf,jf)})
    live_paths=[K.ASSETS/'models/maps/lowtide'/f'{name}{ext}'
        for name in ('lowtide_east','lowtide_west','lowtide_backdrop','lowtide_finish')
        for ext in ('.obj','.mtl','.vmdl')]
    protected={str(path.relative_to(K.ROOT)):W.sha(path) for path in live_paths}
    for relative,change in w['changes'].items():
        name=Path(relative).stem
        historical=baseline(wf,relative,change['before'])
        archive=wf/'stage'/relative
        assert W.sha(archive)==change['after']
        old,new=checked_component(wf,name,w)
        prove_archive(historical,archive.read_text(),old,new)
        current=(K.ASSETS/relative).read_text()
        merged,window_counts=compose(current,old,new)
        door_counts=None
        if relative in d['changes']:
            archive=df/'stage'/relative
            assert W.sha(archive)==d['changes'][relative]['after']
            assert d['changes'][relative]['before']==change['before']
            old,new=checked_component(df,name,d)
            prove_archive(historical,archive.read_text(),old,new)
            merged,door_counts=compose(merged,old,new)
        target=out/'stage/Assets'/relative
        target.parent.mkdir(parents=True,exist_ok=True)
        target.write_text(merged,encoding='utf-8')
        # Keep current libraries even when component material sets are unchanged.
        shutil.copy2(K.ASSETS/Path(relative).with_suffix('.mtl'),target.with_suffix('.mtl'))
        report['models'][name]=dict(triangles=sum(W.face_keys(merged).values()),windows=window_counts,doors=door_counts)
        print(f'Recomposed {name}: {report["models"][name]["triangles"]:,} triangles',flush=True)
        del current,merged,historical,old,new
        gc.collect()
    relative='models/maps/lowtide/lowtide_finish.obj'
    historical=baseline(pf,relative,p['changes'][relative]['before'])
    original_pipe_stage=pf/'stage'/relative
    assert W.sha(original_pipe_stage)==p['changes'][relative]['after']
    old,new=checked_component(pf,'drains',p)
    prove_archive(historical,original_pipe_stage.read_text(),old,new)
    current=(K.ASSETS/relative).read_text()
    merged,pipe_counts=compose(current,old,new)
    archive=jf/'stage'/relative
    assert W.sha(archive)==j['staged_files'][relative]
    old,new=checked_component(jf,'junctions',j)
    prove_archive(original_pipe_stage.read_text(),archive.read_text(),old,new)
    merged,junction_counts=compose(merged,old,new)
    # These new materials only belong to the installed grates. Every corner
    # attribute must survive the pipe and gutter replacement exactly.
    grate=lambda text:{k:v for k,v in W.face_keys(text,attributes=True).items() if k[0].startswith('lt_grate_')}
    assert grate(current)==grate(merged)
    target=out/'stage/Assets'/relative
    target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(merged,encoding='utf-8')
    shutil.copy2(K.ASSETS/Path(relative).with_suffix('.mtl'),target.with_suffix('.mtl'))
    report['models']['lowtide_finish']=dict(triangles=sum(W.face_keys(merged).values()),pipes=pipe_counts,junctions=junction_counts,grate_triangles_preserved=sum(grate(merged).values()))
    for path,h in p['sources'].items():
        if path.endswith('.png') or path.startswith('Assets/materials/'):
            assert W.sha(K.ROOT/path)==h,f'Drain material input changed: {path}'
    for relative,h in j['inherited_materials'].items():
        source=jf/'stage'/relative
        assert W.sha(source)==h
        if relative in p['staged_material_changes']['changes']:
            assert W.sha(K.ASSETS/relative)==p['staged_material_changes']['changes'][relative]['before']
        target=out/'stage/Assets'/relative
        target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(source,target)
        report['materials'][relative]=h
    for path in (out/'stage').rglob('*'):
        if not path.is_file():continue
        relative=path.relative_to(out/'stage').as_posix()
        report['staged_files'][relative]=W.sha(path)
        live=K.ROOT/relative
        report['live_before'][relative]=W.sha(live) if live.exists() else None
    assert all(W.sha(K.ROOT/path)==h for path,h in protected.items())
    report['protected_models']=protected
    report['preserved_grate_status']='Sources/Lowtide/drainage/grate-status.json'
    (out/'manifest.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report['models'],indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    main(parser.parse_args().output)
