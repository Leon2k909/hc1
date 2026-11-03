"""Where Cerro Blanco's cafe chairs are, as cerroblanco_map places them: plan ( e, n ) and the plan yaw each faces (cerroblanco_parts.turned's). Shared by the comparison and the install."""
import math

INSIDE = ((620, 220), (800, 160), (860, 420), (640, 440))  # The cafe's tables, three chairs each at 30, 150 and 270.
COURTYARD = ((-540, 870), (-420, 940), (-540, 990), (-300, 920))  # Under the parasols, two each at 20 and 200.


def chairs():
    out = []
    for tables, angles in ((INSIDE, (30, 150, 270)), (COURTYARD, (20, 200))):
        for e, n in tables:
            for a in angles:
                out.append((e + 24 * math.cos(math.radians(a)), n + 24 * math.sin(math.radians(a)), (a + 180) % 360))
    return out


def world_yaw(plan_yaw):
    """The model faces its +x: plan heading ( cos, sin ) is world ( sin, -cos ), so world yaw is the plan's less 90."""
    return (plan_yaw - 90.0) % 360.0
