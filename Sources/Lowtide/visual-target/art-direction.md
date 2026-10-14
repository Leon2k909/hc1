# Lowtide environment target

The generated canal paintover is a visual target, not an in-engine screenshot.

Keep the existing Speicherstadt warehouse architecture and playable low-tide
layout. Use muted fired clay, soot-black iron, oxidized copper and dark estuary
silt. Add construction detail at believable sizes: socketed drainpipes,
wall clamps, masonry ties, quay drains and rope fittings. Wear should follow
water, building bases and fittings rather than cover every surface uniformly.

Keep shadows readable for multiplayer. Use restrained warm daylight and cool
sky fill, damp patches rather than mirror-wet streets, and local reflections
on water. Avoid bloom, depth of field and heavy colour grading.

Current implementation: world-space masonry weathering and moisture, varied
paving dampness, generated silt material with continuous bank wetness, finer
water ripples, additive drainage / anchoring / quay details, and a dedicated
lighting profile. Existing collision and gameplay objects are retained.

The marine pass replaces the lighter's flat hull with rounded corners, a turned
rim, internal frames, mooring cleats and hollow tyre fenders. Its generated
marine enamel has matching roughness and restrained surface relief. Low stones
break up the banks, with clearance around stair and ladder landings. The water's
diffuse contribution is lower, allowing reflected colours to read more clearly.
Generated granite now replaces the quay stone, with profiled sills, beveled
coping and individual radial bricks around the prominent window arches. The
tidal-bank pass uses darker damp sediment and irregular clusters of partly
buried granite along the waterline. A narrow cap closes a hairline gap above
the old high-tide brick strip. A generated slate scan now replaces the low
resolution roof texture. The quay and yard sheds have open half-round gutters,
rolled lips, stop ends, brackets and downpipes reaching the eaves.

Canal water has camera-dependent planar reflections at half resolution, capped
at 960 pixels wide. The capture excludes water and first-person models, draws
the surface before the regular transparent pass, and releases its temporary
render target. Orthographic cameras, cameras below the plane and cameras that
already exclude water retain their existing behavior. Harbour water and bank
pools keep their cubemaps because they lie at different elevations.
The reflection is also detached when the canal's bounds leave the camera
frustum, then reattached when the canal becomes visible again.

Validation: game and editor projects build without errors. The current scoped
audit in `output/lowtide/quality-pass/current-scope-checks.txt` confirms retention
of original gameplay roots, navigation, world renderer/collider declarations,
and material-only roof, glazing, concrete and ceiling remaps. The historical strict audit and its original
hash snapshot are preserved; it now fails because concurrent work changed the
two dressing OBJ files and the sealed-window pass changed architectural UVs. It must not be cited as a current unchanged-mesh check.
The drainage and luminaire detail mesh is 61,316 triangles, the marine mesh is 98,627 triangles, and the masonry mesh is
131,584 triangles, all without physics shapes. The two new quay probes capture
on enable in the saved map. Runtime preview checks cover reflection attachment,
offscreen removal and visible reattachment, orthographic transitions, disable
cleanup, preserving authored exclusions and re-enabling.

Capture method: use the existing editor viewport through the native camera
screenshot tool, restoring its position afterwards. The old isolated-scene /
SceneRenderingWidget method is retired: later captures produced render-target
registration errors and editor exits. Do not reuse it or its benchmark loop.
The live-prefixed pictures below are historical evidence from that earlier
workflow; older non-live captures are darker and must not guide illumination.
Current verification uses the normal viewport captures described at the end
of this document.
A coarse indirect-light experiment was not added to the production scene.

The frame enamel source was generated with the built-in image tool; its prompt
is saved in `frame-enamel-imagegen.json`. The neutral scan has derived roughness
and shallow relief, with separate green and cream material tints. This frame
finish is validated in `live-frame-enamel.png`. The built-in image tool also
generated `slate-source.png`; its full prompt is in `slate-imagegen.json`.

