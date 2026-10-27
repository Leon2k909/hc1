## Controller in the menus (s&box's virtual cursor)
- On a controller, s&box's virtual cursor stands in for the mouse (`Input.EnableVirtualCursor`): the left stick moves
  the pointer, A clicks and the right stick scrolls. The header's LB / RB step through its tabs
  (`MainMenuRoot.ControllerNavRoutes`), WEAPONS included since 2026-10-15 (the user: RB "skips past it"): it loads the
  gunsmith's scene, whose header has LB / RB too (`GunsmithPanel.NavStep`), back out to PLAY and OPERATORS. Both start
  with the bumpers counted as held, so one still held through the scene load doesn't step on again. The D-pad drives the
  UIs that offer themselves to `PadNavigation` (below).
- `GameUtils.UpdateCombatMouseVisibility` turns the virtual cursor off in combat, where the stick moves the player, and
  since 2026-10-14 back on whenever the cursor shows (as does `TheaterController.ShowCursor`). Before, nothing turned it
  back on, so after the first match the left stick couldn't move the pointer in any menu (the user's report). The
  bumpers also skipped Ranked and Custom Game.
- Compiled with dotnet, not yet tried with a controller in-game.
- Jump is on the pad's A (2026-10-14, `ProjectSettings/Input.config`): it had no controller button. Only the project's
  default changes; a player who rebound Jump in s&box's bind editor keeps theirs.

