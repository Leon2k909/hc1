# Veridant reception doors — 2026-11-05

User approved keeping the new doors ("ye use new door") on 2026-11-05.

Added two usable glazed leaves to the reception entrance shown by the user, the
60-by-100-inch opening at plan e=140..200, n=200..216. Existing dark Veridant steel,
clear glass and brass materials are reused. Each 704-triangle leaf has hinges,
paired pull handles and a lower brass panel. Asset:
`models/props/veridant/reception_doors_v1/leaf.vmdl`.

The native editor saved two root objects, `Reception glazed door left/right`, at
world (208,-140.65,0) and (208,-199.35,0), yaw 0/180. Each uses Facepunch.Door
(90 degrees, .55 seconds, opens away from the user) and a moving BoxCollider.
No gameplay C# changes. Tools/veridant_reception_doors.py builds the model and
provides the scene objects; veridant_map.write_scene includes them at root level
to preserve the existing Door component's local pivot assumptions.

Native model compilation and matched screenshots passed. In play, both leaves
reached Open, rotated 90 degrees, then returned to Closed at their original
rotations. Two traces through the opening at y=-155/-185, z=45 cleared the open
doors and hit the corresponding closed leaves. No console errors were reported.
Evidence and pre-edit scene: output/veridant/reception-doors-v1/.
