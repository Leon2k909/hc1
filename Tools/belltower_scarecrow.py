"""Cloth, sacking and a worn field hat over Belltower's original scarecrow frame.

Visual geometry only. The map generator keeps the existing collision separately.
All materials reuse existing project texture pixels.
"""
import math
import numpy as np
import belltower_furniture as F

RESOURCE = 'materials/belltower/scarecrow-v1'
SACK, SHIRT, HAT, TWINE, STITCH, PATCH = (
    'scarecrow_sack', 'scarecrow_shirt', 'scarecrow_hat',
    'scarecrow_twine', 'scarecrow_stitch', 'scarecrow_patch')
MATERIALS = {
    SACK: 'materials/stillhouse/sh_sack.vmat',
    SHIRT: 'materials/stillhouse/sh_canvas.vmat',
    HAT: f'{RESOURCE}/hat.vmat',
    TWINE: 'materials/stillhouse/sh_rope.vmat',
    STITCH: f'{RESOURCE}/stitch.vmat',
    PATCH: f'{RESOURCE}/patch.vmat',
}


def unit(v):
    v = np.asarray(v, float)
    return v / max(np.linalg.norm(v), 1e-12)


def build(model,p):
    from belltower_scarecrow_v2 import build as detailed_build
    return detailed_build(model,p)
