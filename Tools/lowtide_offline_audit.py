"""Compare historical offline candidates with the current checkout, without rebasing hashes.

Historical success reports describe their original snapshot. This audit keeps
that evidence intact and identifies stale source data and direct write targets.
It does not establish native acceptance or authorize copying any staged file.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT/'output/lowtide/quality-pass'
SETS = ('construction-integration', 'construction-lods', 'warehouse-floor', 'concrete-wear',
        'material-integration', 'sack-construction', 'sack-lods', 'drain-construction',
        'drain-junctions', 'paving-use', 'water-filter')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None


def audit(destination=None):
    cache = {}

    def current(relative):
        if relative not in cache:
            path = (ROOT/relative).resolve()
            assert path.is_relative_to(ROOT), relative
            cache[relative] = sha(path)
        return cache[relative]

    def differences(expected):
        return {p:dict(expected=h, current=current(p)) for p, h in expected.items() if current(p) != h}

    records = {}
    for name in SETS:
        path = BASE/name/'manifest.json'
        data = json.loads(path.read_text())
        protected = data.get('protected', {})
        inputs = dict(data.get('sources', {}))
        inputs.update(data.get('source_manifests', {}))
        targets = {}
        for key in ('changes', 'models'):
            for p, value in data.get(key, {}).items():
                if isinstance(value, dict) and 'before' in value:
                    targets[p if p.startswith(('Assets/', 'Code/')) else 'Assets/'+p] = value['before']
        for p in data.get('staged_files', data.get('assets', {})):
            live = p if p.startswith(('Assets/', 'Code/')) else 'Assets/'+p
            targets.setdefault(live, protected.get(live, inputs.get(live)))
        if 'live_before' in data:
            targets.update(data['live_before'])
        if name == 'drain-junctions':
            targets['Assets/models/maps/lowtide/lowtide_finish.obj'] = data['live_before_sha256']
            material_data = json.loads((BASE/'drain-construction/manifest.json').read_text())
            for p, value in material_data['staged_material_changes']['changes'].items():
                targets['Assets/'+p] = value['before']
        if name == 'sack-lods':
            parent = json.loads((ROOT/data['baseline_manifest']).read_text())
            targets.update({'Assets/'+p:v['before'] for p, v in parent['changes'].items()})
        if name == 'construction-lods':
            parent = json.loads((BASE/'construction-integration/manifest.json').read_text())
            targets.update({'Assets/'+p:v['before'] for p, v in parent['changes'].items()})
        # Existing targets not explicitly recorded as before-values use the
        # original protected/input snapshots, never their staged after hashes.
        source_drift = differences(inputs)
        target_drift = differences(targets)
        broad_drift = differences(protected)
        records[name] = dict(manifest=path.relative_to(ROOT).as_posix(), manifest_sha256=sha(path),
            protected_file_count=len(protected), protected_drift=broad_drift,
            source_drift=source_drift, target_drift=target_drift,
            target_before=targets,
            disposition=('rebase_required' if source_drift or target_drift else
                         'fresh_context_validation_required' if broad_drift else 'matches_recorded_snapshot'),
            native_accepted=False)
    all_drift = sorted(set(p for record in records.values() for key in ('protected_drift', 'source_drift', 'target_drift') for p in record[key]))
    report = dict(status='historical_snapshots_require_revalidation' if all_drift else 'historical_snapshots_current',
        project_root=str(ROOT), project_file_sha256=sha(ROOT/'hc1.sbproj'),
        observed_utc=datetime.now(timezone.utc).isoformat(), tool_sha256=sha(Path(__file__)),
        production_changed_by_audit=False, current_hashes=cache, candidates=records,
        changed_paths=all_drift, safe_to_bulk_promote=False,
        note='A target match alone does not establish current scene appearance, compilation, gameplay performance or persistence.')
    if destination:
        destination = Path(destination).resolve()
        assert destination.is_relative_to(BASE)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8', newline='\n')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=BASE/'rebase-2026-10-18/audit.json')
    report = audit(parser.parse_args().output)
    print(json.dumps(dict(status=report['status'], changed_paths=report['changed_paths'],
        candidates={n:dict(disposition=r['disposition'], source_changes=len(r['source_drift']),
                           direct_target_changes=len(r['target_drift'])) for n, r in report['candidates'].items()}), indent=2))
