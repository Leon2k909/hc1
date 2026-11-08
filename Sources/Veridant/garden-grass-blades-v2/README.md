# Grass geometry correction

User requested hyper-realistic grass. Found an error in v1 width adjustment: each blade has nine connected vertices, so pairing the whole vertex array distorted tips across blade boundaries. V2 partitions the mesh by connected blade, adjusts paired edge vertices within each component, preserves the tip, and reduces horizontal sprawl to 65%. Original v1 retained. Same scene object 4cce916e-5444-49ba-b215-b15e4358ae50 now uses models/props/shared/veridant_short_garden_grass_v2/grass.vmdl. Native compile/model load succeeded and scene saved.

Actual matching viewport captures: output/veridant/garden-grass-blades-v2/before.png and after.png (19.31.42). The corrected geometry remains visibly strand-like; this is a modelling repair, not a validated hyper-realistic result. Further grass asset work is needed. Other lawns unchanged.
