# Raised trailer L1 roof ladder — installed; original retained

Adapts the approved Lowtide quay ladder recipe to L1's220-inch rise and38-inch lean, reusing the retained galvanized steel finish and existing hardware/grip materials. No new textures. Continuous rails, returned roof handholds, anti-slip treads, grip studs, sealed lower ends, wall brackets and bolted roof feet replace the original204-triangle rods. Top feet are individually fitted to the trailer's pitched roof at their actual lateral positions. Original trailer, roof, graffiti, physics, lighting and climbing behavior are unchanged.

Worktree C:/sbox-projects/hc1/roof-ladder-review, branch codex/riverside-roof-ladder-v1. Private resource models/maps/riverside/roof-ladder-v1/ladder.vmdl; placement(407,-697,96), yaw90. LODs6,904/4,252/2,060 at0/20/45. Four reused non-emissive finishes. Original approved recipe/material files are unchanged. This is separate from the installed guard-tower ladder and T2 steps.

Actual Riverside play verified one player, zero error models and copied gameplay post-processing. in-game-whole/detail-before/after.png are matching night captures with no added lights. studio-whole/detail-before/after.png use matched inspection lights in an isolated native SceneWorld, clearly supplementary to the night map. Source scene/play state restored. Geometry, materials, source hashes, original public physics and saved scene validated; verification.json records results.

Installation was approved and completed. The original asset remains available for reuse; see the installation receipt below.

## Installed; original retained

User approved the new roof ladder and requested that the original remain a reusable game asset. The public riverside_levee.vmdl now imports levee_without_ladder.obj plus installed_lod0/1/2.obj, baked to the approved world placement. Original shared geometry remains in all three LODs; the full original PhysicsShapeList and saved scene are unchanged. Actual public model checked in play without temporary model replacement: one player, zero error models. Tools/riverside_roof_ladder.py and the narrow riverside_map.py hook reproduce the approved geometry without a full-map regeneration.

The original 204-triangle model remains at models/maps/riverside/roof-ladder-v1/legacy_ladder.vmdl, with its OBJ/MTL and original aluminum material. It is not placed on Riverside. Local foot is origin, native lean toward negative Y, rise220 inches, width18 inches between rails. It can be placed on other maps through the Asset Browser. No original asset was deleted. Receipts: installed.json, installed-runtime.json and installed-state-restored.json. Final photos: in-game-whole-installed.png and in-game-detail-installed.png.
