using Sandbox;

public class TestGraphics {
    public static void Run() {
        Log.Info(typeof(Sandbox.Game).Assembly.GetTypes().FirstOrDefault(t => t.Name.Contains("VideoSettings"))?.FullName ?? "None");
    }
}
