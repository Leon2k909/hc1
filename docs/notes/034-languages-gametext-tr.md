## Languages (`GameText`, `Tr`)
- Settings → Game → Language is the game's own language (`GameSettings.Language`), separate from s&box's: English (UK),
  English (US), French, German, Spanish and Brazilian Portuguese, the ones the user asked for, then (asked for later)
  Italian, Polish, Russian, Ukrainian, Turkish, Japanese, Korean and Simplified and Traditional Chinese. A first run
  picks it from the system's culture (`GameSettings.GetDefaultLanguage`).
- The setting is a dropdown with a search box (`LanguagePicker` opens `LanguageMenu`), which the user asked for. Each
  language shows its own name with the English one beside it, sorted by its own name. The search matches either
  name, ignoring case and accents; a new language's accented letters go in `LanguageMenu.Accented` / `Plain`.
  - The list is a `Popup` in the root panel, outside the menu's stylesheets, so it sets its own fonts. s&box closes it
    on any press outside it.
  - MainMenuRoot, and over a match MainHUD and PauseMenuPanel, ask `LanguageMenu.CloseAny()` first, so Escape closes
    the list before the quit prompt or the pause menu.
- Code keeps its English and shows it through `Tr( "PLAY NOW" )`, or `Tr( "{0} XP TO LEVEL {1}", xp, level )` for text
  with values (`GlobalGameNamespace`, usable in any .cs or .razor). Text with no translation shows in English. Keys are
  the English, ignoring case. An ALL-CAPS key shows its translation in capitals (ß as SS: Mina has no capital ß), so
  the tables are written in natural case.
- Tables are in `Code/Settings/Text/*.cs`, one per area, as `["English"] = (French, German, Spanish, Portuguese)`:
  - `CommonText` holds menu names, buttons, modes and their descriptions, weapon classes, slots, ranks and teams. It
    wins over the other tables, so don't repeat its keys.
  - They're C# rather than JSON because hc1.sbproj's Resources wouldn't package a loose data file, and C# hotloads.
- The languages after those four have a table each, `Code/Settings/Text/Languages/<Language>.cs`, as
  `["English"] = "text"` (`GameText.OwnTable`), with every key of the column tables. So a new key needs a line in
  each of those nine files as well, or those languages show it in English. `check_translations.py` reports each one
  that's INCOMPLETE; `--missing <Language>` lists what its file lacks, and `--todo <Language>` gives that as JSON with
  the four columns' text for context.
- To add a language: append it to `GameLanguage` (last: `GameText.Current`'s range ends at the last value), then add
  it to `NativeName`, `EnglishName`, `OwnTable`, `GetDefaultLanguage` and `dev_language`, and give it a Languages file.
- s&box falls back to system fonts for glyphs Chakra Petch lacks, so Cyrillic, Japanese, Korean and Chinese render
  with no font changes. Turkish capitals keep the dotted İ and make the dotless ı an I (`GameText.Capitalise`). CSS
  `text-transform: uppercase` can't: the engine writes "Sesli" as "SESLI", not "SESLİ". Text written in capitals in the
  code gets the Turkish rules.
- Some translations are short on purpose, to fit fixed-width labels: the gunsmith's stat names (96 px: Polish fire rate
  "Tempo", Turkish mobility "Hareket") and its fire-mode column (Russian and Ukrainian semi-auto "Полуавт." /
  "Напівавт."). The hub rail sets a mode name over 14 letters smaller (`HubModeRail.Fit`).
- English (UK) and (US) differ by `GameText.Spellings` (colour/color, armour/armor, centre/center). Each English
  respells the code's text its own way, and a key matches in both spellings.
- Translate on the machine that shows the text, when it's drawn. Don't translate on the host for text sent to
  clients, and don't store translated text in fields. `GameText.SetLanguage` saves and calls StateHasChanged on every
  panel, so the whole screen changes at once.
- So toasts and notices carry the English and its values: `Toast.Show( "{0} Wins!", type, duration, args )` translates
  when it's shown (a `Team` argument shows its translated name), `GameMode.ShowToast` sends the English over its RPC,
  and the gunsmith's notices are a `GunsmithMessage` (English plus arguments; `.Shown` translates). Toasts the host
  builds with the values already in stay English until their RPC carries the arguments: Battle Royale's winner,
  Zombies' revive, Weapon Crate and not-enough-points toasts, and the Retakes site.
- Names aren't translated: players, weapons, attachments, camos, maps and "RAZED".
- A word with two meanings needs two keys. The volume slider "Master" is looked up as "Master volume"
  (`SettingEntry.FullTitles`), because "Master" is also the top rank.
- `python Tools/check_translations.py` lists:
  - literal text passed to Tr that no table has;
  - empty translations, placeholder mismatches and duplicate keys.
  It takes the first string literal in a `Tr( ... )` call as the key, so build a key in a property outside the call
  (`GunsmithPanel.DrawerCategory`). In-game, `dev_text_missing` lists what was shown in English, including text
  passed by value (`Tr( mode.Title )`).

