# Ares bulkhead lamp — approved and installed

The user approved this lamp on 2026-11-05 and requested deletion of the old asset. One approved lower-hall fixture is now installed. Exactly 24 old render triangles were deleted from the active dressing import; the original lamp was embedded geometry rather than a separate asset. `Tools/ares_bulkhead_lamp.py` supplies the saved standalone renderer, and `Tools/ares_map.py` omits the old lamp at that placement. Unrelated lamps and shared materials remain in use.

The approved close mesh is unchanged, with 32,482 triangles. Authored distance meshes have 6,496 and 1,460 triangles, using native thresholds 25/65. Reduction produced 22/39 triangles with opposing interpolated normals; these now use matching geometric normals. All three meshes pass finite/nondegenerate geometry and winding checks. The private whole-map preview assets were retired outside Assets. `verify_installed.py` proves exact face deletion, unchanged unrelated geometry/collision/materials, one scene-node addition with all other parsed scene data identical, and retained generator behavior. Installed native captures and three-LOD checks are under `output/ares/bulkhead-lamp-native-v1/installed/`.

The text below records the original review workflow; do not rerun `prepare.py`, `setup.py` or staging against the installed map. Those historical operations expect the original lamp to exist.

Adapts the existing uninstalled `bulkhead-lamp-trial-v1` model to engine inches, orientation and native materials. It replaces one lower-hall lamp at world `-300,1100,120` in a disposable render scene only. The public Ares scene, original dressing import, ModelDoc, lights and collision remain unchanged. Branch: `codex/ares-bulkhead-lamp-native-review`.

The proposal adds a stepped casting, closed ribbed lens, cage, seals, socket fasteners, anchor hardware and service details within the original 10×6×4.2 inch envelope. Native glass adapts the existing Ares glass shader. Internal tubes reuse the approved Ares warm LED material; a weaker private copy lights the diffuser. The original eight material slots and authored texture maps are retained. No new lights or colliders.

`prepare.py` stages private assets outside Assets and identifies exactly 24 original triangles in the CURRENT active dressing import. Every unrelated line is retained. `setup.py` imports through the native editor, compiles both ModelDocs and eight materials, then renders before/after with matching cameras and map lights. It copies scripts into the native session exchange directory. The temporary scene is destroyed in finally; active editor scene, dirty flag and play state remain unchanged.

Evidence is in `output/ares/bulkhead-lamp-native-v1/native/`: detail and context before/after PNGs, with `validation.json`. `verify.py` validates protected hashes, imported bytes, exact face removal, finite geometry, winding and native receipts. All models and materials compiled successfully. Run commands from the canonical checkout, prefixed with `rtk python`.

At initial review this had no distance LODs; installation resolved that requirement as described above. No performance benchmark is claimed. No background renderer or helper remains running.