The engine reported a missing generated default normal texture used by the old
glass. Recompiling the original material did not remove its square reflection
pattern. Lowtide now has a dedicated thin-glass material with a valid, subtly
wavy project normal map and restrained blur. `live-glass-test.png` validates
interior sightlines; `live-canal-window-finish.png` uses the saved production
remap. All compiled texture dependencies for the two frame paints, new slate
and new glazing were checked on disk in `new-material-dependencies.txt`.

Live editor/game performance snapshots flagged CPU render cost, point-light
shadows and roughly ten thousand draw calls. Other game and editor work was
active, and one saved sample includes a hotload hitch. These snapshots are
diagnostic leads, not a controlled benchmark or evidence of a measured speedup.

The result is still short of the reference. Architectural repetition, window
and facade variation, contact lighting and the wider quay/interior presentation
need further review. This pass does not claim a measured frame-rate improvement
or a finished AAA environment.

The warehouse interior uses generated troweled concrete at two-metre scale,
with shallow aggregate normals and local roughness variation. Long pine boards
replace the old brick-like ceiling pattern at 24 cm board width. Eighteen spun
enamel pendant shades now sit at the existing warehouse light positions. Their
rolled rims, separate cream interiors, bulbs, hanging rods and ceiling mounts
are part of the existing visual detail mesh. Bulb geometry leaves the light
emitter clear underneath. Original light positions and scene components remain.
The built-in image tool sources and complete prompts are concrete-source.png /
concrete-imagegen.json and ceiling-boards-source.png / ceiling-imagegen.json.
interior-target.png is a generated art reference, not a game capture.

The interior indirect-light bake and directional-light variants are isolated
QA experiments only. Neither was applied to the production scene: the previews
did not establish enough visual benefit. Contact lighting needs further work.
The nine visible boards in the generated ceiling source cover 2.16 metres
across; UV scaling preserves their intended 24 cm width.

Final production interior capture: live-interior-finish.png. Its diagnostics
confirm 24 point lights, no spot lights, zero material errors, and unobstructed
downward rays from all 18 warehouse emitters. Interior scope checks pass.
Pendant close-up: live-interior-pendant-final.png, with 32-sided shade curves.

Sealed architectural windows now use view-dependent warehouse interiors behind
the glass reflection. The built-in image tool generated a four-cell room atlas;
the original is warehouse-room-atlas.png and the complete prompt and mode are
saved in warehouse-room-imagegen.json. The runtime atlas is 2048 square. Samples
stay inset from the cell seams. Physical room proportions preserve the square
atlas aspect, and the shader accounts for the OBJ importer's V flip. Final
interior brightness is 0.16, with depth 32 scaled by window width. The shader
intersects room walls as the view moves, with dim side walls and floors.

The patch changes UV records for 886 sealed windows across the east, west and
backdrop architecture, plus their material remap. Vertex positions, normals,
faces, non-window UVs and all collision declarations are preserved. Playable
glazing and crane cab materials are excluded. window-scope-checks.py verifies
this against the preserved pre-patch files, checks idempotence, and checks all
six compiled texture dependencies. This adds no geometry, lights or scene objects.
The room shader adds texture sampling work; no performance improvement is claimed.
The generator applies the same UV convention only to those three model names.

Room orientation, parallax and exposure were inspected with frontal and oblique
engine captures. The full canal capture is live-canal-interior-windows.png.
Earlier front/v2 previews are rejected iterations with inverted or stretched
room contents, not representative of the saved material.

Warehouse facade weathering now follows the actual architecture. A numerical
4096 x 2048 RGB mask bakes contact occlusion, rain deposits and sparse lime
deposits for 316 sills, floor courses and pilaster edges across eight elevations.
It is shader data generated from the canonical layout, not an AI colour texture.
Only the two main brick materials opt in, and world/normal bounds exclude
interior walls, other buildings and projecting oriels. The mask adds one sampled
texture to those facades and no geometry, collision, lights or scene objects.
The two buildings have different runoff patterns. facade-checks.py verifies
sill registration, no contact term above the sills, material scope and dependency
integrity. All eight materials sharing the brick shader compile successfully.
The close-up is live-facade-wear-close.png. This improves architectural contact;
it does not replace scene-wide indirect lighting.

