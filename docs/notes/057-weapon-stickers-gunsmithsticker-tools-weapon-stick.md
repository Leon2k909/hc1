## Weapon stickers (`GunsmithSticker`, `Tools/weapon_stickers.py`)
- The user asked for a weapon sticker (2026-09-29) and left the design to Claude. Gunsmith → CUSTOMIZE → Stickers lists
  them (the tab was already there, with no parts), and clicking the fitted one takes it off. They have no gameplay
  effect and no unlock.
- `Tools/weapon_stickers.py` draws four original die-cut vinyl stickers with numpy and PIL, from the game's own fonts:
  Razed Logo, Ace of Spades, Hot Rod Flames and Hazard Stripes (`--preview <png>` draws them on a sheet instead). For
  each it writes:
  - the artwork (`materials/stickers/<name>.png`, cropped to its cut), which is also the gunsmith's tile;
  - the cut (`_mask.png`) and the material (`.vmat`: alpha tested, satin vinyl);
  - a universal part (`gunsmith/stickers/<name>.gnsmth`).
  It also writes `prefabs/gunsmith/stickers/sticker.prefab`, which every sticker mounts.
- `GunsmithSticker` builds a quad in the artwork's shape, as large as the point's `StickerSize` allows. It sits 0.012
  off the surface and is drawn from both sides. It's a mesh rather than a decal: a decal would lag the viewmodel by a
  frame and paint the hands too.
  - The point's +X is the surface's outward normal, +Z is up and +Y = Z × X. So on the left side the artwork reads from
    the muzzle to the butt.
  - The camo loop skips it (`GunsmithLoadoutManager`: a sticker is vinyl over the paint).
  - Theater doesn't record it: `MatchRecorder` skips models built at runtime, since a replay can only name model files.
- Every gun but the SCAR-H has one Sticker point, on its left side, which the gunsmith's camera shows:
  - The ported guns' come from `kastov_prefabs.py` (`Prefabs.sticker`: the centre and outward normal in world model
    space, and the room). The viewmodel's point rides the `tag_sling` bone object like the charm's (the M18's rides
    its slide's, `Prefabs.sticker_bone`). The world model's
    is `WORLD_STICKER_LIFT` (0.018) further out, so it doesn't flicker into the gun at a distance.
  - The older guns' (M4A1, MP5, M700, Spaghelli, USP, USP-SD, 1911) were placed by hand in their prefabs. Their bone
    objects' frames differ gun to gun (the MP5's are placeholders at 0), so each viewmodel point is a child of the gun
    renderer's own object, in the model's bind space. `StickerBone` names the bone the sticker follows (`weapon_root`;
    the pistols' `slide`), through `GunsmithMw22Attachment.BoneDelta`. The world model points sit on the w_ models'
    surface plus 0.018. The Spaghelli's and 1911's w_ models are offset from their v_ ones (5.138 and 0.355 back).
  - Don't give a sticker point a `MountBone`: `GunsmithMw22Attachment.IsRemounted` takes any point with one for a
    non-M4 gun, which turns off the M4's factory piece swap.
  - The SCAR-H's model couldn't be exported to look for a flat spot, so it has no point yet.
  - The spots come from scans of each model's left side for flat, clear patches. In first person at the hip, the
    P90's and MP7A1's show only in part, and the AUG's and FAMAS F1's don't show at all. A holstered gun shows no
    sticker.
- Checked offline only: the artwork, and the spots in renders of the models (the side, and for the ported guns the
  hip view from the camera). The code compiled and hotloaded into a running game (2026-09-29), but no sticker has been
  seen in the engine yet. If the Stickers tab is empty, the new .gnsmth files weren't loaded: recompile them.

