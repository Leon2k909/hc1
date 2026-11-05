# Boxyard pipe stacks — 2026-11-04

Replaced both six-pipe stacks by bomb site B with smooth hollow tubes, bevelled wall thickness, complete inner
bores, longitudinal weld seams, low-contrast aged steel and mill markings. Rounded steel shipping bands follow
the 3-2-1 bundle, with crimped buckles and rivets; bevelled timber bearers and fitted chocks support the pipes.
Pipe positions, lengths and deterministic end staggering match the original stacks. Four private materials use
authored 2048×512 color, roughness and normal maps. No external assets or image generation.

`build.py` stages review resources. The old stack's faces are checked against the public asset and transformed
to the origin with the original texture coordinates, normals and material preserved. Native `capture.cs.txt`
renders before and after with identical lighting/camera/exposure. It uses a temporary isolated scene. The saved
Boxyard visual roots are loaded separately for installed context captures; no user scene switch or play control.
Once the generator helper is installed, `build.py` stages texture updates only, preserving comparison geometry.

`prepare_install.py` snapshots current inputs and prepares a narrow Counter splice into `boxyard_props.obj`.
Native `install.cs.txt` refuses changed inputs, publishes the three merged model resources and two generator
files, and registers assets. Exactly480 old faces are removed,11,352 added and1,526 other faces retained exactly.
The entire ModelDoc physics suffix, all hull sources and saved scene are unchanged. Both generated collision
boxes match the original generator point for point. `boxyard_map.pipes` calls `Tools/boxyard_pipe_stacks.py` for
the new render mesh and retains the original collision expression. No complete map rebuild is needed.

`verify.py` checks file hashes, exact face retention, byte-identical physics, unchanged scene/hulls, finite and
nondegenerate mesh data, generated geometry/collision matching the installation, and the original comparison
materials. `check_public.cs.txt` confirms the compiled public model and all four new material bindings. The
public model was fully compiled successfully. No gameplay, lighting or other map changes; no frame-time benchmark.

Evidence, snapshots and receipts: `output/boxyard/pipe-stacks-v1/`. `before.png`/`after.png` are actual engine
renders, and `context/*-installed.png` shows the map installation. The unused old `before.*` resource is retired
outside Assets, with hashes in `retirement.json`. Screenshots and rollback snapshots remain. Do not rerun the
historical comparison import/capture after retirement; it would restore the old review asset.

The user subsequently requested keeping both versions, with the new one active. `keep_legacy.cs.txt` restores
the original render mesh as the separate, inactive `models/maps/boxyard/pipe-stacks-v1/legacy_pipes.vmdl` asset,
with fresh editor metadata and references to its own OBJ/MTL. The active map and generator remain on the new
version. `retained-variants.json` records the alternate files and hashes of the unchanged active map sources.
The old stack's collision continues to be preserved by the active merged model; the alternate is a render mesh.
