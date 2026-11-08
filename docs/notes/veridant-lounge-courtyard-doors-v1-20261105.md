# Veridant lounge courtyard doors — 2026-11-05

Installed matching glazed double doors in the empty 100 x 96 courtyard opening,
plan e=-216..-200,n=-300..-200. Reuses reception_doors_v1/leaf.vmdl at scale
(1,49.15/29.15,.96), with hinges at world (-299.35,208,0)/(-200.65,208,0),
yaw +90/-90. Native saved roots: Lounge courtyard glazed door left/right.
Each has moving BoxCollider and Facepunch.Door (.55 seconds,90 degrees).

Both saved leaves reached Open and Closed in play. Traces at x=-275/-225,
y=185..230,z=45 cleared the open leaves and hit the corresponding closed leaf.
Bot traversal and multiplayer were not tested. Generator retention is through
lounge_courtyard_scene_objects in Tools/veridant_reception_doors.py.

Matched actual editor viewport screenshots and the pre-edit scene backup are in
output/veridant/lounge-courtyard-doors-v1/. Both captures use position
(-250,70,60), angles (4.97,90,0), FOV80,1000x800. Restored the prior Veridant
viewport transform and Riverside's active tab, with play stopped.