Water now uses a 48-inch ripple scale, strength 0.8 and roughness 0.10. Its
normal-incidence reflectance is 0.02037 for the air/water interface. The planar
reflection offset is derived from the reflected ray change projected into the
camera view, including aspect correction; it no longer treats world XY as
screen XY. Existing per-pixel filtering carries unresolved wave energy into
roughness. Shallow depth absorption and the reflection capture lifecycle remain.
live-command-ripple-camera.png verifies the near-water view and passes capture
attachment, offscreen removal/reattachment, orthographic transition, disable
cleanup, preservation of authored exclusions and re-enable.
The angled water view is live-ripple-projection-oblique.png. These close views
also expose remaining weaknesses: flat bank silhouettes, coarse angular stones,
uniform sediment colour and coarse mooring timber. These need another art pass.
The new facade mask and water changes have not been benchmarked in a controlled
game session; no frame-rate improvement is claimed.

The bank revision uses a second generated cohesive silt texture for lower, wetter
terrain, blended continuously with the existing dry surface. Its original bitmap
is estuary-wet-silt-source.png; wet-silt-imagegen.json records the full built-in
image tool prompt and mode. Runtime colour and shallow normal maps are 2048 square.
The wet scan covers one metre, with texture scale and normal decoding matched to
the engine's UV convention. The bank shader adds two sampled textures.

There are 1,056 partly buried granite and clay fragments. Their silhouettes have
worn fractures and broad faces, with smooth shading, restrained relief and
elevation-dependent darkening and roughness. Faces fully below the bank are omitted.
The final material tints are .20/.22/.20 for granite and .30/.24/.18 for clay;
roughness ranges from .78 dry to .36 wet. Initial pale-stone previews are rejected.
The two visual meshes add 78,070 triangles compared with the pre-bank snapshots.
No performance improvement is claimed; a controlled benchmark is still needed.

bank-scope-checks.py preserves the barge, drains, gutters, ropes and luminaires
and checks finite, correctly oriented smooth normals and staged mesh identity.
Stones retain at least 45 inches of clearance from landing centres and project
at most 5.21 inches above the bank. bank-contact-checks.py samples the actual
6,720-triangle Fleet terrain: no floating stones, fully buried stones or exposed
cut edges. All four materials compile and all 16 compiled texture references
resolve. Final close and oblique views are live-bank-final-close.png and
live-bank-final-oblique.png. The three final captures report 15 valid renderers,
zero material/model errors and 18 clear emitters; no QA scene remains.
The saved gameplay layout, navigation and collision declarations pass the current
scope checks. The following timber and tyre pass addresses the coarse canal
props. Facade repetition, bank surface detail and contact lighting still need
work; the overall environment is not yet at the requested target.

Six mooring clusters now contain 18 smoothly shaded, slightly irregular timber
posts. Each has vertical grain, a separate crosscut end, a worn top bevel and
formed iron retaining straps with overlapping ends and rivets. The built-in
image tool generated pile-timber-source.png and pile-end-source.png; full prompts
and generation mode are saved in pile-timber-imagegen.json and
pile-end-imagegen.json. Shallow derived normals preserve the wood grain scale.
The shader darkens damp lower timber. Final tints are .24/.23/.21 on the sides
and .30/.28/.24 on the ends; the pale first preview is rejected.

The pile patch removes 612 old triangles and adds 14,016, a net increase of
13,404. It preserves all unrelated Fleet faces, UVs and normals, all six original
pile collision boxes, and every model physics declaration. pile-scope-checks.json
records the geometry checks. pile-render-checks.json records three final engine
views, 15 valid renderers, zero material/model errors, 18 clear emitters and all
11 resolved compiled texture dependencies. The close views are live-piles-final
and live-piles-end. The Fleet hashes in that report are the validated pile
snapshot immediately before the subsequent tyre patch.

