## Hotload: editor code can't use a type new to the game code
- Editor tools that name a type added to the game code in the same change break the hotload. The editor assembly
  compiles against the new game code, then fails to load ("Enrollers register event for tools": TypeLoadException),
  and the new game assembly never goes live: the match plays on with the old code.
  Reach the new type by reflection (`Editor/Hc1M16OpticQa.cs` reads `ManualOffset.OpticSightLines` that way), or add
  it in one hotload and the tool in the next.
- Fixing the editor file alone doesn't bring the game code in: change any game file (touching it is enough) so the
  game assembly rebuilds.
- A C# `record` in editor code failed after s&box's codegen ("type not found"). Use a class.

