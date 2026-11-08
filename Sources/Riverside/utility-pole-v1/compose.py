"""Put each matched before/after pair of editor viewport captures side by side (comparison-<name>.png).

The captures are the editor's own viewport (`screenshot_game`, cropped to the viewport pane), from the same camera pose each
time (poses in README.md), with the editor's gizmos in both. Nothing is retouched. `comparison-arms-zoom.png` is an
enlargement (4x, Lanczos resize) of one small region of the arms pair, labelled as such; it is not a separate capture.

    python compose.py            writes output/riverside/utility-pole-v1/comparison-*.png from captures/before-*.png + after-*.png
"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import io

OUT = Path(__file__).absolute().parents[3] / 'output/riverside/utility-pole-v1'
CAP = OUT / 'captures'
# name -> title (all poses are in README.md)
PAIRS = [
    ('trunk', '3.6 m from a lane pole, looking up the trunk'),
    ('foot', '3.3 m from a lane pole, standing eye height'),
    ('arms', '6.7 m from a lane pole, looking up at the crossarms and the lamp'),
    ('mid', '16 m from a lane pole, standing eye height'),
    ('far', 'looking down the lane at the row of poles'),
    ('padmid', '15 m from the spawn pad deck, looking at the first pole'),
    ('east', '13.5 m from an east-side pole, standing eye height'),
]
ZOOM_BOX = (440, 150, 670, 290)  # region of the arms capture to enlarge (230 x 140 px -> 920 x 560)
bold = ImageFont.truetype('C:/Windows/Fonts/arialbd.ttf', 30)
small = ImageFont.truetype('C:/Windows/Fonts/arial.ttf', 22)
INK, GOLD, BACK = (230, 233, 224), (222, 210, 170), (20, 24, 27)


def sheet(a, b, title, note=None):
    assert a.size == b.size, (a.size, b.size)
    w, h = a.size
    out = Image.new('RGB', (w * 2 + 12, h + 92), BACK)
    d = ImageDraw.Draw(out)
    d.text((16, 10), 'RIVERSIDE UTILITY POLES - ' + title.upper(), font=small, fill=INK)
    d.text((16, 44), 'BEFORE', font=bold, fill=GOLD)
    d.text((w + 28, 44), 'AFTER', font=bold, fill=GOLD)
    if note:
        d.text((w - 8 - d.textlength(note, font=small) + 12, 52), note, font=small, fill=(170, 176, 168))
    out.paste(a, (0, 92))
    out.paste(b, (w + 12, 92))
    return out


def save(img, name):
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    (OUT / name).write_bytes(buf.getvalue())
    print(OUT / name, img.size)


def main():
    for key, title in PAIRS:
        pa, pb = CAP / f'before-{key}.png', CAP / f'after-{key}.png'
        if not (pa.exists() and pb.exists()):
            print('skipped (no pair):', key)
            continue
        a, b = Image.open(pa).convert('RGB'), Image.open(pb).convert('RGB')
        save(sheet(a, b, title), f'comparison-{key}.png')
        if key == 'arms':
            za = a.crop(ZOOM_BOX).resize((920, 560), Image.LANCZOS)
            zb = b.crop(ZOOM_BOX).resize((920, 560), Image.LANCZOS)
            save(sheet(za, zb, 'the crossarms, 4x enlargement of one region of the arms pair',
                       'enlarged crop of the same two captures, not a new shot'), 'comparison-arms-zoom.png')


if __name__ == '__main__':
    main()
