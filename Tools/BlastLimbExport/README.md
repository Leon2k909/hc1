Exports the installed citizen shirt and trousers for `Tools/blast_limb_assets.py`.
Run `rtk proxy python Tools/blast_limb_assets.py` from the repository root with
.NET 10 and NumPy installed. Override `SBOX_CITIZEN_ASSETS` if s&box is installed
elsewhere.

The export reads a copy of each compiled garment, strips only its GUID metadata
block, and omits the packed normal stream unsupported by the glTF exporter.
The Python generator rebuilds smooth normals and retains the original UVs and
materials. It clips the garment at both knees or elbows, separates the skin
weights, and closes each cut with a neutral cloth interior. The caps are hidden
until the corresponding bodygroup is selected on a detached ragdoll.
Left-only and right-only variants retain the opposite limb's original skinning.

Generation checks that clipping preserves the source surface area and that
moving a detached bone subtree moves complete triangles, without cloth spanning
the gap. Generated sources and reports are cached in `output/blast-limbs/`.
The resulting ModelDoc and DMX files are in `Assets/models/dismemberment/`.
The installed citizen assets remain unchanged.
