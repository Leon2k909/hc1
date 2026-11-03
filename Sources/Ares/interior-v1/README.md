# Ares main hall interior — approved concept implementation

Installed 2026-11-03 on `codex/ares-interior-v1`, after the user approved the prototype and instructed implementation.
Visual target: `Sources/Ares/interior-concept-20261103/concept-v1.png`.

The main hall now has four curved north–south pressure frames, six side-wall haunches, warm off-white panel
bays with service joints, oxide-red collars, overhead ducts and cable trays, formed gallery fascias and brackets,
and 24 suspended light fixtures at the existing hall light locations. Gallery toe boards use a dark finish;
stair/threshold safety markings are retained. The hall floor uses larger matte panels with actual seam geometry.
The four pump boxes have formed housings, service screens, vent inserts, flanges and curved pipe elbows.

This pass applies the prototype's architecture and material direction to the existing main hall. It preserves
the room's dimensions, all door imports, stairs, routes, cover positions, source scene, actual lights,
post-processing and existing reflection/bounced-light resources. It does not rebuild the wings or cargo concourse.

## Sources and assets

- `Tools/ares_interior.py`: reusable render geometry and private material mappings.
- `Tools/ares_map.py`: narrow hooks retain the interior, pump housings and toe-board finish on regeneration.
- `Assets/materials/ares/interior-v1/`: six private PBR finishes; 512-pixel power-of-two normal/roughness/colour maps.
- Published hall base: `Assets/models/maps/ares/pressure-doors-v2/hall_base.obj`.
- Published reactor mesh: `Assets/models/maps/ares/ares_reactor.obj`.
- Existing hall/reactor ModelDocs retain every previous import and the complete byte-identical physics suffix;
  only the private finish aliases are added. Their source paths and scene identities stay the same.
- Assets under `models/maps/ares/interior-v1/` are historical preview models, not runtime scene dependencies.

## Scope and validation

The hall delta removes 3,374 old truss/pilaster/floor triangles, adds 32,918 architecture triangles and changes
the material of 524 existing gallery toe triangles. Every other original face retains its material, positions,
UVs and normals. The reactor removes 560 old pump triangles and adds 6,664. Its four original pump collision boxes
are preserved. Source-generated hall/wing/concourse/reactor collision boxes and hulls were compared before/after;
the architecture additions are independently checked to contain no collision.

`output/ares/interior-v1/` retains all evidence:

- `before/`: original model sources, ModelDocs, generator and scene snapshots. Do not remove these migration backups.
- `manifest.json`, `install-plan.json`, `installed.json`: exact source guards, staged hashes and native installation.
- `source-collision-verification.json`, `verification.json`: collision/import/geometry preservation checks.
- `preview-compilation.json`, `installed-compilation.json`: native asset compilation results.
- `overview`, `floor`, `wall`, `pump` PNGs: matched before/after and installed captures.
- `capture-installed.json`: zero error models, six private hall materials, editor/play state preserved.

Captures use a disposable native editor scene and retain the saved map's visual roots, doors and baked lighting.
No reflection bake is invoked. The comparison camera uses the same fixed settings for each version; saved map
post-processing is unchanged. Every temporary scene is destroyed in `finally`. Full gameplay frame time has not
been benchmarked; the pass adds no scene lights or shadows. No background helper or browser is retained.

## Workflow

`build.py` is a guarded one-time migration. It takes only the scoped old polygons from the installed meshes and
merges the new shapes into those meshes; it never publishes a full regenerated Ares map. `import_preview.cs.txt`
publishes private review assets through native MCP. `prepare_install.py` checks inputs and generated collision;
`install.cs.txt` validates all targets/staged hashes, then atomically installs the scoped sources through the editor.
`verify.py` checks the installed face delta and immutable source scene/imports/physics against the snapshots.

Use `rtk` before shell commands. Execute C# through `native.py script`, which copies the script into the native
session exchange directory. The migration intentionally refuses unexpected or already modified source files.
