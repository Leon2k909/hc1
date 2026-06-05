using Sandbox;
using System.Reflection;
using System;
using System.Linq;

public class SettingsCheck {
    public static void Run() {
        var types = AppDomain.CurrentDomain.GetAssemblies()
            .SelectMany(a => a.GetTypes())
            .Where(t => t.Name.Contains("Video") || t.Name.Contains("Settings") || t.Name.Contains("Graphics"))
            .Select(t => t.FullName);
        
        foreach(var t in types.Take(20)) {
            Log.Info(t);
        }
    }
}
