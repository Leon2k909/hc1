# Selectable tracer rounds

In **Gunsmith → Build → Ammunition**, choose **Tracer Rounds** for visible bullet
trails or **Standard Rounds** to disable them. The choice is unlocked immediately,
saves independently for each weapon and class, and is included in shared build
codes. It changes shot visuals without changing damage, recoil, or ammunition use.

The ammunition resource supports M4A1, SCAR-H, MP5, M700, Spaghelli, Colt 1911,
USP, and suppressed USP. The loadout manager creates their ammunition slot without
requiring a model socket. The `Ammunition` category is pinned to enum value 13;
the resource uses that numeric value so it also loads in editor sessions whose
enum-name converter predates the hotloaded category.

The locally controlled HC1 weapon reads its saved selection on deployment and
firing. Only tracer shots broadcast the visual event, using the shot's spread and
hit endpoint (or maximum range on a miss). Observers use the firing event rather
than their own saved loadout. SWB weapons receive their equipment resource from
the inventory and refresh their firing configuration before a shot. Bots keep
their own explicit ammo setting and do not inherit the human player's selection.

## Verification

- `hc1_gunsmith_ammo_test`: checks resource eligibility, equip/unequip, weapon and
  class isolation, share-code contents, HC1 tracer creation and endpoint,
  observer independence, and SWB selection/reset/bot isolation.
- With Gunsmith open, `hc1_gunsmith_ammo_ui_test` clicks both ammunition choices,
  checks saved state, and captures the two rendered states. It restores the
  original ammunition selection after the test.
- `hc1_tracer_qa` covers the default-off SWB hitscan/physical bullet gates and
  the lightweight bot's shot payload and visual effect.

Reports, screenshots, and the zero-error Code/Editor build log are in
`qa/tracer-rounds`. These checks ran in the live s&box editor; a two-client
multiplayer playtest has not been performed.
