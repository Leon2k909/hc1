using Sandbox;
using System.Threading.Tasks;

public class TestMapFetcher
{
    private static bool _trigger;
    [ConVar("dump_thieves")]
    public static bool Trigger
    {
        get => _trigger;
        set
        {
            _trigger = value;
            if (value)
            {
                _ = DumpAsync();
            }
        }
    }

    private static async Task DumpAsync()
    {
        try
        {
            var p = await Package.FetchAsync("thieves.aesthetic", false);
            var sb = new System.Text.StringBuilder();
            if (p == null) {
                sb.AppendLine("Package is null");
            } else {
                sb.AppendLine($"Title: {p.Title}");
                sb.AppendLine($"PrimaryAsset: {p.GetMeta<string>("PrimaryAsset")}");
                sb.AppendLine($"Type: {p.PackageType}");
                await Package.MountAsync("thieves.aesthetic", false);
                var scenes = ResourceLibrary.GetAll<SceneFile>();
                sb.AppendLine($"Total Scenes in ResourceLibrary: {System.Linq.Enumerable.Count(scenes)}");
                foreach(var s in scenes) {
                    if (s.ResourcePath.Contains("thieves") || s.ResourcePath.Contains("aesthetic")) {
                        sb.AppendLine($"MATCHING SCENE: {s.ResourcePath}");
                    }
                }
            }
            FileSystem.Data.WriteAllText("dump_thieves.txt", sb.ToString());
            Log.Warning("DUMP_THIEVES COMPLETE! Wrote to data/dump_thieves.txt");
        }
        catch (System.Exception e)
        {
            FileSystem.Data.WriteAllText("dump_thieves.txt", $"Error: {e.Message}");
            Log.Warning($"DUMP_THIEVES ERROR: {e.Message}");
        }
    }
}
