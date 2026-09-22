using System;
using System.Reflection;
using Sandbox;

public class TestGraphics {
    public static void Run() {
        foreach (var prop in typeof(Sandbox.ScreenPanel).GetProperties(BindingFlags.Public | BindingFlags.Instance)) {
            Log.Info($"Prop: {prop.PropertyType.Name} {prop.Name}");
        }
        foreach (var field in typeof(Sandbox.ScreenPanel).GetFields(BindingFlags.Public | BindingFlags.Instance)) {
            Log.Info($"Field: {field.FieldType.Name} {field.Name}");
        }
    }
}
