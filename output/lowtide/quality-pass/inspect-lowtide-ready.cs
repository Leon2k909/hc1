var session=Editor.SceneEditorSession.Active;
var view=Editor.SceneViewWidget.Current;
var renderers=session?.Scene.GetAllComponents<ModelRenderer>().ToArray();
return new{Game.IsPlaying,scene=session?.Scene?.Source?.ResourcePath,editor=session?.Scene?.IsEditor,
 dirty=session?.HasUnsavedChanges,viewMatches=view?.Session==session,camera=view?.LastSelectedViewportWidget?.Renderer?.Camera!=null,
 renderers=renderers?.Length,errors=renderers?.Where(r=>r.Model==null||r.Model.IsError).Select(r=>r.GameObject.Name).ToArray()};
