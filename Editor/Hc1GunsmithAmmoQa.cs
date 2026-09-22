using Editor;
using Sandbox;
using Sandbox.UI;
using Facepunch;
using Facepunch.Gunsmith;
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using Label = Sandbox.UI.Label;

public static class Hc1GunsmithAmmoQa
{
	private const string PartPath = "gunsmith/ammunition/tracer_rounds.gnsmth";
	private static string Folder => Path.Combine( Project.Current.GetRootPath(), "Sources/Weapons/qa/tracer-rounds" );
	private static readonly BindingFlags PrivateInstance = BindingFlags.Instance | BindingFlags.NonPublic;

	[ConCmd( "hc1_gunsmith_ammo_test" )]
	public static void Test()
	{
		AssetSystem.FindByPath( PartPath )?.Compile( true );
		var part = ResourceLibrary.Get<GunsmithPart>( PartPath );
		Require( part.IsValid() && part.Category == GunsmithPartType.Ammunition && part.UsesTracerRounds, "ammo asset loads" );
		var rifle = ResourceLibrary.Get<EquipmentResource>( "weapons/m4a1/m4a1.equip" );
		var pistol = ResourceLibrary.Get<EquipmentResource>( "weapons/usp/usp.equip" );
		Require( part.Supports( rifle ) && part.Supports( pistol ), "rifle and pistol eligibility" );
		Require( !part.Supports( ResourceLibrary.Get<EquipmentResource>( "weapons/knife/knife.equip" ) ), "melee excluded" );
		var activeClass = GunsmithLoadoutManager.GetActiveClassIndex();
		var cookies = new Dictionary<string, string>();
		foreach ( var c in new[] { activeClass, 9876 } )
		foreach ( var resource in new[] { rifle, pistol } )
		foreach ( var id in new[] { resource.ResourcePath, resource.ResourceName } )
		{
			var key = $"hc1.gunsmith.class{c}.{id}.Ammunition";
			cookies[key] = Game.Cookies.Get<string>( key, "" );
		}
		var currentPawn = typeof( Pawn ).GetProperty( "Current", BindingFlags.Static | BindingFlags.NonPublic );
		var previousPawn = currentPawn.GetValue( null );
		var scene = new Scene();
		try
		{
			using var scope = scene.Push();
			GunsmithLoadoutManager.SetAttachment( rifle, GunsmithPartType.Ammunition, null );
			Require( !GunsmithLoadoutManager.UsesTracerRounds( rifle ), "standard ammo has no tracers" );
			GunsmithLoadoutManager.SetAttachment( rifle, GunsmithPartType.Ammunition, part );
			Require( GunsmithLoadoutManager.UsesTracerRounds( rifle ), "equipped tracer rounds persist" );
			GunsmithLoadoutManager.SetAttachment( pistol, GunsmithPartType.Ammunition, null );
			Require( !GunsmithLoadoutManager.UsesTracerRounds( pistol ), "ammo choice is per weapon" );
			var build = GunsmithLoadoutManager.ExportWeaponBuildCode( rifle );
			var encoded = build.Substring( "HC1W1-".Length ).Replace( '-', '+' ).Replace( '_', '/' );
			encoded = encoded.PadRight( (encoded.Length + 3) / 4 * 4, '=' );
			var json = System.Text.Encoding.UTF8.GetString( Convert.FromBase64String( encoded ) );
			Require( json.Contains( "Ammunition" ) && json.Contains( PartPath ), "share code includes ammo" );
			GunsmithLoadoutManager.SetActiveClassIndex( 9876 );
			GunsmithLoadoutManager.SetAttachment( rifle, GunsmithPartType.Ammunition, null );
			Require( !GunsmithLoadoutManager.UsesTracerRounds( rifle ), "ammo choice is per class" );
			GunsmithLoadoutManager.SetActiveClassIndex( activeClass );
			Require( GunsmithLoadoutManager.UsesTracerRounds( rifle ), "returning to class restores ammo" );

			var pawn = new GameObject( false, "Ammo QA owner" ).Components.Create<PlayerPawn>();
			currentPawn.SetValue( null, pawn );
			var gun = new GameObject( false, "Ammo QA weapon" );
			var equipment = gun.Components.Create<Equipment>();
			equipment.Owner = pawn;
			equipment.Resource = rifle;
			var shooter = gun.Components.Create<Shootable>();
			typeof( EquipmentComponent ).GetProperty( "Equipment", PrivateInstance ).SetValue( shooter, equipment );
			var refresh = typeof( Equipment ).GetMethod( "RefreshAmmunitionLoadout", PrivateInstance );
			refresh.Invoke( equipment, null );
			Require( equipment.UsesTracerRounds, "owned weapon reads equipped ammo" );
			var play = typeof( Shootable ).GetMethod( "PlayTracer", PrivateInstance );
			var end = Vector3.Forward * 1000f;
			play.Invoke( shooter, new object[] { end, Vector3.Zero } );
			var tracer = scene.GetAllComponents<Tracer>().Single();
			Require( tracer.EndPoint.Get().Distance( end ) < 0.01f, "tracer reaches shot endpoint" );

			// Observers must render the firing event even when their local loadout uses standard ammo.
			GunsmithLoadoutManager.SetAttachment( rifle, GunsmithPartType.Ammunition, null );
			typeof( Shootable ).GetMethod( "DoTracerEffects", PrivateInstance ).Invoke( shooter, new object[] { end, Vector3.Zero } );
			Require( scene.GetAllComponents<Tracer>().Count() == 2, "observer does not read local ammo cookies" );
			refresh.Invoke( equipment, null );
			Require( !equipment.UsesTracerRounds, "standard rounds clear weapon state" );
			play.Invoke( shooter, new object[] { end, Vector3.Zero } );
			Require( scene.GetAllComponents<Tracer>().Count() == 2, "standard rounds emit no effect" );

			GunsmithLoadoutManager.SetAttachment( rifle, GunsmithPartType.Ammunition, part );
			currentPawn.SetValue( null, null );
			refresh.Invoke( equipment, null );
			Require( !equipment.UsesTracerRounds, "non-owned weapon ignores local loadout" );

			var swb = new GameObject( false, "SWB ammo QA" ).Components.Create<SWB.Base.Weapon>();
			var bridge = pawn.Components.Create<SWB.PlayerPawnBridge>();
			typeof( SWB.Base.Weapon ).GetProperty( "Owner" ).SetValue( swb, bridge );
			swb.GunsmithResource = rifle;
			var shootInfo = swb.Components.Create<SWB.Base.ShootInfo>();
			var swbRefresh = typeof( SWB.Base.Weapon ).GetMethod( "RefreshAmmunitionLoadout", PrivateInstance );
			swbRefresh.Invoke( swb, new object[] { shootInfo } );
			Require( shootInfo.UsesTracerRounds, "SWB firing configuration reads equipped ammo" );
			GunsmithLoadoutManager.SetAttachment( rifle, GunsmithPartType.Ammunition, null );
			swbRefresh.Invoke( swb, new object[] { shootInfo } );
			Require( !shootInfo.UsesTracerRounds, "SWB standard rounds clear tracer state" );
			bridge.IsBot = true;
			GunsmithLoadoutManager.SetAttachment( rifle, GunsmithPartType.Ammunition, part );
			swbRefresh.Invoke( swb, new object[] { shootInfo } );
			Require( !shootInfo.UsesTracerRounds, "SWB bot ignores the human loadout" );
			Directory.CreateDirectory( Folder );
			File.WriteAllText( Path.Combine( Folder, "validation.txt" ), "PASS: asset eligibility, standard/tracer equip, per-weapon and per-class persistence, share code, owned weapon state, tracer spawn and endpoint, observer independence, unequip, SWB selection/reset/bot isolation.\n" );
			Log.Info( "HC1_GUNSMITH_AMMO PASS" );
		}
		finally
		{
			currentPawn.SetValue( null, previousPawn );
			GunsmithLoadoutManager.SetActiveClassIndex( activeClass );
			foreach ( var cookie in cookies ) Game.Cookies.Set( cookie.Key, cookie.Value );
			scene.Destroy();
		}
	}

