# Orion launch-mount service pedestals — review, 2026-11-05

Substantial rebuild of the four plain dark28×20×40-inch equipment boxes beneath the accepted cage lights, centred
at plan(524,2630), (864,2630), (864,2970), (524,2970), basez230. Flanged mounting plinth, folded sheet-metal body,
open front aperture, recessed gasket and separate service door, hinges, connected pull handle, lock bezel,
weather-blade vents/hood, side terminal cover and capped glands, mounting and cover screws.

Only the existing `oa_dark` and `oa_steel` materials are used. No new textures, external assets or lights. Footprint
and roof mounting plane remain28×20 inches andz270; small corner cover screws rise0.11 inches above the roof plane,
outside the unchanged cage-light base. All accepted cage lights, original point-light declarations and collision
remain unchanged. The other previously approved props are retained.

**Accepted and installed.** Public pad and generator now use all four new service pedestals. The user requested
deleting old assets: six `before.*` files were removed from game Assets, with receipt and rollback archive under
`review/`. The accepted cage lights, original collision and scene stayed unchanged. `pedestal.py` freezes the old box and generates
the new render-only body. `build.py` requires48 original faces to match, adds7,800 new faces, and preserves112,630
unrelated pad faces exactly. The full physics suffix, hull sources and saved scene remain unchanged. On acceptance,
narrow-splice only these boxes and replace the equipment-box draw in `orion_parts.launch_mount`, leaving its four
work-lamp calls untouched. Do not rebuild the whole map.

Both matched comparison samples include the same accepted cage light. Native `capture.cs.txt` uses identical
camera, lighting, exposure, floor and framing. `context.cs.txt` renders saved Orion visual roots in an isolated
scene with only the candidate pad model substituted. Temporary scenes destroyed; no play or document control.
`verify.py` checks exact retained faces, hashes, bounds, finite data, triangle area and unchanged physics/scene.
Sources, evidence and snapshots live in local `review/` on C:. Native calls use `direct.py` to avoid persistent
connection timeouts. No FPS benchmark or performance claim.
