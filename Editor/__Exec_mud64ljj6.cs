using Editor;
using Sandbox;
using System;

public static class __Exec_mud64ljj6
{
	[ConCmd( "claude_exec_mud64ljj6" )]
	public static void Run()
	{
		try
		{
			var z = Model.Load("zombie_project/models/zombie_male.vmdl"); foreach(var p in new[]{"models/citizen_human/citizen_human_male.vmdl","models/citizen_human/citizen_human.vmdl","models/citizen_human/citizen_human_female.vmdl"}){ var c=Model.Load(p); if(c==null||c.IsError){Log.Info("ZM3 "+p+" missing");continue;} int miss=0; foreach(var b in z.Bones.AllBones) if(c.Bones.GetBone(b.Name)==null) miss++; Log.Info("ZM3 "+p+" bones="+c.Bones.AllBones.Count+" zombieBonesMissingInIt="+miss+" graph="+c.AnimGraph?.ResourcePath);}
			Log.Info( "[EXEC mud64ljj6] DONE" );
		}
		catch ( System.Exception __e ) { Log.Error( "[EXEC mud64ljj6] ERROR=" + __e.Message ); }
	}
}
