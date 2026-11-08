"""How alike are two pictures? Used to check that the reverted desk looks like the BEFORE picture.

    python compare_images.py a.png b.png [diff_out.png]

Prints the size of each picture, the mean absolute difference per channel (0-255) and the share of pixels that differ by
more than 8 levels in any channel. With a third argument it writes the difference, amplified 8 times, as a picture.
"""
import sys
from pathlib import Path

import numpy as np
from PIL import Image


def main():
    a_path, b_path = Path(sys.argv[1]), Path(sys.argv[2])
    a = np.asarray(Image.open(a_path).convert("RGB"), dtype=np.int16)
    b = np.asarray(Image.open(b_path).convert("RGB"), dtype=np.int16)
    print(a_path.name, a.shape[1], "x", a.shape[0], "|", b_path.name, b.shape[1], "x", b.shape[0])
    if a.shape != b.shape:
        print("different sizes: not comparable")
        raise SystemExit(2)
    d = np.abs(a - b)
    print(f"mean abs difference {d.mean():.3f} / 255   max {d.max()}   pixels differing by more than 8: {100.0 * (d.max(axis=2) > 8).mean():.3f} %")
    if len(sys.argv) > 3:
        Image.fromarray(np.clip(d * 8, 0, 255).astype(np.uint8)).save(sys.argv[3])
        print("wrote", sys.argv[3])


if __name__ == "__main__":
    main()
