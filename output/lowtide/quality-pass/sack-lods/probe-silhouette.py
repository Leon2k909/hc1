"""Compare the medium body with all longitudinal rings before rebuilding sets."""
import json
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT/'Tools'))
import lowtide_sack_lod_review as R

OUT = ROOT/'output/lowtide/quality-pass/sack-lod-shape-probe'
R.D.LEVELS[1]['rings'] = R.S.RINGS.tolist()
base = json.loads((R.D.BASE/'manifest.json').read_text())
seeds = [R.S.seed_for(base['layout']['lowtide_dress_east'][0]['lo']), R.S.seed_for(base['layout']['lowtide_fleet'][-1]['lo'])]
rows = []
for sample, seed in enumerate(seeds):
    model = R.K.Model()
    R.D.sack(model, (-10.5, -16.5, 0), (21, 33, 11), 1, seed=seed)
    path = OUT/f'full-rings-{sample}.obj'
    R.K.write_obj(path, model, 'sack-lod-review')
    lower, _ = R.R.read_obj(path)
    close, _ = R.R.read_obj(OUT/f'preview/sample-{sample}-level-0.obj')
    for name, view in R.VIEWS.items():
        for size in (320, 160, 80):
            spec = R.view_spec(close, view, size)
            rows.append(dict(sample=sample, view=name, size=size,
                **R.mask_error(R.silhouette(close, spec), R.silhouette(lower, spec))))
    print(f'Compared full rings for seed {sample}', flush=True)
(OUT/'full-rings-metrics.json').write_text(json.dumps(rows, indent=2)+'\n')
print(json.dumps({size:max(row['max_edge_pixels'] for row in rows if row['size']==size) for size in (320,160,80)}, indent=2))
