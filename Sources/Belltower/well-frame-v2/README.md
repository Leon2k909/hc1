# Garden well frame and windlass — review only

Rebuilt the two posts, upper crossbeam and drum at plan `(0,-1225,-48)` using eased timber,
knee braces, bearing blocks/straps, an axle, iron drum ends, a crank with wooden handle,
wound rope and a free rope descending into the existing well opening. Existing masonry,
water, tiled roof and gameplay collision remain unchanged. Existing materials are reused.

LODs: 6,222 / 3,910 / 1,746 triangles; original selected render geometry: 72 triangles.
The private centre variant removes precisely those 72 faces and retains unrelated records.
Three native VMDLs compiled. Warm matched before/after views restore camera/tone/model/object
and editor state; saved map/shared-source hashes are unchanged. One final capture aborted
during streaming when another editor selection changed, before camera/model mutation.
Effective GPU exposure is not independently measured.

Evidence: `output/belltower/well-frame-v2/{before,after}-final.png`, with camera/restore receipts.
Native compile/source verification: `review.json`. Approved and installed. Removed 72 old render triangles from three mesh sources; deleted eleven obsolete private assets. Native centre compilation, scene save and physics/object-ID/editor-state preservation passed. See installed.json.
