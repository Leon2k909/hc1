using Editor;
using Sandbox;
using System;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Text.Json;

/// <summary>Temporary fixed-size game viewport for reproducible Forest Base runtime measurements.</summary>
public static class Hc1ForestBaseViewportQa
{
    private static Window window;
    private static SceneRenderingWidget viewport;
    private static SceneRenderingWidget previous;

    private sealed class MeasurementWindow : Window
    {
        public MeasurementWindow() : base(null) { }
        protected override void OnClosed()
        {
            RestorePrevious();
            viewport=null;window=null;
            base.OnClosed();
        }
    }

    [EditorEvent.Frame]
    public static void Update()
    {
        if(window==null||!window.IsValid) return;
        if(!Game.IsPlaying||Game.ActiveScene?.Name!="forestbase") { Close(); return; }
        if(viewport!=null&&viewport.IsValid) viewport.Scene=Game.ActiveScene;
    }

    [ConCmd("hc1_forestbase_viewport")]
    public static void Open(int width=1920,int height=1080)
    {
        if(width<=0) { Close(); return; }
        width=Math.Clamp(width,320,3840);height=Math.Clamp(height,180,2160);
        if(!Game.IsPlaying||Game.ActiveScene?.Name!="forestbase") return;
        Close();
        previous=Editor.Application.FocusWidget as SceneRenderingWidget;
        if(previous==null || !previous.IsValid)
            previous=SceneEditorSession.All.Where(s=>s.Scene?.Name=="forestbase")
                .Select(s=>s.OnFrameTo?.Target).OfType<Widget>()
                .SelectMany(w=>w.GetDescendants<SceneRenderingWidget>())
                .FirstOrDefault(w=>w.IsValid && w.Visible);
        if(previous==null) { Log.Warning("Forest Base viewport: no restorable game view found."); return; }
        window=new MeasurementWindow { Title="Forest Base runtime measurement",Size=new Vector2(width+20,height+45),DeleteOnClose=true };
        window.Canvas=new Widget(window);
        window.Canvas.Layout=Layout.Column();
        window.Canvas.Layout.Margin=0;
        viewport=new SceneRenderingWidget(window.Canvas) { Scene=Game.ActiveScene,FixedSize=new Vector2(width,height) };
        window.Canvas.Layout.Add(viewport);
        window.Show();
        Editor.GameMode.SetPlayWidget(viewport);
        previous.Hide();
        Log.Info($"Forest Base measurement viewport requested {width}x{height}; verify actual screen with perfcontext.");
    }

    [ConCmd("hc1_forestbase_viewport_close")]
    public static void Close()
    {
        RestorePrevious();
        if(window!=null&&window.IsValid) window.Close();
        viewport=null;window=null;previous=null;
    }

    private static void RestorePrevious()
    {
        if(previous!=null&&previous.IsValid)
        {
            previous.Show();
            if(Game.IsPlaying) Editor.GameMode.SetPlayWidget(previous);
        }
        previous=null;
    }

    [ConCmd("hc1_forestbase_viewportschema")]
    public static void Schema()
    {
        var types=new[] { typeof(SceneRenderingWidget),typeof(SceneEditorSession),typeof(Editor.GameMode),typeof(Window),typeof(Widget),typeof(GameEditorSession),typeof(SkyBox2D),typeof(GradientFog),typeof(DirectionalLight),typeof(ColorAdjustments),typeof(Tonemapping),typeof(Bloom),typeof(Editor.Application),typeof(DockWindow),typeof(DockManager) };
        var result=types.Select(t=>new {
            type=t.FullName,
            constructors=t.GetConstructors().Select(c=>c.ToString()).ToArray(),
            properties=t.GetProperties(BindingFlags.Public|BindingFlags.Instance|BindingFlags.Static)
                .Select(p=>new {p.Name,type=p.PropertyType.FullName,p.CanRead,p.CanWrite}).ToArray(),
            methods=t.GetMethods(BindingFlags.Public|BindingFlags.Static|BindingFlags.Instance|BindingFlags.DeclaredOnly)
                .Where(m=>!m.IsSpecialName).Select(m=>m.ToString()).ToArray()
        }).ToArray();
        File.WriteAllText(Path.Combine(Project.Current.GetRootPath(),"output/forestbase/viewport-schema.json"),
            JsonSerializer.Serialize(result,new JsonSerializerOptions{WriteIndented=true}));
        var editor=Editor.Application.Editor;
        var editorResult=new {
            editor=editor?.GetType().FullName,
            properties=editor?.GetType().GetProperties().Select(p=>new {p.Name,type=p.PropertyType.FullName}).ToArray(),
            focus=Editor.Application.FocusWidget?.GetType().FullName,
            sessionViews=SceneEditorSession.All.Select(s=>new{
                name=s.Scene?.Name,
                target=s.OnFrameTo?.Target?.GetType().FullName,
                views=(s.OnFrameTo?.Target as Widget)?.GetDescendants<SceneRenderingWidget>().Select(w=>new{type=w.GetType().FullName,w.Visible,scene=w.Scene?.Name}).ToArray(),
                gameTarget=s.GameSession?.OnFrameTo?.Target?.GetType().FullName
            }).ToArray(),
            methods=editor?.GetType().GetMethods().Where(m=>!m.IsSpecialName&&m.Name.Contains("Widget")).Select(m=>m.ToString()).ToArray()
        };
        File.WriteAllText(Path.Combine(Project.Current.GetRootPath(),"output/forestbase/editor-window-schema.json"),
            JsonSerializer.Serialize(editorResult,new JsonSerializerOptions{WriteIndented=true}));
    }
}