Four discarded tyres now have hollow centres, shaped inner liners, bead lips,
rounded sidewalls and three rows of chamfered tread blocks. Existing project
rubber maps provide restrained grain and roughness. The formerly overlapping
pair is separated by moving one decorative tyre seven inches along the bank.
All four remain partly buried in the actual triangulated terrain. The patch
removes 168 old triangles and adds 28,512, a net increase of 28,344. It changes
no scene objects, gameplay layout, navigation or collision. tyre-scope-checks.json
checks every retained face/UV/normal, winding, open centres and ground contact.
tyre-render-checks.json records the final material dependencies and engine views.
No controlled performance benchmark has been performed for these additions.

The following stone-surface correction supersedes the original bank material
values and cropped masonry textures. Those crops pinched around spherical UVs,
producing visible swirls on the tops of stones. Two continuous mineral scans now
provide granite and fired-clay colour, with shallow derived normals. The original
bitmaps are tidal-granite-source.png and tidal-clay-source.png. Their complete
built-in image-generation prompts and mode are in tidal-granite-imagegen.json
and tidal-clay-imagegen.json. Runtime colour and normal maps are 2048 square.

The shader projects from three world-space directions at 50 cm per granite tile
and 30 cm per clay tile. Surface-normal slopes are reoriented into the geometric
tangent plane; flat input normals retain the authored smooth shape. Legacy mesh
UVs remain but are not sampled by this shader. Granite tint is .30/.32/.30 with
roughness .82 dry to .52 wet; clay tint is .34/.30/.25 with roughness .88 to .66.
This removes the former polished highlights from porous clay fragments. Normal
strength is .6. The shader samples colour and normal on each of three planes.

stone-surface-checks.json verifies all 42 geometry and scene files are unchanged,
both materials and the shader compiled, all five compiled texture references
resolve, and three final engine views have no model/material errors. All 18
warehouse emitters remain clear, and no temporary QA scene remains. The matching
before/after views are live-stone-surfaces-before.png and
live-stone-surfaces-final-low.png; the player-height view is
live-stone-surfaces-final-player.png. This material pass adds no geometry.

Read-only inspection confirmed Ultra texture/shadow quality, 8x MSAA, High AO/SSR
and disabled upscaling. The saved map already has AO at intensity .8, radius 28,
with directional contact shadows enabled. The remaining flat illumination
therefore needs map lighting work, rather than a presumed low user quality
setting. No render preference was changed. Indirect illumination, scene-scale
contact, architectural variation and a controlled performance benchmark remain.

Warehouse concrete now samples a static contact-occlusion atlas baked in Blender
from the current east/west architecture and dressing meshes. The 768-square atlas
contains a separate 384 x 768 cell per warehouse, with 24-inch and 96-inch ray
ranges in red and green. Tools/lowtide_floor_contact.py uses 96 cosine-weighted
rays per texel and records source hashes. Re-bake it if static cargo, stairs or
columns move. The shader applies it only to upward-facing concrete at floor z=0
within the two warehouse bounds; exterior and vertical concrete remain unmasked.
It affects ambient occlusion, preserving the generated concrete colour and direct
lighting. This adds one conditional texture sample and no geometry or lights.

The compiled material initially omitted the new shader input. It was recompiled
after the shader schema refreshed; floor-contact-engine-checks.json confirms the
768-square texture is actually bound. Earlier original-lights, registered and
column-debug captures predate that fix and are rejected. The column-before
capture also used an ineffective override and is not a valid baseline. The valid
comparisons are column-disabled / column-bound and cargo-disabled / cargo-final.
The broad hall view is live-floor-contact-hall-bound.png; the other warehouse is
live-floor-contact-west-final.png. The benefit is subtle and limited to contact
regions; it does not solve the room-wide illumination.

