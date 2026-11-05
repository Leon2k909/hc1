# Lucky Stop ice cabinet v1 — installed 2026-11-04

Approved and installed after actual offline Riverside play verification. Native images: `output/riverside/ice-cabinet-v1/installed-in-game.png` and `installed-porch.png`. These use the map lighting and gameplay camera effects; no extra lights or runtime model substitutions.

`riverside_store.vmdl` now imports `ice-cabinet-v1/store_without_ice.obj` in place of the existing store input (exactly 14 old cabinet triangles removed), retains the upgraded drinks-fridge mesh, and adds three translated cabinet meshes with collision-safe `icev1_` material aliases. Store and drinks-fridge meshes have LOD mask 7; cabinet meshes have masks 1/2/4, 4,692/2,444/1,248 triangles, thresholds 0/20/45. Original ModelDoc physics section and saved scene are unchanged. The existing ice-machine point light remains unchanged.

`Tools/riverside_ice_cabinet.py` reproduces all three approved local OBJ meshes exactly. Its authoring hook replaces the old cabinet and atlas panel in `Tools/riverside_map.py`; no full-map regeneration was run. The authoring helper retains the original 38×30×60 inch collision and placement. Source, guarded installation scripts and receipts are in `Sources/Riverside/ice-cabinet-v1` and `output/riverside/ice-cabinet-v1`.

The subsequent cash-register installation merged switch distances into five public LOD groups (0/10/20/25/45). Current store/drinks masks are 31 and ice masks are 3/12/16; the three cabinet meshes and their geometry remain unchanged. Earlier installation receipts describe the three-group baseline at the time the cabinet was installed.
