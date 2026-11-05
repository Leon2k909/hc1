## Riverside supply crates v2 — installed 2026-11-04

- User approved installing the reviewed wooden crate and deleting the old asset.
- All 12 placements use `models/props/riverside/crate_v2/crate.vmdl`, with their existing positions, headings and three authored sizes. Existing collision boxes stay in the pad/store/dressing models.
- Removed exactly 1,032 old triangles (2 pad crates, 3 store crates, 7 dressing crates). Removed legacy crate faces/remaps in two unpublished comparison backgrounds as dependency cleanup.
- Deleted `materials/riverside/rs_crate.vmat`, its metadata and compiled file through the editor after native dependency count reached zero. Shared wood/sign atlases remain in use.
- Generator integration: `riverside_parts.CRATES`, `crate`, `carry`; `riverside_map.crate_objects`. `riverside_materials` no longer generates the old material. Avoid full map regeneration because of shared-kit drift.
- Verification: `Sources/Riverside/crate-v2/verify-install.py`; all saved placements, exact face removals and unchanged collision/settings passed. Native captures loaded 12 valid models. Evidence/backups: `output/asset-improvement-20261030/riverside-crate/installed/`.
- Native script edits require `SceneEditorSession.HasUnsavedChanges = true` before `save_scene`, followed by file readback. `Game.IsPlaying` reflects script game scope; use the editor session's `IsPlaying` to guard editor mutations.
- Next target found: Riverside sandbag barricades. Reference and brief: `Sources/Riverside/sandbag-v2/README.md`. No replacement built yet.
