"""Keep the shed's OBJ tables before faces, compatible with town partial exports.

Only relocate our own exact table block. No numeric data, material switches or
face indices change. This restores the insertion order expected by later patches.
"""
import copy
import io
import json
from pathlib import Path
import belltower_stage_shed_corners as S


def main():
    previous=S.BASE/'r5/stage'; out=S.BASE/'r6/stage'
    assert not (out/'manifest.json').exists(); out.mkdir(parents=True,exist_ok=True)
    report=copy.deepcopy(json.loads((previous/'manifest.json').read_text()))
    report['stage_revision']='r6'; report['files']={}
    report['source_sha256']['Tools/belltower_normalize_shed_source.py']=S.sha(Path(__file__))
    report['refinement']='Relocate only shed OBJ tables into the initial table section; preserve every numeric value and face index.'
    for side in ('west','east'):
        relative=f'Assets/models/maps/belltower/belltower_{side}.obj'; source=S.ROOT/relative
        piece=previous/f'belltower_{side}-timber.obj'; lines=piece.read_bytes().splitlines(keepends=True)
        kinds=(b'v ',b'vt ',b'vn '); block=b''.join(l for l in lines if l.startswith(kinds))
        staged=(previous/relative).read_bytes(); expected_start=staged.index(block)
        expected_face=next(l for l in staged[expected_start+len(block):].split(b'\n',3) if l.startswith(b'f '))
        local_face=next(l for l in lines if l.startswith(b'f '))
        desired=dict(zip(('v','vt','vn'),(int(a)-int(b) for a,b in zip(expected_face.split()[1].split(b'/'),local_face.split()[1].split(b'/')))))
        before=S.sha(source); data=source.read_bytes(); assert data.count(block)==1
        start=data.index(block); first_face=data.index(b'\nf ')+1
        assert start>first_face, 'This migration requires the original appended shed tables.'
        counts=dict(v=0,vt=0,vn=0); insertion=None; cursor=0
        for line in io.BytesIO(data[:first_face]):
            kind=line.split(b' ',1)[0].decode(errors='replace')
            if kind in counts:counts[kind]+=1
            cursor+=len(line)
            if counts==desired:
                insertion=cursor; break
        assert insertion is not None,('The original table boundary changed',side,desired)
        result=data[:insertion]+block+data[insertion:start]+data[start+len(block):]
        assert len(result)==len(data)
        assert result.count(block)==1
        for kind in kinds:
            assert data.count(b'\n'+kind)==result.count(b'\n'+kind)
        # Removing our own moved block reproduces every other byte exactly.
        assert result[:insertion]+result[insertion+len(block):]==data[:start]+data[start+len(block):]
        prefix=result[:result.index(b'\nf ')+1]
        for kind in kinds:
            assert prefix.count(b'\n'+kind)==result.count(b'\n'+kind),('Late table remains',side,kind)
        target=out/relative; backup=out/'before'/relative
        target.parent.mkdir(parents=True,exist_ok=True); backup.parent.mkdir(parents=True,exist_ok=True)
        target.write_bytes(result); backup.write_bytes(data)
        assert S.sha(source)==before
        report['files'][relative]=dict(before=before,after=S.sha(target),table_block_sha256=__import__('hashlib').sha256(block).hexdigest(),
            table_block_bytes=len(block),moved_from=start,moved_to=insertion,all_other_bytes_identical=True,all_face_indices_identical=True,all_numeric_values_identical=True)
        print(json.dumps(dict(side=side,table_block_moved_only=True,all_face_indices_preserved=True)),flush=True)
    assert all(S.sha(S.ROOT/p)==row['before'] for p,row in report['files'].items())
    (out/'manifest.json').write_text(json.dumps(report,indent=2)+'\n')


if __name__=='__main__':main()
