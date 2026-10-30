## Report a Bug (`BugReportPanel`)
- One panel, opened from the menu header and Settings (MainMenuRoot's) and from the pause menu (PausePage's). The user
  wanted it to match the other menus, so it uses MenuPage.scss's panel, section titles and buttons. Its categories
  are the settings page's choice buttons, its admin tabs are the gunsmith's segmented tabs, and its backdrop is the hub
  map picker's.
- The orange line along the top is a child (`.br-topbar`) over the window's 1px top border, as is QuitPrompt's.
- Reports only go into the reporter's own cookies (`hc1.bug.*`). Nothing is sent anywhere, and the admin tab (the
  developer's Steam ID, `AdminSteamId`) lists that machine's reports only.

