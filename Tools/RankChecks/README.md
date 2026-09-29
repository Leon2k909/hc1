# Ranked progression checks

Run `rtk proxy dotnet run --project Tools/RankChecks/RankChecks.csproj` from the repository root.

The runner compiles the game's actual `Code/Stats/Rank.cs`, with an in-memory cookie store. It checks placement timing, result and contribution weighting, duplicate results, draws, promotion and demotion boundaries, Master, seasonal resets, queue tags and persistence. It does not modify the player's saved profile.

## Current rules

- New profiles begin Unranked, with five completed ranked matches required each season.
- Placement weighting is 70% match results and 30% score contribution. Draws count as half a win. Initial assignment ranges from Bronze III to Platinum I.
- The host compares each participant's match score with their team's average contribution. An average contribution is 0.5; twice the average is 1.0.
- After placement: wins add 12.5 percentage points, losses remove 10, and draws leave progress unchanged. Progress carries through promotion and demotion; Master is capped.
- Placement players search the Unranked pool; placed players search their earned tier. Completed ranked matches return to Ranked so the next search uses the updated tier.

Rank state currently uses the game's local cookie storage. Host-only result RPCs protect the match completion path; this is not a backend account ranking service.
