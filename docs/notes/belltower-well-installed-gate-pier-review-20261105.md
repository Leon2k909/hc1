# Well frame installed; gate pier pending review

User approved the well frame and requested old-asset deletion. Native installation removed 72
old timber/drum render triangles from three centre mesh sources, saved the standalone well-frame
group, compiled the centre model and deleted eleven obsolete private review assets. Existing
masonry, tiled roof, water, physics and other object IDs were preserved. Regeneration emits
`Tools/belltower_well_frame.py`'s stable group and retains the original post collision only.
Receipts: `Sources/Belltower/well-frame-v2/installed.json`.

The next model is the churchyard gate pier at plan `(-459,-405,0)`, rebuilt with a moulded base,
tapered panelled shaft, stepped capital and turned stone finial. LODs 2,136 / 1,480 / 824 triangles,
versus the original 116. Finial UVs sample a single photographed stone. The saved scene is unchanged.
All three native VMDLs compiled. Final matched views use an ephemeral editor-scene camera while
the game continues playing, and verify complete camera/tone/model/object/editor state restoration.

Source: `Sources/Belltower/gate-pier-v2/`. Current evidence is
`output/belltower/gate-pier-v2/{before,after}-preview.png`; the earlier final.png pair is superseded.
NOT installed: pending user approval.
