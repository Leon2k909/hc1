"""Remove markings from a material's maps by cloning clean surface over them, as the specs in specs/*.json say.

A spec is a list of entries:
  {"vmat": "weapons/kastov/materials/x.vmat",
   "regions": [{"rect": [x, y, w, h], "mode": "fill" | "glyphs", "offset": [dx, dy], "k": 11, "pad": 3,
                "ring": [cx, cy, r0, r1, a0, a1], "note": "serial"}],
   "clear_translucency": false}

Coordinates are colour-map pixels. For each region, the pixels to replace (the mask) are the rect grown by `pad`
("fill", the default) or the rect's marks only ("glyphs": pixels that differ from their neighbourhood, grown by 2 px).
"ring" keeps only the mask's pixels between radii r0 and r1 of (cx, cy), and, if a0 and a1 are given, from angle a0
round to a1 (degrees from +x towards +y, which is down): lettering round a ring is covered a sector at a time, since a
rect can't follow a band between two grooves, or round a primer, without taking in their edges.
They're replaced by the same shape copied from `offset` away (source = target + offset), plus a smooth correction that
makes the patch meet its surroundings exactly (the difference between target and source around the mask, interpolated
across it). Without an offset, the one whose surroundings best match the target's is picked among nearby candidates.
Every map in the vmat gets the same edit, scaled to its size. "clear_translucency" makes a decal material's
translucency map fully transparent. The result depends only on the rip's pixels and the spec, so cleaning a fresh
rip again gives the same textures.

cleaned.json records each cleaned map's pixel hash before ("rip") and after ("clean"), so check() can tell a
cleaned map from one the rip's converter has written again.

The converters that write the rips' textures (kastov_materials.py, ks74u_assets.build_material,
Sources/MW2022/convert_materials.py) call after_rip(), so re-running them doesn't bring the markings back.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage
from scipy.sparse import lil_matrix
from scipy.sparse.linalg import spsolve

import texlib as T


def key(vmat: str | Path) -> str:
    """How specs and cleaned.json name a file: its path under Assets, lower case, with forward slashes."""
    path = Path(vmat)
    if path.is_absolute():
        path = path.relative_to(T.ASSETS)
    return path.as_posix().lower()


def entries() -> dict[str, dict]:
    """Every spec entry, by key(vmat), in spec file then list order."""
    found: dict[str, dict] = {}
    for spec in sorted(T.SPECS.glob("*.json")):
        for entry in T.read_json(spec):
            k = key(entry["vmat"])
            if k in found:
                raise ValueError(f"{entry['vmat']} is in {spec.name} and {found[k]['spec']}")
            found[k] = {**entry, "spec": spec.name}
    return found


def read_manifest() -> dict[str, dict]:
    return T.read_json(T.MANIFEST) if T.MANIFEST.is_file() else {}


def write_manifest(manifest: dict[str, dict]) -> None:
    T.MANIFEST.write_text(json.dumps(dict(sorted(manifest.items())), indent=1) + "\n", encoding="utf-8",
                          newline="\n")


def map_states(vmat: str, manifest: dict[str, dict] | None = None) -> dict[str, str]:
    """Each map's state: "clean" (as cleaned), "rip" (as the rip had it, markings and all), "changed" (neither:
    edited since, or the converter changed) or "unrecorded" (never cleaned)."""
    manifest = read_manifest() if manifest is None else manifest
    states = {}
    for path in T.vmat_maps(vmat).values():
        record = manifest.get(key(path))
        h = T.pixel_hash(path)
        states[key(path)] = ("unrecorded" if record is None else "clean" if h == record.get("clean")
                             else "rip" if h == record.get("rip") else "changed")
    return states


def luminance(img: np.ndarray) -> np.ndarray:
    if img.shape[2] >= 3:
        return img[:, :, 0] * 0.299 + img[:, :, 1] * 0.587 + img[:, :, 2] * 0.114
    return img[:, :, 0]


def harmonic_fill(values: np.ndarray, mask: np.ndarray) -> np.ndarray:
    """Fill values[mask] by solving Laplace's equation with the surrounding pixels as boundary (per channel)."""
    h, w = mask.shape
    idx = -np.ones((h, w), dtype=np.int64)
    ys, xs = np.nonzero(mask)
    n = len(ys)
    if n == 0:
        return values
    idx[ys, xs] = np.arange(n)
    a = lil_matrix((n, n))
    out = values.copy()
    chans = values.shape[2]
    b = np.zeros((n, chans))
    for i, (y, x) in enumerate(zip(ys, xs)):
        count = 0
        for ny, nx in ((y - 1, x), (y + 1, x), (y, x - 1), (y, x + 1)):
            if not (0 <= ny < h and 0 <= nx < w):
                continue
            count += 1
            j = idx[ny, nx]
            if j >= 0:
                a[i, j] = -1
            else:
                b[i] += values[ny, nx]
        a[i, i] = count
    sol = spsolve(a.tocsr(), b)
    if sol.ndim == 1:
        sol = sol[:, None]
    out[ys, xs] = sol
    return out


