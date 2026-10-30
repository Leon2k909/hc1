## Menu nav click (`Tools/ui_sounds.py`)
- The gunsmith header's PLAY sounded like s&box's stock click (`ui.button.press`, Kenney's `drop_002`), and the user
  asked for a custom one (2026-09-29). The header's navigation click is `sounds/ui/menu/ui_nav_tab.sound`:
  - `Tools/ui_sounds.py` synthesises it. It's a rifle's selector lever clicking into its next detent, about 0.15 s, and
    the script's docstring has the layers.
  - There are three takes, picked at random, all equally loud. They sit 2 dB over the stock click, by K-weighted
    loudness.
  - It plays on the UI mixer through the event's `DefaultMixer`, so Settings' UI volume sets it.
  - A re-run rewrites the WAVs but keeps the `.sound` event.
- Where it plays:
  - The gunsmith plays it for every header link (`GunsmithPanel.GoToMenu`).
  - The main menu's nav tabs play it as they're pressed (`.gnav-item:not( .active ):active`'s `sound-in` in
    MainMenuRoot.razor.scss), all but the tab you're on. PROFILE's tab now gets `active` like the others (it was
    `selected`), so that rule covers it.
  - The hub's squad card plays it for its cog and the privacy options in the cog's menu (`HubSidebar.ClickSound`).
    The user heard the stock click there and wanted the menus' sounds to match. The card's INVITE FRIENDS, LEAVE and
    ALL FRIENDS use the menus' press (below).
- The rest of the menus use `ui_button_press` / `ui_button_hover` (see World sounds), which replaced s&box's stock
  `ui.button.press` / `ui.button.over`. Upstream's `ui_press` and `ui_action` went on 2026-09-30:
  - `sound-in: ui_press` (Buttons.scss, the map vote, the mode and map cards) is `ui_button_press`;
  - `.action:active`'s `ui_action` is `ui_nav_tab`;
  - Domination's and Hot Zone's capture cues (`DominationFlag`, `HardpointZone`) play `ui_button_press` and
    `ui_nav_tab`.
  Upstream's events set no mixer, so they went to the default one (Game, which the SFX slider sets). Nothing plays them
  now, nor upstream's `ui_hover`.
- Not yet heard in-game.

