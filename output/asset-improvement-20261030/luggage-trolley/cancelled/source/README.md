# Railhead luggage trolley v2: review candidate

Created 2026-10-30 for the user's review. **Nothing plays this model yet.** The shipped
`models/props/railhead/luggage/luggage_trolley` is untouched and stays until the user says otherwise. Nothing is committed.

Why this prop: it's the most-seen weak standalone prop left. Four stand in the open on Railhead's concourse and platforms (the
scene names the model 8 times, a renderer and a collider each). The old one is blocky boxes under a stretched, stripy wood atlas.

The new one is built as a fabricator would: rolled channels, bolted deck boards with gaps, fish plates and gate sockets, leaf
springs on U-bolts, a steering bolster and turntable, a forked drawbar on pivot ears with a return spring, steel disc wheels on
ribbed tyres. The load is seven separate things: two framed, braced and steel-strapped crates with rope handles and waybills, a
fibre trunk in leather straps, a ribbed aluminium flight case, two hard suitcases with travel stickers and a luggage label, a
moulded case, and a strapped canvas roll.

- Triangles: 36,414 / 19,574 / 8,272 / 2,968 (LOD 0-3), against 43,680 and no LODs.
- Same origin and axes. Bounds are within 0.08 in of the old model's on every axis.
- Physics is the old model's, word for word, with its two hull files copied into this model's folder. Each load item fills its
  old collision box. Small hardware stands proud of the boxes (handles, rope loops, about 1.2 in at most), as the old model's did.
- One material, against two. Colour, normal and roughness are 4096; metalness and AO are 2048. That is more texture memory than the
  old 2048 set, and its cost hasn't been measured in the engine. If it matters, halving the atlas is the first thing to try.
- Density is about 11.5 px/in, lower than the capture flag's 24.5 and about the town house doors' outer leaf. Suitcases get 1.3x and
  fleet-stencil parts 1.5x, labels 2.6x; what's under the deck 0.55x; faces nobody can see 0.2x. There are 6,245 UV islands, so padding
  costs a lot: merging them is the cheapest way to sharpen this.
- Fasteners under about 0.5 in (deck bolts, rivets, nails) are painted, not modelled: `trolley.json` lists them for the paint stage.
- Every word is made up or plain German: "rhv" is the made-up operator Railhead's trains already carry, Hohenwald its made-up city.
  The old model's own markings ("rhv", "L-312", "Zul. Gesamtgew. 2000 kg") are kept. The tyres carry only a size, no maker.

## Files

- `trolley.py` builds, bakes and exports. `paint_trolley.py` paints. `render_trolley.py` and `make_sheets.py` make the matched
  sheets. `verify_trolley.py` checks the files. `run_all.ps1` runs them in order at idle priority; `blender_idle.ps1` runs Blender.
- Toolkit: `Sources/Gameplay/capture-flag-v2/`'s `build.py` and `paint.py`, imported, not edited.
- Output: `Assets/models/props/railhead/luggage_trolley_v2/`, `Assets/materials/railhead/luggage_trolley_v2/`.
- Work files, renders and sheets: `output/asset-improvement-20261030/luggage-trolley/`.
- Rerunning the build can change the unwrap, so bake and paint after it. The export refuses to run otherwise.

## Checked, from the files only

`verify_trolley.py` passes: `check_outward.py` reports 0 inside out on LOD 0, bounds match, physics and hulls are identical, every
texture and file the vmat and vmdl name exists, and the old model and the map are unchanged in git.

Stencils and stickers were read in the renders, and the direction of each was worked out (right x up = the face's normal).

## Not checked

- **Never compiled or seen in s&box.** No `_c` files exist for it. The images are Blender Cycles renders, which flatter any asset.
- The LOD switch distances (15, 40, 90) are estimates, and no LOD switch has been watched.
- Collision has only been compared as text, never walked into or shot.
- The renders' test platform isn't Railhead, so how it sits in the station's light is unknown.
- Tyre sidewall lettering hasn't been checked at close range.

## To adopt it

1. Point the 8 references in `Assets/scenes/maps/Railhead/railhead.scene` at `models/props/railhead/luggage_trolley_v2/luggage_trolley.vmdl`.
2. Change `MODEL` in `Tools/railhead_luggage.py` to match, or the next map rebuild puts the old one back.
3. Compile, check it in Railhead, and only then remove the old files if the user says so.
