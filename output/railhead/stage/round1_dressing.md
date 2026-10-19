# Round 1 report for the dressing area (both passes)

SUMMARY: Across both passes, the critique's dressing fixes are done, as are all requests to dressing except two I declined (each noted under requests). All three checks pass: 0 spot problems, 0 spots cut off, 0 Retakes pairs in sight (the baseline had 2). Two things are still unverified: nothing has been seen in the game (no editor access, so no game captures or frame time), and street trees are left out.

Pass 2 changes, in Tools/railhead_map.py and Tools/railhead_dress_detail.py:
- See-through walls blocker: the shed haze volumes are pulled a few inches off every wall, the gable screen, the head building's front and the track bed (structure's report).
- Booking hall:
  - The pendants now hang 7.6 m up (rims at z 300).
  - They are scaled to 840 mm shades on a 40 mm tube, with a ceiling rose and a coupling.
  - Only the n 1450 row casts shadows.
  - The gallery's wire-hung pendants are replaced by four bracket lamps on its back wall's piers (two shadowed).
  - The hall's bracket lamps are moved to door height (3.2 m), and a matching set is added on the north wall.
- Footbridge:
  - Smaller, brighter, lower deck lights, so the deck gets pools of light.
  - LED lines under every stair handrail, with a light over each flight and at each stair's foot.
- Cab roads:
  - A wheel-track pair per lane, carrying the wear down the whole road.
  - Darker fresh-asphalt patch repairs with 50 mm seals, and gutter grime along both kerbs.
  - Grey wear spots on the zebra stripes and dashes where wheels run.
  - TAXI in 1.6 m road letters on the rank.
  - The rank's three estates are now taxis, with roof signs.
  - A Litfass advertising column with three posters, by the head building's corner.
- Goods yard:
  - A yellow-black hazard band along the apron.
  - Oil stains in front of the doors.
  - Bay numbers chalked on the bank face.
  - A third tyre stack and six empty pallets in the hero view.
  - Tyres redrawn with rounded sidewalls, tread grooves and a dusty grey rubber.
- Outer platform walls: a galvanised conduit at 3 m from pilaster to pilaster, with junction boxes and drops to every City-Light, the vending and ticket machines, and the help point; plus the SOS help pillar.
- Concourse: a timetable case at each island head, and DIN A1 notice frames (network map, notices) in the head building's free bays.
- Floors: polished walking lines on the platforms (aligned to the station's own paving texture) and trodden gum spots.
- Lighting and look: the kiosks' fascia lights; a distance fog in a paler blue-grey (backdrop's request).
- A fix to board(): every double-sided board drew both faces inward, so they read mirrored. Both faces now look outward and read correctly (the "Hohenwald Hbf" boards).

Pass 1 work (kept) is listed under changes.

Lights went from 112 at baseline to 168. 11 of mine cast shadows (14 after pass 1); props' signal box adds 7. The map is about 2.26 M triangles.
NEW FILES: D:/Documents/s&box projects/hc1/forked-shooter-main/Tools/railhead_dress_detail.py (pass 1, much extended in pass 2); D:/Documents/s&box projects/hc1/forked-shooter-main/output/railhead/stage/dressing/make_view.py (render-only helper: hard-links my stage plus the other agents' staged materials into dressing/_view so Cycles shows their materials instead of magenta; not for integration); D:/Documents/s&box projects/hc1/forked-shooter-main/output/railhead/stage/dressing/materials/railhead/dress/*.vmat (11 staged vmats)
NOT DONE:
- Fix 6, tree pits: left out. The cab road's glass canopy reaches e 1432, so a cloud oak at e 1460 would grow through it; the far pavement's balconies are close too.
- Fix 6, bicycles in the stands: requested from props, which has no bicycle function yet.
- Fix 10, game captures, frame time and haze tuning: not possible here. The editor and MCP are off-limits, so all judging is in Cycles. The haze stays at 0.035 until a capture shows whether it reads.
- Fix 8, cable tray at z 190 along the outer wall: left out. Every bay of that wall has either a window (z 140-290) or an arch (to z 210) the tray would cross.
- Fix 9, A1 frames in the wing wall bays between the windows: those bays are only 15 in either side of a pilaster. I used the head building's free bays instead.
- Footbridge deck walking line: tried, then removed. A glossier band only sharpened the deck stone's heavy speckle (that texture is structure's/materials').
NEXT:
- Integration: run railhead_map.py without --stage (it writes the dress vmats into Assets), compile, then rebake the native indirect light (DDGI) and the probes, since the hall, gallery, footbridge and stair lights and the haze volumes changed.
- Game captures, with a frame-time check of the 18 shadow-casting lights (11 of mine, 7 props'), of booking_hall, hall_floor, footbridge_deck, platform_c_north and cab_road. If the haze at 0.035 shows no shafts under the lattice, raise it in steps of 0.01 up to 0.06.
- Once props adds pendant_lamp( ..., shade_r, rod_r ), drop the scaling in railhead_map.pendant(). Place the bicycles in the Anlehnbuegel stands once props supplies a bicycle().
- If structure moves the platforms' or deck's paving into another model, update floor_wear()'s model name so polished_band's UVs still line up.
- Street trees: only if the backdrop agent provides a small columnar street tree that fits under the canopy line, or on the far pavement clear of the balconies.
