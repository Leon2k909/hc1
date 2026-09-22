using Editor;
using Sandbox;
using System;

public static class __Exec_mud64bp25
{
	[ConCmd( "claude_exec_mud64bp25" )]
	public static void Run()
	{
		try
		{
			var z = Model.Load("zombie_project/models/zombie_male.vmdl"); var c = Model.Load("models/citizen/citizen.vmdl"); int match=0; var missing=new System.Collections.Generic.List<string>(); foreach(var b in c.Bones.AllBones){ if(z.Bones.GetBone(b.Name)!=null) match++; else missing.Add(b.Name);} Log.Info("ZM2 citizenBones="+c.Bones.AllBones.Count+" match="+match+" missing="+string.Join(",",missing)+" cgraph="+c.AnimGraph?.ResourcePath+" zbones="+string.Join(",", System.Linq.Enumerable.Select(z.Bones.AllBones, b=>b.Name)));
			Log.Info( "[EXEC mud64bp25] DONE" );
		}
		catch ( System.Exception __e ) { Log.Error( "[EXEC mud64bp25] ERROR=" + __e.Message ); }
	}
}
