"""Compose the two offline warehouse materials without losing shared VMDL edits.

Never writes live assets. The combined VMDLs are review snapshots: native work
must revalidate their before hashes and preserve any later LOD/material changes.
"""
import hashlib
import argparse
import json
from pathlib import Path
import re
import shutil

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'output/lowtide/quality-pass'
OUT=BASE/'material-integration'


def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()


def remaps(data):
    pattern=rb'\{\s*from\s*=\s*"([^"]+)"\s+to\s*=\s*"([^"]+)"\s*\}'
    result={}
    for match in re.finditer(pattern,data):
        slot=match[1].decode()
        assert slot not in result
        result[slot]=(match[2].decode(),match[0])
    return result


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    stage=OUT/'stage'
    source_manifests={}; protected={}; resources={}; models={}; plan=[]
    for name,slot in (('warehouse-floor','floorboards.vmat'),('concrete-wear','rw_concrete.vmat')):
        manifest_path=BASE/name/'manifest.json'
        source_manifests[manifest_path.relative_to(ROOT).as_posix()]=sha(manifest_path)
        manifest=json.loads(manifest_path.read_text())
        assert manifest['production_changed'] is False
        assert all(sha(ROOT/p)==digest for p,digest in manifest['sources'].items())
        for path,digest in manifest['protected'].items():
            assert sha(ROOT/path)==digest
            assert protected.get(path,digest)==digest
            protected[path]=digest
        for relative,digest in manifest['staged_files'].items():
            source=BASE/name/'stage'/relative
            assert sha(source)==digest
            if relative.endswith('.vmdl'):
                current=ROOT/'Assets'/relative
                before=current.read_bytes(); after=source.read_bytes()
                old,new=remaps(before),remaps(after)
                assert old.keys()==new.keys()
                changed=[key for key in old if old[key]!=new[key]]
                assert changed==[slot],(relative,changed)
                assert after.replace(new[slot][1],old[slot][1],1)==before
                models.setdefault(relative,dict(before=sha(current),original=before,data=before,slots=[]))
                model=models[relative]
                assert model['original']==before and slot not in model['slots']
                assert model['data'].count(old[slot][1])==1
                model['data']=model['data'].replace(old[slot][1],new[slot][1],1)
                model['slots'].append(slot)
                plan.append(dict(model=relative,slot=slot,before=old[slot][0],after=new[slot][0],source=name))
            else:
                assert resources.get(relative,digest)==digest
                resources[relative]=digest
                destination=stage/relative
                destination.parent.mkdir(parents=True,exist_ok=True)
                shutil.copy2(source,destination)
    records={}
    for relative,model in models.items():
        reverse=model['data']
        for change in [r for r in plan if r['model']==relative]:
            rows=remaps(reverse)
            old=remaps(model['original'])[change['slot']][1]
            reverse=reverse.replace(rows[change['slot']][1],old,1)
        assert reverse==model['original']
        target=stage/relative; target.parent.mkdir(parents=True,exist_ok=True); target.write_bytes(model['data'])
        records[relative]=dict(before=model['before'],after=sha(target),slots=model['slots'])
    manifest=dict(status='combined_offline_material_candidates_not_installed',production_changed=False,
        generator_sha256=sha(Path(__file__)),source_manifests=source_manifests,protected=protected,
        models=records,material_remap_plan=plan,new_geometry=0,new_material_slots=0,
        assets={p.relative_to(stage).as_posix():sha(p) for p in sorted(stage.rglob('*')) if p.is_file()},
        native_warning='Revalidate the before hashes and apply only the four slot remaps. Do not overwrite later model/LOD edits with a whole snapshot.',
        geometry_compatibility='The separate combined window/door set edits OBJ files; this stage edits material bindings only.')
    assert len(plan)==4 and len(records)==2 and len(manifest['assets'])==20
    assert all(sha(ROOT/p)==digest for p,digest in protected.items())
    (OUT/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps(dict(staged_files=len(manifest['assets']),model_snapshots=len(records),
                         exact_material_remaps=len(plan),protected_files=len(protected)),indent=2))


