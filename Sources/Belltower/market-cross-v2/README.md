# Market cross v2 — review only

Rebuilt the market's stone cross and shaft with a moulded foot/capital, tapered shaft, shaped cross
arms, bevelled edges and carved centre bosses. Existing steps and the separate white stone cap remain.
The source appeared to leave a 12-inch gap, but native inspection showed that the existing white cap
fills it. No unsupported claim about floating geometry should be inferred from the procedural function.

Source LODs: 2,384 / 1,616 / 880 triangles. The selected original shaft/cross contributes 40 triangles.
Concave cross faces are ear-clipped, with genuine bevelled solid edges. Existing ashlar material is reused.
No collision, saved lighting, scene or production asset changes. Model origin: plan `(0,0,0)`, placed
at plan `(0,1275,0)` / world `(1275,0,0)`. A private centre variant removes only the selected 40 faces.

All three native model definitions compiled. A freshly compiled unchanged baseline and candidate
were warmed with discarded captures, then shown with the same camera, framing and inspection light.
The comparison restores model/object/camera/tone and editor state per capture. Opening the hidden
document initially selected it; the previously active Sewage document was restored afterward.
Effective GPU exposure was not independently measured. The production scene remains unchanged.

Source: `geometry.py`, `build.py`; evidence: `output/belltower/market-cross-v2/{before,after}-final.png`.
Approved by the user and installed. Removed the original 40 baked triangles from two mesh sources, deleted nine obsolete private review assets, and compiled the centre model. Scene save and preserved physics/object IDs/editor state passed native checks; see installed.json. Regeneration uses Tools/belltower_market_cross.py.
