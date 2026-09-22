using Editor;
using Sandbox;
using System;
using System.Linq;
using System.IO;
using Facepunch;
using Facepunch.Gunsmith;

public static class Hc1AttachmentAudit
{
	[ConCmd( "hc1_attachment_preview" )]
	public static void Preview( string weapon = "m4a1", bool world = false, bool compact = false )
	{
		var folder = Path.Combine( Project.Current.GetRootPath(), "Sources", "Attachments", "qa" );
		Directory.CreateDirectory( folder );
		using var bitmap = new Bitmap( 1600, 900 );
		var scene = new Scene();
		try
		{
			using var sceneScope = scene.Push();
			var prefab = ResourceLibrary.Get<PrefabFile>( $"weapons/{weapon}/{(world ? "wm" : "vm")}_{weapon}.prefab" );
			var root = SceneUtility.GetPrefabScene( prefab ).Clone( new CloneConfig { StartEnabled = false, Transform = new() } );
			foreach ( var component in root.Components.GetAll<Component>( FindMode.EverythingInSelfAndDescendants ) )
				component.Enabled = component is ModelRenderer || component is GunsmithAttachmentPoint || component is WeaponModel;
			var renderer = root.Components.Get<SkinnedModelRenderer>( FindMode.EverythingInSelf );
			var path = weapon == "scarh" ? $"weapons/swb/scarh/{(world ? "w_scarh" : "v_scarh_gunsmith")}.vmdl"
				: $"models/weapons/sbox_assault_m4a1/{(world ? "w" : "v")}_m4a1.vmdl";
			renderer.Model = Model.Load( path );
			renderer.UseAnimGraph = false;
			renderer.BodyGroups = weapon == "scarh" ? 42259UL : world ? 395UL : 9251UL;
			renderer.SetBodyGroup( "muzzle", 0 );
			renderer.SetBodyGroup( "foregrip", 0 );
			foreach ( var other in root.Components.GetAll<SkinnedModelRenderer>( FindMode.EverythingInSelfAndDescendants ) )
				if ( other != renderer ) other.Enabled = false;
			renderer.Sequence.Name = weapon == "m4a1" && !world ? "IdlePose" : renderer.Model.GetAnimationName( 0 );
			renderer.PlaybackRate = 0;
			root.Enabled = true;
			var gunsmith = root.Components.Create<GunsmithWeapon>();
			gunsmith.Resource = ResourceLibrary.Get<EquipmentResource>( $"weapons/{weapon}/{weapon}.equip" );
			foreach ( var point in root.Components.GetAll<GunsmithAttachmentPoint>( FindMode.EverythingInSelfAndDescendants ).ToArray() )
			{
				var partName = point.Category == GunsmithPartType.Barrel ? (compact ? "compact_suppressor" : "rifle_suppressor")
					: point.Category == GunsmithPartType.Underbarrel ? (compact ? "angled_grip" : "vertical_grip") : null;
				if ( partName is null ) continue;
				var part = ResourceLibrary.Get<GunsmithPart>( $"gunsmith/hc1/{partName}/{partName}.gnsmth" );
				if ( part is null ) throw new Exception( $"Part failed to load: {partName}" );
				point.SetPart( part );
				Log.Info( $"HC1_ATTACHMENT_FIT {weapon} {world} {partName} position={point.CurrentGameObject?.WorldPosition}" );
				foreach ( var component in point.CurrentGameObject.Components.GetAll<Component>( FindMode.EverythingInSelf ) )
					Log.Info( $"HC1_ATTACHMENT_COMPONENT {component.GetType().Name} enabled={component.Enabled}" );
			}
			var camera = new GameObject( true, "QA camera" ).Components.Create<CameraComponent>();
			camera.BackgroundColor = new Color( 0.08f, 0.10f, 0.13f );
			camera.FieldOfView = 40;
			scene.EditorTick( 0.01f, 0.01f );
			var center = renderer.Model.Bounds.Center;
			camera.WorldPosition = center + new Vector3( 10, -65, 23 );
			camera.WorldRotation = Rotation.LookAt( center - camera.WorldPosition );
			var light = new GameObject( true, "QA light" ).Components.Create<DirectionalLight>();
			light.WorldRotation = Rotation.From( new Angles( 40, 35, 0 ) );
			light.LightColor = Color.White * 2;
			light.SkyColor = Color.White * 0.5f;
			scene.EditorTick( 0.01f, 0.01f );
			foreach ( var attachment in root.Components.GetAll<GunsmithSocketAttachment>( FindMode.EverythingInSelfAndDescendants ) )
			{
				var point = attachment.GetComponentInParent<GunsmithAttachmentPoint>();
				attachment.Initialize( point );
				Log.Info( $"HC1_ATTACHMENT_ALIGNED {attachment.GameObject.Name} {attachment.WorldTransform}" );
			}
			Log.Info( $"HC1_ATTACHMENT_SOCKET {path} muzzle={renderer.GetAttachment( "muzzle" )}" );
			camera.RenderToBitmap( bitmap );
			File.WriteAllBytes( Path.Combine( folder, $"{weapon}-{(world ? "world" : "view")}-{(compact ? "compact" : "rifle")}-fit.png" ), bitmap.ToPng() );
		}
		finally { scene.Destroy(); }
		Log.Info( "HC1_ATTACHMENT_PREVIEW saved" );
	}

	[ConCmd( "hc1_attachment_audit" )]
	public static void Run()
	{
		foreach ( var path in new[] {
			"models/weapons/sbox_assault_m4a1/v_m4a1.vmdl",
			"models/weapons/sbox_assault_m4a1/w_m4a1.vmdl",
			"weapons/swb/scarh/v_scarh.vmdl",
			"weapons/swb/scarh/v_scarh_gunsmith.vmdl",
			"weapons/swb/scarh/w_scarh.vmdl",
			"models/weapons/sbox_pistol_usp/v_usp.vmdl",
			"models/weapons/sbox_pistol_usp/w_usp.vmdl",
			"attachments/hc1/rifle_suppressor/rifle_suppressor.vmdl",
			"attachments/hc1/compact_suppressor/compact_suppressor.vmdl",
			"attachments/hc1/vertical_grip/vertical_grip.vmdl",
			"attachments/hc1/angled_grip/angled_grip.vmdl"
		} )
		{
			try
			{
				var model = Model.Load( path );
				Log.Info( $"HC1_ATTACHMENT_AUDIT {path} valid={model?.IsError == false} bounds={model?.Bounds}" );
				if ( model is null ) continue;
				foreach ( var name in new[] { "muzzle", "muzzle_silenced", "weapon_root", "Base" } )
				{
					Log.Info( $"HC1_ATTACHMENT_AUDIT {name} attachment={model.GetAttachment( name )} bone={model.GetBoneTransform( name )}" );
				}
			}
			catch ( Exception ex ) { Log.Warning( $"HC1_ATTACHMENT_AUDIT {path}: {ex.Message}" ); }
		}
	}
}
