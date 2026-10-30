## Quitting (`QuitPrompt`): a game can't close s&box
- Escape on the main menu (`MainMenuRoot.HandleEscape`) closes one thing at a time: the language list, the bug report,
  the quit prompt, a header menu, the hub's playlists or zombies map picker, then the squad's privacy menu. With
  nothing open, Escape opens `QuitPrompt`, and so does the header's QUIT GAME. All checked in-game (2026-09-26), and
  QUIT TO S&BOX ended play mode in the editor.
- The user asked for a power button at the hub's bottom right: `.hub-power` in `.hub-footer`, one of the header's round
  buttons (`gnav-round-btn`) with its label above it. It opens `QuitPrompt` (`MainMenuRoot.OpenQuitPrompt`). Checked
  in-game 2026-09-27 (`dev_click hub-power`, then `dev_click qp-btn` to cancel): the button sits opposite "RAZED" and
  opens the prompt with QUIT TO S&BOX as its only option. Its hover label wasn't checked.
- Take Escape in a component's `OnUpdate` (here `MainMenuPanel`'s, over a match `MainHUD`'s), never in a Panel's
  `Tick`. After the scene's update, s&box's pause menu (in the editor, the editor) takes whatever Escape is left, and
  panels tick after that, so a Panel's `Input.EscapePressed` check never fires. The bug report's and the language list's
  own checks were dead for that reason.
- The user asked for a choice between leaving the game and exiting to the desktop, but s&box won't let a game close
  it. Checked in the engine source (sbox-public) and by reflection on 2026-09-27:
  - `Application.Exit` is internal, and so is the setter of `Application.IsStandalone`.
  - `ConsoleSystem.Run` only runs managed commands that aren't protected, and every native command is protected
    (`quit` and `exit` included). No managed command quits.
  - The API whitelist has no `Environment.Exit` / `FailFast`, `Process` or P/Invoke.
  - `Game.Close` goes back to s&box's menu, and in the editor it ends play mode. Only a standalone build (or a
    dedicated server) exits the app on `Game.Close`.
- So the prompt has one option, QUIT TO S&BOX. There's no greyed-out QUIT TO DESKTOP: the user had it removed. A
  standalone build labels the same option QUIT TO DESKTOP, because there `Game.Close` does exit to the desktop.
- The pause menu's quit button is `Game.Close` too, so it reads "Quit to s&box" (in a standalone build, "Quit to
  Desktop").

