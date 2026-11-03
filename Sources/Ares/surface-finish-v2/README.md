# Ares surface finish v2 — native review

**Superseded:** the user rejected this texture-only trial as too far from the reference. Do not install its plan.
The replacement construction pass is documented in `Sources/Ares/constructed-interior-v3/README.md`.

Generated and prepared 2026-11-03 in response to the gap between the approved concept and the first installed hall pass.
**Review assets only: public hall/reactor models, generator and scene have not been changed by this trial.**

The built-in ImageGen tool generated an ivory pressure-panel albedo, warm grey worn-floor albedo, and matching
tangent normal maps. Raw 1254-square results, prompts and provenance are retained here. Native `Sandbox.Bitmap.Resize`
prepares 2048-square engine imports; this does not add source detail. Six private materials separate the wall atlas,
floor, painted frame, structural steel, gunmetal and grating. Bare service pipes retain their original materials.

`build.py` reads the current public models and stages private trial ModelDocs. Only 64 broad wall faces receive the
new `ar_in_wall` alias and a 96-to-192-inch UV scale change. The other 364,388 hall faces retain exact material/corner
data. All positions and normals, all additional door imports, and both complete physics suffixes are preserved.
The reactor mesh is unchanged; its trial ModelDoc changes only finish remaps. No scene objects or lights are added.

Final trial lighting: the existing 24 Hall lights use RGB 5.355 and 5200 K, replacing their cool RGB 2.35/2.55/2.95.
Existing bounced-light volume runtime intensity is 2.2 (previously 0.65), contrast 0.78 (previously 1). Saved probe
textures, light origins/radii/shadows, exposure and other post-processing remain unchanged. The normal-map pair is
a generated visual approximation, not a measured material scan.

Native captures in `output/ares/surface-finish-v2/`:

- `overview-review.png`, `floor-review.png`, `wall-review.png`: actual final native render, using the saved map exposure.
- Other named PNGs: intermediate lighting/material experiments; not the selected finish.
- `capture-report.json`: zero error models; user's scene, play state and dirty state preserved.
- `before/`: guarded snapshots. `manifest.json`: staged preview hashes and preservation checks.
- `install-plan.json` / `install-stage/`: exact pending public patch, including generator retention hooks and native scene mutation arguments.

Workflow: `native.py` attaches to the existing editor, and copies `.cs.txt` scripts into that connection's exchange
directory. `import.cs.txt` imports only private review assets. No cubemap bake, game-code script or background helper
is retained. One initial hall compile exceeded the tool timeout; `asset_info` confirmed it had completed and was up
to date before proceeding. All trial models/materials subsequently compiled successfully.

After visual approval: run the guarded `install.cs.txt`, compile the two public ModelDocs, apply `scene_mutations`
from the install plan through native `set_component`, `save_scene`, and capture the installed result. The advertised
Bridge batch tool is unavailable in this editor build, so the plan uses the engine's own component setter.
Recheck the snapshots before installation; do not overwrite intervening work. Keep the runtime GI values when
merging any future scene regeneration, as the map generator does not own the saved baked-light resources.

This is a surface and light-balance pass. The concept still has denser reactor, ceiling, and structural construction
than the current geometry; these textures alone do not make those shapes equivalent.