	[ConCmd( "hc1_gunsmith_ammo_open" )]
	public static void Open()
	{
		Require( Game.IsPlaying && Game.ActiveScene is not null, "play mode must be running" );
		Facepunch.GameMode.SetCurrent( null );
		Game.ActiveScene.Load( ResourceLibrary.Get<SceneFile>( "scenes/gunsmith.scene" ) );
	}

	[ConCmd( "hc1_gunsmith_ammo_ui_test" )]
	public static async void UiTest()
	{
		var panel = Game.ActiveScene.GetAllComponents<GunsmithPanel>().FirstOrDefault();
		Require( panel is not null && panel.IsValid() && panel.System.IsValid(), "Gunsmith must be open" );
		var weapon = panel.System.Weapon;
		var keys = new[] { weapon.Resource.ResourcePath, weapon.Resource.ResourceName }.Distinct()
			.Select( id => $"hc1.gunsmith.class{GunsmithLoadoutManager.GetActiveClassIndex()}.{id}.Ammunition" ).ToArray();
		var before = keys.ToDictionary( key => key, key => Game.Cookies.Get<string>( key, "" ) );
		try
		{
			Ui( "open" );
			await GameTask.DelaySeconds( 0.25f );
			Ui( "standard" );
			await GameTask.DelaySeconds( 0.25f );
			Require( !GunsmithLoadoutManager.UsesTracerRounds( weapon.Resource ), "UI selected standard rounds" );
			Ui( "ammo-standard-final" );
			Ui( "equip" );
			await GameTask.DelaySeconds( 0.25f );
			Require( GunsmithLoadoutManager.UsesTracerRounds( weapon.Resource ), "UI selected tracer rounds" );
			Ui( "ammo-tracer-final" );
			File.WriteAllText( Path.Combine( Folder, "ui-validation.txt" ), "PASS: clicked Standard Rounds and Tracer Rounds in the live Ammunition drawer; checked saved selection and rendered both states. Original selection restored.\n" );
			Log.Info( "HC1_GUNSMITH_AMMO_UI PASS" );
		}
		finally
		{
			foreach ( var cookie in before ) Game.Cookies.Set( cookie.Key, cookie.Value );
			if ( weapon.IsValid() ) GunsmithLoadoutManager.ApplyAttachments( weapon.Resource, weapon.GameObject );
		}
	}

