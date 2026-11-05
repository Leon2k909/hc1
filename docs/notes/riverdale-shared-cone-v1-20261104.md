# Riverdale shared cone — staged review

Existing-upgrade audit found the approved Boxyard traffic_cone_v2 suitable for Riverdale's crude 14-sided cone. Reused the unchanged resource for one standing north-lane cone at plan (300,2433), without generating replacement geometry/materials. The private preview removes exactly 166 original triangles and preserves all other geometry, collision and scene data. Native actual-play before/after evidence and source validation are in `output/riverdale/shared-cone-v1/`; reproduction is in `Sources/Riverdale/shared-cone-v1/README.md`. Awaiting approval.

The preceding approved cable reel is now installed: exactly 300 old body/hub faces removed and one native-serialized shared Railhead resource inserted, with its 176 loose-cable faces and collision retained. `Tools/riverdale_shared_reel.py` and the targeted yard/map hooks preserve regeneration. The cone runtime review checks the saved reel too.
