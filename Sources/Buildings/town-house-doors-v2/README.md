# Town house doors v2

Created 2026-10-30. **Installed 2026-10-31** at the user's word ("new doors better"): see `docs/notes/166`. The old
`town_house_door_outer` and `town_house_door_inner` stay until the user says otherwise. Nothing is committed.

The old doors are flat slabs with four panels drawn on and blotchy chips. These have real joinery: stiles, rails and a
mullion, fielded panels with mouldings, hinges, a lever and backplate on each face. The front doors add a brass letter
plate and kick plates, plus a knocker and weather bar on the exterior face, which is local +X on all three. Paint is
layered over timber, with grain following each member, and wears on the lock stile, around the lever and along the bottom.

- Triangles: outer 4,574 / 2,186 / 228, inner 3,688 / 1,744 / 228 (LOD 0-2), against 360 and no LODs. Ten doors to a house.
- The leaf fills the prefab's box collider, which isn't changed, and swings about the same origin. Hinges and levers stand
  proud of the collider, as the old levers did. The models carry no physics of their own, like the old ones.
- One material each, one 2048 atlas each. Density is about 11.7 px/in (outer) and 15.7 px/in (inner), lower than the flag's
  24.5: the shelf packer only fills 42-54% of the atlas. A better packer is the cheapest way to sharpen these.
- `door.py` builds, bakes and exports; `paint_door.py` paints; `render_door.py` renders in a plain test wall;
  `verify_door.py` checks the files. They use `Sources/Gameplay/capture-flag-v2/`'s `build.py` and `paint.py` as a toolkit.
- Rerunning the build can change the unwrap, so bake and paint after it. The export refuses to run otherwise.

Not done: never compiled or seen in s&box (the images are Cycles renders, which flatter any asset), and the LOD thresholds
(20, 60) are estimates. The new leaf hasn't been seen in the real frame, or swung.

To adopt them: point the ten door objects in `Assets/prefabs/buildings/town_house.prefab` at
`models/buildings/town_house/door_v2/door_outer.vmdl` and `door_inner.vmdl`, compile, check them in Ridgeback, then remove the
old files if the user says so.
