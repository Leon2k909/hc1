# Veridant moulded equipment cases

The 82 olive and black equipment cases use a continuous tapered shell, rounded
plinth and wraparound corner guards. The broad side fields, reinforcement grooves,
lid pockets and four stacking channels are recessed geometry. There are no thin
bars applied to the lid. Handle wells contain pivot bosses, folding coated-steel
arms and shaped rubber grips. The over-centre catches have separate mounting
plates, pressed levers, bail loops, drive screws and pins; rear hinges and pressure
valves are also modelled.

Nine dedicated materials distinguish fine-grained polymer, rubbed contact edges,
rubber, opaque gaskets, coated steel, bare alloy and identification labels. Coated
steel uses a low metalness paint finish and its own colour texture so it remains
readable in the map's lighting. There are 16 upright inventory-label variants.

`Tools/veridant_parts.hard_case()` still calls `veridant_transport_case`, whose
shared hook now delegates to `Tools/veridant_case_detail.py`. Case stack offsets,
rotations, random-number consumption, dimensions and collision boxes are retained.
The previous generator is preserved in `previous-generator.py`.

Final publication: `output/veridant/cases-v4/stage-v7/manifest.json`. The native
guarded import publishes only this revision's materials/meshes and the two current
map model documents. Every other render import and the complete physics suffix
are preserved; the case publication does not edit the saved scene. Current model documents are read
again for each stage so concurrent work on other props is retained. The initial
staging guard caught an unrelated change to shared parts code before publication;
the final stage checks the exact case layout rather than locking that entire file.

Each case is 8,866 triangles (727,012 across the map). Dedicated imports contain at
most seven cases, below the 65k triangle compilation limit. Frame-rate impact was
not benchmarked. This is a geometry budget, not a performance guarantee.

Evidence and validation:

- `output/veridant/cases-v4/validation.json`
- `output/veridant/cases-v4/native-import.json`
- `output/veridant/quality/cases-v4-before/`
- `output/veridant/quality/cases-v4-final/`

All nine materials and both parent models are compiled through the native editor.
Matched olive/black captures use the same poses, projection and exposure as their
baselines and restore the editor's camera, tone, scene and play state. A live
material audit checks both renderers and all nine dedicated materials.

Another task saved the shared scene between import and the final captures. Camera,
projection and fixed exposure still match the baselines; the saved-scene hashes
are recorded separately and are not claimed to match across the whole task.
Every individual capture preserved its starting scene and editor state.
