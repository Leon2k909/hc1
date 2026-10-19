"""Bind the offline floor handoff to reviewed files and a fresh reproduction."""
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[4]
OUT=ROOT/'output/lowtide/quality-pass/warehouse-floor'
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
manifest=json.loads((OUT/'manifest.json').read_text())
reproduced=json.loads((OUT/'reproduction/manifest.json').read_text())
assert manifest==reproduced
assert all(sha(OUT/'reproduction/stage'/path)==digest for path,digest in manifest['staged_files'].items())
checked=json.loads((OUT/'offline-verification.json').read_text())
preview=json.loads((OUT/'preview/provenance.json').read_text())
assert checked['manifest_sha256']==preview['manifest_sha256']==sha(OUT/'manifest.json')
assert checked['reviewer_sha256']==preview['renderer_sha256']==sha(ROOT/'Tools/lowtide_warehouse_floor_review.py')
assert all(sha(OUT/'preview'/path)==digest for path,digest in preview['previews'].items())
assert all(sha(ROOT/path)==digest for path,digest in manifest['protected'].items())
reproduction=dict(manifest_sha256=sha(OUT/'manifest.json'),fresh_process_reproduction=True,
                  byte_identical_files=len(manifest['staged_files']),protected_live_files=len(manifest['protected']))
(OUT/'reproduction-verification.json').write_text(json.dumps(reproduction,indent=2)+'\n')
status=dict(date='2026-10-15',status='offline_candidate_ready_for_native_review',revision=manifest['revision'],
    user_work_mode='Continue offline for now',production_changed=False,production_generator_integrated=False,
    source='Sources/Lowtide/floor/warehouse-boards-source.png',imagegen='Sources/Lowtide/floor/imagegen.json',
    generator='Tools/lowtide_warehouse_floor.py',reviewer='Tools/lowtide_warehouse_floor_review.py',
    changes=[
        'Separate warehouse floor material replaces the shared domestic-looking floorboards only on the two mezzanines.',
        'Eight generated worn pine scans are sampled unchanged as individual boards; varied selection and flips break up the repeated square.',
        '25.4 cm wide boards run north/south across the existing joists. Staggered 2.794/5.588 m board ends and small recessed nails follow their 110-inch spacing.',
        'Numerical grain normals remain below 0.12 mm amplitude. The dry surface uses roughness 0.72-0.85 and a muted material tint.',
        'Filtered narrow gaps and shallow bevel normals supply edge response without adding mesh faces or displacement.'
    ],
    scope=dict(models=['lowtide_east','lowtide_west'],upward_floor_triangles=12,
        material_slot='floorboards.vmat',new_material_slots=0,delta_triangles=0,
        geometry_collision_scene_ceiling_stairs_shared_floor_material_preserved=True),
    evidence=dict(manifest='output/lowtide/quality-pass/warehouse-floor/manifest.json',manifest_sha256=sha(OUT/'manifest.json'),
        verification='output/lowtide/quality-pass/warehouse-floor/offline-verification.json',
        reproduction='output/lowtide/quality-pass/warehouse-floor/reproduction-verification.json',
        preview='output/lowtide/quality-pass/warehouse-floor/preview/provenance.json',
        preview_count=len(preview['previews']),layout_samples=checked['sampled_points'],
        finite_difference_uv_samples=checked['finite_difference_uv_samples'],mirrored_surface_samples=checked['mirrored_surface_samples'],
        byte_identical_reproduced_files=len(manifest['staged_files']),protected_live_files_unchanged=len(manifest['protected'])),
    preview=dict(kind='Matched CPU perspective material rendering',native_engine_capture=False,
        visual_review='Close, wide and grazing revised-tint views reviewed. Suitable for native evaluation; motion, native filtering and final brightness remain pending.',
        limitations=preview['limitations']),
    integration=dict(stage='output/lowtide/quality-pass/warehouse-floor/stage',
        compatibility='The window/door set replaces OBJ geometry; this candidate remaps one existing VMDL slot. They are independent changes.',
        warning='VMDL files are review snapshots. Apply only the floorboards remap through the editor after fresh validation; do not overwrite later LOD/material edits with a whole staged VMDL.',
        native_followup=[
            'Keep the user-requested offline restriction until they resume native work. Then read fresh project/compile/scene/unsaved/play state.',
            'Check manifest before hashes. Import the new material and shader as unused candidates and compile the shader before the material.',
            'Review the candidate in the existing normal viewport, preserving scene, camera, tab and play state. Do not use temporary-scene/offscreen-render loops.',
            'Inspect both mezzanines at close, walking and grazing distances: grain orientation, atlas edge filtering, joints, nail scale, normal direction and brightness under the actual lights.',
            'Measure shader/gameplay cost. The CPU renders provide no performance or temporal-aliasing result.',
            'After acceptance, add the floor-only material override to lowtide_interior.configure, apply the native material remaps, save and check persistence.',
            'Refresh the existing warehouse DDGI bakes after final material acceptance so their indirect light reflects the changed timber albedo.'
        ]),
    overall_goal='Still open; this offline material pass does not establish AAA quality')
combined_materials=ROOT/'output/lowtide/quality-pass/material-integration/manifest.json'
if combined_materials.exists():
    status['integration']['combined_material_manifest']=combined_materials.relative_to(ROOT).as_posix()
    status['integration']['warning']='The concrete-use and timber candidates share VMDL paths. Use the combined four-slot remap plan and preserve any later model/LOD changes; do not overwrite one with the other.'
(ROOT/'Sources/Lowtide/floor/floor-status.json').write_text(json.dumps(status,indent=2)+'\n')
handoff_path=ROOT/'Sources/Lowtide/construction/offline-status.json'
before=handoff_path.read_bytes()
handoff=json.loads(before)
handoff['separate_pending_work']['warehouse_floor']='Sources/Lowtide/floor/floor-status.json'
handoff['separate_pending_work']['note']='Foliage persistence and warehouse floor materials are separate from the combined window/door geometry. Use the combined material remap plan where present; native review/integration remains pending.'
assert handoff_path.read_bytes()==before
handoff_path.write_text(json.dumps(handoff,indent=2)+'\n')
print(json.dumps(reproduction,indent=2))