def smooth_fill(values: np.ndarray, mask: np.ndarray) -> np.ndarray:
    """Harmonic fill, solved at a coarser scale first for big masks (the correction is smooth anyway)."""
    if mask.sum() <= 6000:
        return harmonic_fill(values, mask)
    f = int(np.ceil(np.sqrt(mask.sum() / 6000)))
    h, w = mask.shape
    hh, ww = (h + f - 1) // f, (w + f - 1) // f
    pad_v = np.zeros((hh * f, ww * f, values.shape[2]), dtype=np.float64)
    pad_m = np.zeros((hh * f, ww * f), dtype=bool)
    pad_v[:h, :w] = values
    pad_m[:h, :w] = mask
    known = (~pad_m).reshape(hh, f, ww, f)
    vals = pad_v.reshape(hh, f, ww, f, -1)
    cnt = known.sum(axis=(1, 3))
    small = (vals * known[..., None]).sum(axis=(1, 3)) / np.maximum(cnt, 1)[..., None]
    small_mask = cnt < (f * f) / 2
    # Cells outside the image padding count as unknown only if they have no known pixel.
    small_mask |= cnt == 0
    filled = harmonic_fill(small, small_mask)
    up = np.repeat(np.repeat(filled, f, axis=0), f, axis=1)[:h, :w]
    up = ndimage.uniform_filter(up, size=(f, f, 1), mode="nearest")
    out = values.copy()
    out[mask] = up[mask]
    return out


class Material:
    def __init__(self, vmat: str):
        self.vmat = vmat
        self.maps = T.vmat_maps(vmat)
        self.images = {k: T.load(p) for k, p in self.maps.items()}
        self.color = self.images["TextureColor"][0]
        self.h, self.w = self.color.shape[:2]
        normal = self.images.get("TextureNormal", (None,))[0]
        self.normal = T.resize_to(normal, (self.h, self.w)) if normal is not None else None
        lum = luminance(self.color)
        dev = np.abs(lum - ndimage.median_filter(lum, size=9))
        if self.normal is not None:
            for c in (0, 1):
                ch = self.normal[:, :, c]
                dev += 0.6 * np.abs(ch - ndimage.median_filter(ch, size=9))
        self.dev = dev
        self.lum = lum
        self.forbidden = np.zeros((self.h, self.w), dtype=bool)

    def features(self) -> np.ndarray:
        f = [self.lum]
        if self.normal is not None:
            f += [self.normal[:, :, 0] * 0.6, self.normal[:, :, 1] * 0.6]
        return np.stack(f, axis=2)


def region_mask(mat: Material, x: int, y: int, w: int, h: int, mode: str, k: int) -> np.ndarray:
    mask = np.zeros((mat.h, mat.w), dtype=bool)
    if mode == "fill":
        mask[y:y + h, x:x + w] = True
        return mask
    m = 8
    y0, y1, x0, x1 = max(0, y - m), min(mat.h, y + h + m), max(0, x - m), min(mat.w, x + w + m)
    feats = mat.features()[y0:y1, x0:x1]
    dev = np.zeros(feats.shape[:2])
    for c in range(feats.shape[2]):
        dev += np.abs(feats[:, :, c] - ndimage.median_filter(feats[:, :, c], size=k))
    inner = dev[y - y0:y - y0 + h, x - x0:x - x0 + w]
    t = max(6.0, float(inner.mean() + 1.2 * inner.std()))
    sel = np.zeros_like(dev, dtype=bool)
    sel[y - y0:y - y0 + h, x - x0:x - x0 + w] = inner > t
    sel = ndimage.binary_closing(sel, iterations=1)
    sel = ndimage.binary_dilation(sel, iterations=2)
    sel &= np.pad(np.ones((h, w), bool), ((y - y0, y1 - y - h), (x - x0, x1 - x - w)))
    mask[y0:y1, x0:x1] = sel
    return mask


def ring_mask(mat: Material, ring) -> np.ndarray:
    """The pixels between radii r0 and r1 of (cx, cy), and from angle a0 round to a1 if they're given (degrees from
    +x towards +y, which is down): ring = [cx, cy, r0, r1] or [cx, cy, r0, r1, a0, a1]."""
    cx, cy, r0, r1 = ring[:4]
    yy, xx = np.mgrid[0:mat.h, 0:mat.w]
    r = np.hypot(xx - cx, yy - cy)
    mask = (r >= r0) & (r <= r1)
    if len(ring) > 4:
        a0, a1 = ring[4:6]
        turned = (np.degrees(np.arctan2(yy - cy, xx - cx)) - a0) % 360
        mask &= turned <= a1 - a0
    return mask


