# Existing 4K scanned lawn reused

Applied the already installed Quixel Megascans Lawn Grass tkynejer balanced material to Veridant's playable lawn surfaces. Exactly three ModelDoc material remaps changed: veridant_ground, veridant_dress (the rooftop garden patches), and garden-relief-v1/garden_strip_relief. The far backdrop retains its original material. All geometry, UVs, collision, relief, lighting and scene components remain unchanged.

Active material: materials/veridant/trials/megascans-lawn-trial-20261105/lawn-balanced.vmat. The existing 4096px base colour, normal, roughness and AO are reused without pixel edits. Scale is the prior material's 1.6256 repeats per 128-inch UV tile, corresponding to the scan's 2m square. Existing licence approval/provenance is documented in Sources/Veridant/megascans-lawn-trial-20261105/README.md and provenance.json.

Original material materials/veridant/vr_lawn.vmat and all previous variants are retained unchanged. Three before ModelDocs and guarded import are under output/veridant/garden-lawn-reuse-v1. The map and garden relief generators now reference the scanned material for repeatability.

Actual native editor viewport before/after: world camera (-1250,-780,64), angles (16,110,0), FOV80, native frames 19.14.20 and 19.15.58. The existing viewport camera was positioned through the native editor; no temporary cameras/scenes, offscreen rendering, lighting or display changes. Before.png and after.png are under output/veridant/garden-lawn-reuse-v1. Review pending.

Rejected by the user: the texture swap did not address the flat lawn silhouette. Original vr_lawn restored on all three ModelDocs and generator overrides removed. Scan assets retained unused. Follow-up: Sources/Veridant/garden-grass-blades-v1/README.md.
