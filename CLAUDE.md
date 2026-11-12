# HC1 (Razed) — Claude notes

This file is kept short on purpose. The full notes that used to live here (~900 KB) are split by section under `docs/notes/`. Open only the section you need.

## Key rules
- Active checkout on the user's PC: `C:\sbox-projects\hc1\forked-shooter-main`. Use the s&box MCP (`sbox-cli --connect`) for editor work; don't take full control of the user's PC.
- M4: `Assets/Weapons/M4A1/weapon_m4a1.prefab` ManualOffset.AimOffset must stay `0,0,0`.
- Shared camera look: ACES tonemapping, AO (radius 48, intensity 0.45, falloff 0.9, thin compensation 1), additive bloom (strength 0.1, threshold 1.6), vignette 0.08, PhotographicResponse 0.65. See the camera-look section.
- No CoD names, logos or markings anywhere.
- No lambdas inside explicit `IGameEventHandler<T>` methods.
- Editor tools can't use a type that is new to game code in the same hotload.
- Graphics upgrade work: one change at a time on a branch, shown to the user and approved before it is kept.
- Model upgrade priority: choose props visible at player eye level on main routes or frequently used interaction points. Avoid spending upgrades on hidden rooftop/background details unless requested (user preference, 2026-11-04).
- Model upgrades: check existing approved models and pending review candidates before building a replacement and reuse suitable ones. Prioritize substantial rebuilds of crude assets; small detail passes were insufficient. Orion uses the existing dark Collider chair, not a pale duplicate (2026-11-04).
- Prioritize model upgrades players can see up close during normal play; avoid inaccessible roofs and similar details (user request, 2026-11-04).
- Always show both before and after images for model and graphics improvements, with matching camera, framing and lighting. Include both images directly in the review response.
- Visual reviews and upgrade recommendations must use actual game/editor viewport captures. No temporary cameras, isolated scenes or offscreen renders unless explicitly requested and labelled; see `AGENTS.md` (user correction, 2026-11-05).
- Terrain relief is selective: the user does not want rises on every map or repeated patches just for coverage. Add only where the local ground and surroundings justify it; leave suitable flat areas alone (user preference, 2026-11-05).
- Keep this file small. Add new long notes as a new file in `docs/notes/` and a line in the index below.

## Index of docs/notes

