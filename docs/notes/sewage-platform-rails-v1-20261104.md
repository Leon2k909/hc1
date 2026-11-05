# Sewage platform rail reuse — 2026-11-04

User deferred the uncertain lock result and requested another model improvement. Leave gate-lock-v2 for later review; it is not approved. Audited current Sewage upgrades first: cabinets, drums, tower vents, lamps, valve wheels, flanges and main stair treads already upgraded. Central platform rails retained crude oversized tubes and simple feet.

Reused `riverdale_parts.railing` including the previously corrected closed socket fittings, without editing that shared kit. Seven central service-platform rail sections now have slimmer tubes, cast tee fittings, proper base plates and toe boards. `Tools/sewage_platform_rails.py` adds restrained anchor heads and maps to existing Sewage yellow and steel materials; `sewage_map.rail` dispatches these exact placements to that helper. Other railings remain unchanged.

Guarded exact splice: 2,596 old triangles removed, 20,758 new triangles added, 53,968 unrelated triangles retained exactly, including the main stair tread upgrade. Public `sewage_catwalks` model physics suffix and metal hull OBJ unchanged. Existing stair before/after assets retained. No scene edits. Previous platform rails retained in `models/maps/sewage/platform-rails-v1/before.vmdl` and output baseline.

Scripts: `Sources/sewage/platform-rails-v1/`; plan, baseline, verification and native matching screenshots: `output/sewage/platform-rails-v1/`. Native model compilation passed and asset is up to date. Platform overview and close fittings views visually checked. Successful isolated captures preserved the user editor scene, dirty and play state. Installed for user visual review; awaiting feedback.
