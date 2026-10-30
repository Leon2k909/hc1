"""Shape the flag: travelling folds as a flag in a steady breeze has them, relaxed so the cloth keeps its length.

python make_flag.py <work dir>
Writes flag_shape.npz: grid (rows along z, columns along the fly) in inches, x along the fly, y across the wind,
z up, hoist at x = 0, plus the hoist's own bow. Everything is seeded.
"""
import os
import sys

import numpy as np
from scipy import ndimage as ndi

WORK = sys.argv[1]
os.makedirs(WORK, exist_ok=True)

FLY, DROP = 40.0, 27.0
NX, NZ = 160, 108
rng = np.random.default_rng(1944)

u = np.linspace(0, 1, NX + 1)
v = np.linspace(0, 1, NZ + 1)
U, V = np.meshgrid(u, v)


def field(sigma_u, sigma_v, seed):
    """Smooth noise over the cloth, about -1..1."""
    r = np.random.default_rng(seed).standard_normal(U.shape)
    f = ndi.gaussian_filter(r, (sigma_v, sigma_u), mode="reflect")
    return f / max(f.std() * 2.2, 1e-9)


# Fold crests lean: the top of the flag runs ahead of the bottom, and each crest bends a little on its way down.
lean = 0.34 * (V - 0.5) + 0.06 * field(30, 18, 2)
reach = np.clip((U - 0.015) / 0.985, 0, 1)
grow = reach ** 0.82

phase = U - lean


def ridge(t, k):
    """A fold: broad troughs and a narrow crest, -1..1, as cloth buckles rather than as a sine wave."""
    return 2.0 * (np.exp(k * (np.cos(t) - 1.0)) - np.exp(-2.0 * k)) / (1.0 - np.exp(-2.0 * k)) - 1.0


waves = (
    4.5 * grow * ridge(2 * np.pi * (phase * 2.3 + 0.08), 1.5)
    + 1.9 * grow ** 1.15 * ridge(2 * np.pi * (phase * 4.6 + 0.37) + 0.7 * field(36, 26, 5), 1.2)
    + 0.72 * grow ** 1.4 * np.sin(2 * np.pi * (phase * 8.7 + 0.11) + 1.2 * field(24, 18, 6))
    + 0.95 * field(20, 12, 9) * grow
)

# A flag's fly end flutters hardest; its corners lift off the fold they sit on.
flutter = np.clip((U - 0.72) / 0.28, 0, 1) ** 2
waves += flutter * (1.5 * np.sin(2 * np.pi * (V * 1.7 + 0.2)) + 0.9 * field(12, 10, 12))

# Loose folds fan out from the two hooks where the strip's weight hangs between them.
hook_top = np.exp(-(((U - 0.0) / 0.2) ** 2 + ((V - 1.0) / 0.34) ** 2))
hook_low = np.exp(-(((U - 0.0) / 0.2) ** 2 + ((V - 0.0) / 0.34) ** 2))
radial_top = np.arctan2(V - 1.0, U + 0.02)
radial_low = np.arctan2(V, U + 0.02)
waves += 0.38 * hook_top * np.sin(radial_top * 9.0 + 0.7) + 0.32 * hook_low * np.sin(radial_low * 8.0 + 2.1)
belly = 0.65 * np.sin(np.pi * V) * np.exp(-(U / 0.16) ** 2)
waves += belly

# The whole flag sags from the hoist, more at the fly and the lower edge.
sag = 3.6 * U ** 1.45 + 0.7 * (1 - V) * U ** 2
target = np.empty(U.shape + (3,))
target[..., 0] = U * FLY * 0.93
target[..., 1] = waves
target[..., 2] = V * DROP - sag + 0.32 * grow * np.cos(2 * np.pi * (phase * 2.05 + 0.08)) * 1.2

hoist_bow = 0.55 * np.sin(np.pi * v)
target[:, 0, 0] = hoist_bow
target[:, 0, 1] = 0.0
target[:, 0, 2] = v * DROP

p = target.copy()
dx = FLY / NX
dz = DROP / NZ
dd = float(np.hypot(dx, dz))


def solve(a, b, rest, k_stretch, k_compress):
    """Project every pair (arrays of the same shape, views of p) toward its rest length."""
    d = b - a
    lengths = np.sqrt((d * d).sum(-1, keepdims=True)) + 1e-9
    error = (lengths - rest) / lengths
    k = np.where(error > 0, k_stretch, k_compress)
    move = d * error * k * 0.5
    a += move
    b -= move


def relax(iterations, pull):
    global p
    for it in range(iterations):
        for start in (0, 1):
            solve(p[:, start:-1:2], p[:, start + 1 :: 2], dx, 0.98, 0.25)
            solve(p[start:-1:2, :], p[start + 1 :: 2, :], dz, 0.98, 0.25)
        for s0 in (0, 1):
            for s1 in (0, 1):
                solve(p[s0:-1:2, s1:-1:2], p[s0 + 1 :: 2, s1 + 1 :: 2], dd, 0.42, 0.05)
                solve(p[s0:-1:2, s1 + 1 :: 2], p[s0 + 1 :: 2, s1:-1:2], dd, 0.42, 0.05)
        for start in (0, 1, 2, 3):
            solve(p[:, start:-2:4], p[:, start + 2 :: 4], 2 * dx, 0.3, 0.018)
            solve(p[start:-2:4, :], p[start + 2 :: 4, :], 2 * dz, 0.3, 0.018)
        p += (target - p) * pull
        # The two hooks hold; the strip between them follows the rope's bow.
        p[:, 0, 0] = hoist_bow
        p[:, 0, 1] = 0.0
        p[:, 0, 2] = v * DROP


relax(1400, 0.004)
relax(600, 0.0005)
p = p.astype(np.float32)

along = np.linalg.norm(p[:, 1:] - p[:, :-1], axis=-1)
across = np.linalg.norm(p[1:, :] - p[:-1, :], axis=-1)
print("stretch along %.3f..%.3f  across %.3f..%.3f" % (along.min() / dx, along.max() / dx, across.min() / dz, across.max() / dz))
print("reach %.1f  y %.1f..%.1f  z %.1f..%.1f" % (p[..., 0].max(), p[..., 1].min(), p[..., 1].max(), p[..., 2].min(), p[..., 2].max()))
np.savez_compressed(os.path.join(WORK, "flag_shape.npz"), grid=p, fly=FLY, drop=DROP)
