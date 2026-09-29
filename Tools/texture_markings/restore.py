"""Put a material's maps back from the backup taken before clean.py first wrote them.

usage: python restore.py <vmat> [<vmat> ...]
"""
from __future__ import annotations

import sys

import texlib as T

for vmat in sys.argv[1:]:
    for key, path in T.vmat_maps(vmat).items():
        print(f"{T.rel(path)}: {'restored' if T.restore(path) else 'no backup (unchanged)'}")
