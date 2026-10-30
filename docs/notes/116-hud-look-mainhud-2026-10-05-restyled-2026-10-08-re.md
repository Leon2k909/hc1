## HUD look (`MainHUD`, 2026-10-05, restyled 2026-10-08, redone 2026-10-09)
- The user asked for the HUD to look different (2026-10-05), and for the weapon list to show only while switching
  weapons. They turned down two looks with dark plates under the HUD: grey boxes over a pale map (2026-10-08), then
  charcoal plates in the menus' look ("i dont like the hud ui at all it needs a total revamp", 2026-10-09).
- So the HUD has no plates. It's crisp white Dinish text, icons and thin bars straight on the world, each with a tight
  dark halo (`$hud-halo`), so it reads over a pale floor and a dark one. The bars run on dark tracks with a darker edge.
  `Hud.scss` has the palette: `$hud-accent` is MenuPage.scss's `$menu-accent`. `$hud-plate` is only for the kill feed
  and the octocopter's feed.
  - Bottom left, `Vitals`:
    - health's number (38 px) left and armour's (blue) right, with the helmet's icon;
    - one 8 px bar for health, with ticks at each quarter and a ghost of what a hit took off, which drains 0.35 s later;
    - armour's 4 px bar under it;
    - health is white, amber under 60% (`hurt`) and red under 30% (`low-health`), where the bar pulses. With no armour
      the armour side dims (`no-armor`).
  - Bottom right, `Ammo`:
    - on top, the lethal and tactical equipment carried, each kind once with "×2" for two and its key;
    - the weapon's name and its fire mode (icon, FULL-AUTO, SEMI-AUTO or BURST, and the key that switches it), an orange
      rule, then the magazine's rounds (54 px), the chambered round raised in orange, and the reserve under them;
    - a thin bar for the magazine under it all.
    It's amber at a quarter of a magazine or less and red when empty. A knife or grenade shows its name alone.
  - The weapon list (`WeaponInfoComponent`), over the ammo: each slot's names and pictures, right-aligned, with its key.
    The slot in hand is white at full strength with an orange bar at its right, and the others dimmer. Each grenade is
    its own Equipment, so a kind carried twice is one row with "×2" (`EquipmentRow.Count`).
    - It shows only for 2.2 s after a switch (`ShowSeconds`): a new weapon in hand, a pickup, or the switch inputs
      themselves. Those are the slot keys, the wheel and the gamepad's NextSlot / PrevSlot.
    - It fades out but keeps its space, so nothing round it moves.
  - Top centre, `RoundStateDisplay`, only while Score (Tab) is held: your team's score, the clock and the enemy's, each
    team on a block of its colour and the clock on a dark one with an orange underline. The mode's name sits under it in
    spaced capitals, and Hot Zone's countdown under that. Free-for-all shows the clock only. `DefuseObjectiveHud` is at
    104 px to clear the strip.
- State classes are set in `Tick` with `SetClass`, since a `<root class="@(...)">` doesn't take a class off again.
  `EquipmentRow`'s `is-active` was a `<root class>`, so a row could stay lit after a switch.
- Checked on 2026-10-09 in a browser mockup of the real SCSS (flattened with Sass, rendered in headless Chromium at
  1920x1080) over the user's Cerro Blanco and Lowtide screenshots, in every state, and compiled with dotnet. Not yet seen
  in a match.

