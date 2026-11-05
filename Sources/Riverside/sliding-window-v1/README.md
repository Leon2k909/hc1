# Riverside T2 sliding-window frame — review candidate

User preferred the original Reef Hall coral and requested a different model encountered up close.
That original remains active; the rejected coral was not installed. The accepted aquarium pedestal remains.

Existing upgrades were checked before choosing this target. T2's precast entry steps already have an
upgrade and were skipped. No existing trailer/sliding-window upgrade was found in model/source filenames;
masonry architectural windows and the entry door's small window are different assemblies.

Selected T2's central south-side lit window, at plan `-820,995,76`, engine `995,820,76`. It faces the
walkable trailer lane at player height. Current frame is one flat aluminium quad and a block sill.
The new unit has a raised rounded mounting extrusion, two offset sash tracks, rubber glazing beads,
meeting stile, pile seal, operating latch, real lower water channel/weep slots, formed drip sill/end caps
and discrete fasteners. The existing lit pane/artwork stays at its exact saved position and UVs.

**Preview only; original frame remains active.** Model
`models/props/riverside/sliding_window_v1/window.vmdl`: LODs 2,586 / 1,970 / 866 triangles,
initial thresholds 0/25/70. Approximately 35 inches wide by 34.6 high, projection 2.74 inches.
No added collision, lights, transparency, opening interaction or new textures/materials.
Existing Riverside aluminium and rubber finishes are reused unchanged.

`audit.py` records the actual seeded T2 window arguments. `build.py` matches exactly 14 old frame/sill
faces in the current lowland mesh by material/rounded positions. Only those lines are omitted from a
private full-trailer preview. Every other original line, including pane positions, normals, artwork
UVs and material bindings, is identical. Its ModelDoc changes only the render-file reference; physics
stay identical. Public lowland OBJ/MTL/ModelDoc and Riverside scene hashes remain unchanged.

Inputs stage outside Assets, then `import.cs.txt` validates paths/hashes and imports natively.
Both private ModelDocs compile. `capture.cs.txt` uses an isolated copy of the map's relevant visual
roots, identical cameras/map lights in both variants and no inspection light. Player view is at
64 inches; the closer view examines the frame. Existing accepted T2 door/steps/hitch/vent props stay.
All three LODs are rendered; temporary scene is destroyed finally. `compose.py` only resizes matched
screenshots and adds labels. Evidence is in `output/riverside/sliding-window-v1/`.

`verify.py` checks source/import hashes, exact cut scope, unchanged pane/physics, finite attributes,
areas/winding, references, bounds and available native LOD/compilation receipts. All triangles agree
with exported normals. No live match or frame-time benchmark is claimed.

After acceptance, replace only this frame/sill, retain original pane art/emission, nearby door,
existing physics and all unrelated trailer geometry, and add a narrow source placement hook.
Do not regenerate the map or alter other windows without a new request.
