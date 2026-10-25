using Editor;
using Facepunch;
using Sandbox;
using Sandbox.Events;
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text.Json;
using GameMode = Facepunch.GameMode;

/// <summary>Controlled local integration checks through real actions and production timers.</summary>
public static class Hc1ForestBaseBombQa
{
	internal static Scene scene;
	internal static PlayerPawn player;
	internal static DefuseC4 carried;
	internal static TimedExplosive bomb;
	internal static int site, initialWins;
	internal static string stage="idle";
	internal static readonly List<object> events=new();
	private static readonly Dictionary<Component,bool> disabled=new();
	private static readonly Dictionary<LightweightCombatBot,(float sight,float engage,float speed,bool god)> bots=new();
	private static Team originalTeam;
	private static bool originalFrozen;
	private static bool originalGod;
	private static DateTime started;
	private static Vector3 target;
	private static bool placed;
	private static DateTime lastWrite;
	private static ForestBaseBombInput input;
	private static string Folder=>Path.Combine(Project.Current.GetRootPath(),"output/forestbase");

	[ConCmd("hc1_forestbase_bomb_prepare")]
	public static void Prepare(int index=0)
	{
		if(!Game.IsPlaying || Game.ActiveScene?.Name!="forestbase" || GameMode.Instance?.Ident!="defuse" || !Networking.IsHost)
		{ Log.Warning("Forest Base bomb QA requires a local Forest Base Defusal match."); return; }
		Restore();
		scene=Game.ActiveScene; player=Client.Local?.PlayerPawn;
		if(!player.IsValid() || player.HealthComponent.State!=LifeState.Alive)
		{ scene=null; Log.Warning("Forest Base bomb QA needs a living local player."); return; }
		site=index==0?0:1; target=site==0?new Vector3(-760,1000,2):new Vector3(-390,-1120,2);
		originalTeam=player.Team; originalFrozen=player.IsFrozen; originalGod=player.HealthComponent.IsGodMode;
		player.HealthComponent.IsGodMode=true;
		started=DateTime.UtcNow; events.Clear(); placed=false; bomb=null; carried=null;
		initialWins=GameMode.Instance.Get<RoundBasedTeamScoring>()?.RoundWinHistory.Count??0;
		stage="waiting-live-round"; Record("prepared",new { site,target=target.ToString() });
		input=new ForestBaseBombInput(scene);
		PauseBots(); Save();
	}

	[ConCmd("hc1_forestbase_bomb_hold")]
	public static void Hold(string action="Attack1",float seconds=6)
	{
		if(input==null||!player.IsValid())return;
		input.Release();
		input.Action=action;input.Until=DateTime.UtcNow.AddSeconds(Math.Clamp(seconds,0.1f,20));
		Record("input-hold",new { action,seconds });
	}

