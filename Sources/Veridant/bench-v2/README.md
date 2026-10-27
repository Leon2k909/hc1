# Veridant promenade bench

The four existing 72-inch benches retain their poses, 18-inch seat height and
original 72 x 18 x 18-inch collision boxes. Individual teak slats now have
5 mm eased edges, sanded ends, mild bowing, a few small edge losses, separate
end-grain mapping and eight flush six-lobed stainless fixings per bench.
The cast supports have rounded arrises and a few small knocks. Steel plates,
downturned anchor ears, bolts and rubber bearing pads join the seat to them.

`Tools/veridant_bench.py` supplies the geometry and materials;
`veridant_parts.bench()` delegates to it. `veridant_map.configure()` preserves
the `vr_bench_` material overrides. Source regeneration therefore retains the
new design. Render geometry is 9,080 triangles per bench, 36,320 for all four.
Frame-rate impact has not been benchmarked.

## Texture sources

The selected albedo textures were generated with the **built-in image_gen tool**
and copied into this project. They are generated photographic-style textures,
not measured scans. Original PNGs are preserved unchanged:

- [Teak albedo](teak-albedo-generated-v1.png)
- [Concrete albedo](concrete-albedo-generated-v1.png)
- [Exact prompts and generation method](imagegen-prompts.json)

The working albedos are resampled into power-of-two GPU sizes, 1024x2048 for
teak and 1024x1024 for concrete, in `Assets/materials/veridant/bench-v2/`.
The original generated PNGs above remain unchanged. Fine-detail normal and roughness maps
are derived by the material writer; broad colour variation is excluded from
relief. Four distinct strips of the teak image cover the four slats, with no
image wrap within a visible board. Material tint controls the in-map finish.

## Publication and verification

`stage-v1` removed precisely 288 old bench triangles from the actual active
`chair-v2/dress-base.obj` import and added one dedicated `bench-v2/benches.obj`
render import plus eight material mappings. All retained OBJ bytes and index
allocations were preserved. The model's complete physics suffix was unchanged.

The first native image check showed overly uniform procedural materials.
`stage-v5` replaces only the bench's own mesh and materials with the selected
generated albedos and corrected, nonrepeating UVs. A concurrent cases-v4 update
changed the shared dressing base and model document; that update is preserved.
The refinement checks that old bench faces remain absent and restricts all
writes to the bench's own resource directories. Stages v2 and v3 stopped at
guards for concurrent prop edits before publishing any files.

Both publication passes use `import.cs.txt` through native `run_csharp`, with
guarded atomic source replacement and asset registration in the existing editor.
No scene document is edited. Capture scripts restore camera, exposure, objects,
selected scene and play state after every capture.

The initial full compile call timed out. Its generated files and editor status
were inspected before any follow-up. Subsequent incremental native compilation
confirmed all eight materials and the model successfully.

The generated images had non-power-of-two dimensions, which the native normal
map mip compiler rejected in stage-v4. Stage-v5 corrects all working texture
dimensions before deriving normal/roughness maps.

Final evidence is in `output/veridant/bench-v2/validation.json`, with the
publication manifest in `stage-v5/manifest.json`. Native overall and end-detail
screenshots are in `output/veridant/quality/bench-v2-final/`. Before/after views
use matched cameras, resolution and exposure. `Tools/veridant_check_bench.py`
checks publication hashes, all four original collision shapes, the physics
suffix, source hooks, compile receipts and capture restoration.
Other authorised work saved the scene between baseline and final captures;
the task did not write that document, and each native capture independently
verifies its entry scene hash is retained on exit.
