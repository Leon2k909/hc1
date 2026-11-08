# Veridant lawn: 4K Megascans comparison

Preview only. The saved scene, original lawn material, ground model, geometry and
collision remain unchanged. The accepted Megascans gravel is retained.

Source: Quixel Megascans Lawn Grass, `tkynejer`, free on Fab:
https://www.fab.com/listings/f50d1f4a-d91a-41c2-86ad-10c4ffe7f658
Downloaded 2026-11-05 after the user's explicit approval to accept the Fab Standard
Licence. `provenance.json` records the archive and original map hashes. The original
4K base colour, normal, roughness and AO images are copied unchanged into the trial
folder. The 2x2 metre scan repeats 1.6256 times per existing 128-inch UV tile.

Recommended comparison material: `lawn-balanced.vmat`, colour tint
(1.1,1.25,1.05,1), a modest greener adjustment for the existing resort palette.
Original-colour and stronger-tint alternatives are retained as comparison evidence.
No pixel edits, displacement or extra grass geometry are applied.

Both matched captures use world position (287,506,182), angles (25.09,-51.65,0),
horizontal FOV 53, 1200x900 output, exposure 2.2. Texture streaming receives explicit
4096-pixel usage requests and a two-second warm-up. Native texture metadata confirms
4096x4096 base colour, normal and AO resources. Temporary isolated editor scenes are
destroyed after every capture. Final capture reports preserved editor state.

Final matched images: `output/veridant/quality/megascans-lawn-trial-20261105-final/before.png`
and `after.png`. A saved-scene update occurred during the earlier trials, so both
final views were recaptured against the same current saved-scene hash, recorded
in `final-pair-validation.json`; other scene work was preserved. The original lawn
material and ground model retain their staging hashes.
Receipts, compile results and validation:
`output/veridant/megascans-lawn-trial-20261105/`.