floor-contact-checks.json verifies all 42 geometry/scene files remain unchanged,
source/baked registration at known contacts, all four compiled texture references,
the bound runtime texture, four clean engine captures and preview cleanup.
The reduced-sky, pendant and reused-GI experiments remain previews. No change to
the saved sun, point lights, exposure or GI volumes was made in this pass.

Warehouse lighting now has a separate, applied pass. Eighteen pendant emitters
use downward shadowed spots (55/30 degree cones, 85% of their original light
colour). The original point components remain disabled to preserve references.
Two native DDGI bakes cover the actual receiving floor, inner walls and ceiling:
20 x 10 x 6 probes per warehouse, density 12, 24-inch outward blending. Earlier
inset volumes missed those surfaces and are rejected. Native direct-plus-one-
bounce lighting uses runtime intensity 4 and contrast .85 for readable corners.
The sun, sky fill, exposure, outdoor lights and all geometry are unchanged.

Sources/Lowtide/lighting contains the engine-exported lighting schema and source
hashes. Tools/lowtide_lighting.py preserves it in the canonical scene generator.
The six native .vtex_c files total 787608 bytes and have a narrow Git ignore
exception; existing LFS rules cover them. Re-bake after static warehouse geometry,
fixture or daylight changes. The exchange-only baker is preserved as
output/lowtide/quality-pass/bake-lowtide-gi.cs; it never owns the user's scene.

Saved-scene captures live-warehouse-lighting-saved-east, -west, -mezzanine and
-doorway have 15 valid renderers and no material/model errors. The native editor
loads both volumes with six valid textures. warehouse-lighting-checks.json
confirms unchanged geometry, all unrelated scene/gameplay data, canonical patch
idempotence and versionable bake assets. The inactive clean Lowtide tab was
reloaded after saving; the user's running game was preserved. No QA scene remains.
The original floor-contact report remains historical; its scene hash predates
this intentional lighting change. A controlled performance comparison and the
broader architectural/exterior art pass remain outstanding. This is not the
completed AAA target.

The following passes are saved after that lighting baseline. Static shadow
caching marks nine fixed world meshes and 24 local lamp objects static; glass,
water, trees, gameplay objects and the weather-controlled sun stay dynamic.
Generated canal biofilm adds irregular wet mineral and algae coverage to the
exterior masonry, with masks excluding warehouse interiors. The raised straight
tidal seam was then removed with a scoped edit: twelve vertex moves, four UV
adjustments and four finish-cap triangles removed. Native compilation and east
and west viewport checks passed. The normal viewport interior check is valid;
the older black temporary-scene capture is rejected.

The perimeter pass closes 42 missing building wall sections across both sides.
Two quay-facing warehouse ends gain 30 sealed windows, masonry sills, corbelled
cornices and round loft vents, replacing the conspicuous sky gaps beneath their
roofs. The northern row's side/back walls are now closed as well.
Tools/lowtide_perimeter.py appends 10,634 visual triangles to Harbour Details
and is called by the finish generator. All 61,312 previous finish triangles,
collision, other model sources and scene data are retained. The six additional
material remaps reuse existing masonry and sealed-window materials.

The installed perimeter check verifies unchanged original attributes and faces,
scope, collision and 2,300 samples through the former quay openings. The model
compiled natively with no model/material errors. Actual viewport captures show
the east and west quay ends and northern roof corners closed. Evidence and
before/after manifests live in output/lowtide/quality-pass/perimeter-*.
The camera restore helper preserves numeric transform components: Angles.ToString()
returns named fields and must not be fed to set_editor_camera's comma parser.

Use the existing native editor viewport for further visual checks. Temporary
offscreen scene capture/benchmark loops caused ResourceSystem.RegisterWeak and
render-target errors and must not be repeated. These passes preserve the saved
scene and restore the user's current view. Earlier strict whole-file hash reports
remain historical baselines: the tidal and perimeter manifests record the later
intentional changes. They do not certify the current hashes or a new lighting
bake. Repeated facade patterns, broad flat roof surfaces, overall composition
and controlled gameplay performance still need work; the AAA goal remains open.

