"""Stage lossless removal of unused OBJ table entries after partial mesh edits.

No installed asset is changed. The report proves that every face resolves to the
same ordered material, position, UV and normal bytes before and after compaction.
"""
import argparse
from array import array
import hashlib
import json
from pathlib import Path

KINDS = (b'v', b'vt', b'vn')


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def tables(path):
    result = {kind: [None] for kind in KINDS}
    for line in path.open('rb'):
        kind = line.split(b' ', 1)[0]
        if kind in result:
            result[kind].append(line)
    return result


def face_tokens(line, counts):
    result = []
    for token in line.split()[1:]:
        values = token.split(b'/')
        if len(values) != 3 or any(not v for v in values):
            raise ValueError('Expected full position/UV/normal face indices')
        row = []
        for kind, raw in zip(KINDS, values):
            index = int(raw)
            if index < 0:
                index += counts[kind] + 1
            if not 1 <= index <= counts[kind]:
                raise ValueError(f'Out of range {kind!r} index {index}')
            row.append(index)
        result.append(row)
    if len(result) != 3:
        raise ValueError('This repair expects triangular faces')
    return result


def semantic_digest(path, data):
    digest = hashlib.sha256()
    counts = {kind: len(values) - 1 for kind, values in data.items()}
    faces = 0
    for line in path.open('rb'):
        if line.startswith(b'usemtl '):
            digest.update(line)
        elif line.startswith(b'f '):
            digest.update(b'face\n')
            for row in face_tokens(line, counts):
                for kind, index in zip(KINDS, row):
                    digest.update(data[kind][index])
            faces += 1
    return digest.hexdigest(), faces


def compact(source, target, deduplicate=False):
    before = sha(source)
    data = tables(source)
    counts = {kind: len(values) - 1 for kind, values in data.items()}
    used = {kind: bytearray(count + 1) for kind, count in counts.items()}
    for line in source.open('rb'):
        if line.startswith(b'f '):
            for row in face_tokens(line, counts):
                for kind, index in zip(KINDS, row):
                    used[kind][index] = 1
    before_semantics, face_count = semantic_digest(source, data)
    remap = {}
    emit = {}
    unique_counts = {}
    for kind in KINDS:
        mapping = array('I', [0]) * (counts[kind] + 1)
        next_index = 0
        first = {}
        emit[kind] = bytearray(counts[kind] + 1)
        for i, present in enumerate(used[kind]):
            if present:
                existing = first.get(data[kind][i]) if deduplicate else None
                if existing is not None:
                    mapping[i] = existing
                else:
                    next_index += 1
                    mapping[i] = next_index
                    emit[kind][i] = 1
                    if deduplicate:
                        first[data[kind][i]] = next_index
        remap[kind] = mapping
        unique_counts[kind] = next_index
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        raise FileExistsError(target)
    seen = {kind: 0 for kind in KINDS}
    with source.open('rb') as stream, target.open('wb') as output:
        for line in stream:
            kind = line.split(b' ', 1)[0]
            if kind in seen:
                seen[kind] += 1
                if emit[kind][seen[kind]]:
                    output.write(line)
            elif kind == b'f':
                tokens = [b'/'.join(str(remap[k][i]).encode() for k, i in zip(KINDS, row))
                    for row in face_tokens(line, counts)]
                output.write(b'f ' + b' '.join(tokens) + b'\n')
            else:
                output.write(line)
    del data
    after_data = tables(target)
    after_semantics, after_faces = semantic_digest(target, after_data)
    assert before_semantics == after_semantics and face_count == after_faces
    assert sha(source) == before, 'Source changed during staging'
    return {'source': source.as_posix(), 'staged': target.as_posix(),
        'before_sha256': before, 'after_sha256': sha(target),
        'before_entries': {k.decode(): v for k, v in counts.items()},
        'after_entries': {k.decode(): len(v) - 1 for k, v in after_data.items()},
        'removed_unused_entries': {k.decode(): counts[k] - sum(used[k]) for k in KINDS},
        'merged_identical_used_entries': {k.decode(): sum(used[k]) - unique_counts[k] for k in KINDS},
        'faces': face_count, 'face_semantics_sha256': before_semantics,
        'all_face_material_position_uv_normal_bytes_identical': True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--deduplicate', action='store_true', help='Also merge byte-identical used table entries')
    args = parser.parse_args()
    report = {'revision': 'lossless-unused-obj-entry-compaction-v1', 'models': {}}
    for side in ('east', 'west'):
        source = Path(f'Assets/models/maps/belltower/belltower_{side}.obj')
        row = compact(source, args.out / source, args.deduplicate)
        report['models'][side] = row
        print(json.dumps(row), flush=True)
    (args.out / 'compaction-report.json').write_text(json.dumps(report, indent=2) + '\n')


if __name__ == '__main__':
    main()
