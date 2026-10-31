## Town house doors v2 (`models/buildings/town_house/door_v2`, `Sources/Buildings/town-house-doors-v2/`, 2026-10-31)
- Replaced the town house's ten doors at the user's word, after comparing old and new side by side in s&box ("new doors better").
- `Assets/prefabs/buildings/town_house.prefab`'s three outer and seven inner doors now point at `door_outer.vmdl` and `door_inner.vmdl`. Nothing else in them changed: position, `BoxCollider` and `FuncDoorRotating` are as they were, and the models share the old pivot and fit inside the old box.
- Seen in s&box in the real prefab, in an isolated editor scene: all ten load and sit in their frames. Not seen in a match or swung open. The green door's dirt along the bottom is blotchy (see the folder's README), and the user took it as it is.
- The old `town_house_door_outer` and `_inner` stay in the repository. To undo: `git checkout Assets/prefabs/buildings/town_house.prefab`.
