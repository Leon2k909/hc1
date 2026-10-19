"""Save the concrete/material handoff only after current offline evidence agrees."""
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[4]
OUT=ROOT/'output/lowtide/quality-pass/concrete-wear'
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def write(path,value): path.write_text(json.dumps(value,indent=2)+'\n')
manifest=json.loads((OUT/'manifest.json').read_text())
checked=json.loads((OUT/'offline-verification.json').read_text())
preview=json.loads((OUT/'preview/provenance.json').read_text())
reproduced=json.loads((OUT/'reproduction/manifest.json').read_text())
assert manifest==reproduced
assert checked['manifest_sha256']==preview['manifest_sha256']==sha(OUT/'manifest.json')
assert checked['reviewer_sha256']==preview['renderer_sha256']==sha(ROOT/'Tools/lowtide_concrete_wear_review.py')
assert checked['shared_renderer_sha256']==preview['shared_renderer_sha256']==sha(ROOT/'Tools/lowtide_warehouse_floor_review.py')
assert all(sha(OUT/'stage'/p)==sha(OUT/'reproduction/stage'/p)==digest for p,digest in manifest['staged_files'].items())
assert all(sha(ROOT/p)==digest for p,digest in manifest['protected'].items())
assert all(sha(OUT/'preview'/p)==digest for p,digest in preview['previews'].items())
combined_path=ROOT/'output/lowtide/quality-pass/material-integration/manifest.json'
combined=json.loads(combined_path.read_text())
assert all(sha(ROOT/p)==digest for p,digest in combined['source_manifests'].items())
assert combined['generator_sha256']==sha(ROOT/'Tools/lowtide_material_stage.py')
assert all(sha(combined_path.parent/'stage'/p)==digest for p,digest in combined['assets'].items())
reproduction=dict(manifest_sha256=sha(OUT/'manifest.json'),fresh_process_reproduction=True,
    byte_identical_files=len(manifest['staged_files']),protected_live_files=len(manifest['protected']))
write(OUT/'reproduction-verification.json',reproduction)
status=dict(date='2026-10-15',status='offline_candidate_ready_for_native_review',revision=manifest['revision'],
    user_work_mode='Continue offline for now',production_changed=False,production_generator_integrated=False,
    generator='Tools/lowtide_concrete_wear.py',reviewer='Tools/lowtide_concrete_wear_review.py',
    layout='Sources/Lowtide/concrete/wear-layout.json',shader_extension='Sources/Lowtide/concrete/warehouse-use.hlsl',
    changes=[
        'Dust follows the actual stored-cargo, column and wall footprints from saved collision shapes.',
        'Twelve clearance-checked warehouse routes receive restrained traffic polishing; broader smooth segments have short dry-rubber deposits.',
        'The original generated concrete colour, micro-normal and static floor-contact bake remain unchanged.',
        'Only the two ground-floor concrete regions are affected. The original shader is preserved through reversible insertions.',
        'No mesh faces, collision, scene data or material slots are added.'
    ],
    scope=dict(warehouses=2,routes=12,mask_dimensions=[2048,2048],mask_channels=manifest['channels'],
               material_slot='rw_concrete.vmat',delta_triangles=0,new_material_slots=0),
    evidence=dict(manifest='output/lowtide/quality-pass/concrete-wear/manifest.json',manifest_sha256=sha(OUT/'manifest.json'),
        verification='output/lowtide/quality-pass/concrete-wear/offline-verification.json',
        reproduction='output/lowtide/quality-pass/concrete-wear/reproduction-verification.json',
        views='output/lowtide/quality-pass/concrete-wear/preview/provenance.json',
        route_samples=checked['path_samples'],atlas_texel_samples=checked['atlas_texel_samples'],
        complete_material_scope_samples=checked['complete_material_scope_samples'],untouched_floor_samples=checked['untouched_floor_material_samples'],
        byte_identical_reproduced_files=len(manifest['staged_files']),protected_live_files_unchanged=len(manifest['protected'])),
    preview=dict(kind='Matched CPU floor-material views and numerical layout diagrams',native_engine_capture=False,
        visual_review='The six matched receiving/loading/grazing material views and both warehouse layout diagrams were reviewed. This is a modest candidate for native evaluation; actual warehouse brightness, reflections, temporal filtering and performance remain unverified.',
        limitations=preview['limitations']),
    superseded=dict(directory='output/lowtide/quality-pass/concrete-wear/first-review',
        reason='The first continuous tire strokes were too uniform; they were replaced by shorter deposits weighted toward turns.'),
    integration=dict(combined_manifest=combined_path.relative_to(ROOT).as_posix(),composer='Tools/lowtide_material_stage.py',
        warning='Both timber and concrete candidates change the same VMDLs. Use the combined four-slot remap plan; copying the independent VMDLs over each other loses one pass.',
        native_followup=[
            'Keep the offline restriction until the user resumes native work. Read fresh editor/project/compile/scene/play/unsaved state.',
            'Revalidate before hashes and compile unused shader/material candidates through the native editor.',
            'Review both floors in the existing normal viewport, preserving camera, scene, tab and play state. No temporary-scene or offscreen-render loops.',
            'Inspect contact placement, subtlety, grazing reflections, atlas edges and distance filtering under the actual warehouse lighting; measure gameplay cost.',
            'After acceptance, add the scoped material generation/remaps to the canonical interior generator and apply the four material bindings through the editor.',
            'Preserve later LOD/model edits rather than replacing a whole VMDL snapshot. Refresh the existing warehouse DDGI bake after accepted albedo changes, save and verify persistence.'
        ]),
    overall_goal='Still open; offline material previews do not establish AAA quality')
write(ROOT/'Sources/Lowtide/concrete/wear-status.json',status)
write(OUT/'first-review/review-status.json',dict(status='superseded_offline_review',selected_for_native_integration=False,
    reason=status['superseded']['reason']))
handoff_path=ROOT/'Sources/Lowtide/construction/offline-status.json'
before=handoff_path.read_bytes(); handoff=json.loads(before)
handoff['combined_materials']=dict(manifest=combined_path.relative_to(ROOT).as_posix(),composer='Tools/lowtide_material_stage.py',
    model_snapshots=2,existing_slot_remaps=4,staged_files=len(combined['assets']),new_material_slots=0,
    warning='Use the combined material remap plan for the timber/concrete passes; independent VMDL copies overwrite each other. Revalidate later LOD/model edits.')
handoff['separate_pending_work']['concrete_floor_use']='Sources/Lowtide/concrete/wear-status.json'
handoff['separate_pending_work']['note']='Foliage persistence remains separate. The timber/concrete floor candidates share the combined material set; all are separate from the combined window/door OBJ geometry.'
assert handoff_path.read_bytes()==before
write(handoff_path,handoff)
floor_path=ROOT/'Sources/Lowtide/floor/floor-status.json'
floor=json.loads(floor_path.read_text())
floor['integration']['combined_material_manifest']=combined_path.relative_to(ROOT).as_posix()
floor['integration']['warning']='The concrete-use and timber candidates share VMDL paths. Use the combined four-slot remap plan and preserve any later model/LOD changes; do not overwrite one with the other.'
write(floor_path,floor)
print(json.dumps(dict(**reproduction,combined_material_files=len(combined['assets'])),indent=2))
