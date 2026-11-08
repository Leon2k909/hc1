var view = Editor.SceneViewWidget.Current;
var vp = view?.LastSelectedViewportWidget;
var chain = new System.Collections.Generic.List<object>();
Editor.Widget w = vp;
int guard = 0;
while ( w != null && guard++ < 14 )
{
    chain.Add( new { Type = w.GetType().Name, w.Name, Size = w.Size.ToString(), Pos = w.Position.ToString(), Visible = w.Visible, Max = w.MaximumSize.ToString(), Min = w.MinimumSize.ToString() } );
    w = w.Parent;
}
return new { Scene = view?.Session?.Scene?.Name, chain };
