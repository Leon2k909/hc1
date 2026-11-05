# NO PLACE BETTER neon sign v1 — rejected; original retained

Substantial rebuild of Riverside's original 36-triangle flat sign: rounded, individually bent emissive tubing on both faces; electrode boots and short insulated leads; ceramic stand-offs and metal clips; mounting rails; formed and weathered steel housing with rolled perimeter, rain lip, side service hatch, hinges and lock; pole cradle, bolted foot plate, junction box and supply conduit. Original hand-drawn lettering paths, cabinet dimensions, placement and two scene lights retained.

Prepared in C:/sbox-projects/hc1/neon-sign-review on codex/riverside-neon-sign-v1. This is separate from the water tower/tank comparisons owned by the other chat. Existing approved models and active work were checked before selecting the neon; no suitable replacement was found.

## Final model

Engine position (1150,60,0), yaw2.8624052. Cabinet111×10×126 inches centered410 inches above the original pole base. Three LODs:34,908/9,660/6,444 triangles at0/20/45. Six material batches. Only neon_red.vmat is emissive; the housing, supports, clips and wiring remain opaque PBR surfaces. Neon color uses a256×64 red-to-hot-center profile mapped from the tube's radial normals; brightness8.0. Coating maps are1024px. All textures use power-of-two dimensions. Unused tuning materials were recycled through the editor.

Tube joints were checked at OBJ's .001-inch export precision. Collapsed fan triangles were removed while retaining their valid neighboring triangles; all final triangles have positive area and all normals/UVs/indices pass validation.

## Evidence and scope

`output/riverside/neon-sign-v1/in-game-front-before.png` and `in-game-front-after.png` are actual offline Riverside play captures, with one player and zero error models. Matching camera, framing and existing scene lighting. The temporary offscreen camera copies gameplay effects, EnablePostProcessing and the gameplay volume anchor; it does not replace the main camera. Near clip5 avoids unnecessary depth artifacts. Runtime renderer substitution and the temporary camera are restored/destroyed in finally.

`verification.json` confirms the original public dressing model/source, its complete PhysicsShapeList, the saved scene and the original two red lights remain unchanged. Six materials load correctly. Both captures have zero magenta error pixels and zero green tube pixels. White-clipped pixels in the same text crop decrease from34,480 to197. Editor state restored. Native isolated engine-before/after.png are supplementary previews with matched studio lighting.

No public sign installation, original-geometry deletion or authoring hook yet; candidate awaits approval under CLAUDE.md. Private dressing_without_neon removes exactly36 old sign triangles for preview and retains all original physics and other prop upgrades. Original public model and legacy review control remain intact. Installation must preserve the original lights and physics and update authoring without full-map regeneration.

Build: `build.py`; precision/geometry checks: `check_geometry.py`; guarded native import: `import.cs.txt`; material check: `check-materials.cs.txt`; actual game capture: `capture.py` / `runtime-review.cs.txt`; final checks: `verify.py`. `refine_glow.py` and `finalize_red.py` are one-time tuning history, not required build steps. `prepare_final_manifest.py` finalized the reviewed inputs. `cleanup_trials.cs.txt` recycled only unused private tuning resources.

## User decision

Rejected: user prefers the original sign. Do not install this candidate. Public dressing model and source were never replaced and remain unchanged. Preview resources are archival, not an approved upgrade.
