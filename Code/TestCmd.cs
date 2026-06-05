using Sandbox;
using System.Linq;
using System.Threading.Tasks;

public class TestCmd
{
    [ConCmd("find_aesthetic")]
    public static void FindAesthetic()
    {
        _ = RunAsync();
    }

    private static async Task RunAsync()
    {
        Log.Info("---- STARTING TEST ----");
        try
        {
            var p = await Package.FetchAsync("thieves.aesthetic", false);
            if (p == null) {
                Log.Info("Package is null!");
                return;
            }
            Log.Info($"Package Title: {p.Title}");
            Log.Info($"Primary Asset: {p.GetMeta<string>("PrimaryAsset")}");
            
            await Package.MountAsync("thieves.aesthetic", false);
            var scenes = ResourceLibrary.GetAll<SceneFile>().Select(s => s.ResourcePath).ToList();
            Log.Info($"Total scenes: {scenes.Count}");
            foreach (var s in scenes.Where(x => x.Contains("mall", System.StringComparison.OrdinalIgnoreCase) || x.Contains("thieves", System.StringComparison.OrdinalIgnoreCase) || x.Contains("aesthetic", System.StringComparison.OrdinalIgnoreCase)))
            {
                Log.Info($"Found matching scene: {s}");
            }
        }
        catch (System.Exception e)
        {
            Log.Info($"Exception: {e.Message}");
        }
        Log.Info("---- ENDING TEST ----");
    }
}
