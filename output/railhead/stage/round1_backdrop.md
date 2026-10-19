# Round 1 report for the backdrop area (both passes)

SUMMARY: The city round the station is much closer to the brief at street level and from above. Pass 2 fixed every regression the art director listed and went through all ten fixes. All ten builds and their checks passed. Five things are only partly done (they're in brief_not_done), mainly the Rotunde card, which still reads as a pale blue-grey drum.

The magenta in the first pass's renders wasn't a backdrop fault. The renderer reads one stage plus Assets, so materials the props and materials agents had only staged showed as missing. For renders only, I copied those materials into my stage; the list is in backdrop/mirrored_for_renders.txt.

What changed this pass:
- **Shops, up close:** a near shop no longer has a painted back-wall picture. It has a real fitting: uprights every ~40 in and four or five shelves 10 in deep. Each shelf carries goods for that trade: crusted loaves, printed packs and jars, book spines, bottles and cans, flowers in buckets, or clothes on rails. There are price tickets on the shelf edges, a glass-fronted counter 36 in high with goods inside, a till, a wall clock and a chalk menu. Walls, ceiling and shelves are lit a little from within, so they read through the glass by day. Ceiling panels are softer. Far shops keep the picture.
- **Shopfronts:**
  - Frames and stall risers are dealt round by the shop's place in its row, so neighbours never match. Frames: black, green, bronze, burgundy, brown or white. Risers: polished granite, dark sandstone, green glazed tile or black.
  - Each riser has a zinc sill flashing.
  - The awning box is grey with a lip, and its canvas is lighter with a scalloped valance, now on 55% of shops.
- **Joinery and dressing:** the flaking trim_ paints are gone from the backdrop. Doors and window frames use clean satin bd_paint_ colours, and stone dressing no longer uses white paint. That removes the dark polka dots at 2 m.
- **Balconies:** the soffit is in the wall render, with a stone drip band and a zinc drip. The block consoles are now cast-stone S-scrolls. Window boxes have soil and mixed planting.
- **Upper windows:**
  - Most of the 16 variants now mirror the sky's blue-grey from top to sill, with a band of sunlit cornice opposite, so they no longer read as black holes.
  - Lit rooms glow through a self-illumination mask.
  - A tilted (Kipp) sash always takes the brightest variant.
- **Far city:** every range has its own eave and covering (60% slate, 25% weathered tile, 15% dark tile). Ridges carry brick stacks with pots every ~400 in, mansards have zinc dormers, most blocks have a rear wing into the courtyard, and courtyards have 1-4 trees. The south city beside the slope was a bare asphalt plain because a performance cut skipped every block there; it's now built as cheap perimeter ranges.
- **Woods and fields:** woods are dense lumpy crowns (radius 280-420, 9 facets, three jittered rings, smooth normals) in clumps 300 apart. They use a new canopy texture of leaf clusters, and the hills between the crowns carry that texture too. Fields are dry October pasture and stubble.
- **Rotunde:**
  - Stone piers now make up about 40% of the drum: glass 110 wide in a 183-in light, set 12 back in stone reveals.
  - Impost and sill bands, a 300-in arcade storey, masonry clerestory piers, stone pilasters and dark glass.
  - Rebaked at 128 samples, exposure -0.2.
  - The card now uses its own bd_rotunda_card material, shown mostly as baked. railhead_map's configure() repoints every rw_ paint, so the card needed a bd_ paint.
- **Sky:** cloud base 2100 m, near heaps half the size and further out, and no heap within 7 km and 30 degrees of the cab roads' axis. The blob over the cab road is gone.
- **Smaller fixes:** terracotta render toned down, roof tiles muted, and the tram shelters have a light frame, a white roof soffit and an LED strip.

Pass 1, for the total (its full report is in this brief):
- Shopfront depth: riser, transom lights, splayed lobby with terrazzo and mat, fascia and lightboxes, spotlights, shutters, bracket signs, posters and pilasters.
- Sooted top storeys, downpipes, gutters, party-wall stacks, ridge caps and aerials.
- House number plaques and bell panels.
- Every in-city block built; courtyard ground inside a pavement ring.
- Street lamps.
- The Rotunde's cone, lantern and arcade storey.
- The first sky tweak.
NEW FILES: D:/Documents/s&box projects/hc1/forked-shooter-main/Tools/railhead_backdrop_art.py (pass 1, extended in pass 2); D:/Documents/s&box projects/hc1/forked-shooter-main/Tools/railhead_rotunda_rebake.py (pass 1)
NOT DONE:
- The Rotunde card still reads as a pale blue-grey drum from the cab road. That's partly physical: the north face is in shade under a blue sky. The flat card also still shows from the high aerials (aerial_north), which an impostor can't avoid. A darker material tint or a warmer bake would make it look more like stone.
- The cable tray along the fascia line and snow guards on the roofs were left out. Hopper heads were also left out: a German swan-neck gutter outlet needs none.
- The woods still read slightly lumpy from close aerials, though they are much better than the bubble crowns.
- Tile roofs in strong sun are still fairly saturated, though they're muted by tint now.
- The tram stop and Platz were only lightly touched: the shelter's frame and lighting. The rest of the Platz furniture is unchanged.
NEXT:
- At integration, run railhead_backdrop_art.py with --force into Assets, then railhead_rotunda_rebake.py, then railhead_sky.py. Rebuild the map and redo the native indirect-light bake.
- Check in a game capture:
- that the bd_room_ / bd_shelf_ self-illumination reads as a lit shop and not as glowing walls (s&box's self-illum strength may differ from Cycles);
- the Rotunde card's brightness and tint (bd_rotunda_card: brightness 1.1, tint 0.5).
- If the Rotunde still reads too blue in-game, rebake it warmer (a small yellow tint on the sun, or exposure -0.4) or lower the card's tint.