- [hc1 won't load on s&box 26.11.10 - startup content build breaks after a few thousand compiles per process (engine bug); prebuild with Tools/contentbuild, editor closed, 2026-11-11](docs/notes/content-build-job-limit-20261111.md)

- [Boxyard yard concrete v2 - procedural 5.3 px/in floor replaced by a concrete_floor_02 scan slab tile (21.3 px/in) plus a world-locked macro layer (tyre rubber, oil, contact dirt) in the detail slot; approved and kept by the user; old bx_concrete material kept for another map; generator updated, 2026-11-09](Sources/Boxyard/yard-concrete-v2/README.md)

- [Veridant fountain roaring-lion crown - prototype layout: recumbent roaring bronze lions (CC-BY beachmouse scan, baked verdigris), carved acanthus pier, fitted bronze base; rejected as a downgrade, Barye crown restored, assets kept unused, 2026-11-08](Sources/Veridant/roaring-lion-crown/README.md)

- [Riverside sleeper retaining walls - procedural rs_ties replaced by a texture laid out from the brown_planks_03 oak scan (43 px/in, Tools/riverside_sleepers.py), installed and kept by the user; old maps and vmat kept for rollback, 2026-11-07](Sources/Riverside/sleeper-wall-v1/README.md)

- [Riverdale spawn guard huts v2 - plain 100 in box replaced by a steel-clad gatehouse (real glass on three sides, ribbed cladding, recessed door, lit furnished interior; 7,118 tris, map materials), render only; review pending, old faces kept, install.py revert tested, 2026-11-07](Sources/Riverdale/guard-hut-v1/README.md)

- [Riverdale B1 control-room desk - plain box replaced by a steel workstation desk with drawers, kneehole and edge detail (1,006 tris, 3 LODs, map materials), render only; approved by the user, old box deleted, 2026-11-06](Sources/Riverdale/b1-desk-v1/README.md)

- [Riverdale locker banks - eight plain steel slabs replaced by two-tier locker-bank models (4- and 6-door, 3 LODs, existing map materials), installed render-only, collision unchanged; approved by the user, old slabs deleted, 2026-11-06](Sources/Riverdale/locker-bank-v1/README.md)

- [Orion launch-deck control shed - rebuilt (9.6k tris, 3 LODs, procedural textures), installed render-only; approved by the user, old box deleted, 2026-11-06](Sources/Orion/deck-shed-v1/README.md)

- [Riverside utility poles — nine timber poles rebuilt (round trunk, bolted bevelled arms, steel braces, real-scan wood), approved and installed; old poles kept as utility_pole_original, revert.py tested, 2026-11-06](Sources/Riverside/utility-pole-v1/README.md)

- [Veridant south garden pergola — approved teak materials/member helper reused, 2026-11-06](Sources/Veridant/garden-pergola-teak-v1-README.md)

- [Veridant colonnade soil — existing courtyard material reused, 2026-11-06](Sources/Veridant/colonnade-soil-reuse-v1-README.md)

- [Veridant colonnade tree — centred and rooted in stone planter; alternatives retained, 2026-11-06](Sources/Veridant/colonnade-tree-fit-v1-README.md)

- [All six Cerro Blanco CCTV cameras replaced; legacy geometry and generator fallback removed, 2026-11-06](output/cerroblanco/all-cameras/README.md)

- [Cerro Blanco courtyard CCTV — approved Riverdale model/materials reused, native review, 2026-11-06](Sources/CerroBlanco/courtyard-cctv-v1/README.md)

- [All 11 red display vases installed; zero plain cylinders remaining, 2026-11-06](output/cerroblanco/all-vases/README.md)
- [Cerro Blanco central cafe pendant shade — spun shell and rolled rim, native review, 2026-11-06](Sources/CerroBlanco/cafe-pendant-v1/README.md)

- [Veridant café planter — approved Reef Hall bronze shell and textures reused, 2026-11-06](Sources/Veridant/colonnade-planter-reuse-v1-README.md)

- [Veridant operations counter — original active; panel-built alternative retained unused, 2026-11-06](Sources/Veridant/operations-counter-v1-README.md)

- [Veridant operations painting — reversed-facing frame corrected and print upgraded, 2026-11-06](Sources/Veridant/operations-art-v1-README.md)

- [Veridant gallery garden painting — high-resolution east-wall print, 2026-11-06](Sources/Veridant/gallery-art-garden-v1-README.md)

- [Veridant gallery seascape — high-resolution west-wall print, 2026-11-06](Sources/Veridant/gallery-art-sea-v1-README.md)

- [Riverside spawn-pad watch deck — timber rebuild approved and installed; old deck kept as watch_deck_original; generator updated (OLD_DECK_IN_PAD), 2026-11-06](Sources/Riverside/watch-deck-v1/README.md)

- [Veridant gallery olive-grove artwork — companion high-resolution print, 2026-11-06](Sources/Veridant/gallery-art-olive-v1-README.md)

- [Veridant gallery coastal artwork — high-resolution generated print, 2026-11-06](Sources/Veridant/gallery-art-v1-README.md)

- [Veridant rug texture density — tiled wool replaces stretched image, 2026-11-06](Sources/Veridant/gallery-rug-v3-README.md)

- [Veridant generated wool rug — replaces rejected flat stripes, 2026-11-06](Sources/Veridant/gallery-rug-v2-README.md)

- [Veridant gallery rug — woven surface, tonal stripes and bound edge, 2026-11-06](Sources/Veridant/gallery-rug-v1-README.md)

- [Veridant terrace tarp — continuous UVs and matte woven canvas, 2026-11-06](Sources/Veridant/terrace-tarp-v1/README.md)

- [Veridant kiosk wall lights — approved reception fixture reused, 2026-11-06](Sources/Veridant/kiosk-wall-lights-v1/README.md)

- [Veridant kiosk service door — frame, panels and hardware replacing plain rectangle, 2026-11-06](Sources/Veridant/kiosk-service-door-v1/README.md)

- [Veridant terrace utility cabinet — framed doors and vents replacing plain block, 2026-11-06](Sources/Veridant/kiosk-cabinet-v1/README.md)

- [Veridant forecourt lamp posts — tapered shafts and shaped bases; original retained, 2026-11-06](Sources/Veridant/forecourt-posts-v1/README.md)

- [Cerro Blanco queue bars — actual brushed colour/normal/roughness textures, close-up review; all variants retained, 2026-11-06](Sources/CerroBlanco/queue-posts-metal-v3/README.md)
- [Cerro Blanco queue barrier — earlier silver finish retained, 2026-11-06](Sources/CerroBlanco/queue-posts-metal-v2/README.md)
- [Cerro Blanco lobby queue barrier — first proposal retained, 2026-11-06](Sources/CerroBlanco/queue-posts-v1/README.md)
- [Cerro Blanco cafe pan dulce — rounded buns and scored crusts installed, old meshes removed, 2026-11-06](Sources/CerroBlanco/pan-dulce-v1/README.md)
- [Cerro Blanco cafe pastry display — curved glazing and continuous frames installed, old geometry removed, 2026-11-06](Sources/CerroBlanco/cafe-display-v1/README.md)
- [Cerro Blanco second East Hall vase — approved vessel reused and installed, 2026-11-06](Sources/CerroBlanco/east-hall-vase-v2/README.md)
- [Cerro Blanco cafe grinder — transparent hopper and dosing hardware installed, old geometry removed, 2026-11-06](Sources/CerroBlanco/cafe-grinder-v1/README.md)
- [Cerro Blanco East Hall display vase — turned form and hollow mouth installed, old cylinder removed, 2026-11-06](Sources/CerroBlanco/gallery-vase-v1/README.md)
- [Cerro Blanco courtyard bin — corrected hood sockets installed, old geometry removed, 2026-11-06](Sources/CerroBlanco/courtyard-bin-v1/README.md)
- [Cerro Blanco courtyard bench — original active; standalone stone-pier/teak alternative retained for another map, 2026-11-06](Sources/CerroBlanco/courtyard-bench-piers-v1/README.md)

- [Veridant terrace flag — smooth static cloth folds; original retained, 2026-11-06](Sources/Veridant/terrace-flag-v1/README.md)

- [Veridant carved fountain bowl — hollow bowl and shaped pedestal; original retained, 2026-11-06](Sources/Veridant/fountain-bowl-v1/README.md)

- [Veridant terrace pergola beam saddles — rejected and removed, 2026-11-06](Sources/Veridant/pergola-brackets-v1/README.md)

- [Veridant café terrace pergola — bolted steel baseplates and collars, 2026-11-06](Sources/Veridant/pergola-bases-v1/README.md)

- [Veridant lounge coffee tables — eased tops and recessed pedestals; original retained, 2026-11-06](Sources/Veridant/lounge-tables-v1/README.md)

- [Veridant forecourt fountain water — existing pool water and stone liner reused, 2026-11-06](Sources/Veridant/fountain-water-v1/README.md)

- [Veridant courtyard planter lights — originals active; louvred housings retained unused, 2026-11-06](Sources/Veridant/planter-lights-v1/README.md)

- [Veridant gallery paintings — moved from glazing onto solid wall piers, 2026-11-06](Sources/Veridant/gallery-wall-art-v1/README.md)

- [Cerro Blanco North Gallery terrace doors (saved and movement checked, 2026-11-06)](docs/notes/cerroblanco-north-gallery-terrace-doors-v1-20261106.md)

- [Veridant terrace bar — plain bar restored; timber frontage retained unused, 2026-11-06](Sources/Veridant/terrace-bar-front-v1/README.md)

- [Veridant north terrace lantern glazing frames — applied review, 2026-11-06](Sources/Veridant/lantern-posts-v1/README.md)

- [Veridant forecourt fountain stone coping — applied review, 2026-11-06](Sources/Veridant/fountain-rim-v1/README.md)

- [Veridant reception ceiling light bezels — applied review, 2026-11-06](Sources/Veridant/downlight-bezels-v1/README.md)

- [Cerro Blanco café courtyard doors (saved and movement checked, 2026-11-06)](docs/notes/cerroblanco-cafe-courtyard-doors-v1-20261106.md)

- [Veridant courtyard drains — rejected layout; all removed for continuous paving, 2026-11-06](Sources/Veridant/courtyard-drains-v1/README.md)

- [Cerro Blanco café terrace doors (direct window comparison, 2026-11-06)](docs/notes/cerroblanco-cafe-terrace-doors-v1-20261106.md)

- [Veridant terrace pedestal stools — applied review; old umbrella retained separately, 2026-11-06](Sources/Veridant/terrace-stools-v1/README.md)

- [Veridant furled terrace umbrella — gathered cloth and fitted tie, applied review, 2026-11-05](Sources/Veridant/terrace-umbrella-v1/README.md)

- [Reef Hall south office doors and glass transom (direct window comparison, 2026-11-05)](docs/notes/reefhall-office-doors-v1-20261105.md)

- [Veridant reception stair rail — smooth tubes and mounted fixings, applied review, 2026-11-05](Sources/Veridant/reception-stair-rail-v1/README.md)

- [Veridant café/lounge link doors (direct window comparison, 2026-11-05)](docs/notes/veridant-lounge-cafe-doors-v1-20261105.md)

- [Veridant operations banner — static cloth folds, applied review, 2026-11-05](Sources/Veridant/operations-banner-v1/README.md)

- [Veridant gallery roof-terrace doors (direct displayed viewport captures, 2026-11-05)](docs/notes/veridant-gallery-terrace-doors-v1-20261105.md)

- [Veridant lounge side doors (direct displayed viewport captures, 2026-11-05)](docs/notes/veridant-lounge-side-doors-v1-20261105.md)

- [Veridant reception entrance wall fixture — applied, 2026-11-05](Sources/Veridant/reception-wall-light-v1/README.md)

- [Veridant café northwest doors (direct displayed viewport captures, 2026-11-05)](docs/notes/veridant-cafe-west-north-doors-v1-20261105.md)

- [Veridant desk — original active; walnut rebuild retained as reusable shared prop, 2026-11-05](Sources/Veridant/reception-desk-v1/README.md)

- [Veridant café west doors (direct displayed viewport captures, 2026-11-05)](docs/notes/veridant-cafe-west-doors-v1-20261105.md)

- [Veridant lounge west doors (direct window captures, 2026-11-05)](docs/notes/veridant-lounge-west-doors-v1-20261105.md)

- [Veridant reception sign v2 — rejected; original restored, 2026-11-05](Sources/Veridant/sign-v2/README.md)

- [Veridant lounge garden doors (saved; runtime validation blocked, 2026-11-05)](docs/notes/veridant-lounge-garden-doors-v1-20261105.md)

- [Veridant breakable railing panes (147 installed, 2026-11-05)](docs/notes/veridant-breakable-rails-20261105.md)

- [Veridant operations south garden doors (actual viewport comparison, 2026-11-05)](docs/notes/veridant-ops-garden-doors-v1-20261105.md)

- [Veridant operations east doors (actual viewport comparison, 2026-11-05)](docs/notes/veridant-ops-east-doors-v1-20261105.md)

- [Veridant operations courtyard doors (actual viewport comparison, 2026-11-05)](docs/notes/veridant-ops-courtyard-doors-v1-20261105.md)

- [Veridant upper gallery balcony doors (actual viewport comparison, 2026-11-05)](docs/notes/veridant-gallery-balcony-doors-v1-20261105.md)

- [Veridant lounge courtyard doors (actual viewport comparison, 2026-11-05)](docs/notes/veridant-lounge-courtyard-doors-v1-20261105.md)

- [Veridant north café entrance doors (actual viewport comparison, 2026-11-05)](docs/notes/veridant-cafe-north-doors-v1-20261105.md)

- [Veridant upper operations lobby doors (installed, 2026-11-05)](docs/notes/veridant-ops-lobby-doors-v1-20261105.md)

- [Veridant café south entrance doors (installed, 2026-11-05)](docs/notes/veridant-cafe-doors-v1-20261105.md)

- [Ares main airlock lightbox (installed and native verified, 2026-11-05)](docs/notes/ares-main-airlock-sign-review-20261105.md)

- [Ares northeast pump isolation valve (accepted valve reused; native review, 2026-11-05)](docs/notes/ares-pump-isolation-valve-review-20261105.md)

- [Ares concourse pillar impact guard (rejected; original retained, 2026-11-05)](docs/notes/ares-concourse-column-guard-review-20261105.md)

- [Ares west control-room operator console (approved core model reused; native review, 2026-11-05)](docs/notes/ares-west-operator-console-review-20261105.md)

- [Door placement audit and candidate shortlist (2026-11-05)](docs/notes/door-placement-audit-20261105.md)
- [Orion recessed undercroft façade (installed and native verified, 2026-11-05)](Sources/Orion/undercroft-facade-v1/README.md)
- [Riverside shopfront depth (actual glazed openings and stocked interior; private native review, 2026-11-05)](Sources/Riverside/storefront-depth-v1/README.md)

- [Ares west main-stair landing railing (native review, 2026-11-05)](docs/notes/ares-stair-landing-rail-review-20261105.md)

- [Veridant usable glazed reception doors (2026-11-05)](docs/notes/veridant-reception-doors-v1-20261105.md)

- [Ares west control-room display (existing approved monitor adapted, native review, 2026-11-05)](docs/notes/ares-control-room-display-review-20261105.md)

- [Ares lower-hall bulkhead lamp installed (old embedded geometry removed, 2026-11-05)](docs/notes/ares-bulkhead-lamp-installed-20261105.md)

- [Ridgeback town house Quixel stucco (exterior material review trial, 2026-11-05)](docs/notes/ridgeback-town-house-quixel-stucco-v1-20261105.md)

- [Ridgeback Megascans brick workshop (single exterior review trial, 2026-11-05)](docs/notes/ridgeback-megascans-workshop-v1-20261105.md)

- [Belltower well frame installed; gate pier review (2026-11-05)](docs/notes/belltower-well-installed-gate-pier-review-20261105.md)

- [Cerro Blanco courtyard bench (compiled review candidate; not installed, 2026-11-05)](docs/notes/cerroblanco-courtyard-bench-v1-review-20261105.md)

- [Riverside subtle trailer-yard edge (installed review trial, 2026-11-05)](docs/notes/riverside-trailer-yard-relief-v1-20261105.md)

- [Riverside subtle entrance shoulder (installed review trial, 2026-11-05)](docs/notes/riverside-entrance-relief-v1-20261105.md)

- [Veridant shallow south garden relief (installed review trial, 2026-11-05)](docs/notes/veridant-garden-relief-v1-20261105.md)

- [Lowtide shallow mud-bank relief (installed review trial, 2026-11-05)](docs/notes/lowtide-mud-relief-v1-20261105.md)

- [Belltower subtle orchard lawn relief (installed review trial, 2026-11-05)](docs/notes/belltower-orchard-relief-v1-20261105.md)

- [Cerro Blanco subtle lawn relief (staged offline comparison, 2026-11-05)](docs/notes/cerroblanco-lawn-relief-v1-review-20261105.md)

- [Landing impacts on moving surfaces (code only, 2026-11-05)](docs/notes/landing-relative-impact-20261105.md)

- [Sprays and personal loading screens (code only, 2026-11-05)](docs/notes/sprays-and-loading-screens-20261105.md)

- [Grenade release clearance (code only, 2026-11-04)](docs/notes/grenade-release-clearance-20261104.md)

- [Radial blast impulse falloff (code only, 2026-11-04)](docs/notes/radial-blast-impulse-20261104.md)

- [Riverdale north-lane fire hydrant (revision 2 realism review, 2026-11-05)](docs/notes/riverdale-hydrant-v1-20261105.md)
- [Riverside west-yard privacy fence (installed; original deleted, 2026-11-05)](docs/notes/riverside-yard-fence-v1-20261104.md)
- [Riverside Lucky Stop timber entrance steps (installed; originals deleted, 2026-11-05)](docs/notes/riverside-store-timber-steps-v1-20261104.md)

- [Riverdale sand bin v3 (structural realism rebuild; staged review, 2026-11-04)](docs/notes/riverdale-sand-bin-v3-20261104.md)

- [Riverdale sand bin v2 (realism revision; staged, 2026-11-04)](docs/notes/riverdale-sand-bin-v2-20261104.md)

- [Belltower market cross installed; well frame review (2026-11-04)](docs/notes/belltower-cross-installed-well-frame-review-20261104.md)

- [Riverside interior drinks fridges (three installed; originals deleted, 2026-11-04)](docs/notes/riverside-interior-fridges-v1-review-20261104.md)
- [Riverside guard-tower corrugated roof v1 (installed; original removed, 2026-11-04)](docs/notes/riverside-tower-roof-v1-review-20261104.md)
- [Riverside STILL HERE plank board v1 (installed; old board removed, 2026-11-04)](docs/notes/riverside-still-here-board-v1-review-20261104.md)

- [Riverdale sand bin (installed and native verified, 2026-11-05)](docs/notes/riverdale-sand-bin-v1-20261104.md)

- [Reef Hall close-range display pedestal (installed; old geometry deleted, 2026-11-04)](docs/notes/reefhall-display-pedestal-v1-20261104.md)
- [Reef Hall display coral (rejected; original retained, 2026-11-04)](docs/notes/reefhall-display-coral-v1-20261104.md)
- [Riverside close-range T2 sliding-window frame (installed, 2026-11-05)](docs/notes/riverside-sliding-window-v1-20261104.md)
- [Ares close-range control console (existing proposal reused, native review, 2026-11-05)](docs/notes/ares-control-console-native-v1-20261105.md)

- [Riverdale shared cone (existing approved asset reused; review) and reel installation, 2026-11-04](docs/notes/riverdale-shared-cone-v1-20261104.md)

- [Riverdale shared cable reel (existing approved model reused; staged review, 2026-11-04)](docs/notes/riverdale-shared-reel-v1-20261104.md)

- [Belltower suspended lamps installed; bakery sack review (2026-11-04)](docs/notes/belltower-suspended-lamps-and-sacks-20261104.md)

- [Sewage maintenance tunnel gates v1 (new model review, 2026-11-04)](docs/notes/sewage-tunnel-gates-v1-20261104.md)

- [Belltower wall lantern v2 (24 installed; original asset retained, 2026-11-04)](docs/notes/belltower-wall-lantern-v2-review-20261104.md)

- [Sewage caged work lamps v1 (existing staged model reused, 2026-11-04)](docs/notes/sewage-work-lamps-v1-reuse-20261104.md)

- [Belltower cafe table v2 (all seven installed, 2026-11-04)](docs/notes/belltower-bistro-table-v2-review-20261104.md)

- [Belltower bistro chairs v2 (all 21 installed, 2026-11-04)](docs/notes/belltower-bistro-chairs-v2-20261104.md)

- [Sewage main stair treads v1 (model review, 2026-11-04)](docs/notes/sewage-stair-treads-v1-20261104.md)

- [Belltower menu boards v2 (six installed; old geometry deleted, 2026-11-04)](docs/notes/belltower-menu-boards-v2-20261104.md)

- [Sewage warning sign v1 (model review, 2026-11-04)](docs/notes/sewage-warning-sign-v1-20261104.md)

- [Ares storage lockers v1 (all fourteen installed, 2026-11-04)](docs/notes/ares-lockers-v1-20261104.md)
- [Railhead brick pallet v1 (east-yard replacement installed, 2026-11-04)](docs/notes/railhead-brick-pallet-v1-review-20261104.md)
- [ReefHall circulation pump v1 (filter-room replacement installed, 2026-11-04)](docs/notes/reefhall-circulation-pump-v1-review-20261104.md)
- [Railhead smoking-area ashtrays v1 (all four installed; old geometry and preview removed, 2026-11-04)](docs/notes/railhead-ashtray-v1-review-20261104.md)
- [ReefHall sealed wall light v1 (installed; old mesh and preview removed, 2026-11-04)](docs/notes/reefhall-wall-light-v1-review-20261104.md)
- [Railhead taxi-rank sign v1 (installed and native verified, 2026-11-05)](docs/notes/railhead-taxi-post-v1-review-20261104.md)
- [Railhead platform help point (installed and native verified, 2026-11-05)](Sources/Railhead/help-point-v1/README.md)
- [Railhead PA speaker (installed and native verified, 2026-11-05)](Sources/Railhead/pa-speaker-v2/README.md)
- [Railhead concourse poster lightbox (installed and native verified, 2026-11-05)](Sources/Railhead/city-light-v1/README.md)

- [Belltower terracotta pots v2 (all twelve installed, 2026-11-04)](docs/notes/belltower-terracotta-pots-v2-20261104.md)
- [Preamble](docs/notes/00-preamble.md) (0 KB)
- [Editor connection](docs/notes/001-editor-connection.md) (0 KB)
- [Shared camera look (2026-10-17)](docs/notes/002-shared-camera-look-2026-10-17.md) (2 KB)
- [Photographic map finish (2026-10-27)](docs/notes/003-photographic-map-finish-2026-10-27.md) (1 KB)
- [Map daylight profiles (2026-10-17)](docs/notes/004-map-daylight-profiles-2026-10-17.md) (2 KB)
- [Iron sights: do not change the M4's AimOffset](docs/notes/005-iron-sights-do-not-change-the-m4-s-aimoffset.md) (1 KB)
- [Kastov viewmodel pipeline (CoD MWII rips → HC1 arms)](docs/notes/006-kastov-viewmodel-pipeline-cod-mwii-rips-hc1-arms.md) (11 KB)
- [RPK (MWII's RPK, mg_iw9_rkilo, addon 3499492742)](docs/notes/007-rpk-mwii-s-rpk-mg-iw9-rkilo-addon-3499492742.md) (5 KB)
- [PP-19 Bizon (MWII's "Minibak", mg_iw9_beta, addon 3499492742)](docs/notes/008-pp-19-bizon-mwii-s-minibak-mg-iw9-beta-addon-34994.md) (1 KB)
- [AK-105 (MWII's "Kastov 545", mg_iw9_akilo105, addon 3499492742)](docs/notes/009-ak-105-mwii-s-kastov-545-mg-iw9-akilo105-addon-349.md) (3 KB)
- [Vepr-12 (MWII's "KV Broadside", mg_iw9_vecho, addon 3499492742)](docs/notes/010-vepr-12-mwii-s-kv-broadside-mg-iw9-vecho-addon-349.md) (3 KB)
- [M16A4 (MWII's M16, mg_iw9_mike16, easy4115's addon 2962304029)](docs/notes/011-m16a4-mwii-s-m16-mg-iw9-mike16-easy4115-s-addon-29.md) (14 KB)
- [FN P90 (MW2019's P90, mg_papa90, Viper's MW2019 SMG pack 2802430252)](docs/notes/012-fn-p90-mw2019-s-p90-mg-papa90-viper-s-mw2019-smg-p.md) (4 KB)
- [MP7A1 (MW2019's MP7, mg_mpapa7, Viper's MW2019 SMG pack 2802430252)](docs/notes/013-mp7a1-mw2019-s-mp7-mg-mpapa7-viper-s-mw2019-smg-pa.md) (4 KB)
- [Steyr AUG A3 (MW2019's AUG, mg_augolf, Viper's MW2019 SMG pack 2802430252)](docs/notes/014-steyr-aug-a3-mw2019-s-aug-mg-augolf-viper-s-mw2019.md) (6 KB)
- [Uzi (MW2019's Uzi, mg_uzulu, Viper's MW2019 SMG pack 2802430252)](docs/notes/015-uzi-mw2019-s-uzi-mg-uzulu-viper-s-mw2019-smg-pack-.md) (6 KB)
- [FN FAL (MW2019's FAL, mg_falima, Viper's MW2019 Assault Rifles pack 2528829149)](docs/notes/016-fn-fal-mw2019-s-fal-mg-falima-viper-s-mw2019-assau.md) (8 KB)
- [SIG Sauer M18 (MW2019's "M19", mg_p320, Viper's MW2019 pistol pack 2459723892)](docs/notes/017-sig-sauer-m18-mw2019-s-m19-mg-p320-viper-s-mw2019-.md) (5 KB)
- [SIG MCX Virtus (MW2019's "M13", mg_mcharlie, Viper's MW2019 Assault Rifles pack 2528829149](docs/notes/018-sig-mcx-virtus-mw2019-s-m13-mg-mcharlie-viper-s-mw.md) (10 KB)
- [L85A2 (MW2019's "SA87", mg_lima86, Viper's MW2019 LMG pack 2960120610)](docs/notes/019-l85a2-mw2019-s-sa87-mg-lima86-viper-s-mw2019-lmg-p.md) (6 KB)
- [HK416 A5 (Ready or Not's HK416 A5, mg_ron_hk416, Ha2ard's pack 3385630838)](docs/notes/020-hk416-a5-ready-or-not-s-hk416-a5-mg-ron-hk416-ha2a.md) (7 KB)
- [AK-12 (Escape from Tarkov's AK-12, ARC9 EFT Assault Rifles 2962829818)](docs/notes/021-ak-12-escape-from-tarkov-s-ak-12-arc9-eft-assault-.md) (8 KB)
- [AK-15 (Escape from Tarkov's AK-12 with its AK-103 magazine, ARC9 EFT Assault Rifles 296282](docs/notes/022-ak-15-escape-from-tarkov-s-ak-12-with-its-ak-103-m.md) (5 KB)
- [AK-74M (Escape from Tarkov's AK-74M, ARC9 EFT Assault Rifles 2962829818)](docs/notes/023-ak-74m-escape-from-tarkov-s-ak-74m-arc9-eft-assaul.md) (9 KB)
- [SIG MCX-SPEAR (Escape from Tarkov's MCX-SPEAR, ARC9 EFT Assault Rifles 2962829818)](docs/notes/024-sig-mcx-spear-escape-from-tarkov-s-mcx-spear-arc9-.md) (9 KB)
- [Colt M16A2 (Escape from Tarkov's M16A2, ARC9 EFT Assault Rifles 2962829818)](docs/notes/025-colt-m16a2-escape-from-tarkov-s-m16a2-arc9-eft-ass.md) (8 KB)
- [RPK-16 (Escape from Tarkov's RPK-16, ARC9 EFT Assault Rifles 2962829818)](docs/notes/026-rpk-16-escape-from-tarkov-s-rpk-16-arc9-eft-assaul.md) (8 KB)
- [MP5 barrels (Workshop MW19 parts)](docs/notes/027-mp5-barrels-workshop-mw19-parts.md) (1 KB)
- [Teams: Red Team and Blue Team](docs/notes/028-teams-red-team-and-blue-team.md) (1 KB)
- [Operator outfits (`OperatorOutfits`, `MilitaryUniform`, the Operators page)](docs/notes/029-operator-outfits-operatoroutfits-militaryuniform-t.md) (4 KB)
- [Corner slicing (Black Ops 6/7-style gun tilt, `ViewModel.CornerSlicing.cs`)](docs/notes/030-corner-slicing-black-ops-6-7-style-gun-tilt-viewmo.md) (2 KB)
- [Breadcrumb bars (the gunsmith's and `MenuTopbar`)](docs/notes/031-breadcrumb-bars-the-gunsmith-s-and-menutopbar.md) (0 KB)
- [Emblem editor (`EmblemEditor`, PROFILE → Emblem Editor)](docs/notes/032-emblem-editor-emblemeditor-profile-emblem-editor.md) (1 KB)
- [Report a Bug (`BugReportPanel`)](docs/notes/033-report-a-bug-bugreportpanel.md) (0 KB)
- [Languages (`GameText`, `Tr`)](docs/notes/034-languages-gametext-tr.md) (4 KB)
- [Video settings: resolution and quality are s&box's](docs/notes/035-video-settings-resolution-and-quality-are-s-box-s.md) (0 KB)
- [Field of view settings (Settings → Video)](docs/notes/036-field-of-view-settings-settings-video.md) (3 KB)
- [Hitmarker (`HitmarkerPainter`, Settings → Crosshair's hit marker)](docs/notes/037-hitmarker-hitmarkerpainter-settings-crosshair-s-hi.md) (1 KB)
- [Quitting (`QuitPrompt`): a game can't close s&box](docs/notes/038-quitting-quitprompt-a-game-can-t-close-s-box.md) (2 KB)
- [Controller in the menus (s&box's virtual cursor)](docs/notes/039-controller-in-the-menus-s-box-s-virtual-cursor.md) (11 KB)
- [Look sensitivity and the settings search (2026-10-14)](docs/notes/040-look-sensitivity-and-the-settings-search-2026-10-1.md) (1 KB)
- [Main menu hub page (`HubPage`)](docs/notes/041-main-menu-hub-page-hubpage.md) (4 KB)
- [Custom games (`CreateLobbyPage`, `CustomGameSettings`)](docs/notes/042-custom-games-createlobbypage-customgamesettings.md) (4 KB)
- [Lobby input (controller / mouse-and-keyboard lobbies, `LobbyInputRules`, `LobbyInputGuard`](docs/notes/043-lobby-input-controller-mouse-and-keyboard-lobbies-.md) (3 KB)
- [Map changes with players connected (`GameUtils.LoadMap`)](docs/notes/044-map-changes-with-players-connected-gameutils-loadm.md) (2 KB)
- [Ranked (`Code/Stats/Rank.cs`, `RankedPage`)](docs/notes/045-ranked-code-stats-rank-cs-rankedpage.md) (1 KB)
- [Soldier training (`SoldierTrainingRules`, `SoldierTraining`, `Client.Training`, `PlayerPaw](docs/notes/046-soldier-training-soldiertrainingrules-soldiertrain.md) (6 KB)
- [Prestige emblem (`Progression.GetPrestigeEmblem`)](docs/notes/047-prestige-emblem-progression-getprestigeemblem.md) (0 KB)
- [Gunsmith (`Code/Gunsmith/GunsmithPanel.razor`)](docs/notes/048-gunsmith-code-gunsmith-gunsmithpanel-razor.md) (13 KB)
- [Weapon tuning is off (`WeaponTuningManager`, `WeaponTuningPanel`)](docs/notes/049-weapon-tuning-is-off-weapontuningmanager-weapontun.md) (1 KB)
- [Gunsmith caches (what a shot and a frame no longer work out again, 2026-10-17)](docs/notes/050-gunsmith-caches-what-a-shot-and-a-frame-no-longer-.md) (4 KB)
- [Fire rate and fire modes in the gunsmith (the Action and Trigger slots)](docs/notes/051-fire-rate-and-fire-modes-in-the-gunsmith-the-actio.md) (3 KB)
- [Part weight (`GunsmithPart.Mass`, `Equipment.LoadedMass`, `Tools/part_masses.py`)](docs/notes/052-part-weight-gunsmithpart-mass-equipment-loadedmass.md) (3 KB)
- [Magnified optics: eye relief and the lens picture (`OpticZoom`, `Tools/optic_eyepieces.py`](docs/notes/053-magnified-optics-eye-relief-and-the-lens-picture-o.md) (3 KB)
- [Flip-to-side magnifiers (`GunsmithFlipMagnifier`, `Tools/flip_magnifiers.py`)](docs/notes/054-flip-to-side-magnifiers-gunsmithflipmagnifier-tool.md) (1 KB)
- [Optic tuning (`OpticTuning`, the gunsmith's TUNE)](docs/notes/055-optic-tuning-optictuning-the-gunsmith-s-tune.md) (3 KB)
- [Aiming lasers and reflex sight glass (`GunsmithLaserBeam`, `LaserOptics`, `m4_optic_lens.s](docs/notes/056-aiming-lasers-and-reflex-sight-glass-gunsmithlaser.md) (11 KB)
- [Weapon stickers (`GunsmithSticker`, `Tools/weapon_stickers.py`)](docs/notes/057-weapon-stickers-gunsmithsticker-tools-weapon-stick.md) (3 KB)
- [Core modes are off (hardcore only)](docs/notes/058-core-modes-are-off-hardcore-only.md) (0 KB)
- [Tactical Defuse (`tactical_defuse.prefab`, verified 2026-10-14)](docs/notes/059-tactical-defuse-tactical-defuse-prefab-verified-20.md) (1 KB)
- [Hardcore hit locations (`HealthComponent.Wounds.cs`)](docs/notes/060-hardcore-hit-locations-healthcomponent-wounds-cs.md) (3 KB)
- [Zombies match (`zombies.prefab`)](docs/notes/061-zombies-match-zombies-prefab.md) (1 KB)
- [Zombies perk dispensers and badges](docs/notes/062-zombies-perk-dispensers-and-badges.md) (1 KB)
- [Zombies workbench (`ZombiesWorkbench.cs`, `ZombiesWorkbenchPanel`)](docs/notes/063-zombies-workbench-zombiesworkbench-cs-zombiesworkb.md) (3 KB)
- [Zombie hits and kills (`ZombieAI.OnDamage`)](docs/notes/064-zombie-hits-and-kills-zombieai-ondamage.md) (0 KB)
- [Zombies, doors and players (`ZombieAI.KeepOut`)](docs/notes/065-zombies-doors-and-players-zombieai-keepout.md) (1 KB)
- [Zombie voices (`ZombieAI.PlayVoice`, `Tools/zombie_sounds.py`)](docs/notes/066-zombie-voices-zombieai-playvoice-tools-zombie-soun.md) (1 KB)
- [Zombie animations (NMRIH mocap and a made walk, on the citizen skeleton)](docs/notes/067-zombie-animations-nmrih-mocap-and-a-made-walk-on-t.md) (9 KB)
- [Maps](docs/notes/068-maps.md) (5 KB)
- [Depot (cloud map integration and performance, 2026-10-27)](docs/notes/069-depot-cloud-map-integration-and-performance-2026-1.md) (2 KB)
- [Collider (accelerator laboratory, `Tools/collider_map.py`)](docs/notes/070-collider-accelerator-laboratory-tools-collider-map.md) (16 KB)
- [Belltower (multiplayer map, `Tools/belltower_map.py`)](docs/notes/071-belltower-multiplayer-map-tools-belltower-map-py.md) (78 KB)
- [Hotload: no lambdas in explicit IGameEventHandler<T> methods](docs/notes/072-hotload-no-lambdas-in-explicit-igameeventhandler-t.md) (0 KB)
- [Hotload: editor code can't use a type new to the game code](docs/notes/073-hotload-editor-code-can-t-use-a-type-new-to-the-ga.md) (0 KB)
- [Play-start stalls in the editor (network file hashing, 2026-10-15)](docs/notes/074-play-start-stalls-in-the-editor-network-file-hashi.md) (3 KB)
- [Testing in-game without input](docs/notes/075-testing-in-game-without-input.md) (2 KB)
- [Play areas ("Return to the AO", `PlayArea`)](docs/notes/076-play-areas-return-to-the-ao-playarea.md) (1 KB)
- [Weapon mount (`PlayerPawn.WeaponMount.cs`)](docs/notes/077-weapon-mount-playerpawn-weaponmount-cs.md) (2 KB)
- [Picking up dropped guns (`PlayerPawn.Using.cs`)](docs/notes/078-picking-up-dropped-guns-playerpawn-using-cs.md) (4 KB)
- [Movement speeds (`PlayerGlobals`, `PlayerPawn.GetWishSpeed`)](docs/notes/079-movement-speeds-playerglobals-playerpawn-getwishsp.md) (1 KB)
- [Jump stamina (`PlayerPawn.Movement.cs`)](docs/notes/080-jump-stamina-playerpawn-movement-cs.md) (0 KB)
- [Landing on slopes and stairs (`CharacterController.CategorizePosition`)](docs/notes/081-landing-on-slopes-and-stairs-charactercontroller-c.md) (1 KB)
- [Prone stamina (`PlayerPawn.Movement.cs`)](docs/notes/082-prone-stamina-playerpawn-movement-cs.md) (1 KB)
- [Sprint and fire (`PlayerPawn.IsPullingTrigger`)](docs/notes/083-sprint-and-fire-playerpawn-ispullingtrigger.md) (1 KB)
- [Mantling (`PlayerPawn.Mantle.cs`)](docs/notes/084-mantling-playerpawn-mantle-cs.md) (4 KB)
- [Sliding (`PlayerPawn.Slide.cs`)](docs/notes/085-sliding-playerpawn-slide-cs.md) (5 KB)
- [Bot slides (`LightweightCombatBot.Slide.cs`, 2026-10-14)](docs/notes/086-bot-slides-lightweightcombatbot-slide-cs-2026-10-1.md) (2 KB)
- [Battle royale (Warzone, `Code/GameLoop/Rules/BattleRoyale/`)](docs/notes/087-battle-royale-warzone-code-gameloop-rules-battlero.md) (4 KB)
- [Reef Hall (multiplayer map, `Tools/reefhall_map.py`)](docs/notes/088-reef-hall-multiplayer-map-tools-reefhall-map-py.md) (19 KB)
- [Railhead (multiplayer map, `Tools/railhead_map.py`)](docs/notes/089-railhead-multiplayer-map-tools-railhead-map-py.md) (34 KB)
- [Lowtide (multiplayer map, `Tools/lowtide_map.py`)](docs/notes/090-lowtide-multiplayer-map-tools-lowtide-map-py.md) (46 KB)
- [Boxyard (multiplayer map, `Tools/boxyard_map.py`)](docs/notes/091-boxyard-multiplayer-map-tools-boxyard-map-py.md) (4 KB)
- [Cerro Blanco (multiplayer map, `Tools/cerroblanco_map.py`)](docs/notes/092-cerro-blanco-multiplayer-map-tools-cerroblanco-map.md) (31 KB)
- [Riverdale (multiplayer map, `Tools/riverdale_map.py`)](docs/notes/093-riverdale-multiplayer-map-tools-riverdale-map-py.md) (11 KB)
- [Riverside (Zombies map, `Tools/riverside_map.py`)](docs/notes/094-riverside-zombies-map-tools-riverside-map-py.md) (8 KB)
- [Ares (multiplayer map, `Tools/ares_map.py`)](docs/notes/095-ares-multiplayer-map-tools-ares-map-py.md) (15 KB)
- [Veridant (multiplayer map, `Tools/veridant_map.py`)](docs/notes/096-veridant-multiplayer-map-tools-veridant-map-py.md) (20 KB)
- [Orion (multiplayer map, `Tools/orion_map.py`)](docs/notes/097-orion-multiplayer-map-tools-orion-map-py.md) (6 KB)
- [Ridgeback (battle royale map, `Assets/scenes/maps/Ridgeback/`)](docs/notes/098-ridgeback-battle-royale-map-assets-scenes-maps-rid.md) (9 KB)
- [Ridgeback buildings (`Tools/ridgeback_buildings.py`)](docs/notes/099-ridgeback-buildings-tools-ridgeback-buildings-py.md) (8 KB)
- [Rain (`Weather`, `RainView`, `Code/World/`)](docs/notes/100-rain-weather-rainview-code-world.md) (14 KB)
- [Bullet drop (real exterior ballistics on hitscan shots, Warzone only)](docs/notes/101-bullet-drop-real-exterior-ballistics-on-hitscan-sh.md) (2 KB)
- [Bullet traces (`Shootable.DoTraceBullet`)](docs/notes/102-bullet-traces-shootable-dotracebullet.md) (2 KB)
- [Wallbangs (`Shootable.ResolvePenetration`, `Shootable.Penetration.cs`)](docs/notes/103-wallbangs-shootable-resolvepenetration-shootable-p.md) (1 KB)
- [Incendiary grenade (thermite, `Code/Weapons/Grenades/Fire/`)](docs/notes/104-incendiary-grenade-thermite-code-weapons-grenades-.md) (5 KB)
- [Flashbang (`FlashbangGrenade`, `FlashbangEffect`, `hc1_flashbang.shader`)](docs/notes/105-flashbang-flashbanggrenade-flashbangeffect-hc1-fla.md) (6 KB)
- [Smoke grenade (`smoke_particles.prefab`, `SmokeSimulation`)](docs/notes/106-smoke-grenade-smoke-particles-prefab-smokesimulati.md) (4 KB)
- [Deaths (`DyingBody`, `DeathPlan`, `Code/PawnSystem/DyingBody.cs`)](docs/notes/107-deaths-dyingbody-deathplan-code-pawnsystem-dyingbo.md) (4 KB)
- [Kill sounds (`KillSounds`, `Tools/kill_sounds.py`)](docs/notes/108-kill-sounds-killsounds-tools-kill-sounds-py.md) (1 KB)
- [Menu nav click (`Tools/ui_sounds.py`)](docs/notes/109-menu-nav-click-tools-ui-sounds-py.md) (1 KB)
- [Knife throwing (`Melee.Throw.cs`, `ThrownKnife.cs`, 2026-10-14)](docs/notes/110-knife-throwing-melee-throw-cs-thrownknife-cs-2026-.md) (2 KB)
- [World sounds (`WorldSounds`, `Tools/world_sounds.py`)](docs/notes/111-world-sounds-worldsounds-tools-world-sounds-py.md) (9 KB)
- [Ordnance and handling sounds (`Tools/ordnance_sounds.py`, `Tools/handling_sounds.py`)](docs/notes/112-ordnance-and-handling-sounds-tools-ordnance-sounds.md) (4 KB)
- [No start sting](docs/notes/113-no-start-sting.md) (0 KB)
- [No radio voice lines](docs/notes/114-no-radio-voice-lines.md) (1 KB)
- [Cloud sessions can't upload LFS files](docs/notes/115-cloud-sessions-can-t-upload-lfs-files.md) (1 KB)
- [HUD look (`MainHUD`, 2026-10-05, restyled 2026-10-08, redone 2026-10-09)](docs/notes/116-hud-look-mainhud-2026-10-05-restyled-2026-10-08-re.md) (3 KB)
- [No per-frame rebuilds in the HUD (2026-10-17)](docs/notes/117-no-per-frame-rebuilds-in-the-hud-2026-10-17.md) (1 KB)
- [Damage indicator (`DamageIndicator`, `PlayerPawn.IndicatorSource`)](docs/notes/118-damage-indicator-damageindicator-playerpawn-indica.md) (1 KB)
- [Scoreboard over the HUD (`Scoreboard.razor.scss`)](docs/notes/119-scoreboard-over-the-hud-scoreboard-razor-scss.md) (2 KB)
- [Usage stats for the dev (`UsageStats`, `dev_usage`)](docs/notes/120-usage-stats-for-the-dev-usagestats-dev-usage.md) (1 KB)
- [Camos (the gunsmith's Customize tab)](docs/notes/121-camos-the-gunsmith-s-customize-tab.md) (2 KB)
- [HUD markers under the gun (`ViewModelMask`)](docs/notes/122-hud-markers-under-the-gun-viewmodelmask.md) (1 KB)
- [Teammate glow (`TeammateOcclusionGlow`, `hc1_teammate_occlusion.shader`)](docs/notes/123-teammate-glow-teammateocclusionglow-hc1-teammate-o.md) (1 KB)
- [Teammate markers (Settings → Game → Hide Teammate Names)](docs/notes/124-teammate-markers-settings-game-hide-teammate-names.md) (0 KB)
- [Voice chat (`Voices`, `PlayerVoiceComponent`)](docs/notes/125-voice-chat-voices-playervoicecomponent.md) (2 KB)
- [Reload times (`Reloadable`)](docs/notes/126-reload-times-reloadable.md) (1 KB)
- [The ported guns' sounds (`ported_shots.py`, `suppressed_shots.py`, `ported_foley.py`)](docs/notes/127-the-ported-guns-sounds-ported-shots-py-suppressed-.md) (4 KB)
- [Gunshot audio (`GunshotAudio`)](docs/notes/128-gunshot-audio-gunshotaudio.md) (1 KB)
- [Bullet cracks (`BulletFlyby`, `Code/Weapons/BulletFlyby.cs`)](docs/notes/129-bullet-cracks-bulletflyby-code-weapons-bulletflyby.md) (9 KB)
- [Weapon fire rates and bots](docs/notes/130-weapon-fire-rates-and-bots.md) (15 KB)
- [Skirmish (1v1 / 2v2): bot fill and the arena (`SkirmishArena`)](docs/notes/131-skirmish-1v1-2v2-bot-fill-and-the-arena-skirmishar.md) (2 KB)
- [Retakes and Defuse rounds (`BotFillRule.RestartRound`)](docs/notes/132-retakes-and-defuse-rounds-botfillrule-restartround.md) (2 KB)
- [Spawn camping: bots' spawns flip (`LightweightBotManager.TryGetUncampedSpawn`)](docs/notes/133-spawn-camping-bots-spawns-flip-lightweightbotmanag.md) (2 KB)
- [C4 detonation (`DemolitionBlast`, `c4_explosion.prefab`)](docs/notes/134-c4-detonation-demolitionblast-c4-explosion-prefab.md) (3 KB)
- [s&box 26.10.02: bool anim parameters can't be set true (`AnimBools`, `Tools/animgraph_flag](docs/notes/135-s-box-26-10-02-bool-anim-parameters-can-t-be-set-t.md) (5 KB)
- [Leg animation speeds (human bots and legacy `rigged_human.vanmgrph`)](docs/notes/136-leg-animation-speeds-human-bots-and-legacy-rigged-.md) (5 KB)
- [First-person body (`PlayerBody.FirstPersonBody`)](docs/notes/137-first-person-body-playerbody-firstpersonbody.md) (1 KB)
- [Prone body and first-person legs (`PlayerPawn.Prone.cs`, `ThirdPersonPronePose`, 2026-10-1](docs/notes/138-prone-body-and-first-person-legs-playerpawn-prone-.md) (2 KB)
- [First-person grime: blood and dirt on the gun and gloves (`FirstPersonGrime`, 2026-10-16)](docs/notes/139-first-person-grime-blood-and-dirt-on-the-gun-and-g.md) (3 KB)
- [First-person clothing (`ViewModelClothing`, `Code/Weapons/ViewModelClothing.cs`)](docs/notes/140-first-person-clothing-viewmodelclothing-code-weapo.md) (10 KB)
- [Third-person sprint carry (`ThirdPersonSprintPose`, 2026-10-14)](docs/notes/141-third-person-sprint-carry-thirdpersonsprintpose-20.md) (2 KB)
- [Third-person left hand (world models' `LeftHandIK`, players and bots)](docs/notes/142-third-person-left-hand-world-models-lefthandik-pla.md) (4 KB)
- [Bots aiming in (shouldered guns, `LightweightCombatBot`)](docs/notes/143-bots-aiming-in-shouldered-guns-lightweightcombatbo.md) (4 KB)
- [No Call of Duty names or markings](docs/notes/144-no-call-of-duty-names-or-markings.md) (3 KB)
- [Theater (match replays: `MatchRecorder`, `TheaterController`)](docs/notes/145-theater-match-replays-matchrecorder-theatercontrol.md) (11 KB)
- [Recon drone (`Tools/build_recon_drone.py`, `Tools/build_recon_tactical.py`)](docs/notes/146-recon-drone-tools-build-recon-drone-py-tools-build.md) (3 KB)
- [Recon octocopter (`ReconOctocopter`, flown from a tablet)](docs/notes/147-recon-octocopter-reconoctocopter-flown-from-a-tabl.md) (9 KB)
- [Nano Drone (`Tools/build_recon_nano.py`, `Tools/build_nano_equipment.py`)](docs/notes/148-nano-drone-tools-build-recon-nano-py-tools-build-n.md) (4 KB)
- [Campaign robot (`Tools/build_campaign_robot.py`)](docs/notes/149-campaign-robot-tools-build-campaign-robot-py.md) (4 KB)
- [Forest Base crown LODs (2026-10-20)](docs/notes/150-forest-base-crown-lods-2026-10-20.md) (0 KB)
- [Native HC1 reconnection (2026-10-20)](docs/notes/151-native-hc1-reconnection-2026-10-20.md) (1 KB)
- [Forest Base current native checks (2026-10-20)](docs/notes/152-forest-base-current-native-checks-2026-10-20.md) (31 KB)
- [Capture flag v2 (`capture_flag_v2`, 2026-10-30)](docs/notes/153-capture-flag-v2-capture-flag-sources-gameplay-capture-flag-v2.md) (1 KB)
- [Range target v2 (`range_target_v2`, no bullet marks, 2026-10-30)](docs/notes/154-range-target-v2-gunsmith-range-target-sources-gunsmithrange-target-v2.md) (0 KB)
- [Field device v2 (`field_device_v2`, the Tactical Defuse prop, 2026-10-30)](docs/notes/155-field-device-v2-weapons-c4-field-device-v2-sources-weapons-field-device-v2.md) (0 KB)
- [LPG cylinder v2 (`lpg_canister_v2`, Lowtide's shootable bottles, 2026-10-30)](docs/notes/156-lpg-cylinder-v2-models-props-lowtide-lpg-canister-v2-sources-lowtide-lpg-canister-v2.md) (1 KB)
- [Wall-buy board v2 (`wall_buy_board_v2`, Zombies' wall-buy stations, 2026-10-30)](docs/notes/157-wall-buy-board-v2-models-zombies-wall-buy-board-v2-sources-zombies-wall-buy-board-v2.md) (1 KB)
- [Ammo case v2 (`ammo_case_v2`, Zombies' Ammo Box stations, 2026-10-30)](docs/notes/158-ammo-case-v2-models-zombies-ammo-case-v2-sources-zombies-ammo-case-v2.md) (1 KB)
- [Cash Grab bag v2 (`cash_bag_v2`, the mode's objective, 2026-10-30)](docs/notes/159-cash-grab-bag-v2-weapons-special-cash-bag-cash-bag-v2-sources-weapons-cash-bag-v2.md) (1 KB)
- [Rifle suppressor v2 (`rifle_suppressor_v2`, the SCAR-H's Pattern 6 suppressor, 2026-10-30)](docs/notes/160-rifle-suppressor-v2-attachments-hc1-rifle-suppressor-v2-sources-weapons-rifle-suppressor-v2.md) (0 KB)
- [Equipment skins (`EquipmentSkins`, the gear picker, 2026-10-30)](docs/notes/161-equipment-skins-equipmentskins-the-gear-picker.md) (1 KB)
- [AN-M14 incendiary skins (`thermite_grenade_v2`, 2026-10-30)](docs/notes/162-an-m14-incendiary-skins-weapons-throwable-molotov-cocktail-thermite-grenade-v2.md) (1 KB)
- [Steel drum v2 (`oil_drum_v2`, Boxyard's drums, 2026-10-30)](docs/notes/162-steel-drum-v2-boxyard-oil-drum-v2-sources-boxyard-oil-drum-v2.md) (1 KB)
- [Burn drum v2 (`burn_drum_v2`, Riverside's drums, 2026-10-30)](docs/notes/163-burn-drum-v2-models-zombies-burn-drum-v2-sources-zombies-burn-drum-v2.md) (1 KB)
- [Station bin v2 (`station_bin_v2`, Railhead's 29 bins, 2026-10-30)](docs/notes/164-station-bin-v2-models-props-railhead-station-bin-v2-sources-railhead-station-bin-v2.md) (1 KB)
- [Traffic cone v2 (`traffic_cone_v2`, Boxyard's cones, 2026-10-31)](docs/notes/165-traffic-cone-v2-boxyard-traffic-cone-v2-sources-boxyard-traffic-cone-v2.md) (1 KB)
- [Town house doors v2 (`door_v2`, the town house's ten doors, 2026-10-31)](docs/notes/166-town-house-doors-v2-models-buildings-town-house-door-v2.md) (1 KB)
- [Riverside's cooler v2 (`cooler_v2`, by the dog run's gate, 2026-10-31)](docs/notes/167-riverside-cooler-v2-models-zombies-cooler-v2-sources-zombies-cooler-v2.md) (1 KB)
- [IBC tote v2 (`ibc_tote_v2`, Boxyard's totes, 2026-10-31)](docs/notes/169-ibc-tote-v2-models-props-boxyard-ibc-tote-v2-sources-boxyard-ibc-tote-v2.md) (1 KB)
- [Wheelie bin v2 (`wheelie_bin_v2`, Boxyard's bins, 2026-10-31)](docs/notes/170-wheelie-bin-v2-models-maps-boxyard-wheelie-bin-v2-sources-boxyard-wheelie-bin-v2.md) (1 KB)
- [Red crate v2 (`red_crate_v2`, Orion's crates, 2026-10-31)](docs/notes/171-red-crate-v2-models-props-orion-red-crate-v2-sources-orion-red-crate-v2.md) (1 KB)
- [Garden boulders v2 (`boulder_v2`, Cerro Blanco's bomb site B, 2026-10-31)](docs/notes/172-garden-boulders-v2-models-props-cerroblanco-boulder-v2-sources-cerroblanco-boulder-v2.md) (1 KB)
- [Riverside's teddy v2 (`teddy_v2`, by the dog run's gate, 2026-10-31)](docs/notes/173-riverside-teddy-v2-models-zombies-teddy-v2-sources-zombies-teddy-v2.md) (1 KB)
- [Mooring bollard v2 (`mooring_bollard_v2`, Lowtide's 12 quay bollards, 2026-10-31)](docs/notes/174-mooring-bollard-v2-models-maps-lowtide-mooring-bollard-v2-sources-lowtide-mooring-bollard-v2.md) (2 KB)
- [Reef Hall bench v2 (`bench_v2`, all 8 benches, 2026-10-31)](docs/notes/175-reef-hall-bench-v2-models-maps-reefhall-bench-v2-sources-reefhall-bench-v2.md) (2 KB)
- [Pallet truck v2 (`pallet_truck_v2`, Railhead's goods yard, 2026-10-31)](docs/notes/173-pallet-truck-v2-models-props-railhead-pallet-truck-v2-sources-railhead-pallet-truck-v2.md) (1 KB)
- [Stacked tyres v2 (`tyre_v2`, Railhead's goods shed, 2026-10-31)](docs/notes/176-stacked-tyres-v2-models-props-railhead-tyre-v2-sources-railhead-tyre-v2.md) (1 KB)
- [Tarp pile v2 (`tarp_pile_v2`, Orion's tarp pile, 2026-10-31)](docs/notes/176-tarp-pile-v2-models-props-orion-tarp-pile-v2-sources-orion-tarp-pile-v2.md) (1 KB)
- [Sewage power cabinet v2 (`power_cabinet_v2`, Sewage's three cabinets, 2026-10-31)](docs/notes/177-sewage-power-cabinet-v2-models-maps-sewage-power-cabinet-v2-sources-sewage-power-cabinet-v2.md) (1 KB)
- [Spillway control desks v2 (`control_desk_v2`, the control room's four desks, 2026-10-31)](docs/notes/178-spillway-control-desk-v2-models-props-spillway-control-desk-v2-sources-spillway-control-desk-v2.md) (1 KB)
- [Firing range bench v2 (`shooting_bench_v2`, the range's four benches, 2026-10-31)](docs/notes/179-firing-range-bench-v2-models-gunsmith-range-shooting-bench-v2-sources-gunsmithrange-bench-v2.md) (2 KB)
- [Railhead's skips (`models/props/railhead/skip`, Lowtide's skip on both sides of the yard, 2026-10-31)](docs/notes/180-railhead-skips-models-props-railhead-skip-sources-railhead-skip.md) (2 KB)
- [Reef Hall information stand v2 (`info_stand_v2`, all 3 stands, 2026-10-31)](docs/notes/181-reef-hall-information-stand-v2-models-maps-reefhall-info-stand-v2-sources-reefhall-info-stand-v2.md) (1 KB)
- [Riverdale's extinguishers (`extinguisher-v2`, all 22 in the hall, 2026-10-31)](docs/notes/182-riverdale-extinguishers-models-props-extinguisher-v2-sources-riverdale-extinguisher-v2.md) (2 KB)
- [Railing post fittings (`riverdale_parts._rail_fitting`, 2026-10-31)](docs/notes/183-railing-post-fittings-riverdale-parts-rail-fitting-sources-riverdale-rail-fittings-v1.md) (1 KB)
- [Riverdale's eye wash v2 (`eyewash_v2`, all 5 in the hall, 2026-10-31)](docs/notes/184-riverdale-eye-wash-v2-models-maps-riverdale-eyewash-v2-sources-riverdale-eyewash-v2.md) (1 KB)
- [Riverdale's notice board v2 (`notice_board_v2`, all 5 in the hall, 2026-10-31)](docs/notes/185-riverdale-notice-board-v2-models-maps-riverdale-notice-board-v2-sources-riverdale-notice-board-v2.md) (1 KB)
- [Riverdale's first aid cabinet v2 (`first_aid_v2`, all 4 in the hall, 2026-10-31)](docs/notes/186-riverdale-first-aid-cabinet-v2-models-maps-riverdale-first-aid-v2-sources-riverdale-first-aid-v2.md) (2 KB)
- [Cerro Blanco's extinguishers (`extinguisher-v2`, all 7, 2026-10-31)](docs/notes/187-cerro-blanco-extinguishers-models-props-extinguisher-v2-sources-cerroblanco-extinguisher-v2.md) (1 KB)
- [Cerro Blanco's courtyard parasols (`parasol_v2`, all 4, 2026-11-03)](docs/notes/188-cerro-blanco-courtyard-parasols-models-maps-cerroblanco-parasol-v2-sources-cerroblanco-parasol-v2.md) (1 KB)
- [Cerro Blanco's cafe chairs (`cafe_chair_v2`, all 20, 2026-11-03)](docs/notes/189-cerro-blanco-cafe-chairs-models-maps-cerroblanco-cafe-chair-v2-sources-cerroblanco-cafe-chair-v2.md) (1 KB)
- [Cerro Blanco's cafe tables (`cafe_table_v2`, all 8, 2026-11-03)](docs/notes/190-cerro-blanco-cafe-tables-models-maps-cerroblanco-cafe-table-v2-sources-cerroblanco-cafe-table-v2.md) (1 KB)
- [Cerro Blanco's cafe cups (`cafe_cup_v2`, all 16, 2026-11-03)](docs/notes/191-cerro-blanco-cafe-cups-models-maps-cerroblanco-cafe-cup-v2-sources-cerroblanco-cafe-cup-v2.md) (1 KB)
- [Cerro Blanco's cafe espresso machine (`espresso_machine_v2`, 2026-11-03)](docs/notes/192-cerro-blanco-espresso-machine-models-maps-cerroblanco-espresso-machine-v2-sources-cerroblanco-espresso-machine-v2.md) (1 KB)
- [Orion's whiteboard v2 (`whiteboard_v2`, the OPS room, 2026-11-03)](docs/notes/189-orion-whiteboard-v2-models-maps-orion-whiteboard-v2-sources-orion-whiteboard-v2.md) (1 KB)
- [Crosshair and hit marker colour picker (`HsvColorPicker`, 2026-11-03)](docs/notes/190-crosshair-colour-picker-hsvcolorpicker.md) (3 KB)
- [Riverdale's fire hose reels v2 (`hose_reel_v2`, all 5 in the hall, 2026-11-03)](docs/notes/191-riverdale-hose-reels-v2-models-maps-riverdale-hose-reel-v2-sources-riverdale-hose-reel-v2.md) (1 KB)
- [Zombie woman (`zombie_female_01`, the second zombie body, 2026-11-03)](docs/notes/195-zombie-female-01-meshy-scan-on-the-citizen-skeleton-tools-zombie-female-01-py.md) (3 KB)
- [Spillway's yard pallets v2 (`pallet_v2`, by container 02, 2026-11-03)](docs/notes/193-spillway-yard-pallet-v2-models-maps-spillway-pallet-v2-sources-spillway-cargo-props-v2.md) (2 KB)
- [Riverside's propane cylinders v2 (`propane_v2`, all 6, 2026-11-03)](docs/notes/194-riverside-propane-cylinders-v2-models-props-riverside-propane-v2-sources-riverside-propane-v2.md) (2 KB)
- [Spillway's canvas cover v2 (`canvas_cover_v2`, B2 loading deck, 2026-11-03)](docs/notes/196-spillway-canvas-cover-v2.md) (2 KB)

- [Riverside lawn chairs v2 (all 4, 2026-11-03)](docs/notes/196-riverside-lawn-chairs-v2.md) (1 KB)
- [Zombie in the open shirt (`zombie_male_02`, a third zombie body, random body per zombie, 2026-11-03)](docs/notes/197-zombie-male-02-meshy-scan-on-the-citizen-skeleton-tools-zombie-male-02-py.md) (4 KB)
- [Crosshair settings preview (`CrosshairPreview`, 2026-10-27)](docs/notes/151-crosshair-settings-preview-crosshairpreview-2026-10-27.md) (1 KB)
- [Spillway's yard hose v2 (`hose_coil_v2`, 2026-11-03)](docs/notes/197-spillway-yard-hose-v2.md) (2 KB)
- [Spillway's turbine wall vent v2 (`wall_vent_v2`, installed 2026-11-04)](docs/notes/198-spillway-wall-vent-v2.md) (2 KB)

- [Riverside supply crates v2 (all 12, 2026-11-04)](docs/notes/riverside-supply-crates-v2-20261104.md) (2 KB)

- [Riverside sandbags v2 (54 installed, 2026-11-04)](docs/notes/riverside-sandbags-v2-review-20261104.md) (1 KB)
- [Riverside speed-limit sign v2 (installed, 2026-11-04)](docs/notes/riverside-speed-sign-v2-review-20261104.md) (1 KB)
- [Riverside porch bulkhead lamp v2 (26 installed; old material deleted, 2026-11-04)](docs/notes/riverside-porch-light-v2-review-20261104.md) (2 KB)
- [Riverside cobra-head streetlight v2 (all four installed, 2026-11-04)](docs/notes/riverside-street-lamp-v2-review-20261104.md) (1 KB)
- [Riverside glazed pole insulator v2 (48 installed; old cylinders removed, 2026-11-04)](docs/notes/riverside-pole-insulator-v2-review-20261104.md) (2 KB)
- [Riverside porch drinks fridge v1 (installed, 2026-11-04)](docs/notes/riverside-drinks-fridge-v1-20261104.md) (2 KB)
- [Railhead east-yard cable reel v1 (installed, original wood finish, 2026-11-04)](docs/notes/railhead-cable-drum-v1-20261104.md) (2 KB)
- [Belltower beer-garden picnic tables v1 (all ten installed, old geometry removed, 2026-11-04)](docs/notes/belltower-picnic-tables-v1-20261104.md) (2 KB)
- [Riverside ice cabinet v1 (installed, 2026-11-04)](docs/notes/riverside-ice-cabinet-v1-20261104.md)
- [Riverside discarded tyres v1 (12 installed, 2026-11-04)](docs/notes/riverside-discarded-tyres-v1-20261104.md)
- [Spillway trench grates v1 (5 installed, 2026-11-04)](docs/notes/spillway-trench-grates-v1-20261104.md)
- [Spillway rooftop extractor fans v1 (7 installed, old assets retained by request, 2026-11-04)](docs/notes/spillway-roof-fans-v1-review-20261104.md)
- [Boxyard pipe stacks v1 (both installed, 2026-11-04)](docs/notes/boxyard-pipe-stacks-v1-20261104.md)
- [Boxyard gantry crane rebuild (all three installed; old geometry deleted, 2026-11-04)](docs/notes/boxyard-gantry-crane-v1-review-20261104.md)
- [Sewage crane blocks v1 (both installed, 2026-11-04)](docs/notes/sewage-crane-blocks-v1-20261104.md)
- [Sewage salvage drums v1 (all six installed, 2026-11-04)](docs/notes/sewage-salvage-drums-v1-20261104.md)
- [Orion yard lamp v1 (installed, 2026-11-04)](docs/notes/orion-yard-lamp-v1-20261104.md)
- [Orion shared dark operator chairs (all six installed; duplicate deleted, 2026-11-04)](docs/notes/orion-shared-operator-chairs-20261104.md)
- [Orion launch vehicle rebuild (installed, old version removed, 2026-11-04)](docs/notes/orion-launch-vehicle-v1-review-20261104.md)
- [Orion radome (keep original in use; retain rebuild as unused alternative, 2026-11-04)](docs/notes/orion-radome-v1-review-20261104.md)
- [Orion close-range yard case (keep both; original active, upgraded alternative retained, 2026-11-04)](docs/notes/orion-yard-case-reuse-v1-20261104.md)
- [Reef Hall bronze entrance planter v1 (2 installed, 2026-11-04)](docs/notes/reefhall-bronze-planter-v1-20261104.md)
- [Reef Hall upper-office workstation v1 (installed, old asset retained by request, 2026-11-04)](docs/notes/reefhall-office-desk-v1-review-20261104.md)
- [Boxyard southwest pallet stack (rejected; keep original texture active, 2026-11-04)](docs/notes/boxyard-pallet-stack-v1-review-20261104.md)
- [Orion launch-platform cage lights (4 installed, old assets removed by request, 2026-11-04)](docs/notes/orion-mount-lamps-v1-review-20261104.md)
- [Orion launch-mount service pedestals (4 installed, old assets removed by request, 2026-11-05)](docs/notes/orion-mount-pedestals-v1-review-20261105.md)
- [Reef Hall suspended whale skeleton (review candidate, original bone material retained, 2026-11-05)](docs/notes/reefhall-whale-skeleton-v1-review-20261105.md)
- [Riverside cash register v1 (installed, 2026-11-04)](docs/notes/riverside-register-v1-20261104.md)
- [Riverside camper rebuild (installed; old version deleted, 2026-11-04)](docs/notes/riverside-camper-v2-review-20261104.md)
- [Riverside office rooftop AC v1 (installed, 2026-11-04)](docs/notes/riverside-roof-ac-v1-review-20261104.md)
- [Lucky Stop fluorescent fixture v1 (both installed; old fixtures deleted, 2026-11-04)](docs/notes/riverside-fluorescent-v1-review-20261104.md)
- [Riverside T2 rooftop TV aerial v1 (installed; old aerial deleted, 2026-11-04)](docs/notes/riverside-tv-aerial-v1-review-20261104.md)
- [Riverside T2 trailer hitch v1 (installed; old hitch deleted, 2026-11-04)](docs/notes/riverside-trailer-hitch-v1-review-20261104.md)
- [Riverside water-tower tank A (installed; rejected B entirely deleted, 2026-11-04)](docs/notes/riverside-water-tank-v1-review-20261104.md)
- [Riverside guard-tower ladder v1 (installed; old wood/steel variants preserved for reuse, 2026-11-04)](docs/notes/riverside-tower-ladder-v1-review-20261104.md)
- [Riverside checkout counter v1 (installed; old version deleted, 2026-11-04)](docs/notes/riverside-counter-v1-20261104.md)
- [Riverside grocery shelving v1 (installed; old version deleted, 2026-11-04)](docs/notes/riverside-shelving-v1-20261104.md)

- [Riverside entrance gate v1 (rejected; original retained, 2026-11-04)](docs/notes/riverside-entrance-gate-v1-review-20261104.md)

- [Riverside trailer entry door v1 (T2 installed; old panel removed, 2026-11-04)](docs/notes/riverside-trailer-door-v1-review-20261104.md)
- [Lucky Stop roof sign v1 (installed; lighting toned down; old sign deleted, 2026-11-04)](docs/notes/riverside-shop-sign-v1-20261104.md)

- [Riverside passive roof vent v1 (T2 installed; old box deleted, 2026-11-04)](docs/notes/riverside-roof-vent-v1-review-20261104.md)

- [Riverside T2 precast entry unit v1 (weathered version installed; old boxes deleted, 2026-11-04)](docs/notes/riverside-t2-precast-entry-v1-review-20261104.md)

- [Riverside L1 roof ladder v1 (installed; original retained for reuse, 2026-11-04)](docs/notes/riverside-roof-ladder-v1-review-20261104.md)

- [Riverside shed downlight (approved bulkhead reused; installed, 2026-11-04)](docs/notes/riverside-shed-downlight-reuse-v1-20261104.md)

- [Riverside folded blue tarp v1 (installed; original retained, 2026-11-04)](docs/notes/riverside-folded-tarp-v1-review-20261104.md)

- [Riverside office porch railing (review candidate, 2026-11-05)](docs/notes/riverside-office-porch-rail-v1-review-20261105.md)

- [Riverside office door (approved trailer door reused; installed, 2026-11-05)](docs/notes/riverside-office-door-reuse-v1-review-20261105.md)

- [Riverside office Park Rules plaque (review candidate, 2026-11-05)](docs/notes/riverside-office-rules-plaque-v1-review-20261105.md)

- [Veridant operations lobby garden window � removed opaque backing, retained original; 2026-11-06](Sources/Veridant/operations-window-backing-v1/README.md)

- [Veridant east terrace lanterns � approved framing/post designs reused; originals retained, review pending, 2026-11-06](Sources/Veridant/east-lanterns-v1/README.md)

- [Veridant map-wide framed lanterns � all 32 active, originals retained, 2026-11-06](Sources/Veridant/all-lanterns-v1/README.md)
- [Veridant operations hall columns � smooth geometry and cylindrical stone UVs, originals retained, review pending, 2026-11-06](Sources/Veridant/hall-columns-v1/README.md)

- [Veridant courtyard stair rail � smooth tubes and side anchors, original retained, review pending, 2026-11-06](Sources/Veridant/court-stair-rail-v1/README.md)

- [Veridant cafe rooftop pergola � approved teak members/materials reused; original retained, review pending, 2026-11-06](Sources/Veridant/cafe-pergola-teak-v1/README.md)

- [Veridant playable lawn � texture swap rejected and reverted; scan retained, 2026-11-06](Sources/Veridant/garden-lawn-reuse-v1/README.md)

- [Veridant garden 3D grass � one-bed blade geometry review; original ground restored, 2026-11-06](Sources/Veridant/garden-grass-blades-v1/README.md)
