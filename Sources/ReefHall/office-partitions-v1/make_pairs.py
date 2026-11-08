"""Side-by-side BEFORE | AFTER pictures for the review, built only from the real editor-viewport captures (nothing is drawn,
re-lit or touched up; the two halves are the unaltered capture files with a caption band above each).

    python make_pairs.py [pose ...]            default: every pose that has both before_<pose>.png and after_<pose>.png
    python make_pairs.py --label reverted      BEFORE | REVERTED instead (proves the revert)

Writes output/model-trial-20261106/reefhall_office_partitions/pair_<pose>.png (or pair_reverted_<pose>.png).
"""
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

OUT = Path(__file__).resolve().parents[3] / "output/model-trial-20261106/reefhall_office_partitions"
GAP, BAND = 6, 26


def font(size):
    for name in ("segoeuib.ttf", "arialbd.ttf", "arial.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def pair(pose, label):
    a_path, b_path = OUT / f"before_{pose}.png", OUT / f"{label}_{pose}.png"
    if not (a_path.exists() and b_path.exists()):
        return None
    a, b = Image.open(a_path).convert("RGB"), Image.open(b_path).convert("RGB")
    if a.size != b.size:
        raise SystemExit(f"{pose}: capture sizes differ {a.size} vs {b.size}; not pairing")
    w, h = a.size
    sheet = Image.new("RGB", (w * 2 + GAP, h + BAND), (18, 18, 20))
    d = ImageDraw.Draw(sheet)
    f = font(15)
    for x, text, colour in ((0, "BEFORE  (old box stairs)", (230, 170, 120)), (w + GAP, f"{label.upper()}  " + ("(new stairs)" if label == "after" else "(old stairs back)"), (140, 215, 150))):
        d.text((x + 8, 4), f"{text}   {pose}", fill=colour, font=f)
    sheet.paste(a, (0, BAND))
    sheet.paste(b, (w + GAP, BAND))
    name = f"pair_{pose}.png" if label == "after" else f"pair_{label}_{pose}.png"
    sheet.save(OUT / name)
    return OUT / name


def main():
    args = sys.argv[1:]
    label = "after"
    if "--label" in args:
        i = args.index("--label")
        label = args[i + 1]
        del args[i:i + 2]
    poses = args or sorted(p.name[len("before_"):-4] for p in OUT.glob("before_*.png"))
    for pose in poses:
        out = pair(pose, label)
        print(("wrote " + str(out)) if out else f"skipped {pose}: needs before_{pose}.png and {label}_{pose}.png")


if __name__ == "__main__":
    main()
