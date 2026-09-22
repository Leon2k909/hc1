using Editor;
using Sandbox;
using System;

public static class __Exec_mud6420y4
{
	[ConCmd( "claude_exec_mud6420y4" )]
	public static void Run()
	{
		try
		{
			var m = Model.Load("zombie_project/models/zombie_male.vmdl"); var names = new System.Collections.Generic.List<string>(m.AnimationNames); Log.Info("ZM bones=" + m.Bones.AllBones.Count + " anims=" + names.Count + ": " + string.Join(",", names) + " graph=" + (m.AnimGraph?.ResourcePath ?? "none") + " head=" + (m.Bones.GetBone("head")?.Name ?? "-") + " bounds=" + m.Bounds);
			Log.Info( "[EXEC mud6420y4] DONE" );
		}
		catch ( System.Exception __e ) { Log.Error( "[EXEC mud6420y4] ERROR=" + __e.Message ); }
	}
}
