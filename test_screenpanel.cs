using Sandbox;
using Sandbox.UI;
using Facepunch;
using SWB.Base;

public class TestScreenPanel : Component
{
    protected override void OnStart()
    {
        var sp = Components.Get<ScreenPanel>();
        if (sp != null)
        {
            Log.Info($"ScreenPanel: Opacity={sp.Opacity}, ZIndex={sp.ZIndex}");
            // Let's see what properties it has
            var props = sp.GetType().GetProperties();
            foreach(var p in props) {
                Log.Info($"Prop: {p.Name}");
            }
        }
    }
}
