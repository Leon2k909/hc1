namespace Facepunch;

/// <summary>
/// Mantling. Jump while moving at a ledge between mid-thigh and just over head height, and you climb up onto it. If it's
/// a wall too thin to stand on, with a floor not far below on the other side, you vault over it instead. Holding Jump in
/// the air catches a ledge the jump brings into reach. Before it starts, the whole move is traced with the body tucked:
/// up with the arms, then over the top. Then the pawn follows that path, so nothing can push it into the wall.
/// Only the owner moves the pawn. Everyone else sees it move, with <see cref="IsMantling"/> tucking the body.
/// </summary>
public partial class PlayerPawn
{
	/// <summary>Ledges lower than this, above the floor you're on, are stepped or jumped onto: about mid-thigh (0.7 m).</summary>
	public const float MinMantleHeight = 28f;

	/// <summary>The highest ledge you can climb from a standstill: ~2.1 m, a fit soldier's pull-up onto a wall.</summary>
	public const float MaxMantleHeight = 84f;

	/// <summary>How much higher a ledge can be when you jump at it and catch it.</summary>
	public const float AirMantleBonus = 10f;

	/// <summary>How far past the body's front the hands reach for a ledge.</summary>
	public const float MantleReach = 20f;

	/// <summary>Tops no deeper than this are vaulted over, not climbed onto: walls, fences, rails and sandbags.</summary>
	public const float VaultMaxDepth = 24f;

	/// <summary>
	/// The furthest drop a vault lands in (~4 m). Past it you climb onto the top instead, so a parapet doesn't throw you
	/// off a roof.
	/// </summary>
	public const float VaultMaxDrop = 160f;

	/// <summary>The body's height going over the top: tucked for a vault, so you can go through a window; crouched for a climb.</summary>
	private const float VaultTuckHeight = 36f;
	private const float ClimbTuckHeight = 48f;

	/// <summary>The standing eye's height over the feet (the Head object in player.prefab).</summary>
	private const float StandingEyeHeight = 60f;

	/// <summary>The feet clear the top by this much on the way over.</summary>
	private const float MantleClearance = 2f;

	/// <summary>Falling faster than this, you can't catch a ledge.</summary>
	private const float MantleFallLimit = 250f;

	/// <summary>A vault goes over at your speed, between these. A climb is slower, since the legs have to come under you first.</summary>
	private const float VaultMinSpeed = 150f;
	private const float VaultMaxSpeed = 260f;
	private const float ClimbOverSpeed = 150f;

	/// <summary>Tags of things you don't climb: people, bots' and zombies' boxes, doors, glass and player clips (or trees).</summary>
	private static readonly string[] NotClimbable = { "player", "movement", "enemy", "door", "glass", "playerclip" };

	/// <summary>Climbing or vaulting: no shooting, aiming or sprinting, and the gun is swung down out of the way.</summary>
	[Sync] public bool IsMantling { get; private set; }

	/// <summary>The eye's offset while mantling: low enough that the tucked body's head clears the top.</summary>
	[Sync] private float MantleEyeOffset { get; set; }

	/// <summary>0 to 1, eased in and out with <see cref="IsMantling"/> on every machine: the viewmodel and camera follow it.</summary>
	public float MantleBlend { get; private set; }

	/// <summary>A planned mantle: rise straight up to <see cref="RiseZ"/>, then go over to <see cref="To"/>.</summary>
	private struct MantlePlan
	{
		public Vector3 From;
		public Vector3 To;
		public float RiseZ;
		public float RiseTime;
		public float OverStart;
		public float OverTime;
		public Vector3 Exit;
		public bool Vault;
		public Vector3 Ledge;
		public float Tuck;

		public float Duration => MathF.Max( RiseTime, OverStart + OverTime );
	}

	private MantlePlan _mantle;
	private float _mantleTime;
	private Vector3 _mantleLast;

	/// <summary>Set by a vault, so its landing is heard even when the drop is too short for a fall's sound.</summary>
	private bool _vaultLanding;

	private void UpdateMantleBlend()
	{
		MantleBlend = MantleBlend.Approach( IsMantling ? 1f : 0f, Time.Delta * (IsMantling ? 6f : 4f) );
	}

