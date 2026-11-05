# Sewage warning sign v1 (2026-11-04)

The foreground safety board now has a solid chamfered metal backing, folded rim, six washer/hex fasteners, rear reinforcement channels and four saddle clamps wrapping the existing handrails. The original texture artwork, UVs and placement remain intact.

`Tools/sewage_warning_sign.py` supplies the hardware; `Tools/sewage_map.py` calls it for the warning sign. Installation splices 3,700 triangles into the published `sewage_signage.obj`, preserving all 140 existing signage triangles exactly. No scene file or collision shape changes. Source snapshots and guarded native integration are under `Sources/sewage/warning-sign-v1/`; matched native renders and validation reports are under `output/sewage/warning-sign-v1/`.

Installed in the original signage model and visually approved. The original three model source files are retained in `output/sewage/warning-sign-v1/baseline/`.

Follow-up: corrected the already-clipped warning texture by measuring the actual glyph bounds. Both rows now share a fitted font, stay within 10% horizontal margins and are vertically centred in their rows. `warning.vmat` references `materials/sewage/warning-sign-v1/warning_color_v2.png`. `Tools/sewage_map.py` enables fitted text only for this warning sign, preserving the fix on regeneration. Reproduction, layout verification and matched captures are in `Sources/sewage/warning-sign-v1/fix_text.py` and `output/sewage/warning-sign-v1/text-fit/`.

After approval, the superseded `warning_color.png` and the duplicate `before`/`after` preview model assets were deleted through the editor. Installed scenes/models do not reference them. The approved public `sewage_signage.vmdl` and fitted texture remain. Historical sources/renders stay outside Assets; importing the preview assets explicitly is necessary before rerunning historical comparisons. Cleanup report: `output/sewage/warning-sign-v1/cleanup.json`.
