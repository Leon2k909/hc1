# Profile, checkbox and language validation

Verified in the running s&box editor on 28 September 2026.

- The header player badge opens `/barracks` and displays the Profile page.
- The Gunsmith header also targets `/barracks` (source check).
- Selecting French, German, Spanish, Brazilian Portuguese, English (US) and English (UK) through the live language menu changes the Settings heading immediately.
- Each choice is written to `gamesettings.json` automatically and survives `GameSettingsSystem.Load()`.
- The original language was restored after the checks.
- The checked Picture-In-Picture Scopes control has a 20 × 20 square. The screenshot confirms its tick is centred and contained.
- `python Tools/check_translations.py`: 1,087 keys, 0 consistency problems across the existing translation tables.
- `dotnet build Code/hc1.csproj --no-restore -v:q -clp:ErrorsOnly`: 0 errors (151 warnings, including existing dependency and file-copy warnings).

Screenshot: `settings-checkbox-verified.png`.
