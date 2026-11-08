# Cerro Blanco lawn relief — staged review, 2026-11-05

User direction: subtle ground variation where appropriate, rather than the reverted Riverside mound.

The four lawn quarters around Cerro Blanco's garden circle have a staged shallow crown: maximum
4 inches (10.16 cm) above their existing surface. The paved paths, inner/outer lawn edges and kerbs
keep their current heights. The steepest generated triangle is 3.58 degrees. A fixed-width smooth
fade along the straight path edges prevents a ridge where those edges meet the curved lawn boundary.

`Tools/cerroblanco_lawn_relief.py` builds only a separate lawn overlay outside Assets, under
`output/cerroblanco/lawn-relief-v1/stage/`. It reuses the lawn material and grounds UV phase.
There are 3,592 triangles and one static collision mesh using the same OBJ. A 0.015-inch offset
avoids coincident render faces. The grass rises around the existing boulders; no props are moved.
Production scene SHA-256 is recorded and checked in `validation.json`.

`Tools/cerroblanco_lawn_relief_render.py` reads the current scene and supported local OBJ models,
then produces matched `eye-before/after.png` and `detail-before/after.png` images. Camera, exposure,
materials and lighting remain fixed within each pair. The standing view is 64 inches above ground;
the detail view is a low 24-inch inspection angle. These are Blender daylight inspection renders,
not engine screenshots: cloud foliage, distant backdrop, unsupported non-OBJ models and particles
are omitted consistently. The garden's cloud hedge therefore does not appear in the comparison.

Validation covers finite geometry, positive face winding, rise limit, slope limit and inner/outer
edge heights; both scripts pass Python compilation. The editor was not used. No live map assets
were edited, and nothing was staged, committed or pushed in Git. This is a review candidate only.
Native asset compilation, collider behaviour, navmesh and in-game appearance remain unverified.

## Native editor comparison

At the user's request after opening the editor, matched native captures were made in the current
Cerro Blanco edit scene using the real map lighting, foliage and materials. Images are under
`output/cerroblanco/lawn-relief-v1/native/`, with standing (`eye`) and low (`detail`) before/after
pairs. A temporary in-memory SceneObject used the candidate's actual OBJ positions, normals and UVs
with the game's lawn material; no candidate assets or scene modifications were installed or saved.
`native/capture.cs.txt` retains the successful capture script. The temporary object and camera were
removed in a finally block, the original Riverside tab was restored, both scenes remained clean,
and the production Cerro Blanco scene hash was unchanged. Code compilation was successful with
zero errors. These are native edit-scene captures, not a live match or collision/navmesh validation.
Nothing was staged, committed or pushed in Git.

## Installed for an in-game decision

The user subsequently requested applying the candidate in-game so they could decide. The model's
OBJ/MTL/VMDL were imported through the editor asset API and compiled successfully. The model loads
without an error flag. Native `spawn_model` and `add_component` placed one saved scene object named
`Garden lawn relief - REVIEW TRIAL` (ID `881fccaf-8e18-43cb-b44b-46019c7f0a9e`) with a ModelRenderer
and static ModelCollider, both referencing `models/maps/cerroblanco/lawn-relief-v1/garden_lawn_relief.vmdl`.

The rollback scene is `output/cerroblanco/lawn-relief-v1/native/before-install.scene`. The saved
scene was checked to contain exactly one trial object. A runtime ground ray at (-1179,1463)
hits that object's collision at Z 4.9977646, rather than the original ground at Z 0. The player
was positioned on the paving at (-1359,1575), facing the lawn. `native/installed-gameplay.png`
records the actual running player view. Play mode was left running at the user's request.

This is an installed review trial, not a final acceptance. The canonical map generator has not
been modified to add the object automatically; do not rebuild the map while assessing it. No
navmesh rebake or AI route sweep was performed. Nothing was staged, committed or pushed in Git.
Prefer removing the named trial object through native scene tools if rejected, preserving any
unrelated scene edits made since installation; the rollback snapshot is a fallback reference.
