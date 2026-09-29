"""HC1's M4 look sway and hand IK, for the Kastov pipeline's guns (port_kastov.py, kastov_vmdl.py, kastov_animgraph.py).

Every frame ViewModel sets aim_yaw_inertia to twice how far the view turned sideways since the last frame (plus 20 at a
full strafe) and aim_pitch_inertia to twice how far it turned up or down. v_m4a1's animgraph blends single-frame deltas
of its weapon_root (Shared_WeaponOffset_Generic_*) by them through springs, so the gun turns, rolls and shifts against
a turn and swings back after it; it halves that at the hip and keeps a fifth of the half in ADS. Its hands stay on the
gun by IK: each arm is solved onto a bone that rides on the gun. The CoD clips have none of it (CoD sways the whole
viewmodel in code), so the ported guns held dead still while the view turned.

  port_kastov.py       IK_TARGETS: a bone under tag_sling per hand, holding that hand's pose on the gun in every
                       frame. Kastov.m4_sway writes anims/sway.dmx: frame 0 is idle's first frame, then one frame per
                       poses() entry, the gun (with the IK targets) moved by that share of the M4 pose, as
                       Kastov.m4_sprint moves it, and the arms left where they are.
  kastov_vmdl.py       IK_CHAINS as ModelDoc IK chains, and sway.dmx cut into one additive sequence per frame (minus
                       idle's first frame; frame 0 gives REST, the zero the blends start from).
  kastov_animgraph.py  blends the poses with the M4's blend values and springs, cuts them to ADS by ironsights_weight,
                       then solves both arms onto their IK targets.

Every per-bone additive layer moves the gun's root bones and the arms' in their own parent spaces, so a sway worked
out on idle only moves the hands with the gun near idle: turning while reloading or drawing took the left hand an inch
or two off the magazine. The IK puts them back in every state, as it does on the M4.
"""

from __future__ import annotations

M4_PREFIX = "Shared_WeaponOffset_Generic_"

# The M4 graph's "Halve it": the poses are halved here, so the graph needs no bone mask (the ported rigs have no weight
# lists).
HIP = 0.5
# Its "20% if in ironsights": the share of the hip sway kept in ADS.
ADS = 0.2

# The M4's blends: (pose, blend value) and the spring on the blend's input (m_fSpeedScale, m_fTension, m_fDamping).
# Positive aim_yaw_inertia turns the gun left, positive aim_pitch_inertia up.
ORIENTATION = [  # 2D, on (aim_yaw_inertia, aim_pitch_inertia)
    ("Orientation_Left", (120.0, 0.0)), ("Orientation_Right", (-120.0, 0.0)),
    ("Orientation_Up", (0.0, 120.0)), ("Orientation_Down", (0.0, -120.0)),
    ("Orientation_UpLeft", (120.0, 120.0)), ("Orientation_UpRight", (-120.0, 120.0)),
    ("Orientation_DownLeft", (120.0, -120.0)), ("Orientation_DownRight", (-120.0, -120.0)),
]
ORIENTATION_SPRING = (50.0, 400.0, 20.0)
ROLL = [("Orientation_Roll_Left", 120.0), ("Orientation_Roll_Right", -120.0)]  # on aim_yaw_inertia
ROLL_SPRING = (35.0, 200.0, 10.0)
VERTICAL = [("Position_Up", 90.0), ("Position_Down", -90.0)]  # on aim_pitch_inertia
VERTICAL_SPRING = (100.0, 110.0, 11.0)
HORIZONTAL = [("Position_Left", 90.0), ("Position_Right", -90.0)]  # on aim_yaw_inertia
HORIZONTAL_SPRING = (100.0, 90.0, 9.0)

# The sequence with no sway (sway.dmx's frame 0 minus idle's first frame), like the M4's bindPose_delta. zero_delta
# won't do: it's idle's whole loop minus its first frame, so each blend would add idle's motion again.
REST = "sway_rest"

# IK target bone (a child of tag_sling) -> the hand it holds, and the arms' IK chains (the M4's: upper arm, forearm,
# hand), each solved onto its target.
IK_TARGETS = {"ik_hand_L": "hand_L", "ik_hand_R": "hand_R"}
IK_CHAINS = [("left_arm_IK", ("arm_upper_L", "arm_lower_L", "hand_L"), "ik_hand_L"),
             ("right_arm_IK", ("arm_upper_R", "arm_lower_R", "hand_R"), "ik_hand_R")]


def sequence(pose: str) -> str:
    """The viewmodel sequence of an M4 pose: sway_orientation_left, sway_position_up, ..."""
    return f"sway_{pose.lower()}"


def poses() -> list[tuple[str, str, float]]:
    """(sequence, M4 sequence, share of the M4 pose) of every sway pose, in sway.dmx's frame order from frame 1."""
    return [(sequence(pose), M4_PREFIX + pose, HIP) for pose, _ in ORIENTATION + ROLL + VERTICAL + HORIZONTAL]
