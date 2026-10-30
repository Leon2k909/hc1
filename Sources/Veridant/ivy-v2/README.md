# Veridant hanging ivy replacement

Installed revision: `stage-v6` on 2026-10-27, in the canonical C: checkout.

The foliage VMDL now imports a private retained base and the new `ivy.obj`.
Exactly 188 original ivy triangles were removed; the remaining base OBJ bytes,
other foliage imports, shared atlas, saved scene and collision were preserved.
The new ivy has 26 assemblies, 70 shoots, 1,670 individually curved leaves and
196,720 triangles including explicit leaf backs and attached stems.

`Tools/veridant_ivy.py` generates the mesh and four dedicated materials.
`veridant_parts.ivy` delegates to it, and the map/material generators retain
its material overrides. Do not regenerate the complete foliage model to apply
an isolated revision: it contains other authored planting imports.

## Texture source

`leaf-source.png` is the unchanged transparent image from the built-in image
generation tool. The exact prompt and original path are in `provenance.json`.
`leaf-packed.png` contains the exact decoded RGBA texels, centered on a transparent
2048 square canvas by the native engine bitmap API. No texels were resampled or
retouched. The original non-power-of-two image could not use the engine's
alpha-weighted mip filter; the padded image compiles. The mesh UVs include the
padding transform. `texture-packing.json` records hashes and the byte-exact check.

## Validation and evidence

Private staging/evidence: `output/veridant/ivy-v2/` (keep logical C: paths even
though output is an offload junction).

- `stage-v6/installed-validation.json`: all 11 installed file hashes, retained
  base bytes, protected assets, OBJ indices/finite values/area/winding, and model
  import/physics checks passed. Zero inverted or degenerate faces.
- `compiled-v6-native/call_tools.json`: all four materials and foliage VMDL
  compiled successfully; editor code compile errors were zero.
- `live-v6-native/run_csharp.json`: all four materials were loaded without
  error, with valid 2048 square color textures on the three leaf materials.
- `captures/final-v6/ivy-closeup.png`: actual native rendering of the installed
  asset, supersampled at 3840x2160 and resolved to 1920x1080. This is a closeup,
  not an exposure-matched comparison. Effective GPU exposure is not measured.
- Capture restoration records verify the selected editor document, game state,
  cameras, tone, scene objects and dirty state were restored. The shared editor
  stayed on Collider; no Veridant scene save was needed for this asset update.

No gameplay performance benchmark or distant LOD assessment was performed.

To recheck the installed asset without regeneration:

```powershell
rtk proxy python -X utf8 Sources/Veridant/ivy-v2/verify.py --stage stage-v6 --installed
```

For an intentional ivy-only revision, first inspect `veridant_revise_ivy.py` and
use a fresh stage name. Its hash guards reject unrelated changes. The native
importer reads the requested staged manifest and guards editor/project state;
it does not select or save another editor document.