def choose_offset(mat: Material, mask: np.ndarray, rect, pending: np.ndarray) -> tuple[int, int, float]:
    x, y, w, h = rect
    m = max(6, min(w, h) // 3)
    wy0, wy1, wx0, wx1 = max(0, y - m), min(mat.h, y + h + m), max(0, x - m), min(mat.w, x + w + m)
    win_mask = mask[wy0:wy1, wx0:wx1]
    ring = ndimage.binary_dilation(win_mask, iterations=m) & ~win_mask & ~pending[wy0:wy1, wx0:wx1]
    feats = mat.features()
    target = feats[wy0:wy1, wx0:wx1]
    target_ring = target[ring]
    target_mean = target_ring[:, 0].mean()
    # Candidates: a grid of offsets within a radius, far enough that the source doesn't overlap the target.
    radius = int(min(600, max(160, 3 * max(w, h))))
    step = max(4, min(w, h) // 3)
    cands = [(dx, dy) for dy in range(-radius, radius + 1, step) for dx in range(-radius, radius + 1, step)
             if abs(dx) >= w + 2 or abs(dy) >= h + 2]
    best = None
    for dx, dy in cands:
        sy0, sy1, sx0, sx1 = wy0 + dy, wy1 + dy, wx0 + dx, wx1 + dx
        if sy0 < 0 or sx0 < 0 or sy1 > mat.h or sx1 > mat.w:
            continue
        if (mat.forbidden[sy0:sy1, sx0:sx1] & (win_mask | ring)).any():
            continue
        source = feats[sy0:sy1, sx0:sx1]
        ring_diff = np.abs(target_ring - source[ring]).mean()
        src = mat.dev[sy0:sy1, sx0:sx1][win_mask]
        # No detail of its own in the patch: its average and its strongest local contrast both count.
        src_dev = src.mean() + 0.35 * np.percentile(src, 98)
        # Prefer matching brightness overall, not just texture, and nearby sources.
        mean_diff = abs(target_mean - source[win_mask][:, 0].mean())
        score = ring_diff + 0.8 * src_dev + 0.5 * mean_diff + 0.004 * np.hypot(dx, dy)
        if best is None or score < best[2]:
            best = (dx, dy, score)
    if best is None:
        raise RuntimeError(f"no clone source for rect {rect}")
    return best


def scaled_mask(mask: np.ndarray, mw: int, mh: int) -> np.ndarray:
    if mask.shape == (mh, mw):
        return mask
    return np.asarray(Image.fromarray(mask.astype(np.uint8) * 255).resize((mw, mh), Image.BILINEAR)) > 0


def apply_region(mat: Material, mask: np.ndarray, rect, offset, pending: np.ndarray) -> None:
    """Clone + correct every map of the material in the rect's window. Pixels still to be cleaned (pending) don't
    count as the patch's surroundings."""
    x, y, w, h = rect
    dx, dy = offset
    for map_key, (img, mode) in mat.images.items():
        mh, mw = img.shape[:2]
        sx, sy = mw / mat.w, mh / mat.h
        # The masks at this map's size.
        mmask = scaled_mask(mask, mw, mh)
        mpend = scaled_mask(pending, mw, mh) & ~mmask
        m = max(3, int(round(max(6, min(w, h) // 3) * min(sx, sy))))
        ys, xs = np.nonzero(mmask)
        if len(ys) == 0:
            continue
        y0, y1 = max(0, ys.min() - m), min(mh, ys.max() + 1 + m)
        x0, x1 = max(0, xs.min() - m), min(mw, xs.max() + 1 + m)
        ddx, ddy = int(round(dx * sx)), int(round(dy * sy))
        if y0 + ddy < 0 or x0 + ddx < 0 or y1 + ddy > mh or x1 + ddx > mw:
            raise RuntimeError(f"{map_key}: clone source out of range")
        win = mmask[y0:y1, x0:x1]
        target = img[y0:y1, x0:x1].astype(np.float64)
        source = img[y0 + ddy:y1 + ddy, x0 + ddx:x1 + ddx].astype(np.float64)
        diff = target - source
        corr = smooth_fill(diff, win | mpend[y0:y1, x0:x1])
        out = target.copy()
        out[win] = source[win] + corr[win]
        img[y0:y1, x0:x1] = out.astype(np.float32)


def preview(mat: Material, before_color, before_normal, rect, path: Path) -> None:
    x, y, w, h = rect
    m = max(16, min(w, h))
    y0, y1, x0, x1 = max(0, y - m), min(mat.h, y + h + m), max(0, x - m), min(mat.w, x + w + m)
    after_color = mat.images["TextureColor"][0]
    after_normal = mat.images["TextureNormal"][0] if "TextureNormal" in mat.images else None
    b = T.lit_preview(before_color, before_normal)[y0:y1, x0:x1]
    a = T.lit_preview(after_color, T.resize_to(after_normal, (mat.h, mat.w)) if after_normal is not None else None)[y0:y1, x0:x1]
    gap = np.full((6, b.shape[1], 3), 255, dtype=np.float32)
    both = np.concatenate([b, gap, a], axis=0)
    scale = max(1, min(5, 1000 // both.shape[1], 1000 // both.shape[0]))
    im = Image.fromarray(np.clip(both, 0, 255).astype(np.uint8)).resize(
        (both.shape[1] * scale, both.shape[0] * scale), Image.NEAREST)
    im.save(path)


def process(entry: dict, dry: bool, previews: bool = True, verbose: bool = True) -> None:
    """Clean one material as its spec entry says. With previews, each region writes out/<stem>/fix_<n>_<x>_<y>.png
    (before above after, shaded). Unless dry, every map is written and cleaned.json updated."""
    vmat = entry["vmat"]
    mat = Material(vmat)
    before_hash = {k: T.pixel_hash(p) for k, p in mat.maps.items()} if not dry else {}
    out = T.OUT / Path(vmat).stem
    if previews:
        out.mkdir(parents=True, exist_ok=True)
    if entry.get("clear_translucency"):
        if "TextureTranslucency" not in mat.images:
            print(f"{vmat}: no translucency map")
        else:
            img, mode = mat.images["TextureTranslucency"]
            img[:] = 0
            if verbose:
                print(f"{vmat}: translucency cleared")
    regions = entry.get("regions", [])
    before_color = mat.color.copy()
    before_normal = mat.normal.copy() if mat.normal is not None else None
    rects, masks = [], []
    for r in regions:
        x, y, w, h = r["rect"]
        pad = r.get("pad", 3)
        x0, y0 = max(0, x - pad), max(0, y - pad)
        x1, y1 = min(mat.w, x + w + pad), min(mat.h, y + h + pad)
        rect = (x0, y0, x1 - x0, y1 - y0)
        rects.append(rect)
        mask = region_mask(mat, *rect, r.get("mode", "fill"), r.get("k", 11))
        if "ring" in r:
            mask &= ring_mask(mat, r["ring"])
        masks.append(mask)
    pending = np.zeros((mat.h, mat.w), dtype=bool)
    for mask in masks:
        pending |= mask
    for i, r in enumerate(regions):
        rect, mask = rects[i], masks[i]
        # Sources can't take in anything still to be cleaned, this region included.
        mat.forbidden = ndimage.binary_dilation(pending, iterations=2)
        pending &= ~mask
        if "offset" in r:
            dx, dy = r["offset"]
            score = float("nan")
        else:
            dx, dy, score = choose_offset(mat, mask, rect, pending)
        apply_region(mat, mask, rect, (dx, dy), pending)
        mat.color = mat.images["TextureColor"][0]
        mat.lum = luminance(mat.color)
        if mat.normal is not None:
            mat.normal = T.resize_to(mat.images["TextureNormal"][0], (mat.h, mat.w))
        name = ""
        if previews:
            path = out / f"fix_{i}_{rect[0]}_{rect[1]}.png"
            preview(mat, before_color, before_normal, rect, path)
            name = f" -> {path.name}"
        if verbose:
            print(f"{vmat} region {i} {rect} {r.get('mode', 'fill')} offset=({dx},{dy}) score={score:.1f} "
                  f"pixels={int(mask.sum())}{name}  {r.get('note', '')}")
    if dry:
        return
    for map_key, (img, mode) in mat.images.items():
        T.save(mat.maps[map_key], img, mode)
    manifest = read_manifest()
    for map_key, path in mat.maps.items():
        record = manifest.setdefault(key(path), {})
        # A map two materials share is cleaned by each in turn: only the first one sees the rip.
        if before_hash[map_key] != record.get("clean"):
            record["rip"] = before_hash[map_key]
        record["clean"] = T.pixel_hash(path)
    write_manifest(manifest)
    print(f"{vmat}: markings removed ({len(regions)} regions{', translucency cleared' if entry.get('clear_translucency') else ''})")


def after_rip(vmat: str | Path) -> bool:
    """For the converters: clean a material whose maps they've just written from the rip. False if it has no spec."""
    entry = entries().get(key(vmat))
    if entry is None:
        return False
    process(entry, dry=False, previews=False, verbose=False)
    return True


def after_rip_under(folder: str) -> int:
    """after_rip() for every material with a spec under an Assets folder (e.g. "attachments/mw2022/")."""
    folder = key(folder).rstrip("/") + "/"
    cleaned = 0
    for k, entry in entries().items():
        if k.startswith(folder):
            process(entry, dry=False, previews=False, verbose=False)
            cleaned += 1
    return cleaned
