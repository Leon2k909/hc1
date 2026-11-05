# Lucky Stop roof sign v1 — review candidate

Isolated branch/worktree: `codex/riverside-shop-sign-v1`, `C:/sbox-projects/hc1/shop-sign-review`. Preview resources are imported through the native editor under unique `shop-sign-v1` paths. The public store model and saved scene remain unchanged by this candidate. Installation awaits user approval under CLAUDE.md's graphics-upgrade rule.

The existing roof sign's simple black box, flat rear face and rectangular lamp boxes become a formed painted-metal cabinet, separate gasket/acrylic face/retainer strips, fasteners, rear service cover, electrical box and conduit, square posts with anchor plates and bolts, diagonal braces, and three curved gooseneck arms with open reflector shades and bulbs. Existing artwork pixels remain unchanged. The current lighting revision treats the face as matte printed material (roughness 0.72, no emission), reduces private bulb brightness from 6 to 1, and previews the sign-local floodlight at intensity 0.20 instead of 1.0. Its HDR color, radius and animation remain unchanged. Shared materials, other light settings and gameplay camera effects are preserved; no lights are added.

- LODs: 9,016 / 5,548 / 2,248 triangles; thresholds 0 / 20 / 45.
- Local base at roof contact; engine placement `514,-220,150`.
- Original cabinet volume remains 168×8×48 inches at local center `0,0,50`. Lamp arms and service hardware sit around that cabinet. Original ModelDoc physics section is retained in the private review store; the candidate renderer adds no collision.
- Exactly 136 original sign/lamps/support triangles are removed from the private store copy. Every unrelated mesh and all seven current store LOD groups remain unchanged, including installed shelving, counter, register and fridges.

## Reproduce and validate

Run `rtk proxy python Sources/Riverside/shop-sign-v1/build.py` in this worktree. It writes private models/materials and a source-hash-guarded review copy. `setup.py` prepares import/capture scripts from the established register workflow. `native.py` attaches to the canonical project's existing editor and places C# in the session exchange directory.

`import.cs.txt` permits only candidate resource paths and preserves scene/dirty/play state. `check_geometry.py` records the three original source meshes; their hashes remain identical through the lighting revision. `check-lighting-materials.cs.txt` checks the actual compiled material features and original/revised model resources. `verify_lighting.py` checks geometry hashes, imported/source hashes, compiled material evidence, the exact runtime floodlight value, saved scene bytes and editor restoration. It rejects magenta GPU error patterns and measures near-white highlights inside the sign face. It composes `lighting-comparison.png` directly from native captures without color/exposure changes. `verify.py` runs this current verifier.

The latest actual gameplay check uses `capture_lighting.py` and `runtime-lighting.cs.txt`: both images show the same new geometry, with previous versus revised lighting. Only the existing sign floodlight's runtime intensity is edited; the original value, model, cameras and editor/play state are restored afterward. Firelight color animation continues naturally and is recorded, rather than being disabled for the capture. The saved Riverside scene is byte-identical before/after. Final images are `lighting-after.png` and `lighting-comparison.png`; `lighting-verified.json` records the passed checks. Permanent geometry/scene-light installation remains pending approval; `lighting-plan.json` contains the proposed settings and target light GUID.

Original geometry-review receipts are retained separately. `bright_reference.vmdl` and `face_bright.vmat` preserve the pre-revision control. One-time preparation utilities (`prepare_lighting_revision.py`, `refine_lighting_material.py`, `reconcile_lighting_source.py`) document that history and should not be rerun blindly. The latter preserves a concurrent removal of 28 old ceiling-fixture faces; it does not change the sign geometry or any other upgrade.

To recapture: run the build/import workflow, `setup_lighting_capture.py`, `capture_lighting.py`, native `check-lighting-materials.cs.txt`, and `verify_lighting.py`. Capturing requires a clean stopped editor; an active user play session is preserved. `isolated-lighting.cs.txt` provides a temporary native asset preview when gameplay is occupied.

The preceding shelving installation and old-model deletion are complete and documented in the canonical checkout's `output/riverside/shelving-v1/installed.json` and `docs/notes/riverside-shelving-v1-20261104.md`.

## Installed 2026-11-04

User approved the toned sign. Public store now uses three new meshes with face_toned.vmat; the existing saved sign PointLight has Intensity 0.20. Old sign assets and bright reference controls were deleted; 136 old triangles removed from six source variants. Existing physics retained byte-for-byte. Tools/riverside_shop_sign.py reproduces all three approved meshes. Actual play verified one player, zero error models, no runtime substitution, no extra lights. See installed.json and in-game-installed.png. Historical preview scripts refer to deleted controls and are archival.
