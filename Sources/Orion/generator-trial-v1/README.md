# Orion deck generator: reviewed model and approved installation

This proposal replaces the plain generator box beside the accepted cable reel on
Orion's launch deck, at plan `(265,1335,240)`, world `(1335,-265,240)`.
After the user approved the comparison, it was installed offline in the saved
Orion scene. The accepted reel and cleared stairwell remain as installed.

`before.json` contains all 12 triangles, original UVs and split normals extracted
from the pre-install saved `models/maps/orion/orion_launch_deck.obj`. It selects only
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

Historical preview commands from the original pre-install source revision.
The installed map now differs, so the original extraction and source guards
intentionally reject a new run against it:

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

## Approved offline installation

The saved scene now has one render-only `ORION standby generator` child at the
original position. Its model is
`models/props/orion/generator_v1/generator.vmdl`, with twelve private materials
under `materials/orion/generator_v1/` and four LODs: 51,658 / 20,662 / 7,232 /
2,324 triangles. The nearest LOD preserves the reviewed geometry, UVs and
normals with only the native axis/unit conversion. Native texture copies encode
the reviewed 0.5 normal-map strength; original texture sources remain untouched.

The installation removed exactly the old twelve box triangles from the packed
launch-deck OBJ and left its ModelDoc, including all collision, byte-identical.
It preserved every other existing scene node and property. The renderer schema was cloned
from the engine-serialized accepted reel, with new instance/component GUIDs and
a model GUID matching the new `.vmdl.meta`. `Tools/orion_generator.py` and the
`Tools/orion_map.py` hooks retain the replacement and its existing collision on
future builds.

`install_offline.py` publishes the guarded staged assets and saves backups.
`verify_install.py` passed installed hashes, scene-only insertion, exact removal
of the old faces, all material/texture paths, GUID consistency, reviewed vertex/
normal/UV preservation, and the generator against its actual pre-install
function. The generator changes only the six old render quads; every collision
box/hull and all other geometry/attributes stay identical. The other 666
protected review files are unchanged.

Temporary editor startup attempts exited before import. The user then requested
work without the editor; it was closed and the saved scene preferences restored.
No native compilation, native screenshot, live match or performance validation
was performed for this installation. Those checks remain pending the next
engine session. `provenance.json` and `export-validation.json` retain the original
preview status; installation status and evidence are in
`output/orion-generator-installed-20261030/offline-install.json` and
`install-verification.json`, beside original map/scene/script backups.

Other prop edits subsequently changed the shared map and scene. `verify_current.py`
checks the generator against that current version without reverting them: its
49 private files and exact scene instance still match, the old box faces remain
absent, its original collision remains intact, and both generator hooks remain.
Evidence: `current-integration-verification.json` in the installation output.
