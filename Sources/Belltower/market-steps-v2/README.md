# Market-cross stone treads — 27 October 2026

Only the three-tier base under Belltower's market cross is rebuilt. Eighty
individual stones have unequal joints, rounded front noses, shallow tread wear
and selective chips. The tiers use four, three and two stones per octagon side;
an inner course replaces the previous featureless centre around the column.
Photographed stone interiors supply the varied finish, with reduced normal
strength and high roughness. Original CC0 scan pixels remain unchanged.

`Tools/belltower_market_steps.py` supplies the local geometry.
`belltower_stone_wear.market_steps` delegates to it, preserving the column's
existing capital. The original radii (100, 80, 60 inches), tier heights
(12, 24, 36 inches) and all three collision hulls remain exact.

`Tools/belltower_stage_market_steps.py` removes only the 17,684 installed base
triangles by material and position matching. It appends 7,460 replacement
triangles to both the canonical centre OBJ and its active bounded stone import,
preserving every other source byte. Two MTL files gain the new material alias;
the centre ModelDoc gains one remap while its entire physics suffix stays exact.
No other render import, fountain part, column, material, scene or gameplay code
is changed. Backups and hashes are in `output/belltower/market-steps-v2/stage-v1`.

The native importer installs the six scoped assets atomically with backups.
Both the material and centre model compile successfully and report up to date.
Native downward traces hit the original 12-, 24- and 36-inch tread heights.
All 80 stones pass the closed-edge check at the exported OBJ precision.

Matched elevated images and a lower view were reviewed in the existing editor
document, with no temporary model override. The capture helper restores the
camera, tone, object set, scene camera and pre-existing unsaved state. No scene
save or play-state change was performed. `verify.py` writes `installed.json`
and `output/belltower/market-steps-v2/validation.json` after checking the files
and native evidence. The editor remains open for the main chat and user.