	[EditorEvent.Frame]
	public static void Tick()
	{
		if(scene==null)return;
		if(!Game.IsPlaying || scene!=Game.ActiveScene || !player.IsValid()) { Restore(); return; }
		using var scope=scene.Push();
		PauseBots();
		if(stage=="waiting-live-round" && GameMode.Instance.Get<FreezePlayers>() is not { Active:true })
		{
			player.Team=Team.Terrorist; player.IsFrozen=false; player.WorldPosition=target;
			player.CharacterController.Velocity=Vector3.Zero; placed=true;
			carried=player.Inventory.Equipment.Select(x=>x.GetComponentInChildren<DefuseC4>(true)).FirstOrDefault(x=>x.IsValid());
			if(!carried.IsValid())
			{
				var resource=ResourceLibrary.GetAll<EquipmentResource>().FirstOrDefault(x=>x.ResourceName.Equals("c4",StringComparison.OrdinalIgnoreCase));
				carried=player.Inventory.Give(resource,true)?.GetComponentInChildren<DefuseC4>(true);
			}
			if(carried.IsValid())player.Inventory.Switch(carried.GetComponentInParent<Equipment>());
			stage="settling"; Record("positioned",new { player=player.GameObject.Id,team=player.Team.ToString() });
		}
		if(stage=="settling" && carried.IsValid() && carried.CanPlant())
		{ stage="ready-to-plant"; Record("can-plant",new { grounded=player.IsGrounded,plantTime=carried.PlantTime,zone=player.GetZone<BombSite>()?.Index }); }
		if(carried.IsValid() && carried.IsPlanting && stage=="ready-to-plant")
		{ stage="planting"; Record("plant-start",new { progress=carried.Progress }); }
		if(stage=="planting" && carried.IsValid() && !carried.IsPlanting)
		{ stage="ready-to-plant"; Record("plant-cancelled",new { remainingBombs=scene.GetAllComponents<TimedExplosive>().Count() }); }
		if(!bomb.IsValid() && stage=="planting")
		{
			bomb=scene.GetAllComponents<TimedExplosive>().FirstOrDefault(x=>x.Active&&!x.IsDefused);
			if(bomb.IsValid()) { stage="planted"; Record("planted-observed",new { zone=Zone.GetAt(bomb.WorldPosition+Vector3.Up*2).Select(x=>x.GetComponent<BombSite>()?.Index).Where(x=>x.HasValue).ToArray(),position=bomb.WorldPosition.ToString() }); }
		}
		if(stage=="ready-to-defuse" && bomb.IsValid())
			player.EyeAngles=Rotation.LookAt(bomb.WorldPosition+Vector3.Up*4-player.CameraGameObject.WorldPosition).Angles();
		if(bomb.IsValid() && bomb.DefusingPlayer.IsValid() && stage=="ready-to-defuse")
		{ stage="defusing"; Record("defuse-start-observed",new { defuseTime=bomb.DefuseTime }); }
		if(bomb.IsValid() && !bomb.IsDefused && !bomb.DefusingPlayer.IsValid() && stage=="defusing")
		{ stage="ready-to-defuse"; Record("defuse-cancelled-observed",new { elapsed=(float)bomb.TimeSinceDefuseStart,canUse=bomb.CanUse(player).CanUse }); }
		if(bomb.IsValid() && bomb.IsDefused && stage=="defusing")
		{ stage="defused"; Record("defused-observed",new { elapsed=(float)bomb.TimeSinceDefuseStart }); }
		if(stage=="defused" && (GameMode.Instance.Get<RoundBasedTeamScoring>()?.RoundWinHistory.Count??0)>initialWins)
		{
			stage="round-complete";
			Record("round-result",new { winner=GameMode.Instance.Get<RoundBasedTeamScoring>().RoundWinHistory.Last().ToString() });
		}
		if((DateTime.UtcNow-lastWrite).TotalSeconds>1)Save();
	}

	private static void PauseBots()
	{
		foreach(var bot in scene.GetAllComponents<LightweightCombatBot>())
		{
			if(!bots.ContainsKey(bot))bots[bot]=(bot.SightRange,bot.EngageRange,bot.MoveSpeed,bot.HealthComponent.IsGodMode);
			bot.SightRange=0;bot.EngageRange=0;bot.MoveSpeed=0;bot.HealthComponent.IsGodMode=true;
			if(bot.Agent.IsValid())bot.Agent.MaxSpeed=0;
		}
		foreach(var component in scene.GetAllComponents<BotPlayerController>().Cast<Component>().Concat(scene.GetAllComponents<BotController>()))
		{
			if(!disabled.ContainsKey(component))disabled[component]=component.Enabled;
			component.Enabled=false;
		}
	}

	[ConCmd("hc1_forestbase_bomb_defender")]
	public static void Defender()
	{
		if(scene!=Game.ActiveScene || !bomb.IsValid() || bomb.IsDefused || !player.IsValid())return;
		// A single local client changes role for this controlled test. Disable the
		// no-attacker shortcut so the prefab's real defuse timer is also exercised.
		foreach(var rule in scene.GetAllComponents<AllowInstantDefuse>())
		{ if(!disabled.ContainsKey(rule))disabled[rule]=rule.Enabled; rule.Enabled=false; }
		player.Team=Team.CounterTerrorist; player.IsFrozen=false;
		player.WorldPosition=bomb.WorldPosition+new Vector3(28,0,2);
		player.CharacterController.Velocity=Vector3.Zero;
		player.EyeAngles=Rotation.LookAt(bomb.WorldPosition+Vector3.Up*4-player.CameraGameObject.WorldPosition).Angles();
		stage="ready-to-defuse";
		Record("defender-ready",new { canUse=bomb.CanUse(player).CanUse,defuseTime=bomb.DefuseTime,duration=bomb.Duration,distance=player.WorldPosition.Distance(bomb.WorldPosition) });
		Save();
	}

	[ConCmd("hc1_forestbase_bomb_status")]
	public static void Status()=>Save();

