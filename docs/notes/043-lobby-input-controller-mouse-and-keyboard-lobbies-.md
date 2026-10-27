## Lobby input (controller / mouse-and-keyboard lobbies, `LobbyInputRules`, `LobbyInputGuard`)
- The user asked for controller-only and mouse-only lobbies, for players who only want to play in those (2026-10-14).
  Settings → Game → Lobby Input (`GameSettings.LobbyInput`): Any Input (the default), Controller Only or Mouse &
  Keyboard Only. It's saved by number, so a new value goes last.
- A lobby carries its rule in its lobby data, `input` = `pad`, `kbm` or `any` (`LobbyInputRules.Stamp`, called just
  before `Networking.CreateLobby`, which copies `Networking.SetData`'s data into the new lobby):
  - `GameNetworkManager` stamps every match a player hosts: the custom game page's INPUT (MATCH tab, starting at the
    player's setting), else the host's setting. Ranked's `HostRankedMatch` stamps the setting.
  - A lobby with no key (an older build's, or one from the editor's Start Hosting) is open to all.
- Joining (`LobbyInputRules.CanJoin`): with a preference, only lobbies with that rule. With Any Input, open lobbies and
  those for what the player is using now (`Input.UsingController`: the last button pressed; a pad's buttons and
  triggers count, a key or a mouse button the other way, and moving a stick or the mouse alone neither).
  - SESSIONS lists every lobby, the joinable ones first. A restricted one has a controller or mouse icon, and one the
    player can't join is dimmed. Its details show INPUT and why, and Join Session reads the rule and does nothing.
  - Ranked's matchmaking skips lobbies it can't join.
- Invites and a squad following its leader skip both, so in a match `LobbyInputGuard` (a GameObjectSystem) holds every
  machine's player to the rule:
  - The host syncs it (`GameMode.LobbyInputRule`, FromHost) from its lobby data. Clients don't read their own: the
    engine keeps lobby data after leaving a lobby (nothing in sbox-public's networking code clears it, and a new
    lobby's handshake only overwrites the keys it has), so a key from an earlier lobby can linger.
  - Only play counts: alive, with no pause menu, class or buy menu, chat, scoreboard, gunsmith or win banner open. A
    button of the right input starts the count again.
  - After 1 s with the other input, `LobbyInputOverlay` warns (in MainHUD while there's a pawn), with a countdown for
    clients. After 15 s (`Grace`) a client disconnects to the menu, which says why (`MainMenuRoot.PendingNotice`: a
    DialogModal with only OK, since DialogModal now hides Cancel when it's given no text for it).
  - The host is only warned: taking it out would end the match or hand it to another player.
- Ranked: `HostRankedMatch` sets `ranked_closed` to 0 before making its lobby. A finished ranked match sets it to 1,
  every client gets it, and the engine copies a machine's leftover lobby data into the next lobby it makes, so the
  next ranked lobby that host or any of its players made was closed to matchmaking from the start.
- Compiled with dotnet on 2026-10-14 (0 errors), with its text in every language (`check_translations.py` at its 22
  problems from before, none new). The open editor stalled at 21:55 that day, before the last of it, so it hasn't
  compiled there. Nothing has been seen in-game: the setting, the browser's icons and details, the custom game's
  INPUT, the warning and the leave, the menu's notice, a host migration keeping the rule, and two machines (one on a
  controller, one on mouse and keyboard).

