# Reef Hall circulation pump — play-mode review candidate

A single asset proposal on `codex/reefhall-circulation-pump-v1`, following the
approved and installed Lowtide ladders. This pump is not installed in the saved
map: it is shown for approval under the project's graphics review rule.

The selected pump is the first filter-hall unit, at plan `(-380, 1610)`, yaw 0.
Its original 220 triangles are a base and four capped polygonal cylinders. The
candidate adds a formed motor housing and fan cover, 24 axial cooling fins,
terminal box, cable gland, lifting eye, motor feet, shaft coupling and open cage,
asymmetric cast volute, bolted cover, gasket, flange bores and fasteners, drain
plug and anchored base. The original inlet/outlet centres and end heights remain.
Three private enamel/powder-coat materials use deterministic 512-square colour,
subtle micro-normal and roughness maps. Existing Reef Hall finishes are retained
for exposed stainless hardware and the dark internal faces. The saved map's
materials are unchanged. There are no new lights, colliders, scripts or gameplay
components. The candidate is 13,144 triangles.
Frame time has not been benchmarked.

`build.py` matches the saved pump by exact material/triangle position signatures,
then removes only its 220 triangles in a private copy of the filter-hall model.
All unrelated vertex, UV, normal and face records and the complete original
ModelDoc physics suffix are preserved. It does not regenerate the room or map.
The cast casing has smooth radial shading and chamfered shoulders. New review assets are imported through native `run_csharp` in the CLI exchange
directory and compiled with `asset_compile`.

`review.py` loads the actual map during offline play, with a local player present.
It switches only the runtime renderer between the original and the private pump
replacement. A temporary main camera copies the actual player camera's bloom,
tonemapping, sharpen, ambient occlusion, vignette and photographic response.
Exposure is held at the player's configured range midpoint (1.5 in the verified
run) for both variants. Normal camera streaming settles for 180
frames per view. No forced texture residency is used. It restores the menu in
`finally`, preserving the user's playing state. Transient scene identities can
change when loading maps, but the saved scene files are never written.

`verify.py` checks native play-mode evidence, source hashes, unrelated geometry,
physics and restoration, then writes labelled comparison sheets. All before/after
captures are actual s&box play-mode renders, not concepts or offline renders.

From the canonical checkout, sequentially:

```powershell
rtk python Sources/ReefHall/pump-v1/build.py
rtk python -u Sources/ReefHall/pump-v1/review.py
rtk python Sources/ReefHall/pump-v1/verify.py
```

Pictures and `validation.json`: `output/reefhall/pump-v1/`.
After approval, preserve the existing three pump positions, collision, other
room improvements, lights and scene. Do not publish a whole-map rebuild.
