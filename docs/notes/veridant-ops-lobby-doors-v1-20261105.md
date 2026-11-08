# Veridant upper operations lobby doors — 2026-11-05

Installed matching approved glass-and-brass double doors in the previously empty
100 x 100 balcony entrance at plan e=460..560, n=-436..-420, base z=128.
Native root objects `Operations lobby glazed door left/right` use
models/props/veridant/reception_doors_v1/leaf.vmdl with scale (1,49.15/29.15,1),
hinges at world (-428,-460.65,128) and (-428,-559.35,128), yaw 0/180.

Both use Facepunch.Door (90 degrees, .55 seconds, opens away from user) and a
moving BoxCollider. Native play verification reached Open and Closed for both.
Traces from x=-450 to -400 at y=-485/-535, z=173 passed the open leaves and hit
the appropriate closed leaf. Bot passage and multiplayer were not checked.
The reception desk is over 100 inches behind the hinge plane, outside the
49.15-inch swing radius. The balcony rail is also outside that radius.

Native scene save completed. Tools/veridant_reception_doors.py provides
ops_lobby_scene_objects; veridant_map.py includes this pair on regeneration.
Matched before/after captures and immediate scene backup are in
output/veridant/ops-lobby-doors-v1/. Camera position (-290,-510,188), target
(-435,-510,178), FOV70, 900x700. Restored Riverside as the active scene with play
stopped, matching the initial state.
