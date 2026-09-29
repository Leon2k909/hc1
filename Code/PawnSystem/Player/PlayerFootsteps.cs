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
		// Corpses (ZombieAI) are silent underfoot: step on the floor beneath them.
		var tr = Scene.Trace
			.Ray( Player.WorldPosition + Vector3.Up * 20, Player.WorldPosition + Vector3.Up * -20 )
			.IgnoreGameObjectHierarchy( Player.GameObject )
			.WithoutTags( "corpse" )
			.Run();

		if ( !tr.Hit )
			return;

		var surface = WorldSounds.SurfaceAt( tr );
		if ( surface is null )
			return;

		TimeSinceStep = 0;

		flipFlop = !flipFlop;

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

	protected override void OnFixedUpdate()
	{
		if ( !Player.IsValid() )
			return;

		if ( Player.HealthComponent.State != LifeState.Alive ) return;

		if ( TimeSinceStep < GetStepFrequency() )
			return;

		if ( Player.CharacterController.Velocity.Length > 50f )
		{
			Footstep();
		}
	}
}
