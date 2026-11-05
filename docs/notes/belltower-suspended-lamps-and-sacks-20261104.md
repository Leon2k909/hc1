# Belltower suspended lamps installed; bakery sacks pending review

The user approved the suspended lamp and requested deletion/replacement of the old model.
All ten lamps (five west, five east) are installed with stable scene IDs through
`Tools/belltower_dish_lamps.py`. Native publication removed 3,560 old triangles from eight source
meshes, compiled all seven affected VMDLs and saved the scene. Thirteen obsolete private review
files were deleted. Physics, previous object IDs and the explicitly retained original wall-lantern
asset were preserved. Receipts: `Sources/Belltower/dish-lamp-v2/installed.json`.

The next candidate is the seven-sack pile inside the bakery, at plan `(-1215,730,0)`. Rounded cloth
bodies, folds and seams replace 84 box triangles, using existing canvas. Three source LODs are
9,170 / 8,120 / 6,720 triangles. All three native model definitions compiled. A private variant
removes only those old box faces. The final warmed comparison uses an interior view, identical
camera/light parameters and verified restoration of editor/camera/tone/object/model state.
Saved map/shared source hashes remain unchanged. This candidate is NOT installed.

Source: `Sources/Belltower/sack-pile-v2/`; final evidence:
`output/belltower/sack-pile-v2/{before,after}-interior.png`. Await user visual approval.

The user subsequently approved the sacks and requested old-asset deletion. Both mirrored piles (14 sacks) are now installed and saved. Removed 168 legacy box triangles from four source meshes and deleted nine obsolete private review files. All seven affected map VMDLs compiled; saved models load and regenerated collision matches exactly. Sources/Belltower/sack-pile-v2/installed.json records validation. Saved after image: output/belltower/sack-pile-v2/after-installed.png.
