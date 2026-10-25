# Fountain water v2

The fountain now uses `belltower_fountain_surface_v2.shader` for its basin and
`belltower_fountain_stream_v2.shader` for its jets and droplets. The older shared
fountain-water shader remains unchanged for the garden well.

`Tools/belltower_fountain_water.py` owns the two material definitions and the
water-only geometry. `belltower_fountain.py` delegates its pool and four spouts
to it. Regeneration retains the existing limestone, bronze, roof, collision and
normal-map pixels. Droplet identity is stored in integer texture U; fractional
UVs remain valid for tangent generation. A 3.25-inch peak and 0.26-second flight
keep the small impact spray close to normal gravity, independently of texture
flow speed.

The publication replaced only faces using `fountain_water` or `fountain_jet`
in the centre OBJ. Every other original mesh byte, the VMDL, material mapping,
physics and saved scene are retained. `water-v2.json` links the native compile,
loaded-resource and preview evidence. Hashes and the independent source
regeneration preservation check are in `output/belltower/fountain-water-v2/`.

Use the engine's `Editor.EditorUtility.CompileShader` for these shader sources;
the generic native `asset_compile` tool does not compile `.shader` sources.
The water materials compile with the normal native asset tool. Let the asset
watcher compile the centre model rather than forcing a full town rebuild.

The accepted close-up is a native basin model preview. A full in-map lighting
and moving-camera check remains pending; the shared editor's play session was
preserved throughout this water-only task.
