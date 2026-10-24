"""Restore original OBJ index order after the first shelf insertion.

Preserve every face and material record, including subsequent lounger work.
Only reorder tables whose allocation order is proven by the original snapshot.
"""
import json
from pathlib import Path
import shutil
import veridant_stage_door_clearance as T

PREFIXES=(b'v ',b'vt ',b'vn ')
FILES=('Assets/models/maps/veridant/veridant_buildings.obj',
       'Assets/models/maps/veridant/lounger-v2/veridant_buildings-base.obj')


def tables(lines):return [line for line in lines if line.startswith(PREFIXES)]


def main():
    stage=T.OUT/'stage-v5-index-repair'
    assert not stage.exists()
    stage.mkdir()
    previous=json.loads((T.OUT/'stage-v1/manifest.json').read_text())
    original=T.ROOT/next(iter(previous['files'].values()))['backup']
    original_lines=original.read_bytes().splitlines(keepends=True)
    first_material=next(i for i,line in enumerate(original_lines) if line.startswith(b'usemtl '))
    original_tables=tables(original_lines)
    prefix_count=len(tables(original_lines[:first_material]))
    prefix=original_tables[:prefix_count];suffix=original_tables[prefix_count:]
    assert suffix,'This repair specifically handles original tables following faces.'
    shelf_tables=tables((T.OUT/'stage-v1/shelves.obj').read_bytes().splitlines(keepends=True))
    prefix_bytes=b''.join(prefix);suffix_bytes=b''.join(suffix);shelf_bytes=b''.join(shelf_tables)
    base_tables=b''.join(tables((T.ROOT/FILES[1]).read_bytes().splitlines(keepends=True)))
    assert base_tables.startswith(prefix_bytes+shelf_bytes+suffix_bytes)
    later_base_tables=base_tables[len(prefix_bytes+shelf_bytes+suffix_bytes):]
    replacement=T.ROOT/'Assets/models/maps/veridant/lounger-v2/veridant_buildings-replacements.obj'
    replacement_tables=b''.join(tables(replacement.read_bytes().splitlines(keepends=True)))
    canonical_tables=b''.join(tables((T.ROOT/FILES[0]).read_bytes().splitlines(keepends=True)))
    assert canonical_tables.count(replacement_tables)==1
    assert canonical_tables.replace(replacement_tables,b'',1)==base_tables
    ordered_base=b''.join(original_tables)+shelf_bytes+later_base_tables
    wanted={FILES[1]:ordered_base,FILES[0]:ordered_base+replacement_tables}
    protected={p:T.sha(T.ROOT/p) for p in previous['protected_sha256']}
    sources={p:T.sha(T.ROOT/p) for p in ('Tools/veridant_map.py','Tools/veridant_parts.py',
        'Tools/veridant_stage_door_clearance.py','Tools/veridant_repair_door_indices.py',
        'Tools/map_kit.py','Tools/railhead_stage_extinguisher.py')}
    files={};proof={}
    for relative in FILES:
        source=T.ROOT/relative;before=T.sha(source)
        lines=source.read_bytes().splitlines(keepends=True)
        ordered=wanted[relative].splitlines(keepends=True)
        added=ordered[len(original_tables):]
        records=[line for line in lines if not line.startswith(PREFIXES)]
        assert all(int(token.split(b'/')[0])>0 for line in records if line.startswith(b'f ') for token in line.split()[1:])
        target=stage/relative;target.parent.mkdir(parents=True,exist_ok=True)
        target.write_bytes(b''.join(ordered+records))
        assert [line for line in target.read_bytes().splitlines(keepends=True) if not line.startswith(PREFIXES)]==records
        for kind in PREFIXES:
            expected=[line for line in original_tables if line.startswith(kind)]+[line for line in added if line.startswith(kind)]
            assert [line for line in ordered if line.startswith(kind)]==expected
        backup=stage/'before'/relative;backup.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(source,backup)
        assert T.sha(backup)==before and T.sha(source)==before
        files[relative]={'before':before,'after':T.sha(target),'source':target.relative_to(T.ROOT).as_posix(),
                         'backup':backup.relative_to(T.ROOT).as_posix()}
        proof[relative]={'face_and_material_bytes_preserved':True,'original_index_mapping_restored':True,
                         'original_table_records':len(original_tables),'added_table_records':len(added)}
    for group in (protected,sources):
        for p,h in group.items():assert T.sha(T.ROOT/p)==h,p
    manifest={**previous,'revision':'veridant-door-clearance-index-repair-v1','files':files,
              'source_sha256':sources,'protected_sha256':protected,'index_repair_proof':proof,
              'unrelated_geometry_bytes_exact':False,'unrelated_face_and_material_records_exact':True,
              'original_geometry_indices_restored':True}
    (stage/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps({'files':files,'proof':proof}))


if __name__=='__main__':main()
