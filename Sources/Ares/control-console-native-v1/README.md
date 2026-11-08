# Ares control console — native review 2026-11-05

Reuses the existing uninstalled `Sources/Ares/control-console-trial-v1` proposal, found during the required existing-upgrade audit. No replacement console was authored from scratch. Current map remains active; this is preview only.

Compared with the 40-triangle baseline, the existing proposal adds a folded cabinet, recessed service door, louvres, rounded screen housing and bezel, individual keyboard keys, trackball, switches, stop button, handles and cable glands. About 60×34×64 inches, world origin `-440,-230,0`. This is the walk-up core-process console. The current original `materials/ares/ar_screens.vmat` retains approved screen artwork and emission.

`prepare.py` adapts the legacy metre OBJ to engine inches/orientation, retaining UVs, authored PBR textures and original material slots. It stages outside Assets. The current active dressing import is `observation-sign-v1/dressing_without_sign.obj`; exactly 40 matched baseline faces are omitted in the private preview. All other lines/imports and physics are identical. Public map, ModelDoc, scene, shared screen material and legacy proposal are unchanged.

`import.cs.txt` checks hashes/path allowlists and imports natively. Both ModelDocs and all twelve private materials compiled successfully. `capture.cs.txt` deserializes only visual map roots in a temporary scene, uses matching cameras and existing map lights, renders both versions, then destroys that scene. Latest successful capture preserved active editor and play state; player floor trace hit Z=0. Earlier discarded capture exposed a source orientation mismatch, corrected in the adapter before the final captures.

41,806 triangles, one implicit base mesh, **no authored distance LODs** (native MeshInfo.LodCount reports 0). LOD reduction/performance review is required before installation. No new collision or lights; no live-match/frame-time benchmark claimed. `verify.py` checks finite attributes, nondegenerate triangles, winding (100% agreement), references, protected hashes, exact cut scope and native capture receipts. `compose.py` resizes matched screenshots and adds labels only.

Evidence: `output/ares/control-console-native-v1/comparison.png`, `verification.json`, `native/validation.json`. Left current; right native preview. Do not delete or replace the active original until user chooses the preview.
