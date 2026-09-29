"""Shared helpers for finding and removing markings (text, numbers, logos, QR codes) from ripped weapon textures.

A material's maps (colour, normal, roughness, metalness, AO, translucency, ...) come from its .vmat, and every edit is
made to all of them at once, scaled to each map's size, so the maps stay in step. Originals are backed up once under
BACKUP before the first write. BACKUP and OUT live outside the repo (HC1_TEXTURE_WORK, else the temp folder).
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
ASSETS = HERE.parents[1] / "Assets"
SPECS = HERE / "specs"
MANIFEST = HERE / "cleaned.json"
WORK = Path(os.environ.get("HC1_TEXTURE_WORK") or Path(tempfile.gettempdir()) / "hc1_texture_markings")
BACKUP = WORK / "backup"
OUT = WORK / "out"


def font(size: int = 14):
    try:
        return ImageFont.truetype("arial.ttf", size)
    except OSError:
        return ImageFont.load_default()


def vmat_maps(vmat: str | Path) -> dict[str, Path]:
    """The image files a .vmat uses, by key (only files inside Assets)."""
    path = Path(vmat)
    if not path.is_absolute():
        path = ASSETS / path
    text = path.read_text(encoding="utf-8", errors="replace")
    maps = {}
    for key, value in re.findall(r'"?(Texture\w+)"?\s+"([^"]+)"', text):
        if value.startswith("["):
            continue
        file = ASSETS / value
        if file.is_file():
            maps[key] = file
    return maps


def load(path: Path) -> tuple[np.ndarray, str]:
    with Image.open(path) as im:
        mode = im.mode
        if mode not in ("RGB", "RGBA", "L", "LA", "I;16", "I"):
            im = im.convert("RGBA" if "A" in mode else "RGB")
            mode = im.mode
        arr = np.asarray(im).astype(np.float32)
    if arr.ndim == 2:
        arr = arr[:, :, None]
    return arr, mode


def save(path: Path, arr: np.ndarray, mode: str) -> None:
    backup(path)
    if mode in ("I;16", "I"):
        out = np.clip(np.rint(arr[:, :, 0]), 0, 65535).astype(np.uint16)
        Image.fromarray(out, mode="I;16").save(path)
        return
    out = np.clip(np.rint(arr), 0, 255).astype(np.uint8)
    if out.shape[2] == 1:
        out = out[:, :, 0]
    Image.fromarray(out, mode=mode).save(path)


def pixel_hash(path: Path) -> str:
    """A hash of the decoded pixels (not the file bytes, which change with the PNG encoder's settings)."""
    with Image.open(path) as im:
        arr = np.asarray(im)
        head = f"{im.mode} {arr.shape}".encode()
    return hashlib.sha1(head + arr.tobytes()).hexdigest()


def backup(path: Path) -> None:
    rel = path.relative_to(ASSETS)
    dest = BACKUP / rel
    if not dest.exists():
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, dest)


def restore(path: Path) -> bool:
    rel = path.relative_to(ASSETS)
    src = BACKUP / rel
    if src.exists():
        shutil.copy2(src, path)
        return True
    return False


def lit_preview(color: np.ndarray, normal: np.ndarray | None) -> np.ndarray:
    """The colour map shaded by its normal map (light from the top left), so engraving shows as well as print."""
    rgb = color[:, :, :3] if color.shape[2] >= 3 else np.repeat(color[:, :, :1], 3, axis=2)
    if normal is None:
        return rgb
    n = normal[:, :, :3]
    if n.shape[:2] != rgb.shape[:2]:
        n = np.asarray(Image.fromarray(np.clip(n, 0, 255).astype(np.uint8)).resize(
            (rgb.shape[1], rgb.shape[0]), Image.BILINEAR)).astype(np.float32)
    nx, ny = n[:, :, 0] / 127.5 - 1, n[:, :, 1] / 127.5 - 1
    nz = np.sqrt(np.clip(1 - nx * nx - ny * ny, 0, 1))
    light = np.array([-0.55, 0.55, 0.63])
    light /= np.linalg.norm(light)
    shade = np.clip(nx * light[0] + ny * light[1] + nz * light[2], 0, 1)
    # Stretch the shading so small engravings stand out, and keep the albedo visible.
    return np.clip((rgb * 0.6 + 60) * (0.35 + 1.1 * shade[:, :, None]), 0, 255)


def grid_image(img: np.ndarray, x0: int, y0: int, step: int = 64, label_every: int = 256,
               scale: float = 1.0) -> Image.Image:
    """Draw a grid in texture pixel coordinates over a crop that starts at texture (x0, y0) and is shown at `scale`
    image pixels per texture pixel."""
    im = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8)).convert("RGB")
    draw = ImageDraw.Draw(im, "RGBA")
    f = font(13)
    h, w = img.shape[:2]
    tw, th = w / scale, h / scale
    for gx in range((x0 // step + 1) * step, int(x0 + tw), step):
        major = gx % label_every == 0
        px = (gx - x0) * scale
        draw.line([(px, 0), (px, h)], fill=(0, 255, 255, 110 if major else 45), width=1)
        if major:
            draw.text((px + 2, 2), str(gx), fill=(0, 255, 255, 255), font=f)
    for gy in range((y0 // step + 1) * step, int(y0 + th), step):
        major = gy % label_every == 0
        py = (gy - y0) * scale
        draw.line([(0, py), (w, py)], fill=(255, 0, 255, 110 if major else 45), width=1)
        if major:
            draw.text((2, py + 2), str(gy), fill=(255, 0, 255, 255), font=f)
    return im


def resize_to(arr: np.ndarray, shape: tuple[int, int]) -> np.ndarray:
    if arr.shape[:2] == shape:
        return arr
    chans = [np.asarray(Image.fromarray(arr[:, :, c]).resize((shape[1], shape[0]), Image.BILINEAR))
             for c in range(arr.shape[2])]
    return np.stack(chans, axis=2).astype(np.float32)


def rel(path: Path) -> str:
    return path.relative_to(ASSETS).as_posix()


def read_json(path: Path):
    return json.loads(Path(path).read_text(encoding="utf-8"))
