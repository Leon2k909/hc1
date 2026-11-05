# Ares storage lockers v1 — installed

- All fourteen wing lockers use the user-approved formed enclosure, lighter existing door material, physical vents/hinges/handle and correctly facing identifiers 01–14. Generator: `Tools/ares_lockers.py`, called by `Tools/ares_map.py`.
- Removed exactly 336 old render triangles from the live `pressure-doors-v2/hall_base.obj`. All unrelated faces and vertex/UV/normal records remain. Added `locker-v1/installed_lockers.obj` to `ares_hall.vmdl`, preserving its other imports, full physics suffix, bank collision, materials and scene. No full-map regeneration.
- New combined geometry: 75,074 triangles. No performance benchmark. Both installed banks were visually inspected in actual offline Ares play with a player, copied gameplay effects, ordinary streaming, no added lights and no error models. The prior scene/play state was restored.
- Recipe: `Sources/Ares/locker-v1/README.md`. Receipts/backups/captures: `output/ares/locker-v1/installed.json`, `install-before/`, `runtime-installed/`. Use the installed verifier after installation; original prototype source guards are historical.
