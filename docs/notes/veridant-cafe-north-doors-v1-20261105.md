# Veridant north café entrance doors — 2026-11-05

Installed the missing pair at the second café shopfront opening, centred at plan
e=-268,n=80 (64 x 96). Uses the approved reception glass-and-brass leaf, scale
(1,31.15/29.15,.96), hinges at world (48.65,268,0)/(111.35,268,0), yaw +90/-90.
Saved native root objects: Cafe north glazed door left/right. Each has a moving
BoxCollider and Facepunch.Door, .55-second operation and 90-degree swing.

Both saved leaves reached Open then Closed in play. Traces through x=65/95,
y=245..290,z=45 cleared both open leaves and hit the respective closed leaf.
Bot passage and multiplayer were not tested. The generator retains both café
pairs with cafe_scene_objects(ids,north=False/True); IDs remain distinct.

Actual editor-camera viewport captures, not a temporary scene camera, are in
output/veridant/cafe-north-doors-v1/before-viewport.png and after-viewport.png.
Both use viewport position (80,130,60), angles (4.97,90,0), FOV80, 1000x800.
Immediate scene backup is in the same folder. Restored Veridant's previous
viewport transform and Riverside's active tab, with play stopped.
