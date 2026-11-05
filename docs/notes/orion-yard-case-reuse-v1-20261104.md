# Orion central-yard equipment case — reuse preview, 2026-11-04

User requested both versions kept. Original remains in use in Orion; shared upgraded model and reuse
comparison retained as an alternative. No installation requested and no deletion pending.

Checked existing approved assets first and found Collider's equipment case. Reuse
`models/props/collider/equipment-case-trial-v1/after.vmdl`; no duplicate upgraded mesh/materials.
Selected the large single pallet case beside Orion's playable yard route (`case_block` seed10), visible
at player height. Recessed handles, latches, edge rails, hinges, seals and ID plate make the close-up change.

Preview only. Private props copy omits exactly 568 matched current case triangles, retaining the pallet
and every other face/attribute. Shared 15,568-triangle renderer at world `600.564985,-17.337997,5.7`,
yaw0, scale `0.7142857,0.7,0.7076923`; no added collider. Public scene/props/physics and shared case assets
unchanged. Native compilation, in-map renders and geometry/scope guards passed. Player-view floor ray
hits z0. No live match/performance benchmark; shared case has one LOD.

Read `Sources/Orion/yard-case-reuse-v1/README.md` before integration. Source/import/capture/verifier and
matching before/after comparison are in that folder and `output/orion/yard-case-reuse-v1/`.
