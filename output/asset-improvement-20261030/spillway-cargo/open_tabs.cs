// The editor's open scene tabs, read only.
return Editor.SceneEditorSession.All.Select(s => new { s.Scene?.Name, Path = s.Scene?.Source?.ResourcePath, s.HasUnsavedChanges }).ToArray();
