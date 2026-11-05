namespace Facepunch;

/// <summary>
/// Produces footstep sounds for the player.
/// </summary>
public sealed class PlayerFootsteps : Component
{
	[Property] public PlayerPawn Player { get; set; }
	[Property] public float FootstepBaseDecibels { get; set; } = 70f;
	[Property] public float FootstepScale { get; set; } = 1f;
	[Property] public float SprintFootstepScale { get; set; } = 2f;

	public TimeSince TimeSinceStep { get; private set; }

	bool flipFlop = false;

	public float GetStepFrequency()
	{
		if ( Player.IsSprinting ) return 0.25f;
		if ( Player.IsCrouching || Player.IsSlowWalking ) return 0.6f;

		return 0.35f;
	}

	private void Footstep()
	{
		var nextLeft = !flipFlop;
		// Approximate boot spacing in body space. At a material boundary, each foot can land on
		// a different floor instead of both sampling the point beneath the player's centre.
		var foot = Player.WorldPosition + Player.WorldRotation.Left * (nextLeft ? 6f : -6f);
		var tr = TraceFloor( foot );
		var surface = tr.Hit ? WorldSounds.SurfaceAt( tr ) : null;
		if ( surface is null )
		{
			// A boot can extend over a stair/ledge while the controller remains supported. Preserve
			// the ordinary supported step rather than losing its timing or inventing a surface.
			tr = TraceFloor( Player.WorldPosition );
			surface = tr.Hit ? WorldSounds.SurfaceAt( tr ) : null;
		}
		if ( surface is null )
			return;

		TimeSinceStep = 0;

		flipFlop = nextLeft;

		// Don't make footsteps sometimes, but keep the step info
		if ( Player.IsCrouching || Player.IsSlowWalking )
			return;

		// A soldier's boots on this floor, walking or running (Tools/world_sounds.py).
		var sound = WorldSounds.Footstep( surface, Player.IsSprinting, flipFlop );
		if ( sound is null ) return;

		var handle = Sound.Play( sound, tr.HitPosition + tr.Normal * 5 );
		if ( !handle.IsValid() ) return;

		if ( Player.Components.TryGet<PlayerPerks>( out var perks, FindMode.EnabledInSelf ) && perks.HasPerk( "ninja" ) )
		{
			handle.Volume *= 0.15f; // Reduce footstep sound volume significantly
		}

		// Someone else's steps are muffled through a wall, like any other sound.
		handle.OcclusionEnabled = !Player.IsViewer && handle.OcclusionEnabled;
		handle.SpacialBlend = Player.IsViewer ? 0 : handle.SpacialBlend;
	}

	private SceneTraceResult TraceFloor( Vector3 at ) => Scene.Trace
		.Ray( at + Vector3.Up * 20f, at + Vector3.Up * -20f )
		.IgnoreGameObjectHierarchy( Player.GameObject )
		.WithoutTags( "corpse" )
		.Run();

	protected override void OnFixedUpdate()
	{
		if ( !Player.IsValid() )
			return;

		if ( !Player.HealthComponent.IsValid() || Player.HealthComponent.State != LifeState.Alive ) return;
		if ( Player.IsNoclipping || Player.IsFrozen || Player.IsMantling || Player.IsPipeClimbing
			|| Player.IsSliding || Player.IsProne || Player.IsFallKnockedDown || Player.IsPilotingDrone ) return;

		// Remote controllers don't drive movement locally; use the same replicated state as their animation.
		var local = Player.IsLocallyControlled;
		var controller = Player.CharacterController;
		if ( local && !controller.IsValid() ) return;
		var grounded = local ? controller.IsOnGround : Player.SyncedIsGrounded;
		if ( !grounded ) return;

		if ( TimeSinceStep < GetStepFrequency() )
			return;

		var velocity = local ? controller.Velocity : Player.SyncedVelocity;
		if ( velocity.WithZ( 0f ).LengthSquared > 50f * 50f )
		{
			Footstep();
		}
	}
}
