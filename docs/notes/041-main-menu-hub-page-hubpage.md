## Main menu hub page (`HubPage`)
- `.hub-container` is a row of three: `HubModeRail` (the "Play" tabs, 240 px), the featured screen (see Maps below),
  then `HubSidebar` (squad, then daily challenges). The featured screen is flex-grow, so it takes whatever the rail leaves.
- The rail's Multiplayer, Battle Royale and Zombies cards pick what the featured screen shows (`Selected` / `OnSelect`);
  Campaign is locked. Their art is the portrait mode art, cropped by a layer 375% of the card's height with a
  negative `top`: s&box's `background-position` percentages offset the image by a share of the box (`center 28%`
  pushed it down, leaving a gap), unlike CSS. The Zombies skull is `ui/modes/zombies_icon.png` (cropped from the
  minimap's), since Material Icons has no skull.
- The toggle in the rail's heading folds it to a 72 px strip of icons with hover labels (`.rail-tip`), saved in the
  `hc1.hub.rail.collapsed` cookie. Below 1900 wide (tight-nav) it stays folded, without the heading, because it's the
  featured screen's only mode switch. `collapsed` is set with `SetClass`: a Panel's `<root class="@(...)">` added the
  class but never took it off again. And in a `.razor` file, an auto-property initialised with a cookie read failed to
  compile ("An attribute argument must be a constant expression" in the generated code), so `_collapsed` is a field.
- `HubSidebar` (330 px, hidden below 1600 wide) is real data only. Daily challenges come from
  `Code/Stats/DailyChallenges.cs`: three a day from a fixed pool, picked by a hash of the UTC day so everyone gets the
  same set, reset at midnight UTC. Progress is kept in `hc1.daily.*` cookies, and the XP is paid through
  `Progression.AddXP` on the step that finishes a challenge. Kills and headshots count in
  `PlayerStatsRule.SendKillStat` (runs on the killer's machine; zombies don't raise `KillEvent`, so they don't count).
  Finished and won matches count in `EndOfMatchScreen.AwardXp`. The squad is the Steam `PartyRoom.Current`. It sits
  above the challenges and has a single INVITE FRIENDS row (`PartyPanel.InviteFriends()`) while there's room, as the user
  asked: a row per free slot looked like duplicate buttons.
- The squad card's cog sets who can join (`Code/Party/SquadPrivacy.cs`, cookie `hc1.party.privacy`, the player's own):
  Open (listed in s&box's party browser, as squads always were), Invite Only (unlisted, as s&box's own menu makes them)
  or Private. s&box takes a party's listing only when it's made (`PartyRoom.Create`'s `ispublic`), so a squad of one is
  made again at once, and one with others in it keeps its listing until the next squad ("Applies to your next squad").
  Private holds the party's `MaxMembers` at its size (`SquadPrivacy.Enforce`, also run in every scene by
  `SquadSocialSystem`) and puts a lock where the invite row was. Only the leader can change it. The invite row ends
  with the setting's icon, not its name, which pushed the row onto two lines in German. The menu comes last in the
  card's markup, because siblings draw in order and the squad's rows were drawn over it.
- Under the squad, the FRIENDS card lists the Steam friends the player has been in a match or a squad with
  (`RecentFriends`, cookie `hc1.friends.recent`, the newest 20) with their live status (`new Friend( id )`). A game can't
  read the Steam friends list or invite a chosen friend: `MenuUtility.Friends` / `InviteToParty` are in Sandbox.Menu,
  which games don't reference, and a `Friend` only answers for an id you already have (checked by reflection
  2026-09-27). So a row's INVITE opens s&box's invite overlay, like INVITE FRIENDS, and ALL FRIENDS opens s&box's own
  list (`Game.Overlay.ShowFriendsList`). These open in the editor too: s&box's menu pushes them the way it pushes the
  settings modal (read from its code 2026-09-27, not yet clicked there), so they have no `Game.IsEditor` check any more.
  `dev_friends_sample [rows]` fills it to check the layout (you, plus made-up offline rows; again to take them off);
  `dev_friends_clear` empties the card, real friends too.
- The header bell opens an empty NOTIFICATIONS panel ("No notifications"). It used to list hand-written "what's new"
  notes (`MenuNews`), which the user had removed (2026-09-26) because they read as fake update notices. Only real
  notifications belong there.
- Changing `MainMenuRoot`'s markup can hotload with "Lambda signature has changed", and then NavigationHost throws in
  `OnTemplateSlot` and the hub page goes blank. A fresh menu fixes it: `dev_scene scenes/menu.scene`.