### D-pad navigation (`PadNavigation`, `Code/UI/Navigation/`, 2026-10-14)
- The user: "the settings menu isnt compatible on controller, all UIs should be really well supported".
- `PadNavigation` is a GameObjectSystem (Stage.StartUpdate, before the game's components). It drives the UI that offers
  itself every Tick (`PadNavigation.Offer( panel, IPadScope, layer )`), the topmost when several are up: a dialog at
  100, a popup at 50, a page at 0.
  - The D-pad moves a focus to the nearest target that way (`PadNavMath.Pick`: the nearest edge, with sideways distance
    counted three times, so a move stays in its column). Held, it repeats after 0.35 s.
  - The pointer follows the focus (`Mouse.Position`, every frame), so A, the virtual cursor's click, presses what has
    the focus, and hover styles and sounds work as for a mouse. Moving the stick or the mouse hands the pointer back.
  - Left and right change an `IPadAdjustable` (a settings row) or a `CustomSlider` instead of leaving it
    (`PadNavMath.SliderStep`: about fifty presses end to end on the slider's own grid, four times as far once held
    1.2 s). B is the scope's `PadBack` (else Escape), LT and RT its `PadTab`.
  - Back from a popup or a dialog, the focus goes back where it was.
  - When the focused control goes away (A swapped the list it was in), it waits two frames for the new one to be laid
    out, then takes the target nearest where the old one was (`Replacement`, `PadNavMath.Distance`). If that target's
    list (the nearest panel round it with other targets) has a `pad-first` one, that wins: the fitted part, the slot
    just backed out of. Before 2026-10-15 it went to the page's first target: opening a gunsmith slot's parts on the
    right put the focus on the primary weapon on the left (the user's report).
  - Scopes on the same layer that sit inside each other are driven as one (`Chain`, innermost first): the outermost's
    panel is where the targets are, and B, LT, RT and the first focus ask the innermost scope first. That's how the
    main menu works: `MainMenuRoot` offers itself and each page offers itself inside it, so the D-pad reaches the
    header from the page, and the page still gets B and the triggers first. Among equals on a layer, the one offered
    first is under (a pause menu opened over the class menu wins).
  - `PadScope` is an `IPadScope` made of delegates (`First`, `Back`, `Tab`), for a UI that offers more than one scope
    (a page and the popups it opens). Keep it in a field.
- Targets: panels with the `pad-target` class, checkboxes, sliders (`CustomSlider` and the engine's `SliderControl`),
  or a `cursor: pointer` panel. The cursor style is inherited, so it's the first one down the tree; what's inside a
  target isn't another, unless it's marked `pad-target` (`CollectMarked`: a row's TUNE button, a card's favourite
  star). A cursor set only on `:hover` doesn't count: those need `pad-target`. `pad-skip` leaves a panel
  and everything in it out, so never put it on a modal's backdrop that holds the modal. The focus starts on a
  `pad-first` target, else the first that isn't inside a `pad-late` panel (`MenuTopbar`, a page's back button), else
  the first. The focused one gets `pad-focus`: Theme.scss rings it (2 px, the accent orange), and a UI can restyle it.
- The pad's menu buttons are actions in `Input.config`'s "Menus" group, hidden from the keybinds: MenuUp, MenuDown,
  MenuLeft and MenuRight (the D-pad), MenuSelect (A, for hints), MenuBack (B), MenuPrevTab and MenuNextTab (LT, RT).
  While a UI is driven with a controller, every action on those buttons is cleared each frame before the game reads it
  (`Input.Clear`): in the pause menu the D-pad dropped the gun (Drop) and opened the class menu (ChooseClass).
- What offers itself so far:
  - The settings page. Each row (`SettingEntry`) is one target: up and down move between rows, and left and right
    change it (a slider steps, a switch or a checkbox goes to its left, off, or right, on side, a row of choices to the
    next). A presses the row's control (`PadPoint`: the checkbox, the chosen option, the slider's thumb, the language
    field). LT and RT step through the categories. B clears a search, or saves and goes back ("/": the hub, or the
    pause menu's page). `PadHints` in the footer shows the buttons while a controller is in use.
  - The language list (B closes it), `DialogModal` (B cancels, or dismisses a notice), the bug report (B closes it, LT
    and RT change its admin tabs), and the pause menu's page (B resumes; its leave-match question traps the focus; B
    closes the party invite popup first).
  - The main menu (2026-10-15), all as one area with the header:
    - `MainMenuRoot`: B on any page but the hub goes back to the hub, and on the hub it's Escape, so the quit prompt.
      An open header menu (the bell's notifications, the round MORE button's menu) is a popup (layer 40) that B closes.
      `QuitPrompt` is a dialog (100) that starts on CANCEL.
    - The hub: the focus starts on the featured screen's PLAY / PLAY NOW (`pad-first`), LT and RT step through the
      rail's Multiplayer, Battle Royale and Zombies, and the playlists overlay and the zombies map picker are popups
      that B closes. The squad card's privacy menu and the party's invite popup are popups too. The hub's power button
      is a target.
    - Custom game: LT and RT step through MATCH, RULES and PLAYER (not for Zombies, nor while starting).
    - Profile (`BarracksPage`): B leaves a section for the profile page; in the emblem editor LT and RT change the
      picker's SHAPES / EMOJI / LETTERS tab (`EmblemEditor.CyclePickerTab`). Career Record: B goes back to the profile,
      and the service milestone cards are targets.
    - Sessions, Ranked, Operators, Store and the Theater page needed nothing of their own: their controls already
      have pointer cursors, and B goes back to the hub.
  - The gunsmith: the focus starts on the primary weapon's card, B steps back one layer as Escape does (the last step
    leaves), LT and RT switch BUILD and CUSTOMIZE. An open modal (builds, share, compare) is a popup (50) that
    B steps out of, and a build's name is a target (A renames it).
    - Opening a list puts the focus on its current choice (`pad-first`): a slot's fitted part, the weapon on the stand,
      the equipped perk or gear, the active class. Backing out puts it on the row it was opened from (the browser's
      `_lastCategory`, the panel's `_padReturn`).
    - TUNE (in a slot row and on the fitted optic), the weapon cards' chevrons and the favourite stars on weapons and
      camos are `pad-target` inside their rows.
    - Every part row is `pad-target`: a locked one has no pointer cursor, so the D-pad skipped it and never scrolled
      the list down to it. The tactical buy menu's owned and unaffordable items are `pad-target` for the same reason.
  - Also `pad-target` inside their rows (2026-10-15, from an audit of every pad-driven UI): the emblem editor's layer
    up, down and delete buttons, the squad bar's kick buttons, and the settings' English (UK) / (US) buttons.
  - The firing range's pause menu (`FiringRangeHud`): the focus starts on RESUME, and B resumes.
  - Colour pickers (`ColorPicker`: the gunsmith's custom paint and reticle colour, the settings, the emblem editor):
    left and right turn the hue field's hue (`ColorSlider`, an `IPadAdjustable`; a grey starts from full colour), and
    step each RGB box (`ColorChannel`, 0-255, five a press, twenty once held). The hue field's cursor now follows a
    colour set any way, not only by dragging.
  - In a match:
    - The class menu (`ClassSelect`): B steps back as Escape does (a slot's choices, the editor, then closed), LT and RT
      change the primaries' category. Its choices, slots, perks and buttons are `pad-target` (their pointer is
      hover-only).
    - The tactical buy menu: B closes it, LT and RT step through its categories.
    - The Zombies workbench: B steps back (a slot's parts, then closed), LT and RT change the gun; its rows and buy
      buttons are `pad-target`.
    - The map vote: the map cards (`MapVoteCard`, `pad-target`), the other modes and Leave game. B is Escape (the
      pause menu), which opens over it.
    - The end-of-match screen: the focus starts on CONTINUE or PLAY AGAIN; B continues where there's nothing to start.
  - The Theater's playback HUD: the focus starts on play/pause, LT and RT change the soldier followed (not in
    freecam), and B is Escape (back to the Theater page). While it's driven, A doesn't pause any more (Jump is on A,
    which is cleared for the HUD): press the play button.
  - To add a UI: offer it every Tick (a PanelComponent in OnUpdate), implement `IPadScope` or keep a `PadScope`, give
    targets without a steady pointer cursor `pad-target`, and mark where the focus should start `pad-first`.
- Text boxes (`TextEntry`) are targets since 2026-10-15, never the first focus: A focuses one (a class or build name,
  the import code, the bug report's title, the searches). Typing still needs a keyboard or the Steam on-screen keyboard:
  the game has none of its own.
- What the pad still can't do: drag (the gunsmith stage, the emblem canvas, the Theater timeline) or fly the Theater's
  freecam. The virtual cursor and the sticks still do those.
- The scoreboard isn't pad-driven. It shows while Score is held (the cursor and the virtual cursor come on then), and
  driving it would take A, B, the D-pad and the triggers from the game while it's held: no jumping or shooting with it
  up. On a pad, Score shares the left thumb with the D-pad, so it would want a press-to-toggle there. Left to the user.
- `dotnet run --project Tools/PadNavChecks` checks `PadNavMath` on a settings-like layout, the sliders' steps and the
  replacement for a focus that went away (30 checks, all passing). The settings part was compiled with dotnet and hotloaded into the user's match on 2026-10-14;
  the hotload warned "Lambda signature has changed" for PausePage, so reopen the pause menu (or restart play) if its
  buttons misbehave. The rest (2026-10-15) was compiled with dotnet only, with the editor shared with the user's match.
  `PadNavigation` is a GameObjectSystem, so changes to it only run once play restarts. None of it has been tried with
  a controller: every UI above, the header reached from a page, the popups' layers, and the triggers' tabs.
  The user then tried the gunsmith with a controller (2026-10-15) and found RB skipping WEAPONS and the focus jumping
  left on opening Muzzle. Those fixes, the nested targets, the text boxes, the colour pickers and the range menu
  compiled with dotnet and hotloaded into the editor with no errors; none of them has been tried with a controller yet.