	[ConCmd("hc1_forestbase_bomb_restore")]
	public static void Restore()
	{
		if(scene==null)return;
		Save();
		input?.Release();input?.Dispose();input=null;
		foreach(var item in disabled)if(item.Key.IsValid())item.Key.Enabled=item.Value;
		disabled.Clear();
		foreach(var item in bots)if(item.Key.IsValid())
		{ item.Key.SightRange=item.Value.sight;item.Key.EngageRange=item.Value.engage;item.Key.MoveSpeed=item.Value.speed;item.Key.HealthComponent.IsGodMode=item.Value.god;if(item.Key.Agent.IsValid())item.Key.Agent.MaxSpeed=item.Value.speed; }
		bots.Clear();
		if(player.IsValid()) { player.Team=originalTeam; player.IsUsing=false; player.HealthComponent.IsGodMode=originalGod; player.IsFrozen=originalFrozen||GameMode.Instance?.Get<FreezePlayers>() is {Active:true}; }
		scene=null;player=null;carried=null;bomb=null;stage="idle";
	}

	internal static void Record(string name,object data)
	{
		events.Add(new { name,seconds=(DateTime.UtcNow-started).TotalSeconds,data });
		Log.Info($"Forest Base bomb QA: {name}"); Save();
	}
	private static void Save()
	{
		if(scene==null)return; Directory.CreateDirectory(Folder); lastWrite=DateTime.UtcNow;
		File.WriteAllText(Path.Combine(Folder,$"bomb-site-{site}-qa.json"),JsonSerializer.Serialize(new {
			site,stage,placed,runId=started.ToString("O"),controls="Local host; active bots have movement/sight clamped and damage protection; actor protected, teleported and role switched; instant-defuse shortcut disabled for timed test. Production plant/defuse input and timers retained.",
			playerId=player.IsValid()?player.GameObject.Id.ToString():null,
			team=player.IsValid()?player.Team.ToString():null,
			position=player.IsValid()?player.WorldPosition.ToString():null,
			zone=player.IsValid()?player.GetZone<BombSite>()?.Index:null,
			zoneActive=player.IsValid()&&player.GetZone<BombSite>() is {Active:true},
			deployed=carried.IsValid()&&carried.GetComponentInParent<Equipment>().IsDeployed,
			currentEquipment=player.IsValid()?player.CurrentEquipment?.Resource?.ResourceName:null,
			plantRuleActive=GameMode.Instance?.Get<BombPlantedEventComponent>() is {Active:true},
			frozen=player.IsValid()&&player.IsFrozen,
			locallyControlled=player.IsValid()&&player.IsLocallyControlled,
			menuOpen=Facepunch.UI.ClassSelect.IsAnyOpen||Facepunch.UI.ZombiesWorkbenchPanel.IsAnyOpen,
			hovered=player.IsValid()?player.Hovered?.GetType().Name:null,
			inputTicks=input?.Ticks??0,
			grounded=player.IsValid()&&player.IsGrounded,
			canPlant=carried.IsValid()&&carried.CanPlant(),
			isPlanting=carried.IsValid()&&carried.IsPlanting,
			bombPosition=bomb.IsValid()?bomb.WorldPosition.ToString():null,
			isDefused=bomb.IsValid()&&bomb.IsDefused,
			isUsing=player.IsValid()&&player.IsUsing,
			defusingPlayer=bomb.IsValid()?bomb.DefusingPlayer?.GameObject.Id.ToString():null,
			secondsRemaining=bomb.IsValid()?bomb.SecondsRemaining:0,
			defuseProgress=bomb.IsValid()?bomb.Progress:0,
			events },new JsonSerializerOptions{WriteIndented=true}));
	}
}

// Constructed explicitly for the active test scene; never auto-installed in a game.
internal sealed class ForestBaseBombInput : GameObjectSystem
{
	public string Action;
	public DateTime Until;
	public int Ticks;
	public ForestBaseBombInput(Scene scene):base(scene)
	{
		Listen(Stage.StartUpdate,-10,Apply,"Forest Base QA input");
		Listen(Stage.StartFixedUpdate,-10,Apply,"Forest Base QA fixed input");
	}
	private void Apply()
	{
		Ticks++;
		if(string.IsNullOrEmpty(Action))return;
		Sandbox.Input.SetAction(Action,DateTime.UtcNow<Until);
		if(DateTime.UtcNow>=Until)Action=null;
	}
	public void Release()
	{
		if(!string.IsNullOrEmpty(Action))Sandbox.Input.SetAction(Action,false);
		Action=null;
	}
}
