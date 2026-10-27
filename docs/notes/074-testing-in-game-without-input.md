## Testing in-game without input
Dev console commands (`Code/GameLoop/DevCommands.cs`): `dev_quickplay`, `dev_zombies [map]` (e.g. `innocent`),
`dev_zombie_hit [damage] [head]` (hits the nearest zombie as you through `ZombieAI.OnDamage`, default 1000; head 1 for a
headshot), `dev_give <weapon>`, `dev_force_aim 1`,
`dev_no_damage 1`, `dev_reload`, `dev_aim_offset x y z` (live, not saved), `dev_aim_info`,
`dev_optic <name>` (fits an optic and saves it to the loadout), `dev_optic_correction x y z` (live, not saved),
`dev_corner [radius] [side]` (moves you to the nearby spot where corner slicing cants the gun most, and logs the cant),
`dev_force_move 1` / `-1` (walks forward/back without input; reset to 0 after), `dev_legshot [damage]` (a hardcore
leg hit on yourself, default 1 damage, for testing the limp), `dev_fall [damage]` (fall damage on yourself, default 10),
`dev_jumps [count]` (jumps again the moment you land, for testing jump stamina), `dev_prone [count] [interval]` (presses
Prone that many times, default 6 at 0.2 s, logging prone stamina), `dev_mantle` (mantles the ledge you're looking
at, as if you'd pressed Jump while moving at it, and logs the plan or why there's none), `dev_use` (presses E on whatever
you're looking at), `dev_escape` (presses Escape as the next update starts, `DevEscapeSystem`: the bridge runs
commands at any point in the frame, and setting `Input.EscapePressed` straight from one often came too late),
`dev_menu <route>` (opens a main menu page), `dev_click <class[.class]> [n]` (clicks the nth
visible UI element with those classes, e.g. `dev_click squad-cog`), `dev_scene <path>` (loads a scene while playing),
`dev_thumbnails <weapon> [filter] [probes]` (writes the gunsmith's attachment pictures to the data folder),
`dev_language <uk|us|fr|de|es|pt|it|pl|ru|ua|tr|ja|ko|zh|tw>` (switches and saves the game's language; "uk" is
English (UK), so Ukrainian is "ua"), `dev_text_missing` (logs the text shown
in English since the language was last set), `dev_voices_sample` (made-up rows in the HUD's list of who's talking;
again to take them off).
Bots and battle royale (`Code/GameLoop/Bots/BotDevCommands.cs`): `dev_mode <mode> [map]` (e.g. `dev_mode battle_royale
flatgrass`), `dev_bots [count] [radius]`, `dev_bots_clear`, `dev_bot_styles` (each bot's play style and move),
`dev_perf [frames]` (logs frame and bot times),
`bot_lod_off 1` (turns the bots' savings off to compare; respawn the bots after), `dev_zone_next` (skips the zone's
hold or shrink), `br_bots <n>` (bots in the next battle royale, saved; 0 = the mode's 40) and `br_map <scene path>`
(the hub's map pick, saved). `dev_mode battle_royale ridgeback` starts one on Ridgeback.
The bridge's held `Jump` input doesn't reach the pawn's fixed-update movement, so use `dev_jumps` rather than
simulate_input.

