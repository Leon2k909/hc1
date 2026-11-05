# Riverside T2 trailer hitch v1 - installed

Built 2026-11-04 after the approved rooftop TV aerial, then installed following explicit user approval.

The old hitch has two unrounded beams, a six-sided jack stub and a concrete box. This replacement rebuilds the entire assembly:
beveled A-frame rails at the same attachment points, cross brace and sloped gusset plate, smoothly shaded pressed coupler shell
with inner ball-seat cup and flanges, positive latch pivot, folding handle, retaining pin, fasteners, telescopic jack and crank,
steel foot, alternating oval-link safety chains, and a curved seven-pin electrical lead with connector contacts and clips.
Paint has restrained small corrosion flecks, color/roughness/normal maps; galvanized metal uses the aerial's zinc texture sources.

Five materials. LODs: 8,422 / 5,470 / 1,526 triangles. Links simplify with distance and become a continuous chain silhouette in
the far LOD. No physics or runtime component. Ground clearance at the foot is 0.08 in; jack crank top is 31.1 in. Original frame
cross-section and body attachment points remain; the coupler adds eight inches past the old beam tip. Engine placement
`1050,1030,0`, yaw zero; plan `-1030,1050,0`, at the hitch end of trailer T2.

Build: `rtk proxy python -u Sources/Riverside/trailer-hitch-v1/build.py`. Stages under
`output/riverside/trailer-hitch-v1/stage/Assets`; `--geometry-only` updates candidate geometry/materials without re-cutting the
legacy comparison. Import/compile with `review.py import`; capture with `review.py isolated` then `review.py context`.
Check `verify.py` and compose `compose.py`. `prepare_review.py` records the template transformations used to create the checked-in
native scripts and is not required for routine capture. Model winding and degenerate-triangle checks run at every LOD.

Resource `models/props/riverside/trailer_hitch_v1/hitch.vmdl`. Private background removes exactly 48 old triangles for T2's hitch
from the current lowland mesh, preserving the newly installed aerial. Public source OBJ, public ModelDoc and saved scene remain
hash-protected. Native captures use isolated worlds/scenes; no public mesh substitution, scene save, new lights or editor play
state changes. Matching cameras and lighting in each before/after pair; context exposure held at 3.5. Studio texture usage is
marked explicitly before capture so the metal maps can stream in.

Work, hashes, validation, eight resource compilation receipts and images: `output/riverside/trailer-hitch-v1/`.
Installation removed exactly 48 old triangles from the current public lowland OBJ and saved one native renderer under
`Trailer Hitches / T2 Trailer Hitch`. Public ModelDoc, every existing scene object, trailer collision and lights are preserved,
including concurrent door/camper improvements. The narrow generator hook emits only T2's hitch and preserves all random choices;
default trailers are unchanged. Native saved-map capture and compilation pass. Twelve legacy/private-background files were
archived outside Assets and deleted through the editor. See `installed.json`, `generator-check.json`, `native-install-compile.json`
and `installed-capture.json`. Do not rerun pre-install build/verify against the installed map: old-face guards will reject it.
