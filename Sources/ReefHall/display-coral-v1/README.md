# Reef Hall display sea fan — review candidate

**Rejected by the user (2026-11-04): the original/left version is preferred.** Keep the original
coral active. Do not install this candidate. The accepted pedestal remains installed. Preview assets
are retained as historical work; no deletion was requested with this rejection.

The selected purple colony sits inside the small southwest rotunda aquarium, beside the player walkway
and bench. It is viewed through the glass at close range. Existing coral/reef-rock model and source
filenames and upgrade notes were checked first; no suitable upgraded colony was found.

Rebuilt straight, square-section, open-ended branches as a curved fan with seven shared-root trunks,
smaller lateral forks, smooth tapered circular sections, rounded terminal growth, a holdfast and small
pale polyp crowns on the upper branches. Existing purple/cream coral materials are reused unchanged.
No external assets, new textures, lighting or shaders. Each LOD fits the exact original occupied
envelope: plan `(-403.939,-155.842,32.812)` to `(-386.707,-151.520,44.132)`.

**Preview only; original coral remains active.** Standalone renderer-only resource
`models/props/reefhall/display_coral_v1/coral.vmdl`: LODs 11,768 / 3,500 / 1,628 triangles,
initial thresholds 0/20/55. World origin `-153.681,395.323,32.812`, scale1, yaw0. No collider or
fauna changes. The newly approved aquarium pedestal is installed and appears in both review columns.

`audit_baseline.py` extracts the exact 288 original purple-colony faces from the current rotunda tank
mesh by material and the selected aquarium's bounds, preserving its source hash and occupied bounds.
`build.py` stages models outside Assets and refuses a changed source. The private whole-tank preview
omits only those 288 face lines; all other original lines and material/UV/normal records are identical.
The private ModelDoc changes only the render-file reference. Public tank sources and saved scene remain
unchanged. The original mesh forms the before view; this is not a regenerated approximation.

`import.cs.txt` imports through native `run_csharp` after path/hash guards. Both resources compile.
`capture.cs.txt` uses an isolated copy of the room's visual roots, with identical native cameras and
aquarium lights in each variant. Top view is at player eye height, lower view is through the glass
beside the colony. No additional lights or fish/gameplay scripts. All three LODs are captured. The
isolated scene is destroyed finally. `compose.py` only resizes matching images and adds labels.

`verify.py` checks source/import hashes, exact scope, finite attributes, triangle areas, winding,
references, original occupied envelope, compilation and available native LOD receipts. All exported
triangles agree with their normals. Evidence: `output/reefhall/display-coral-v1/`. No live match or
frame-time benchmark is claimed.

After approval, replace only this colony and add a source hook while consuming the same original
random stream and retaining its original `fit_obstacle` result. Check the fitted mesh against that
original avoidance volume before integrating; matching its AABB alone does not prove that fit.
Keep every other coral/rock, sand,
glass, fish avoidance volume and the installed pedestal. Do not regenerate the whole map.
