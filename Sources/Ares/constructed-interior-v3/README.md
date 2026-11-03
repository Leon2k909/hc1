# Constructed Ares interior — v3 native review

The follow-up generated floor finish is documented in `Sources/Ares/floor-finish-v4/README.md`.
Use its combined installation plan: it retains this construction pass and supersedes the old floor materials.

This revision responds to the rejected texture-only v2 trial. It is a new physical construction pass using the
approved `Sources/Ares/interior-concept-20261103/concept-v1.png` as its visual target. Public map assets and the
user's saved scene remain unchanged pending review. Branch: `codex/ares-constructed-interior-v3`.

## Actual geometry

- Four deeper curved pressure frames and six wall haunches, with inset red service plates, captive fasteners,
  substantial shoes and mounted practical lamps.
- Enclosed ceiling cassettes, I-section purlins, large segmented HVAC ducts with clamp rings/hangers, open cable
  ladders with individual cable runs, and manufactured light housings at the original 24 light positions.
- Modular formed gallery/bridge fascias, curved bolted ring panels, underside lamps, column collars and knee braces.
- Reactor base plinth, segmented vented skirting, multi-layer chamber end rings, sealed label collar, removable
  face plates/handles, glazing stanchions, flange pairs, insulated service risers and upper hood panels.
- Four cylindrical process-pump bodies with dished ends, cast covers, saddles, bolted end plates, service screens,
  swept feeds and sealed core nozzles. Their existing 72x56x64 pump collision boxes are retained.
- Smaller eased floor plates keep their tops at z0. Stair nosings retain warnings at the first/last steps while
  middle treads use dark coated metal. Door thresholds and existing markings are retained.

All prior ModelDoc imports and collision shapes remain. The larger gallery supports add 28 collision boxes;
the new lower reactor skirt adds one convex hull. Riser details at gallery player height stay inside the original
170-inch core collision radius. Floors, stairs, gallery routes, doors and cover positions are preserved.

## Materials and light

Built-in ImageGen produced the new access-panel albedo and matching roughness map. Exact raw files:

- `Sources/Ares/constructed-interior-v3/generated/skin-color-v1.png`
- `Sources/Ares/constructed-interior-v3/generated/skin-rough-v1.png`
- Full prompts: `skin-prompt.txt`, `skin-rough-prompt.txt`; provenance: `asset_provenance.json`.

The raw 1774x887 outputs are retained. Native `Sandbox.Bitmap.Resize` prepares 2048x1024 engine copies at
`Assets/materials/ares/constructed-v3/skin_color.png` and `skin_rough.png`. Curved panel faces get a local UV layout
so edge wear reaches their actual edges. Matching bevels, joints and fasteners are geometry; a quiet existing
powder-coat normal supplies fine grain. These generated maps are visual approximations, not measured scans.
The useful generated v2 wall/floor maps remain dependencies; their v2 installation plan is superseded.

The existing 24 Hall lights use RGB3.57, 5000K. Four central work lights cast shadows. Hall light contribution is
Diffuse+Transmissive: disabling the point-light specular contribution removes the white dots reflected in the
observation glass. Existing reflection resources still supply surface reflections. The saved bounced-light volume
uses runtime intensity1.8 and contrast0.85. Other lights, origins/radii, exposure, grading and probe textures remain.
No cubemap or GI bake is invoked; no lights or game scripts are added.

## Review and installation

`output/ares/constructed-interior-v3/` holds immutable input snapshots, hashes, staged assets and evidence.
Final raw native captures are `hero-review.png`, `overview-review.png`, `floor-review.png`, and `pump-review.png`.
The camera warms up streaming textures, marks them used at full resolution, and enables native anti-aliasing.
Captures are never composited or relit outside the engine. Temporary scenes are destroyed in `finally`.

`build.py` migrates only the scoped hall geometry and reactor mechanical body, preserving original plasma, glass,
signs, lights and stack shapes. `collision.py` adds bounded support/skirt collision without replacing existing shapes.
`import.cs.txt` publishes private review assets through the existing editor; unchanged hashes skip redundant writes.
`compile.py` waits for real native asset compile results and inspects timed-out operations before continuing.

`prepare_install.py` stages nine public mesh/ModelDoc/generator files and exact native component mutation arguments
without applying them. The future generator uses `Tools/ares_constructed.py`, with narrow existing map hooks,
and is checked against the reviewed reactor by `verify_source.py`. Source/public hashes must still match at install.
`check_navigation.cs.txt` compares all 91 pairs of 14 hall floor/gallery points in disposable native scenes.
All 91 are Complete in both the current map and the trial, with no changed path statuses. Native scenes preserve
the user's scene/dirty/play state. The staged generator reproduces all 100,246 reviewed reactor faces exactly;
its four pump boxes, four reactor hulls and 28 support boxes pass the source check. Riser details at gallery
player height remain inside the original core radius. Native materials and both models compile successfully.

After visual approval: guarded `install.cs.txt`; compile public hall/reactor; apply the 25 native `set_component`
calls from `install-plan.json`; save_scene; verify native installed captures and compile state. The generator does
not own the saved baked-light resources: retain runtime GI settings when merging any future scene regeneration.
Full gameplay frame time has not been benchmarked. No hidden editor, browser, development server or helper is kept.
