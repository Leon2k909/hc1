# Round 1 report for the materials area (both passes)

SUMMARY: I worked through the art director's ten fixes for Railhead's materials in my stage only: nothing went into Assets, no models changed, and the editor wasn't touched. All three checks are still 0 / 0 / 0 on the final build.

**Evidence first.** The first pass's comparison renders were full of magenta because other agents' new paints had no material in that stage. I now render from merged folders: my build's models plus the props', backdrop's, structure's and dressing's staged materials, with hard links so it costs no space. The final renders have no magenta. Before and after use the same final build and lighting; only my textures differ, from the pass-1 snapshot (`p1snap`) to now.

**Main changes this pass:**
- **Lime plaster:** it finally changes measurably. Colour spread is std 9.1 (was 5.0) and the trowel-mark normal std 4.7 (was 1.1). Repairs are smoother and lighter, the hairline cracks are wider, and the sooted variant is an even cloud instead of the vertical streaks that looked like curtains.
- **Asphalt:** back to a dark binder (texture mean about 85, was 93), with two wheel paths per 4.9 m tile that are darker and glossier.
- **Riveted iron:** its wear now shows in the colour, not just the normal map: chalking, rust running from about a third of the rivets, soot and drip tracks (std 11.4 / 7.5 / 8.1, was 10.3 / 4.2 / 5.8).
- **Concrete sleepers:** grey again (median sRGB 145), with the grease darkening capped at 0.45.
- **Brick:** the wall-wide blotches that read as camouflage are gone. It now has 20 % purple burnt headers, lighter mortar, sand grains and iron spots. I checked it at the engine's real scale with my own tiling preview, because the Cycles renderer ignores the material's texture scale and draws brick at half size.
- **Terrazzo:** darker matrix, roughness 0.28 (was 0.22), wider brass strips. It no longer reads as a mirror in Cycles.
- **Smaller fixes:** facades, kerb and roof-glass soot runs as briefed. Containers lost the texture's own corrugation ribs, which doubled the props agent's new corrugation geometry and read as planks, and their rust is clustered instead of evenly spread.

**Two mistakes, both fixed:**
- My first texture draw went into a misnamed folder (`stage/materials/materials/materials/railhead`). I moved it into place and re-rendered.
- A test run wrote plaster textures into a new `D:\c\...` folder because of a path mix-up. I moved them to my scratchpad and removed the empty folders.

The game itself hasn't been captured with any of this: everything is judged in Cycles and in my tiling previews.
NEW FILES: Tools/railhead_finish.py (pass 1 rewrite, still untracked; pass 2 edits); output/railhead/stage/materials/materials/railhead/* (staged rw_ textures and vmats); output/railhead/stage/materials/materials/railhead/finish/* (lime x3, brick x2: PNGs and vmats); output/railhead/stage/materials/p1snap/ (pass-1 texture snapshot, for like-for-like before renders); output/railhead/stage/materials/merged_p1/ and merged_p2/ (hard-linked render stages: my build plus all agents' staged materials, with pass-1 or pass-2 textures); output/railhead/stage/materials/renders/pass2-before-final/, pass2-final/, pass2-compare/, pass2-texture-previews/
NOT DONE:
- Asphalt gutter stain and sealed cracks are not baked in. A tiling 4.9 m texture with random per-model UV offsets can't line up with a kerb, and dressing's road_wear() already places sealed cracks and patches as decals. I asked dressing for a gutter-grime decal strip instead. The wheel paths are also not tied to the real lane positions: same UV-offset reason.
- Sleeper oil band confined to the four-foot and rust at the clip seats: the sleepers' UVs are planar in world space, not per sleeper. The props' track fittings provide the clips.
- Facade ground-floor rustication: the 276 in anchored tile repeats every two storeys, so it would appear on the third floor too. The rw_facade_* paints are only used on the distant skyline model anyway; the cab-road tenements are backdrop's own paints.
- Brick soot 'per-tile band': left out, because it would put a soot band every 3.4 m up the wall. Soot is in the joints, and rw_brick_dark (already assigned by structure) covers the eaves.
- No engine captures: I am not allowed to touch the editor. Terrazzo gloss, roof-glass diffusion and the brick's real scale still need checking in a game capture. Cycles ignores g_vTexCoordScale, so brick shows at half size there, and it shows the dark-green columns as light grey through reflections, where the baseline game capture shows them dark green.
- rw_train_red panel-seam and skirt grime: not changed. A 96 in tile can't place a skirt.
NEXT:
- Integrate (commands above), rebuild railhead_map.py into Assets, redo the native indirect-light bake, then capture in the engine: terrazzo gloss in the hall, roof-glass diffusion, brick at real scale on the goods sheds, lime cloud and trowel marks under the hall lamps, asphalt wheel paths in sun.
- Structure: assign rw_lime_dado to the hall walls below z 60.
- Dressing: gutter-grime decals along the kerbs; use rw_setts in the goods yards; optionally per-carriageway UV offsets so the asphalt wheel paths sit in the lanes.
- Materials, next pass: per-object wear for trains (rw_train_red skirt grime and panel seams through UVs tied to each body); a two-scale variant of the steel's chalk field so the 128 in repeat is less visible up a 10 m column; possibly 4096 px for terrazzo if close-ups in the hall look soft in the engine.