	[ConCmd( "hc1_gunsmith_ammo_ui" )]
	public static void Ui( string action = "open" )
	{
		var panel = Game.ActiveScene.GetAllComponents<GunsmithPanel>().FirstOrDefault();
		Require( panel is not null && panel.IsValid() && panel.System.IsValid(), "Gunsmith must be open" );
		using var scope = panel.Scene.Push();
		var weapon = panel.System.Weapon;
		var browser = Descendants( panel.Panel ).OfType<GunsmithAttachmentBrowser>().First();
		if ( action == "open" )
		{
			AssetSystem.FindByPath( PartPath )?.Compile( true );
			GunsmithLoadoutManager.ApplyAttachments( weapon.Resource, weapon.GameObject );
			var point = weapon.GetComponentsInChildren<GunsmithAttachmentPoint>( true ).Single( x => x.Category == GunsmithPartType.Ammunition );
			browser.SelectPoint( point );
			return;
		}
		if ( action is "equip" or "standard" )
		{
			var title = action == "equip" ? "Tracer Rounds" : "Standard Rounds";
			var option = Descendants( browser ).First( p => p.HasClass( "attachment-option" ) && Descendants( p ).OfType<Label>().Any( x => x.Text == title ) );
			option.CreateEvent( "onclick" );
			return;
		}
		Directory.CreateDirectory( Folder );
		using var bitmap = new Bitmap( 1920, 1080 );
		panel.Scene.Camera.RenderToBitmap( bitmap, true );
		File.WriteAllBytes( Path.Combine( Folder, $"{action}.png" ), bitmap.ToPng() );
		var text = Descendants( browser ).OfType<Label>().Select( p => p.Text );
		File.WriteAllLines( Path.Combine( Folder, $"{action}.txt" ), text );
		Log.Info( $"HC1_GUNSMITH_AMMO_UI {action} saved" );
	}

	private static IEnumerable<Panel> Descendants( Panel panel )
	{
		yield return panel;
		foreach ( var child in panel.Children )
		foreach ( var descendant in Descendants( child ) ) yield return descendant;
	}
	private static void Require( bool value, string message )
	{
		if ( !value ) throw new Exception( "HC1_GUNSMITH_AMMO FAIL: " + message );
	}
}
