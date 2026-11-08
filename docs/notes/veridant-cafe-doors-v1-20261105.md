# Veridant café south entrance doors — 2026-11-05

Installed a second pair of the approved reception glass-and-brass door leaves in
the café's south shopfront entrance. This is the 64 x 96 opening centred at plan
e=-268, n=-100. Native scene root objects are `Cafe south glazed door left/right`,
world (-131.35,268,0) and (-68.65,268,0), yaw +90/-90. Reuses
models/props/veridant/reception_doors_v1/leaf.vmdl, scaled (1,31.15/29.15,.96).

Each leaf has a moving BoxCollider and Facepunch.Door, with .55-second opening and
90-degree swing away from the user. Native save verified the new objects persisted.
Play validation reached Open and Closed for both leaves. Two traces through the
entrance at x=-115/-85, z=45 cleared the open door and hit the corresponding
closed leaf. No bot traversal or multiplayer check is claimed.

The generator includes cafe_scene_objects so regeneration retains this pair.
Matched native captures and the immediate pre-edit scene backup are in
output/veridant/cafe-doors-v1/. Before and after use position (-100,100,60), target
(-100,270,48), FOV70, 900x700. Riverside was restored as the active editor tab;
play is stopped as it was before this task.
