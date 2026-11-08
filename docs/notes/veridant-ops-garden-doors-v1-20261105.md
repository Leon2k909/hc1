# Veridant operations south garden doors — 2026-11-05

Installed matching glazed double doors in the empty south garden entrance,
80 x 100 opening at plan e=60..140,n=-700..-684. Reuses reception leaf at
scale (1,39.15/29.15,1). Saved roots Operations garden glazed door left/right
have hinges (-692,-60.65,0)/(-692,-139.35,0), yaw0/180. Each has moving
BoxCollider and Facepunch.Door,90 degrees,.55 seconds.

Both saved leaves reached Open then Closed in play. Traces through y=-80/-120,
x=-715..-670,z=45 cleared the open leaves and hit the respective closed leaf.
Bot passage and multiplayer were not tested. Generator retains this pair through
ops_courtyard_scene_objects(ids,garden=True); courtyard/garden IDs are distinct.

Matched actual viewport captures and immediate scene backup are in
output/veridant/ops-garden-doors-v1/. Camera (-830,-100,60), angles(4.97,0,0),
FOV80,1000x800. Restored prior Veridant viewport and Riverside tab; play stopped.
