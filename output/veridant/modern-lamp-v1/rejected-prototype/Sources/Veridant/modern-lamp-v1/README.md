# Rejected modern path-light prototype

The user rejected the style change: the problem was the original lantern's
placement in open circulation. This prototype was never placed in the map.
It is archived out of Assets and must not replace Veridant's original lanterns.
The accepted placement correction is documented in
`Sources/Veridant/lamp-placement-v1/README.md`.

- Reusable model: `Assets/models/props/veridant/modern-lamp-v1/bollard.vmdl`.
- Source: `Tools/veridant_modern_lamp.py`; staging: `Tools/veridant_stage_modern_lamp.py`.
- Size: 40 inches tall; 6.55-inch head and 8.6-inch mounting plate.
- 836 triangles, four materials and one collision box.
- Powder-coated charcoal body with eased edges, a recessed service panel,
  shielded narrow warm lenses, a flat weather cap and captive screws.
- Materials are private to this fixture. No existing material was replaced.
- Native publisher: `import-asset.cs.txt`, restricted to the new asset folders.
- All four materials and the model compiled successfully.
- `preview.cs.txt` renders a disposable standalone scene, then destroys it;
  it does not change the active document, camera, play state or saved map.
- Native preview: `output/veridant/modern-lamp-v1/fixture-preview.png`.
- Asset verification: `output/veridant/modern-lamp-v1/asset-validation.json`.

The original fixture design, height, materials and lighting parameters are
retained by the accepted correction. Do not apply this modern fixture.
