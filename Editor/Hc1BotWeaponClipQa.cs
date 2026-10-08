using Editor;
using Sandbox;
using Facepunch;
using System;
using System.IO;
using System.Linq;
using System.Threading.Tasks;

/// <summary>Samples live weapon poses and renders the worst stock clearance without changing the running scene.</summary>
public static class Hc1BotWeaponClipQa
{
	private record Mesh( Model Model, Transform Transform, ulong Groups, Color Tint );
	private record Pose( Model Body, ulong Groups, Transform[] Bones, Mesh[] Garments, Mesh[] Gun, string Description );

	[ConCmd( "hc1_bot_weapon_clip_sample" )]
	public static async void Sample( string label = "current", string weapon = "kastov74u", bool skipReload = true )
	{
		var scene = Game.ActiveScene;
		var folder = Path.Combine( Project.Current.GetRootPath(), "output/bot-grip" );
		Directory.CreateDirectory( folder );
		Pose worst = null;
		var min = float.MaxValue;
		var count = 0;
		for ( var frame = 0; frame < 180 && scene.IsValid(); frame++ )
		{
			await Task.Delay( 16 );
			foreach ( var bot in scene.GetAllComponents<LightweightCombatBot>() )
			{
				if ( !bot.IsAlive || bot.WeaponResource?.ResourceName.Contains( weapon, StringComparison.OrdinalIgnoreCase ) != true ) continue;
				var body = bot.Renderer;
				var gun = bot.GetComponentInChildren<WorldModel>();
				if ( !body.IsValid() || !body.SceneModel.IsValid() || !gun.IsValid() || !gun.ModelRenderer.IsValid() ) continue;
				var sinceReload = typeof( LightweightCombatBot ).GetField( "_sinceReloadClip", System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance )?.GetValue( bot ) is TimeSince since ? (float)since : 999f;
				if ( skipReload && sinceReload < 1.67f ) continue;
				var chestBone = body.Model.Bones.GetBone( "spine_2" ) ?? body.Model.Bones.GetBone( "spine_1" );
				if ( chestBone is null ) continue;
				var chest = body.SceneModel.GetBoneWorldTransform( chestBone.Index );
				var bounds = gun.ModelRenderer.Model.Bounds.Transform( gun.WorldTransform.ToLocal( gun.ModelRenderer.WorldTransform ) );
				var bore = gun.Muzzle.IsValid() ? gun.WorldTransform.PointToLocal( gun.Muzzle.WorldPosition ).z : bounds.Center.z;
				var butt = gun.WorldTransform.PointToWorld( new Vector3( bounds.Mins.x, 0f, bore ) );
				// Body forward rather than the bind-pose bone axes, which differ between skeletons.
				var localButt = body.WorldTransform.PointToLocal( butt );
				var localChest = body.WorldTransform.PointToLocal( chest.Position );
				var clearance = localButt.x - localChest.x;
				count++;
				if ( clearance >= min ) continue;
				min = clearance;
				var inBody = body.WorldTransform.ToLocal( gun.WorldTransform );
				var eye = body.GetAttachment( "eye_R_forward" ) ?? body.GetAttachment( "eyes" );
				var description = $"{bot.BotName} {bot.WeaponResource?.Name}: aiming={bot.IsAimingIn} rightIk={body.GetInt( "ik.hand_right.enabled" )} sinceReload={sinceReload} crouching={bot.IsCrouching} aim={bot.AimDirection} butt={localButt} chest={localChest} gunInBody={inBody} bounds={bounds} eyeInGun={(eye is {} e ? gun.WorldTransform.PointToLocal(e.Position) : Vector3.Zero)}";
				Mesh CopyMesh( SkinnedModelRenderer mesh ) => new( mesh.Model, body.WorldTransform.ToLocal( mesh.WorldTransform ), mesh.BodyGroups, mesh.Tint );
				worst = new Pose( body.Model, body.BodyGroups,
					body.Model.Bones.AllBones.OrderBy( b => b.Index ).Select( b => body.WorldTransform.ToLocal( body.SceneModel.GetBoneWorldTransform( b.Index ) ) ).ToArray(),
					body.GetComponentsInChildren<SkinnedModelRenderer>().Where( r => r != body && r.BoneMergeTarget == body ).Select( CopyMesh ).ToArray(),
					new[] { gun.ModelRenderer }.Concat( gun.GameObject.Components.GetAll<SkinnedModelRenderer>( FindMode.EverythingInSelfAndDescendants ) ).Distinct().Select( CopyMesh ).ToArray(), description );
			}
		}
		var stem = Path.GetFileName( label );
		if ( worst is null )
		{
			File.WriteAllText( Path.Combine( folder, $"clip-{stem}.txt" ), $"No living bots carrying '{weapon}' were available to sample." );
			Log.Info( $"HC1_BOT_CLIP {stem}: no matching bots" );
			return;
		}
		File.WriteAllText( Path.Combine( folder, $"clip-{stem}.txt" ), $"Samples: {count}\nMinimum stock X relative to chest: {min:0.000}\n{worst?.Description}\nGun meshes: {string.Join( "; ", worst?.Gun.Select( g => $"{g.Model.Name} groups={g.Groups} transform={g.Transform}" ) ?? Array.Empty<string>() )}" );
		if ( worst is not null ) Render( worst, Path.Combine( folder, $"clip-{stem}.png" ) );
		Log.Info( $"HC1_BOT_CLIP done: {stem}, samples={count}, stockX={min:0.000}" );
	}

