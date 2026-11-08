# Veridant reception sign v2 — rejected and reverted 2026-11-05

The user rejected this change. The original sign is restored and the regeneration
hook removed. Keep these sources as history; do not reinstall this candidate.

Replaces the reception pylon's rectangular slab, cap, plinth and flat lettering
cards with eased stone edges and actual recessed logo/type geometry. The outlines
come from the existing letter atlas, preserving the resort identity and placement.
Letter pockets are 0.5 inches deep with dark backs and stone side walls.

The scoped import removes 42 exact original triangles from a copy of the current
`chair-v2/dress-base.obj`; it retains every other record and original index. The
parent `veridant_dress.vmdl` imports that copy and the 10,464-triangle sign mesh.
The original foot lamp, all other render imports and the complete physics suffix
remain unchanged. No scene, exposure, lighting or post-processing edits.

`build.py` stages the patch; `verify.py` checks finite vertices, unit normals,
nondegenerate triangles, and preservation of unrelated records. `prepare_import.py`
writes the guarded native import script into the CLI exchange directory. Do not
rerun historical imports over newer edits: the parent and source mesh guards must
match a deliberately selected baseline. `Tools/veridant_sign.py` and the narrow
`veridant_parts.pylon` hook retain the upgrade during map regeneration.

Evidence: `output/veridant/sign-v2/before.png` and `after.png` are actual displayed
editor frames from `Sandbox.ScreenshotService.RequestCapture`, with the same
existing editor camera and settings. No temporary cameras, isolated scenes or
RenderToBitmap were used. Editor gizmos are present in both captures.

`installed.json` checks the installed files against the stage and verifies the
unchanged physics suffix. The native loaded Dressing model reported IsError=false.
The editor was left in its existing stopped state with Riverside active; the
Veridant document has no unsaved scene changes. Branch: codex/veridant-reception-sign-v2.
