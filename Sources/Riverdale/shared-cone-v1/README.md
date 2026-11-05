# Riverdale shared traffic cone — review only

Audited existing models first and reused the approved Boxyard traffic cone v2, already installed in Boxyard. It has a hollow tip and underside, shaped rubber base, worn orange plastic and reflective sleeves, and 5600/2440/796 triangle LODs. No duplicate replacement model, material or texture was built.

Preview replaces only the standing north-lane cone at plan (300,2433), using the unchanged shared resource at engine (2433,-300,0), identity rotation/scale. The adjacent standing and tipped cones stay unchanged. Exactly 166 original cone triangles are removed from a private copy; all other records, ModelDoc content, source files, scene and collision are unchanged.

`build.py` stages the private base and records the existing-upgrade audit. `review.py` imports through native s&box and runs offline Riverdale play. Matching before/after cameras copy gameplay effects, lock exposure and use 180 ordinary streaming frames per view without extra lights or forced texture residency. The same check captures the approved reel from its saved scene installation. `verify.py` checks source guards, exact triangle removal, unchanged records and ModelDoc, real map/player/error-model evidence and editor state restoration. Evidence: `output/riverdale/shared-cone-v1/`.

Staged pending approval; the public map still uses the original cone.
