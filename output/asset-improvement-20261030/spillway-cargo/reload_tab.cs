// Reloads the editor's Spillway tab from disk, only if it has no unsaved changes, so it holds the installed pallets.
var session = Editor.SceneEditorSession.All.FirstOrDefault(s => s.Scene?.Source?.ResourcePath == "scenes/maps/spillway/spillway.scene");
if (session is null) return "no Spillway tab";
if (session.HasUnsavedChanges) return "Spillway tab has unsaved changes: not reloaded";
session.Reload();
var pallets = session.Scene.GetAllObjects(false).Count(o => o.Name.StartsWith("Yard Pallet") || o.Name == "B2 Canvas Cover");
return $"reloaded; {pallets} pallets and covers in the tab";
