"""Rebase the verified shed patch without rebuilding its unchanged new mesh."""
from collections import Counter
import copy
import json
from pathlib import Path
import shutil
import numpy as np
import belltower_stage_shed_corners as S
import belltower_shed_wood as W


def original_timber():
    old, sink = S.K.Model(), S.K.Model()
    original = W.board

    def record(model, centre, axes, size, paint=S.F.WOOD, seed=0, trim=False):
        centre, size = np.array(centre,float), np.array(size,float)
        if trim and np.allclose(size[:2],(3.5,1.10)):
            centre += np.asarray(axes[1])*.08; size[1]=.44; bevel=.11
        elif trim and abs(size[1]-.64)<1e-6: bevel=.1
        elif trim and np.allclose(size,(2,1.24,77)): bevel=.14
        elif trim and np.allclose(size,(44,1.24,2.6)): bevel=.15
        elif not trim and np.allclose(size,(4.77,1.08,75.6)): bevel=.09
        elif not trim and abs(size[1]-.65)<1e-6: bevel=.08
        else: raise AssertionError(('Unexpected shed member',size,trim))
        S.F.bevel_box(old,centre,axes,size,paint,bevel,seed)
    try:
        W.board=record
        for e0,e1,n0,n1,door,small in S.SHEDS:
            S.G.shed(sink,e0,e1,n0,n1,-48,door,small)
    finally: W.board=original
    return Counter(row[0] for row in S.triangles(old))


def main():
    prior=S.BASE/'r2/stage'; out=S.BASE/'r4/stage'
    assert not (out/'manifest.json').exists()
    report=copy.deepcopy(json.loads((prior/'manifest.json').read_text()))
    for p,digest in report['source_sha256'].items():
        assert S.sha(S.ROOT/p)==digest,('Geometry source changed',p)
    report['stage_revision']='r4'; report['files']={}; report['input_guards']={}
    report['source_sha256']['Tools/belltower_refresh_shed_corners.py']=S.sha(Path(__file__))
    report['scene_sha256']=S.sha(S.ROOT/'Assets/scenes/maps/Belltower/belltower.scene')
    removed=original_timber()
    assert sum(removed.values())==report['removed_triangles_per_half']==5280
    for side in ('west','east'):
        wanted=removed
        if side=='east':
            wanted=Counter()
            for (paint,face),count in removed.items():
                reflected=frozenset(f'{-float(p.split()[0]):.3f} {float(p.split()[1]):.3f} {float(p.split()[2]):.3f}' for p in face)
                wanted[paint,reflected]+=count
        source=S.ROOT/f'Assets/models/maps/belltower/belltower_{side}.obj'
        # Validate the reconstructed selection against the earlier, exact diff.
        prior_scan=S.scan(prior/'before'/source.relative_to(S.ROOT),wanted)
        assert prior_scan['found']==wanted
        row=S.scan(source,wanted); assert row['found']==wanted
        report['files'][source.relative_to(S.ROOT).as_posix()]=S.patch_file(source,out,row,prior/f'belltower_{side}-timber.obj')
        for item in report['models'][side]['imports']:
            relative=item['asset']; current=S.ROOT/relative
            previous=json.loads((prior/'manifest.json').read_text())['files'][relative]
            assert S.sha(current)==previous['before'],('Shared timber import changed',relative)
            target=out/relative; backup=out/'before'/relative
            target.parent.mkdir(parents=True,exist_ok=True); backup.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(prior/relative,target); shutil.copyfile(current,backup)
            assert S.sha(target)==previous['after'] and S.sha(backup)==previous['before']
            report['files'][relative]=previous
        for suffix in ('.vmdl','.mtl'):
            p=source.with_suffix(suffix); report['input_guards'][p.relative_to(S.ROOT).as_posix()]=S.sha(p)
        print(json.dumps(dict(rebased=side,removed=len(row['drop']))),flush=True)
    assert all(S.sha(S.ROOT/p)==row['before'] for p,row in report['files'].items())
    out.mkdir(parents=True,exist_ok=True)
    (out/'manifest.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(stage=str(out),files=len(report['files']))),flush=True)


if __name__=='__main__':main()
