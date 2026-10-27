## Operator outfits (`OperatorOutfits`, `MilitaryUniform`, the Operators page)
- Blue Team has two outfits: the Military Operator (the army kit it always wore) and the Tactical Operator, which the
  user asked for on 2026-10-05 ("we only have british military operator one"). Red Team has three: the Field Operator
  and the Desert Operator, asked for next ("add another red team outfit too"), and the Militia Fighter (2026-10-13,
  "we only have british army ones atm").
- The Tactical Operator (`MilitaryUniformStyle.Tactical`) is a counter-terror team's dark kit: the same army garments
  dyed by `MilitaryUniform.TacticalTint`, plus the engine's balaclava under the helmet. A black helmet and plate carrier,
  dark grey camouflage, and black boots and fingerless gloves.
  - A garment's Tint multiplies its colour in linear space: the Field Operator's tints on military.png's colours give
    field_military.png's to within 2 sRGB steps. So each dye was worked out from the garment's colour in military.png
    to land on a target (the helmet 33,33,35, the carrier 36,36,38, the sleeves 49,50,52, the boots 30,29,29), and the
    gloves' from the Field Operator's undyed brown leather. The balaclava's own colour isn't known; it's only darkened.
  - The engine also has police versions of the helmet and vest (`tactical_helmet.clothing`, `tactical_vest.clothing`:
    the same meshes, other textures). Their textures aren't in sbox-public, so their colours couldn't be seen, and
    they're not used.
  - `MilitaryUniformStyle` is saved in prefabs by number: add new styles last. Each style's garments are listed in the
    code (`TacticalClothingPaths`) and in the prefabs' `MilitaryUniform` (`TacticalPieces`), as Field's are.
- The Desert Operator (`MilitaryUniformStyle.Desert`) wears the Field Operator's garments (its `FieldClothingPaths` /
  `FieldPieces`) dyed by `MilitaryUniform.DesertTint`, worked out the same way: brown camouflage (65,50,36 on the
  sleeves), a tan helmet (66,56,43) and vest (76,62,45) and brown boots (70,55,40). Its gloves stay the brown leather
  they are. Every dye is at most 1, since a tint over 1 brightens and may not hold.
- The Militia Fighter (`MilitaryUniformStyle.Militia`) is the one outfit that isn't army kit: s&box's citizen clothing
  in its own colours (`MilitiaClothingPaths` / `MilitiaPieces`). A green beanie, a bandana over the face, a flannel
  shirt, a black tactical vest, brown cargo trousers, black boots and fingerless gloves, with no tints.
  - The citizen vest's back patch reads POLICE. `Tools/militia_vest.py` copies its material with the lettering filled
    from the patch round it (`materials/operators/militia_vest.vmat`), and `MilitaryUniform.Refresh` gives that
    style's vest it (`MilitiaVestMaterial`). s&box ships the vest's colour map only compiled, so the script takes it as
    read out from the editor (its docstring has the snippet).
  - It has no portrait yet, so its card shows the Field Operator's.
  - Checked in offscreen renders of the body on 2026-10-13, the patch blank on the model. Not yet seen in first person
    (its sleeves and gloves through `ViewModelClothing`), on the Operators page or in a match.
- Who wears what:
  - A player wears the outfit they equipped for their team: EQUIP over the 3D preview on the Operators page (cookie
    `hc1.operator.<Team>`), else the team's first in `OperatorOutfits.All`. Their client sends its picks to the host
    (`Client.OperatorPicks`, as the clan tag goes), resent each second until they arrive.
  - The host picks the outfit (`HumanOutfitter.OutfitFor`; its own player's straight from its cookies) and broadcasts
    the style (`Wear`), so the body and the first-person legs match on every machine. Picks that arrive after a spawn
    dress the living body.
  - Each lightweight bot is issued one at random with its gun, kept per name all match (`BotIdentity.Outfit`), and set
    before networking, so clients spawn it with the uniform's style. A player-pawn bot gets one by its BotId.
- The Tactical and Desert Operators' portraits (`ui/operators/tactical.png`, `desert.png`) are stand-ins, not renders:
  `Tools/operator_portraits.py` (standard library only) recolours military.png with the same dyes, draws the
  Tactical Operator's balaclava with an eye slot and puts the gloves on. They aren't in the repository: the session
  that made them couldn't upload to the LFS store (Forbidden). Run the script and commit the PNGs from a machine that
  can push LFS. Until they're there, a card shows its team's first outfit's picture (`OperatorOutfit.Portrait`).
  Replace them with in-engine captures like the other two (512x640, transparent).
- The Operators page's text wasn't in the nine languages after the four columns; it is now.
- Made without the editor or a compiler (2026-10-05): none of it has been compiled or seen in-game. To check: the dyes
  in the 3D preview, the balaclava under the helmet (clipping), EQUIP, a client's pick reaching the host, a late
  joiner seeing the right kit, and bots in every kit.

