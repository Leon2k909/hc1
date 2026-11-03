"""Where Cerro Blanco's cafe cups are, as cerroblanco_fitout puts them: two on each cafe table, 6 in from its middle at 70 and 230 degrees, their saucers on the top at 29.5. Plan ( e, n ) of each, and
the plan angle it sits at round its table, which turns its handle. Shared by the comparison and the install."""
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "cafe-chair-v2"))
from chairs import COURTYARD, INSIDE  # noqa: E402

TOP = 29.5


def cups():
    out = []
    for e, n in list(INSIDE) + list(COURTYARD):
        for k in range(2):
            a = 70 + 160 * k
            out.append((e + 6 * math.cos(math.radians(a)), n + 6 * math.sin(math.radians(a)), a))
    return out
