# Ares core ring light mounts

The upper flared ring's 24 bare emitting boxes are replaced by metal mounting
plates, dark housings, fasteners, protective bezels and recessed emitting faces.
The mounting plane follows an actual facet of the 48-sided conical underside;
the plate's rear is embedded 0.10 inch into that plane. All placements are
centred within facets, with their optics facing outward/downward.

`Tools/ares_core_lamps.py` supplies the fixtures. The call in `ares_map.reactor`
changes only the previous upper-ring lamp loop. It preserves any collision
already present in the parent model. The existing steel, gunmetal and warm LED
materials are reused, and only the lens face emits light.

The staged sparse migration removes exactly 288 old triangles from
`Assets/models/maps/ares/ares_reactor.obj` and appends 10,608 fixture triangles.
Every retained original OBJ byte and vertex/UV/normal index stays in place.
The ModelDoc, MTL, collision sources, materials and scene are not written.
The guarded native importer publishes only that one render OBJ and registers
it with the editor before native VMDL compilation.

The `stage-v1` manifest preserves the initial authoring hash. A subsequent
helper correction changes its collision assertion to accept a pre-existing
parent collision model; it does not change any generated render geometry.
The checker reproduces the exact staged fixture OBJ with the corrected helper
and also runs the complete reactor source construction.

Native before/after captures use a temporary isolated copy of Ares' visual
scene and destroy it afterward. No active camera, exposure, selected document
or play state is edited. Three matching views cover the close mounting plane,
an oblique attachment view and the full ring. Reports and captures are in
`output/ares/core-lamp-mounts-v1/`; `installed.json` links the final validation.

Geometry count is recorded; frame rate was not benchmarked.
