# Orion deck generator: separate model review

This proposal replaces the plain generator box beside the accepted cable reel on
Orion's launch deck, at plan `(265,1335,240)`, world `(1335,-265,240)`.
It is not installed. No game asset, scene, material, collision or generator is
changed. The accepted reel and cleared stairwell remain as installed.

`before.json` contains all 12 triangles, original UVs and split normals extracted
from the current saved `models/maps/orion/orion_launch_deck.obj`. It selects only
the eight exact generator corners, excluding the adjacent pipes. The enabled
Launch Deck renderer in the saved Orion scene references that import at the
identity transform. `Tools/orion_map.py` explicitly identifies the box as a
generator. `provenance.json` records its source hash, placement and dimensions.
The recent native screenshot at
`output/orion-cable-reel-installed-20261030/installed-reel-and-clear-stairs.png`
shows the original box immediately beside the accepted reel. The editor was
closed for this proposal; no new native capture or engine import was performed.

The replacement is an enclosed standby generating set with a welded skid and
actual open fork pockets, a belly tank, vibration isolators, separate gasketed
service doors, hinges, handles, captive fasteners, open inclined intake louvres,
a radiator fan and open wire guard, controller with a private LCD graphic,
physical buttons and emergency stop, fuel cap, folded rain roof, open lifting
eyes, exhaust silencer, straps, seams and hinged rain flap. All geometry stays
within the original 130 by 70 by 70 inch envelope. Fictional Orion equipment
markings and all PBR textures are authored privately for this proposal.

Pictures are offline Blender Cycles CPU renders of real geometry with identical
camera, scale, floor, lights, exposure and AgX view transform. The baseline uses
its saved materials; its constant roughness is explicitly preserved at 0.55
where the shared converter would otherwise default to 0.7. These renders do
not establish native engine material or performance results.

Run from the canonical checkout:

```powershell
rtk proxy python Sources/Orion/generator-trial-v1/prepare.py
rtk proxy python Sources/Orion/generator-trial-v1/run_render.py --validate-only
rtk proxy python Sources/Orion/generator-trial-v1/run_render.py
rtk proxy python Sources/Orion/generator-trial-v1/verify_export.py
```

One owned hidden Blender process runs at idle priority on four logical CPUs,
renders on CPU and exits on completion. Existing interactive processes remain
alone. Geometry verification rejects nonfinite coordinates, zero-area triangles
and vertices outside the original envelope. `source-guard.json` fingerprints
669 existing files covering Orion's scene, source model and materials, the
accepted reel, generator hooks and the two earlier Ares proposals.

Outputs: `generator_review.blend` (editable parts and packed textures),
`generator_after.glb` (one mesh with embedded images), OBJ/MTL and `textures/`.
The validated export has 51,658 triangles, 12 materials and 21 embedded images,
with its pivot at the footprint centre on the floor. Both rendered image hashes
and all 669 protected source hashes passed the final verification.
Blender/OBJ uses metres, +Z up and front -Y; glTF has its standard +Y-up
conversion. Review pictures and validation reports are in
`output/asset-improvement-20261030/orion-generator/`.
Native materials/import, LODs, collision policy and performance checks belong
to a later approved integration step.
