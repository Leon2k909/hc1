"""Record the isolated parcel-layout prototype and its production dependencies."""
import hashlib
import json
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'output/belltower/quality/parcel-shapes-v4-hires'


def digest(path):
    with path.open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def main():
    candidate = OUT / 'vista_c_color.jpg'
    accepted = ROOT / 'Assets/materials/belltower/vista/vista_c_color.jpg'
    with Image.open(candidate) as im:
        assert im.size == (1024, 1024)
    with Image.open(accepted) as im:
        assert im.size == (4096, 4096)
    report = {
        'status': 'offline prototype only; no live assets replaced',
        'zone': 'c', 'candidate_size': [1024, 1024], 'accepted_size': [4096, 4096],
        'parcel_multiplier': 0.9,
        'candidate_sha256': digest(candidate),
        'accepted_sha256': digest(accepted),
        'source_sha256': digest(ROOT / 'Tools/belltower_vista_paint.py'),
        'comparison': 'output/belltower/quality/parcel-shapes-v4-hires/compare.jpg',
        'remaining': [
            'Rebuild every 4K vista zone using the same parcel layout so overlap blending is consistent',
            'Regenerate painted vegetation and the sector forest if parcel changes affect cover or crown positions',
            'Verify accepted collision and 94 gameplay spots remain unchanged',
            'Stage isolated native assets, compare matched Belltower gameplay views and measure performance',
        ],
        'in_engine_verified': False,
        'changes_to_production_scene_or_materials': False,
    }
    (OUT / 'prototype-review.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
