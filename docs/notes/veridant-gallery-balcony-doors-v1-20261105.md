# Veridant upper gallery balcony doors — 2026-11-05

Installed matching glazed double doors in the upper lounge's missing 60 x 96
balcony opening at plan e=-216..-200,n=-400..-340,base z=128. Reuses the approved
reception leaf with scale (1,1,.96). Saved native roots Gallery balcony glazed
door left/right have hinges (-399.35,208,128)/(-340.65,208,128), yaw +90/-90.
Each has a moving BoxCollider and Facepunch.Door (.55 seconds,90 degrees).

Both saved leaves reached Open then Closed in play. Traces through x=-385/-355,
y=185..230,z=173 cleared the open leaves and hit their respective closed leaf.
No bot traversal or multiplayer verification is claimed. The map generator now
includes gallery_balcony_scene_objects from Tools/veridant_reception_doors.py.

Matched actual editor viewport captures and immediate scene backup are in
output/veridant/gallery-balcony-doors-v1/. Camera position (-370,80,188), angles
(4.97,90,0), FOV80,1000x800. Restored prior Veridant viewport and Riverside tab;
play stopped, matching the initial state.