	/// <summary>
	/// Start mantling the ledge in front, if there's one in reach. On the ground this replaces the jump, so it needs Jump
	/// pressed while moving forward. In the air it runs every tick that Jump is held. With <paramref name="ignoreInput"/>
	/// (dev_mantle) it goes the way you're looking.
	/// </summary>
	internal bool TryStartMantle( bool airborne, bool ignoreInput = false, bool log = false )
	{
		var reason = CanMantle( airborne, ignoreInput );
		MantlePlan plan = default;
		if ( reason is null && !PlanMantle( airborne, ignoreInput, out plan, out reason ) )
			reason ??= "no ledge";

		if ( reason is not null )
		{
			if ( log ) Log.Info( $"Mantle: {reason}" );
			return false;
		}

		if ( log )
			Log.Info( $"Mantle: {(plan.Vault ? "vault" : "climb")} {plan.RiseZ - WorldPosition.z:F1} up, {(plan.To - plan.From).WithZ( 0 ).Length:F1} over, {plan.Duration:F2} s" );

		StartMantle( plan );
		return true;
	}

	private string CanMantle( bool airborne, bool ignoreInput )
	{
		if ( IsMantling ) return "already mantling";
		if ( HealthComponent.State != LifeState.Alive ) return "dead";
		if ( IsProne || IsFallKnockedDown ) return "lying down";
		if ( IsNoclipping || IsFrozen || _isTouchingLadder ) return "can't move";
		if ( HasEquipmentTag( "planting" ) ) return "planting";
		if ( !ignoreInput && WishMove.x < 0.3f ) return "not moving forward";
		if ( airborne && CharacterController.Velocity.z < -MantleFallLimit ) return "falling too fast";
		return null;
	}

	private static BBox MantleBox( float radius, float height ) =>
		new( new Vector3( -radius, -radius, 0f ), new Vector3( radius, radius, height ) );

	private static bool IsClimbable( in SceneTraceResult tr )
	{
		// The Ridgeback's trees and hedges (clutter: bodies with no GameObject). You don't stand on top of a hedge.
		if ( tr.Shape is { } shape && shape.Tags.Has( "clutter" ) )
			return false;

		var go = tr.GameObject;
		if ( !go.IsValid() ) return true;

		foreach ( var tag in NotClimbable )
		{
			if ( go.Tags.Has( tag ) )
				return false;
		}

		return true;
	}