	private static void Render( Pose pose, string path )
	{
		var scene = new Scene();
		try
		{
			using ( scene.Push() )
			{
				var body = new GameObject( true, "Sampled bot" ).Components.Create<SkinnedModelRenderer>();
				body.Model = pose.Body;
				body.BodyGroups = pose.Groups;
				body.UseAnimGraph = false;
				SkinnedModelRenderer CreateMesh( Mesh mesh )
				{
					var renderer = new GameObject( true, "Sampled mesh" ).Components.Create<SkinnedModelRenderer>();
					renderer.Model = mesh.Model;
					renderer.WorldTransform = mesh.Transform;
					renderer.BodyGroups = mesh.Groups;
					renderer.Tint = mesh.Tint;
					renderer.UseAnimGraph = false;
					return renderer;
				}
				var garments = pose.Garments.Select( CreateMesh ).ToArray();
				var guns = pose.Gun.Select( CreateMesh ).ToArray();
				var camera = new GameObject( true, "Pose camera" ).Components.Create<CameraComponent>();
				camera.BackgroundColor = new Color( .10f, .12f, .15f );
				camera.FieldOfView = 40f;
				camera.ZNear = 1f;
				var light = new GameObject( true, "Pose light" ).Components.Create<DirectionalLight>();
				light.WorldRotation = Rotation.From( 40f, 150f, 0f );
				light.LightColor = Color.White * 2f;
				light.SkyColor = Color.White * .6f;
				scene.EditorTick( .016f, .016f );
				using var sheet = new Bitmap( 1800, 600 );
				using var tile = new Bitmap( 600, 600 );
				var views = new[] { new Vector3( 4f, 62f, 56f ), new Vector3( -60f, -30f, 58f ), new Vector3( 4f, -62f, 58f ) };
				for ( var v = 0; v < views.Length; v++ )
				{
					camera.WorldPosition = views[v];
					camera.WorldRotation = Rotation.LookAt( new Vector3( 4f, 0f, 50f ) - views[v] );
					scene.EditorTick( .016f, 0f );
					foreach ( var gun in guns )
					{
						gun.SceneModel.Transform = gun.WorldTransform;
						gun.SceneModel.Update( 0f );
					}
					for ( var i = 0; i < pose.Bones.Length; i++ ) body.SceneModel.SetBoneWorldTransform( i, pose.Bones[i] );
					foreach ( var garment in garments ) garment.SceneModel?.MergeBones( body.SceneModel );
					camera.RenderToBitmap( tile );
					sheet.DrawBitmap( tile, new Rect( v * 600, 0, 600, 600 ) );
				}
				File.WriteAllBytes( path, sheet.ToPng() );
			}
		}
		finally { scene.Destroy(); }
	}
}
