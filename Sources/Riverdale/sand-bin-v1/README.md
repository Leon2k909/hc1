# Riverdale sand bin — staged review

Checked existing upgrades before building: no sand/grit-bin replacement was found in Sources, Tools, notes or model filenames. The existing upgraded Boxyard wheelie bin and Railhead station bin have different functions and silhouettes. This proposal rebuilds one court sand bin at plan (-1250,258), facing north, using Riverdale's unchanged yellow bin material and original SAND label.

The new body has tapered sides, rounded corners and a formed foot/shoulder. A rolled weather lip overlaps the seating gap under a sloped lid, with reinforcing ribs, two knuckle hinges, hinge pins, recessed front grip and low skids. The original general footprint and height are retained. No new texture was generated.

Exactly 38 legacy triangles are removed from a private yard-props preview. All original vertex, UV and normal records, unrelated faces, ModelDoc imports/remaps, saved scene and collision remain unchanged. Other sand bins remain unchanged. Six preview model source files are imported through native s&box; public assets are untouched.

`model.py` builds the model. `build.py` stages it and exact-matches the old bin; `review.py` imports and incrementally compiles the candidate/private base, then checks actual offline Riverdale play. Matching cameras use gameplay effects, locked exposure and 180 ordinary streaming frames per view, with no added lighting or forced texture residency. `verify.py` validates source guards, removal and preservation, live map/player/error-model evidence and editor state restoration, then composes comparisons under `output/riverdale/sand-bin-v1/`.

Pending installation approval. The preceding shared-cone candidate remains staged; the shared cable reel is installed.
