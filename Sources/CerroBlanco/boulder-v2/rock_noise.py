"""Gradient noise over points, in plain numpy, for the boulder's shape and its paint.

Gradient noise, because thresholded value noise comes out in blocks that read as pixels. Each octave is turned, so nothing lines up with the axes.
"""
import numpy as np


def _rotation(seed):
    rng = np.random.default_rng(seed)
    q, _ = np.linalg.qr(rng.normal(size=(3, 3)))
    return q.astype(np.float32)


class _Lattice:
    tables = {}

    @classmethod
    def get(cls, seed):
        if seed not in cls.tables:
            rng = np.random.default_rng(seed)
            perm = rng.permutation(256)
            grads = rng.normal(size=(256, 3))
            grads /= np.linalg.norm(grads, axis=1, keepdims=True)
            cls.tables[seed] = (np.concatenate((perm, perm, perm)).astype(np.int32), grads.astype(np.float32))
        return cls.tables[seed]


def perlin(p, seed):
    """Noise at points p (N, 3), about -1..1. Worked through in chunks, since an atlas has millions of points."""
    out = np.empty(p.shape[0], np.float32)
    perm, grads = _Lattice.get(seed)
    for start in range(0, p.shape[0], 1 << 20):
        q = p[start : start + (1 << 20)]
        cell = np.floor(q)
        f = (q - cell).astype(np.float32)
        i = cell.astype(np.int64) & 255
        u = f * f * f * (f * (f * 6 - 15) + 10)
        total = np.zeros((q.shape[0],), np.float32)
        for dx in (0, 1):
            wx = u[:, 0] if dx else 1 - u[:, 0]
            for dy in (0, 1):
                wy = u[:, 1] if dy else 1 - u[:, 1]
                for dz in (0, 1):
                    wz = u[:, 2] if dz else 1 - u[:, 2]
                    index = perm[perm[perm[i[:, 0] + dx] + i[:, 1] + dy] + i[:, 2] + dz]
                    g = grads[index]
                    dot = g[:, 0] * (f[:, 0] - dx) + g[:, 1] * (f[:, 1] - dy) + g[:, 2] * (f[:, 2] - dz)
                    total += wx * wy * wz * dot
        out[start : start + (1 << 20)] = total * 1.6
    return out


def fbm(p, freq, seed, octaves=3, gain=0.5, lacunarity=2.03):
    """Summed noise, about -1..1."""
    total = np.zeros(p.shape[0], np.float32)
    amp, norm = 1.0, 0.0
    f = freq
    for k in range(octaves):
        total += amp * perlin((p.astype(np.float32) @ _rotation(seed * 7 + k)) * f + 17.3 * (k + 1), seed + k)
        norm += amp
        amp *= gain
        f *= lacunarity
    return total / norm


def smooth(a, b, x):
    t = np.clip((x - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)