	private bool PlanMantle( bool airborne, bool ignoreInput, out MantlePlan plan, out string reason )
	{
		plan = default;
		reason = null;

		var cc = CharacterController;
		var pos = WorldPosition;
		var radius = cc.Radius;
		var height = cc.Height;

		var forward = ignoreInput ? Vector3.Zero : WishVelocity.WithZ( 0 );
		if ( forward.LengthSquared < 1f ) forward = EyeAngles.WithPitch( 0 ).ToRotation().Forward.WithZ( 0 );
		forward = forward.Normal;

		// A wall in front, between the knees and the top of the head.
		var lift = cc.StepHeight + 1f;
		if ( height < lift + 8f ) { reason = "too low to reach"; return false; }

		var body = new BBox( new Vector3( -radius, -radius, lift ), new Vector3( radius, radius, height ) );
		var wall = cc.TraceBox( body, pos, pos + forward * MantleReach );
		if ( wall.StartedSolid || !wall.Hit ) { reason = "no wall in reach"; return false; }
		if ( MathF.Abs( wall.Normal.z ) > 0.5f || !IsClimbable( wall ) ) { reason = "not a wall"; return false; }

		// Go straight over, square to the wall, as long as you're roughly facing it.
		var dir = (-wall.Normal).WithZ( 0 ).Normal;
		if ( dir.Dot( forward ) < 0.6f ) { reason = "not facing it"; return false; }

		// How far the wall's face is from our centre, along the way over.
		var face = (wall.HitPosition - pos).WithZ( 0 ).Dot( dir );

		// The floor the height counts from. In the air that's the floor under you, so a jump doesn't add its own height.
		var groundZ = pos.z;
		if ( airborne )
		{
			var below = cc.TraceBox( MantleBox( radius - 0.5f, 4f ), pos, pos + Vector3.Down * 120f );
			groundZ = below.Hit && !below.StartedSolid ? below.EndPosition.z : pos.z - 120f;
		}

		var minZ = MathF.Max( groundZ + MinMantleHeight, airborne ? pos.z + 4f : pos.z + MinMantleHeight );
		var maxZ = groundZ + MaxMantleHeight + (airborne ? AirMantleBonus : 0f);
		if ( minZ > maxZ ) { reason = "too high"; return false; }

		// Where the top is, straight ahead of our centre, just inside the face: the first solid then free height in that
		// column. Starting free and going solid is a rail or a ledge's lip with open space under it.
		var probe = MantleBox( 3f, 4f );
		var column = pos + dir * (face + 3.5f);
		const float step = 6f;

		var solidZ = float.NaN;
		var freeZ = float.NaN;
		for ( var z = minZ; z <= maxZ + step; z += step )
		{
			var at = column.WithZ( MathF.Min( z, maxZ + 2f ) );
			var solid = cc.TraceBox( probe, at, at ).StartedSolid;
			if ( solid ) solidZ = at.z;
			else if ( !float.IsNaN( solidZ ) ) { freeZ = at.z; break; }
		}

		if ( float.IsNaN( solidZ ) ) { reason = "nothing to climb ahead"; return false; }
		if ( float.IsNaN( freeZ ) ) { reason = "too high"; return false; }

		var topTrace = cc.TraceBox( probe, column.WithZ( freeZ ), column.WithZ( solidZ ) );
		if ( !topTrace.Hit || topTrace.StartedSolid ) { reason = "no top"; return false; }
		if ( topTrace.Normal.z < 0.7f || !IsClimbable( topTrace ) ) { reason = "the top can't be stood on"; return false; }

		var top = topTrace.EndPosition.z;
		if ( top < minZ - step || top > maxZ ) { reason = "out of reach"; return false; }

		// How deep the top is. One that ends within VaultMaxDepth is a wall to go over.
		var depth = float.NaN;
		for ( var d = 8f; d <= VaultMaxDepth; d += 8f )
		{
			var at = pos + dir * (face + d);
			var t = cc.TraceBox( probe, at.WithZ( top + 4f ), at.WithZ( top - cc.StepHeight ) );
			if ( !t.StartedSolid && !t.Hit ) { depth = d; break; }
		}

		var riseZ = top + MantleClearance;
		var vault = false;
		var to = Vector3.Zero;

		if ( !float.IsNaN( depth ) )
		{
			// Over it, landing past its far side, if there's a floor within a few metres down.
			to = (pos + dir * (face + depth + radius + 2f)).WithZ( riseZ );
			var land = cc.TraceBox( MantleBox( radius, VaultTuckHeight ), to, to + Vector3.Down * VaultMaxDrop );
			vault = !land.StartedSolid && land.Hit && land.Normal.z >= 0.7f;
		}

		var tuck = vault ? VaultTuckHeight : ClimbTuckHeight;

		if ( !vault )
		{
			// Onto it, just past its face, with room at least to crouch and a floor to stand on.
			to = (pos + dir * (face + radius + 1f)).WithZ( riseZ );
			if ( cc.TraceBox( MantleBox( radius, Height - 16f ), to, to ).StartedSolid ) { reason = "no room on top"; return false; }

			var floor = cc.TraceBox( MantleBox( radius, 4f ), to, to + Vector3.Down * (MantleClearance + cc.StepHeight) );
			if ( floor.StartedSolid || !floor.Hit || floor.Normal.z < 0.7f ) { reason = "nothing to stand on"; return false; }
		}

		var riseHeight = MathF.Max( riseZ - pos.z, 0f );
		var entrySpeed = MathF.Max( cc.Velocity.WithZ( 0 ).Dot( dir ), 0f );
		var overSpeed = vault ? entrySpeed.Clamp( VaultMinSpeed, VaultMaxSpeed ) : ClimbOverSpeed;

		plan = new MantlePlan
		{
			From = pos,
			To = to,
			RiseZ = riseZ,
			// A step up is quick and a pull-up slow: 0.24 s for 20 units, 0.44 s waist high, 0.72 s chest high, 1.2 s
			// for a ledge at 2 m.
			RiseTime = 0.12f + 0.004f * riseHeight + 0.0001f * riseHeight * riseHeight,
			OverTime = MathF.Max( (to - pos).WithZ( 0 ).Length / overSpeed, 0.12f ),
			Exit = dir * overSpeed * (vault ? 1f : 0.5f),
			Vault = vault,
			Ledge = (pos + dir * (face + 3.5f)).WithZ( top ),
			Tuck = tuck,
		};

		// The legs start over while the arms are still lifting (a vault's swing more than a climb's), if that path is
		// clear; else up first, then over.
		var overlap = MathF.Min( plan.OverTime * (vault ? 0.5f : 0.25f), plan.RiseTime * 0.6f );
		var box = MantleBox( radius - 0.5f, tuck );
		plan.OverStart = plan.RiseTime - overlap;
		if ( overlap > 0f && !MantlePathClear( plan, box ) )
			plan.OverStart = plan.RiseTime;

		if ( !MantlePathClear( plan, box ) ) { reason = "something in the way"; return false; }

		return true;
	}

