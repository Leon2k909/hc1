# Veridant operations east doors — 2026-11-05

Installed matching glazed double doors at the empty east forecourt entrance,
80 x 100 opening at plan e=744..760,n=-640..-560. Reuses reception leaf at
scale (1,39.15/29.15,1). Saved roots Operations east glazed door left/right,
hinges (-639.35,-752,0)/(-560.65,-752,0), yaw +90/-90. Moving BoxCollider and
Facepunch.Door,90 degrees,.55 seconds per leaf.

Both saved leaves reached Open then Closed in play. Traces through x=-620/-580,
y=-775..-730,z=45 cleared the open leaves and hit the respective closed leaf.
Bot passage and multiplayer were not tested. Generator retains this pair through
ops_east_scene_objects in Tools/veridant_reception_doors.py.

Matched actual viewport captures and immediate scene backup are in
output/veridant/ops-east-doors-v1/. Camera (-600,-890,60), angles(4.97,90,0),
FOV80,1000x800. Restored prior Veridant viewport and Riverside tab; play stopped.
