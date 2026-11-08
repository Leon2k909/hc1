# Veridant reception desk — original active; new prop retained, 2026-11-05

The user chose the old desk for Veridant and asked to retain the new asset for
another map. The original buildings render import is restored and the regeneration
hook removed. The new desk is available as the standalone prop
`models/props/shared/reception_desk_walnut_v1/reception_desk.vmdl`.
It has a floor-centred origin, unchanged UVs/materials, the emissive strip and
body/top collision. It is not placed in Veridant. `retain_standalone.py` records
this conversion; its stage and verification are under `output/veridant/reception-desk-v1/retained/`.
Do not reinstall the historical map patch below unless explicitly requested.

The remaining notes describe the superseded installation and its review evidence.

The user rejected the preceding sign upgrade and requested a different change.
The sign's original render import was restored through the native editor and its
generator hook removed. `verification.json` checks that restoration.

The reception's plain box counter is replaced with a rounded, eased limestone top,
separate vertical walnut battens with real shadow grooves, a recessed dark toe
space, and fitted rear cabinet doors/pulls. It retains the 144x34-inch countertop
footprint, 42-inch height, original collision and original emissive under-top strip.
All materials are reused from existing Veridant assets.

`Tools/veridant_reception_desk.py` builds 2,746 visual triangles. The narrow
`veridant_parts.bar_counter` hook retains this one desk during map regeneration;
all other counters use the original function. The original body/top's 24 triangles
are removed from a byte-preserving copy of the latest active buildings base. The
parent ModelDoc imports that copy and the new desk. All other vertex/UV/normal
records, render imports and the entire physics suffix remain unchanged.

`build.py` stages; `prepare_import.py` guards the source and parent before a native
editor import; `verify.py` checks finite/unit data, no degenerate triangles,
retained unrelated records, installed hashes, physics and the reverted sign.
Both the loaded Buildings and Dressing models reported IsError=false. No scene,
lighting, exposure, post-process or play-state changes were required.

`output/veridant/reception-desk-v1/before.png` and `after.png` are actual displayed
editor viewport frames captured with `ScreenshotService.RequestCapture`, at the
same existing editor camera and settings. Native focus/update of the visible
SceneRenderingWidget ensures the requested viewport actually displays a frame;
no temporary camera, isolated scene or RenderToBitmap was used. Editor spawn/probe
gizmos are visible in both images. The scene has no unsaved changes.

Backups, stage, checks and final verification are in the same output directory.
Do not rerun historical imports over newer changes without refreshing their
explicit baseline and preserving any intervening work.
