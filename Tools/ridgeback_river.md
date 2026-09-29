# Ridgeback river

The `River` root in `Assets/scenes/maps/Ridgeback/ridgeback.scene` holds 21 water
sections following the existing west-to-east channel. They use a dedicated
flowing normal-map shader with transparent shallows and depth-faded gravel banks.
Water is about 30 units above the channel bed, leaving the original terrain as
the walkable surface. The meshes have no collision and cast no shadows.

## Refit after sculpting the terrain

1. Save the terrain and scene, then run Ridgeback in the editor.
2. Run `ridgeback_river_export` in the editor console.
3. Run `python Tools/ridgeback_river.py` from the project directory.
4. Run `ridgeback_river_compile`, wait for asset compilation, and reload Ridgeback.
5. Run `ridgeback_river_validate` to check mesh loading and sampled water depths.

The builder consumes the current terrain export in `output/river`; it does not
run the terrain generator. It replaces only the River scene group. Avoid saving
an older editor copy of the scene over the newly generated group.

`ridgeback_river_capture` saves an aerial preview to `output/river` without moving
the player. It also accepts camera x/y/z, target x/y/z and an output name.
