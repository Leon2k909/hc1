## Burn drum v2 (`models/zombies/burn_drum_v2`, `Sources/Zombies/burn-drum-v2/`, 2026-10-30)
- Riverside's 14 drums (blue 4, red 3, rust 5, cold 2), replacing `riverside_parts.drum`'s flat 14-sided cylinders at the user's word after a
  before/after. Same size, and the ember bed is at the old height, under where `MapFire`'s flames sit.
- `riverside_parts.drum` keeps the hull and fire and records a placement. The scene's "Burn Drums" group holds the models.
- **Don't rerun `Tools/riverside_map.py` without looking at what it changes.** The shared kit has moved on since the map was last generated: on
  2026-10-30 an unmodified run rewrote the ground, levee, pad and dressing, and reported paints with no material (`rv_steel`, `rv_yellow`,
  `rv_zinc`). `install_drums.py` cuts the drums from the checked-in OBJs instead.
- Seen in s&box on 2026-10-31 in an isolated editor scene, with `MapFire`'s real flames under the map's own light (`Sources/Zombies/cooler-v2/capture_engine.cs.txt`):
  it holds up, and the hull's collision tested with rays. That showed one fault Blender hadn't, fixed since: the fire's light reached the drum's bare floor, which
  read as a pale patch through the air holes. **Not yet seen in a live match**, and the LOD distances are unchecked. See the folder's README.
- Fire fit corrected 2026-11-04 after the user's match screenshot showed flames outside the drum. Flame sprites had been about 37 in
  wide on centres scattered across an 18 in square, wider than the 22.5 in drum before wind drift. The 12 drum fires now use an optional
  9.5 in opening radius and rim 7.59 in above the emitter; full billboard widths and circular spawn positions fit inside it, with wind
  drift withheld until a tongue clears the rim. Height 30, width setting 12, 18 flames/s; confined fires do not grow at distant LOD.
  Depth feather reduced from 8 to 1 near the wall. Other map fires and grenade fire keep the unconfined behaviour (radius 0).
- Saved with native component tools and `save_scene`; the generator retains these settings without rebuilding Riverside. Native captures
  from front, side and above checked several animation frames. 24,646 sub-rim particle samples, 0 escaped bases, maximum reach 8.75 in;
  no error models. Scene comparison preserves all other data apart from new zero-valued opening defaults. Work/receipts and before-scene
  backup: `output/riverside/drum-fire-fit/`. Scripts: `Sources/Zombies/burn-drum-v2/fire_fix.py` and `fire_fix_sheet.py`.
- Follow-up realism pass 2026-11-04: mostly short flames with occasional taller licks, coordinated burn/firelight pulses, gentler sway,
  narrowing and warmer fading tips, reduced white glare. The boundary accounts for tilted sprite extents. Drum profiles now use
  24 flames/s, smoke 2/s at size 48 / life 4.5, 2 small embers/s, light brightness 2.2 placed closer to the fuel. Other fire profiles remain
  unconfined. Native saved-scene application and verification: `fire_realism.py`; captures/snapshots/receipts under
  `output/riverside/drum-fire-realism/`. The scene comparison preserves everything except the twelve drum profile edits.
- Later 2026-11-04, replaced the contained-fire animation after the user still saw dancing cards. `BarrelFlameParticles` uses seven
  persistent sources on the drum model's four logs, transformed with each barrel's actual rotation. No random relocation, whole-card
  roll or lift-off. Smooth height variation preserves the photographic flame's proportions, with smaller outer flames. Full card widths
  stay inside the opening. One subtle heat-refraction card per barrel uses a shared dynamic 32x64 upward noise field (at most 25 Hz).
  Existing opening settings select this automatically; no scene or generator rewrite. Other map/grenade fire keeps its emission path.
  Native three-angle motion QA and receipts: `fire_rooted.py`, `output/riverside/drum-fire-rooted/`; GIF/contact sheet helper
  `make_rooted_preview.py`. This supersedes the earlier fit/realism scripts' particle measurements. See the README for current checks.
- Current follow-up: the separate heat-refraction card has been removed after angle-dependent clipping was reported; contained flame
  depth feather is now 2 in, and a version marker rebuilds the transient visuals after hotload. Exact viewport clipping remains
  unconfirmed. The playback change made during that pass was too fast: sprite phase must be normalized. Corrected to
  `(time * (20/64) + phase/Tau) % 1`, a 3.2-second cycle. Live editor samples measured 20.000156 sheet frames/s on all twelve controllers,
  with normalized phases and zero compilation errors. Receipt: `output/riverside/drum-fire-speed/playback-validation.json`.
