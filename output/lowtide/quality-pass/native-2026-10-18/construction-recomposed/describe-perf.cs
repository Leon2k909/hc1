return typeof(Editor.Mcp.PerfTools).GetMethods(System.Reflection.BindingFlags.Public|System.Reflection.BindingFlags.Static).Select(m=>m.ToString()).ToArray();
