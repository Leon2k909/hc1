# Pump tower safety railing review

Continuous smooth curved handrails, 32 uprights, bevelled base plates with four
washer/hex anchors each, weld collars and a low rolled toe board. Radius and
handrail heights follow the original tower guardrail. The existing lightly
chipped Riverdale safety-yellow finish is reused with Sewage metal hardware.

Targeted splice removes exactly 9,472 old railing faces and retains all 7,928
other faces of the approved vent-free tower base with identical positions, UVs
and normals. The approved vent housing group stays separate and unchanged.
Original tower physics is retained. New railing: 54,016 triangles, render only.

Both models compiled through native MCP and matched screenshots were checked.
Captures: `output/sewage/tower-rails-v1/before.png` and `after.png`, also copied
to the current chat preview folder. Camera is on the inside of the upper deck,
looking at the outer railing away from the vent housings.

Approved and installed in Sewage on 2026-11-04; saved disk references verified.
`install.cs.txt` checks the source
SHA-256 and expected renderer model, adds one railing group, updates the tower
renderer, saves only Sewage and verifies disk references. The old railing remains
available in both the original tower asset and the approved vent-free tower base.
No whole-map rebuild and no scene lighting changes.
