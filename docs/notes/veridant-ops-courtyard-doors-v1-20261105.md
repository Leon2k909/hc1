# Veridant operations courtyard doors — 2026-11-05

Installed matching glazed double doors in the missing ground-floor operations
courtyard entrance (80 x 100), plan e=280..360,n=-336..-320. Reuses reception
leaf at scale (1,39.15/29.15,1). Saved root objects Operations courtyard glazed
door left/right have hinges (-328,-280.65,0)/(-328,-359.35,0), yaw0/180.
Each uses moving BoxCollider and Facepunch.Door,90 degrees,.55 seconds.

Both saved leaves reached Open then Closed in play. Traces across x=-350..-300,
y=-300/-340,z=45 cleared both open leaves and hit their respective closed leaf.
Bot traversal/multiplayer were not tested. Regeneration retains this pair through
ops_courtyard_scene_objects in Tools/veridant_reception_doors.py.

Matched actual viewport captures and immediate scene backup are in
output/veridant/ops-courtyard-doors-v1/. Camera (-190,-320,60), angles(4.97,180,0),
FOV80,1000x800. Restored prior viewport and Riverside active tab; play stopped.