def build_current(out):
    """Revalidate reviewed resources and compose only their four current bindings.

    Construction edits change render meshes without necessarily changing the floor
    scope. Collision-source changes must still reproduce the exact reviewed floor
    footprints; changed footprints require regenerating and reviewing the wear mask.
    """
    import numpy as np
    from PIL import Image
    import lowtide_warehouse_floor as F
    import lowtide_concrete_wear as C

    out=Path(out).resolve()
    assert out.is_relative_to(BASE) and not out.exists(), 'Use a new quality-pass output directory'
    manifests={name:json.loads((BASE/name/'manifest.json').read_text())
               for name in ('warehouse-floor','concrete-wear')}
    source_changes={}; protected={}; floor_scope={}; collision_checks={}
    allowed_changes={f'Assets/models/maps/lowtide/lowtide_{part}{side}.vmdl'
                     for side in ('east','west') for part in ('','dress_')}
    # The native opaque-floor import uses RGB box mips for the unchanged 1254px
    # source atlas. Verify this exact reviewed shader fix before accepting it.
    floor_shader='Sources/Lowtide/floor/warehouse-floor.shader'
    reviewed=(BASE/'warehouse-floor/stage'/F.SHADER).read_text()
    common='    #include "common/utils/Material.CommonInputs.hlsl"'
    opaque=('    // This floor is opaque. Ordinary RGB mips also support the source scan\'s\n'
            '    // non-power-of-two dimensions, which the alpha-weighted filter rejects.\n'
            '    #define AlphaWeighted( color, opacity ) Box( color )\n'+common+'\n'
            '    #undef AlphaWeighted')
    assert reviewed.count(common)==1
    assert (ROOT/floor_shader).read_text()==reviewed.replace(common,opaque,1)
    allowed_changes.add(floor_shader)
    for name,manifest in manifests.items():
        changed=[p for p,h in manifest['sources'].items() if sha(ROOT/p)!=h]
        assert set(changed)<=allowed_changes, ('Candidate inputs changed; rebuild and review',name,changed)
        source_changes[name]=changed
        for p in manifest['sources']:
            protected[p]=sha(ROOT/p)
        for relative,digest in manifest['staged_files'].items():
            assert sha(BASE/name/'stage'/relative)==digest, ('Reviewed resource changed',name,relative)
        # Existing texture inputs must still match the reviewed material.
        for relative in manifest['staged_files']:
            if not relative.endswith('.vmat'): continue
            text=(BASE/name/'stage'/relative).read_text()
            for dependency in re.findall(r'"((?:materials|shaders)/[^"\n]+)"',text):
                path=ROOT/'Assets'/dependency
                if dependency in manifest['staged_files'] or not path.is_file(): continue
                key=path.relative_to(ROOT).as_posix()
                assert key in manifest['protected'] and sha(path)==manifest['protected'][key], ('Material input changed',key)
                protected[key]=sha(path)

    concrete=manifests['concrete-wear']
    def footprints(shapes):
        return sorted(tuple(sorted(tuple(round(v,8) for v in point) for point in shape['polygon'])) for shape in shapes)
    for side in (1,-1):
        shapes,inputs=C.collision(side,concrete['settings'])
        protected.update(inputs)
        assert footprints(shapes)==footprints(concrete['details'][str(side)]['collision_shapes']), ('Floor footprint changed',side)
        occupied=C.occupancy(shapes,concrete['settings']['bounds_plan_inches'],concrete['settings']['atlas_cell_pixels'])
        reference=np.asarray(Image.open(BASE/'concrete-wear'/f'occupied-{side:+}.png'))>0
        assert np.array_equal(occupied,reference), ('Collision raster changed',side)
        collision_checks[str(side)]=dict(shapes=len(shapes),footprints_exact=True,occupied_raster_exact=True)
    for half in ('east','west'):
        model=ROOT/f'Assets/models/maps/lowtide/lowtide_{half}.obj'
        floor_scope[half]=F.verify_floor_faces(model)
        protected[model.relative_to(ROOT).as_posix()]=sha(model)
    assert C.staged_shader()==(BASE/'concrete-wear/stage'/C.SHADER).read_text()
    protected['Assets/scenes/maps/Lowtide/lowtide.scene']=sha(ROOT/'Assets/scenes/maps/Lowtide/lowtide.scene')

    stage=out/'stage'; plan=[]; model_bytes={}; model_before={}
    for name,slot in (('warehouse-floor','floorboards.vmat'),('concrete-wear','rw_concrete.vmat')):
        for relative,digest in manifests[name]['staged_files'].items():
            source=BASE/name/'stage'/relative
            if relative.endswith('.vmdl'):
                live=ROOT/'Assets'/relative
                original=live.read_bytes()
                old,new=remaps(original),remaps(source.read_bytes())
                expected='materials/buildings/floorboards.vmat' if name=='warehouse-floor' else 'materials/lowtide/interior/lt_concrete.vmat'
                assert old[slot][0] in (expected,new[slot][0])
                replacement=old[slot][1].replace(old[slot][0].encode(),new[slot][0].encode())
                current=model_bytes.setdefault(relative,original)
                model_before[relative]=sha(live)
                model_bytes[relative]=current.replace(old[slot][1],replacement,1)
                plan.append(dict(model=relative,slot=slot,before=old[slot][0],after=new[slot][0],source=name))
                protected['Assets/'+relative]=sha(live)
            else:
                destination=stage/relative
                destination.parent.mkdir(parents=True,exist_ok=True)
                shutil.copyfile(ROOT/floor_shader if relative==F.SHADER else source,destination)
    for relative,data in model_bytes.items():
        target=stage/relative;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
        reverse=data
        original=(ROOT/'Assets'/relative).read_bytes()
        for row in [p for p in plan if p['model']==relative]:
            reverse=reverse.replace(remaps(reverse)[row['slot']][1],remaps(original)[row['slot']][1],1)
        assert reverse==original
    assets={p.relative_to(stage).as_posix():sha(p) for p in sorted(stage.rglob('*')) if p.is_file()}
    assert len(assets)==20 and len(plan)==4
    assert all(sha(ROOT/p)==h for p,h in protected.items())
    result=dict(status='current_floor_candidates_ready_for_native_review',production_changed=False,
                project_root=str(ROOT),generator_sha256=sha(Path(__file__)),
                source_manifests={name:sha(BASE/name/'manifest.json') for name in manifests},
                historical_source_changes=source_changes,current_collision_checks=collision_checks,
                current_mezzanine_scope=floor_scope,protected=protected,
                material_remap_plan=plan,models={p:dict(before=model_before[p],after=assets[p]) for p in model_bytes},
                assets=assets,new_geometry=0,new_material_slots=0,
                native_warning='Import the unused resources first. Review both floors before applying only the four current remaps; preserve current geometry, collision, LODs and model identity.',
                limitations=['Review again if material inputs or layout change; gameplay performance remains pending','Lighting bake must be reviewed after accepted albedo changes'])
    (out/'manifest.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(stage=str(stage),files=len(assets),remaps=len(plan),
                         protected=len(protected),collision_checks=collision_checks,
                         current_mezzanine_scope=floor_scope),indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--current',action='store_true')
    parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    if args.current:
        if args.output is None: parser.error('--current requires a new --output folder')
        build_current(args.output)
    else:
        if args.output is not None: parser.error('--output requires --current')
        main()
