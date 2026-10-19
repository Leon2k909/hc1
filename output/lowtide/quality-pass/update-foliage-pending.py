from pathlib import Path
import json

root = Path(__file__).resolve().parents[3]
path = root / 'Sources/Lowtide/foliage/foliage-status.json'
status = json.loads(path.read_text())
status['status'] = 'visually_accepted_persistence_pending_after_editor_restart'
status['v2'].update({
    'status': 'compiled_and_visually_accepted_with_tint',
    'not_imported': False,
    'tint': [.48, .66, .54],
    'native_compile': 'output/lowtide/quality-pass/foliage/v2-compile.json',
    'native_bindings': 'output/lowtide/quality-pass/foliage/v2-bindings.json',
    'accepted_visual_review': 'output/lowtide/quality-pass/foliage/v2-tint-preview.json',
    'accepted_views': ['quay-v2-tint.png', 'crown-v2-tint.png', 'west-v2-tint.png'],
    'visual_result': 'Original silhouette retained, finer generated leaf detail, and restrained green tint. Untinted version was too pale. All four overrides, camera and prior Sewage tab were restored after each preview.',
    'production_stage': 'output/lowtide/quality-pass/foliage/production-stage',
    'production_manifest': 'output/lowtide/quality-pass/foliage/production-manifest.json',
    'production_preflight': 'output/lowtide/quality-pass/foliage/production-preflight.json',
    'canonical_resource_writer': 'Tools/lowtide_trees.py',
    'map_generator_integration_pending': True,
    'scene_assignment_pending': True,
    'requires': [
        'Connect to the new editor process and confirm project, compile, play and dirty-scene state.',
        'Apply staged tint through apply-foliage-material.cs, then check the report and loaded value.',
        'Inspect native per-slot material serialization through inspect-foliage-persistence.cs; the previous timed-out call wrote no report and its process has exited.',
        'Integrate the exact native material-slot serialization into the canonical map writer.',
        'Apply only the leaf slot on the four trees through the editor and save; verify scene diff, resource bindings and actual production captures.',
        'Keep the wider AAA goal open; this is a foliage improvement only.'
    ]
})
status['preservation'].update({'protected_files_checked': 547,
    'preview_attempt': 'V2 and tinted V2 native comparisons completed. All four material overrides restored; camera and prior tab restored; no fresh errors through native console cursor 9918.'})
status['blocker'] = {
    'previous_pid': 16792,
    'previous_process_exited': True,
    'current_pid': 35332,
    'started_local': '2026-10-15T00:30:46.581406',
    'state': 'New editor process confirmed alive, startup reached dependency propagation then logged a stall. Native MCP is disconnected and CLI does not yet list an open project.',
    'editor_last_log_local': '2026-10-15 00:32:55: ToolsStallMonitor: Stall detected',
    'process_not_restarted_or_terminated_by_this_work': True
}
before = path.read_bytes()
data = (json.dumps(status, indent=2) + '\n').encode()
temporary = path.with_suffix('.json.next')
temporary.write_bytes(data)
assert path.read_bytes() == before
temporary.replace(path)
print('Saved accepted-variant evidence and exact remaining persistence steps.')
