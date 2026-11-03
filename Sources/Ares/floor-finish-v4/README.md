# Generated Ares floor finish — v4

## Installed floor-only update (2026-11-03)

The floor is now installed in the public `ares_hall.vmdl`, rather than only in the private trial model.
`build_live_floor.py` staged the current public hall, removed exactly the600 original main-floor triangles,
and added22,178 beveled plate triangles. The existing24 gallery/wing/concourse `ar_floor` triangles retain
their positions and normals with80-inch texture repeats. The main floor uses individual roughly80-inch
plates with explicit rotated UVs. `Tools/ares_floor_finish.py` and the narrow generator hooks retain this
finish on future generation. All363,828 other hall triangles remain exact; the ModelDoc physics and scene
are unchanged. Only the two floor remaps changed in the public ModelDoc.

`install_live_floor.cs.txt` installed the five guarded public/source files through the native editor.
`verify_live_floor.py` checks installed hashes, scene preservation, ModelDoc remaps, other geometry and
generator syntax. Evidence, original backups and the exact plan are in `output/ares/floor-live-v4/`.
The public model compiled successfully. A forced compile exceeded the CLI response timeout, then native
asset inspection confirmed the completed model was compiled/up to date with no compile failure.

`prepare_live_capture.py` / `capture_live_floor.cs.txt` capture the installed public assets in a disposable
copy of the saved Ares scene, with its original lights and exposure and no trial-model substitutions.
`gallery-installed.png`, `ground-installed.png` and `hero-installed.png` show the actual installed finish.
The capture report confirms both new material paths, no error models and preserved user editor/play state.
The editor was on Spillway during verification; that scene was neither switched nor edited.

The earlier combined v3/v4 install plan below is historical and must not be applied over this floor update.
It contains a broader architecture/lighting pass that was not installed by this floor-only repair.

## Earlier material review

The user requested a generated floor texture because the floor looked blurry/black. The old gallery floor still
used `ar_floor` (mean albedo roughly RGB61/59/57, metalness0.55) while the v3 main floor used a separate finish.
This pass replaces both with coordinated generated materials and raises the gallery texture density from one
repeat per192 inches to one per80 inches. It changes no geometry positions, normals, collision, light or exposure.

Built-in ImageGen generated six square maps, with the approved Ares concept as a material reference:

- `generated/plate-color.png`, `plate-normal.png`, `plate-rough.png`: satin steel hall access panels.
- `generated/grip-color.png`, `grip-normal.png`, `grip-rough.png`: framed anti-slip gallery/walkway panels.
- Full exact prompts are in `prompts.json`; output filenames and preparation are in `provenance.json`.

The original1254-square outputs are retained. Native `Sandbox.Bitmap.Resize` prepares2048-square engine imports in
`Assets/materials/ares/floor-finish-v4/`. These generated material maps are visual approximations rather than scans.
The private VMATs use metalness0.08 and coordinated color/normal/roughness maps. The plain plates have neutral tint;
the gallery finish uses0.65 neutral-grey tint after native review to avoid an excessively pale floor and keep surfaces
readable under the hall lighting. Existing grating, stair nosings, yellow route markings and thresholds are retained.

`build.py` overlays the previously reviewed v3 hall, retile-maps24 existing `ar_floor` triangles and remaps the two
floor materials. All478,734 triangle positions/normals and the complete model physics suffix remain identical.
`import.cs.txt` publishes only private floor review assets through the editor and skips unchanged hashes.
`compile.py` compiles the two materials and model, inspecting any timed-out compile before proceeding.

Matched raw native before/after captures are in `output/ares/floor-finish-v4/`: `gallery`, `ground`, and `hero`.
They use the same v3 scene lighting and camera settings, warm streamed textures, and native anti-aliasing.
No screenshot is composited or relit. All temporary scenes are destroyed and the user's active scene is preserved.
Both materials and the trial model compile successfully; the matched native captures report zero error models.
The previous91-pair navigation comparison still applies: no collision or positions change in this material pass.

`prepare_install.py` merges this floor into the pending nine-file v3 public/generator patch. It retains the v3 light
mutations and support/skirt collision additions, changes future floor material mappings and the gallery tile size,
and rehashes the combined plan. That plan was not installed; the later floor-only update above supersedes it.
Native source inputs must still match, and scene mutations require Ares to be the
active scene before saving; do not apply them to another open map. No helper, browser or development server remains.
