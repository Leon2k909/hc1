"""Review checked native baseline and temporary far-field material captures."""
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
QUALITY = ROOT / 'output/belltower/quality'
BASE = QUALITY / 'farfield-v3-baseline'
TRIAL = QUALITY / 'farfield-v3-trial'
OUT = QUALITY / 'farfield-v3'
VIEWS = ('valley', 'west-ridge', 'terrace')


def main():
    width = 820
    height = 461
    sheet = Image.new('RGB', (width * 2, 3 * (height + 31)), '#172027')
    draw = ImageDraw.Draw(sheet)
    records = {}
    for i, name in enumerate(VIEWS):
        before = json.loads((BASE / f'{name}-camera.json').read_text())
        after = json.loads((TRIAL / f'{name}-camera.json').read_text())
        restore = json.loads((TRIAL / f'{name}-restore.json').read_text())
        assert before['Capture'] == after['Capture']
        assert before['Projection'] == after['Projection']
        assert before['TrialFarfieldSlots'] == 0 and after['TrialFarfieldSlots'] > 0
        assert restore['MaterialsRestored'] and restore['Slots'] == after['TrialFarfieldSlots']
        assert all(m['TexturesValid'] for m in before['Lighting'] + after['Lighting'])
        assert all(p['GamePreserved'] and p['SelectedDocumentPreserved'] and not p['SceneHasUnsavedChanges'] for p in (before, after))
        with Image.open(BASE / f'{name}.png') as image:
            a = image.convert('RGB')
        with Image.open(TRIAL / f'{name}.png') as image:
            b = image.convert('RGB')
        assert a.size == b.size == (1920, 1080)
        A = np.asarray(a, dtype=np.int16)
        B = np.asarray(b, dtype=np.int16)
        delta = np.abs(A - B)
        difference = delta.max(axis=2)
        records[name] = {
            'mean_rgb_difference_8bit': [round(float(x), 3) for x in delta.mean(axis=(0, 1))],
            'pixels_difference_over_8_fraction': round(float((difference > 8).mean()), 5),
            'pixels_difference_over_16_fraction': round(float((difference > 16).mean()), 5),
            'maximum_difference': int(difference.max()),
            'capture_camera_identical': True, 'materials_restored': True,
            'scene_preserved': True, 'trial_slots': after['TrialFarfieldSlots'],
        }
        top = i * (height + 31)
        draw.text((12, top + 8), f'{name}: accepted vista', fill='white')
        draw.text((width + 12, top + 8), f'{name}: new world-space field variation', fill='white')
        sheet.paste(a.resize((width, height), Image.Resampling.LANCZOS), (0, top + 31))
        sheet.paste(b.resize((width, height), Image.Resampling.LANCZOS), (width, top + 31))
    sheet.save(OUT / 'native-comparison.jpg', quality=91, subsampling=0)
    (OUT / 'native-review.json').write_text(json.dumps({
        'status': 'native trial reviewed, acceptance pending', 'views': records,
        'original_scene_modified': False,
    }, indent=2) + '\n')
    print(json.dumps(records, indent=2))


if __name__ == '__main__':
    main()