The low sheds now have eight circular louvred vents, with recessed dark backing,
angled painted blades, cast frames and individually chamfered radial bricks.
Four curved metal ridge caps with lap joints cover the earlier square ridge
outline. The vent paint follows each half's green/cream frames. This gives the
blank gable triangles readable construction detail from the playable quay and
yard. Tools/lowtide_shed_details.py is included by the finish generator.

The accepted addition contains 14,784 triangles and no collision. All 71,946
previous finish triangles, other model sources, materials and scene data remain
unchanged. Finish now has 86,730 triangles. Native compilation reported no model
or material errors; installed scope checks and 384 opaque vent-backing samples
passed. Five reviewed native viewport views are shed-details-quay-east,
shed-details-quay-west, shed-details-yard-east, shed-details-elevated and
shed-details-vent-close. The final fresh console read was empty, and the saved
scene, play state and user's view were preserved. No controlled performance gain
is claimed.

A separate thin slate-course geometry experiment was rejected and completely
removed from production assets and the canonical build. Even after correcting
roof pitch, OBJ V-flip compensation and edge shading, it aliased from playable
ground views. Its root-level roof-*-after / roof-*-final and roof-relief-*
captures are experiments, not current accepted screenshots. The rejected source
is archived under output/lowtide/quality-pass/rejected-lowtide_roof_relief.py;
do not reapply it. Production retains the original generated slate surfaces.
The roof's broad material response remains an open art issue. Existing viewport
capture reapplies the requested camera immediately before rendering, since
navigation inertia can otherwise move it during the settling delay.

The normal editor viewport now renders the canal's planar reflection. The engine
copies the scene main camera's render hooks onto editor cameras, so the previous
viewport-only registration hid water without executing its replacement draw.
LowtideWaterReflections now registers on the correct command owner while retaining
the view camera for reflection projection and exclusion. Gameplay cameras keep
their original route; multiple perspective editor views use regular cubemap water
to avoid submitting several mirrors through one shared hook. No shader, material,
geometry or saved-scene changes were needed. Eight native lifecycle checks cover
registration, looking away/returning, disable, intentional exclusions and shared
view fallback. The corrected overview, bank and quay captures are water-*-fixed;
the scene stays clean and the user's view is restored. Compilation passed without
water diagnostics, and the global console was clear. This is editor verification;
controlled gameplay performance and the broader visual-quality goal remain open.

Roof material response now uses a dedicated slate shader rather than the masonry
weathering shader. The charcoal [.40,.44,.48] tint reduces the earlier pale-grey
appearance; metre-scale rain deposits follow the roof pitch and vary colour and
roughness. Stronger split-stone normals and shallow joint AO make the overlaps
read more clearly. The existing generated albedo and roughness source are retained,
and Tools/lowtide_roofs.py reproduces the new material and derived maps. This adds
no geometry and does not change models, collision, scene data or the lighting bake.
Five reviewed existing-viewport views cover both quays, the yard, canal and an
elevated roof detail. Shader/material compilation and loaded 2048px bindings pass;
the scoped checker protects 45 source files and verifies all six installed files.
The earlier geometric slate experiment remains rejected. The broader visual goal
and controlled gameplay performance are still open.

The four low sheds now receive architectural contact and rain deposits beneath
their real sills, cornices, corbels and downpipes, plus broken foundation splash
dirt. Tools/lowtide_shed_weathering.py reads the facade generator's opening layout
and writes a separate numerical 2048px atlas for 16 elevations and 32 sills. Tight
world bounds and outward normals keep it off warehouse interiors and floors.
All eight installed files match the staged manifest; 46 protected model, scene,
roof and original masonry-source files remain unchanged. Four native material
recompiles and loaded 2048px texture/strength checks passed after the interrupted
editor reload. Three reviewed normal viewport captures cover both quays and the
yard, with no new errors and the user's camera restored. The modest deposits
improve contact and breakup; they do not resolve the broader quality goal.