	private static float SmoothStep( float x )
	{
		x = x.Clamp( 0f, 1f );
		return x * x * (3f - 2f * x);
	}

	/// <summary>Where the feet are <paramref name="time"/> seconds into the mantle.</summary>
	private static Vector3 MantlePositionAt( in MantlePlan plan, float time )
	{
		var up = SmoothStep( time / plan.RiseTime );
		var over = SmoothStep( (time - plan.OverStart) / plan.OverTime );
		return Vector3.Lerp( plan.From, plan.To, over ).WithZ( plan.From.z.LerpTo( plan.RiseZ, up ) );
	}

	/// <summary>Trace the tucked body along the path, through the rise and then the rest, eight steps each.</summary>
	private bool MantlePathClear( in MantlePlan plan, BBox box )
	{
		var cc = CharacterController;
		var previous = plan.From + Vector3.Up;
		var duration = plan.Duration;

		for ( var i = 1; i <= 16; i++ )
		{
			var time = i <= 8 ? plan.RiseTime * i / 8f : plan.RiseTime + (duration - plan.RiseTime) * (i - 8) / 8f;
			var next = MantlePositionAt( plan, time );
			var tr = cc.TraceBox( box, previous, next );
			if ( tr.StartedSolid || tr.Hit )
				return false;

			previous = next;
		}

		return true;
	}

	private void StartMantle( in MantlePlan plan )
	{
		var cc = CharacterController;

		_mantle = plan;
		_mantleTime = 0f;
		_mantleLast = WorldPosition;
		_vaultLanding = false;

		IsMantling = true;
		MantleEyeOffset = plan.Tuck - 4f - StandingEyeHeight;
		IsSprinting = false;

		cc.IsOnGround = false;
		cc.Velocity = Vector3.Zero;

		// The support hand goes onto the ledge, so the sights come down.
		if ( CurrentEquipment.IsValid() )
		{
			foreach ( var aimable in CurrentEquipment.Components.GetAll<Aimable>( FindMode.EverythingInSelfAndDescendants ) )
				if ( aimable.IsValid() ) aimable.CancelAim();
		}

		BroadcastPlayerJumped();
		PlayMantleSound( plan.Ledge, false );
	}

	/// <summary>Follow the planned path, one fixed tick at a time. Only the owner moves the pawn.</summary>
	private void UpdateMantle()
	{
		var cc = CharacterController;

		// Something else moved us (a teleport, a respawn): let go where we are.
		if ( HealthComponent.State != LifeState.Alive || WorldPosition.Distance( _mantleLast ) > 8f )
		{
			StopMantle( Vector3.Zero );
			return;
		}

		_mantleTime += Time.Delta;
		var next = MantlePositionAt( _mantle, _mantleTime );

		cc.Velocity = (next - WorldPosition) / MathF.Max( Time.Delta, 0.001f );
		cc.IsOnGround = false;
		WorldPosition = next;
		_mantleLast = next;

		if ( _mantleTime < _mantle.Duration )
			return;

		if ( _mantle.Vault )
			_vaultLanding = true;
		else
			PlayMantleSound( next, true );

		StopMantle( _mantle.Exit );
	}

	private void StopMantle( Vector3 velocity )
	{
		IsMantling = false;
		CharacterController.Velocity = velocity;
	}

	/// <summary>
	/// A hand slapping onto the ledge, or the boots coming up onto it, on whatever it's made of: the footstep for that
	/// floor, the hand quieter.
	/// </summary>
	[Rpc.Broadcast]
	private void PlayMantleSound( Vector3 position, bool feet )
	{
		var tr = Scene.Trace.Ray( position + Vector3.Up * 8f, position + Vector3.Down * 16f )
			.IgnoreGameObjectHierarchy( GameObject )
			.WithoutTags( "corpse", "ragdoll" )
			.Run();

		if ( !tr.Hit ) return;

		var sound = WorldSounds.Footstep( WorldSounds.SurfaceAt( tr ), false, true );
		if ( sound is null ) return;

		var snd = Sound.Play( sound, tr.HitPosition );
		if ( !snd.IsValid() ) return;

		snd.Volume *= feet ? 1f : 0.6f;
		snd.SpacialBlend = IsViewer ? 0 : snd.SpacialBlend;
	}
}
