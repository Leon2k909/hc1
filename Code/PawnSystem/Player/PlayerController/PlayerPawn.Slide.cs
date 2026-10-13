namespace Facepunch;

/// <summary>
/// Sliding. Press Duck while sprinting on the ground and you drop onto a hip and slide on, faster than the sprint for a
/// moment, then slowing until you come up in a crouch (or standing, if Duck isn't held). A tap is enough: letting go of
/// Duck doesn't stop it. Jump ends it in a jump that keeps the speed, Prone ends it on the floor. Downhill keeps it
/// going and uphill stops it sooner. Only the owner moves the pawn; everyone else sees it crouched
/// (<see cref="IsSliding"/> holds the crouch) and hears it go down.
/// </summary>
public partial class PlayerPawn
{
	/// <summary>The eye's offset in a slide: lower than a crouch (-16), sat back on one hip.</summary>
	private const float SlideEyeOffset = -24f;

	/// <summary>How fast a slide bleeds speed (a crouch's is 4): from 345 u/s it's down to <see cref="SlideEndSpeed"/> in ~0.86 s, ~195 units on.</summary>
	private const float SlideFriction = 1.05f;

	/// <summary>How much the keys steer a slide: barely.</summary>
	private const float SlideAcceleration = 1.5f;

	/// <summary>The push the drop gives, on top of the sprint's speed, up to <see cref="SlideMaxSpeed"/>.</summary>
	private const float SlideBoost = 60f;
	private const float SlideMaxSpeed = 360f;

	/// <summary>Slower than this over the ground and Duck only crouches.</summary>
	private const float SlideMinStartSpeed = 200f;

	/// <summary>The slide ends below this speed (the friction's stop speed, under which it would halt in a few ticks).</summary>
	private const float SlideEndSpeed = 140f;

	/// <summary>The longest a slide lasts, even downhill.</summary>
	private const float SlideMaxTime = 1.1f;

	/// <summary>How long after a slide ends before another can start.</summary>
	private const float SlideCooldown = 0.8f;

	/// <summary>The share of the slope's pull a slide gets: downhill keeps it going, uphill stops it sooner.</summary>
	private const float SlideSlopeHelp = 0.5f;

	/// <summary>Down on one hip, sliding. The body is crouched, footsteps are silent and the gun is canted.</summary>
	[Sync] public bool IsSliding { get; private set; }

	/// <summary>0 to 1, eased in and out with <see cref="IsSliding"/> on every machine: the viewmodel and camera follow it.</summary>
	public float SlideBlend { get; private set; }

	private TimeSince _slideTime;
	private TimeUntil _slideCooldown;

	private void UpdateSlideBlend()
	{
		SlideBlend = SlideBlend.Approach( IsSliding ? 1f : 0f, Time.Delta * (IsSliding ? 8f : 4f) );
	}

	/// <summary>
	/// Start a slide on a Duck press while sprinting, or keep one going until it's slowed down, timed out, left the ground,
	/// or been jumped or dropped out of. Runs from <see cref="BuildInput"/>, before the crouch is read.
	/// </summary>
	private void UpdateSlide( bool wasSprinting )
	{
		if ( !IsSliding )
		{
			if ( Input.Pressed( "Duck" ) && (wasSprinting || IsSprinting) )
				TryStartSlide();
			return;
		}

		var cc = CharacterController;
		if ( CanSlide( ignoreInput: true ) is not null || !cc.IsOnGround || Input.Pressed( "Jump" )
			|| cc.Velocity.WithZ( 0 ).Length < SlideEndSpeed || _slideTime > SlideMaxTime )
			StopSlide();
	}

	internal bool TryStartSlide( bool ignoreInput = false, bool log = false )
	{
		var reason = CanSlide( ignoreInput );
		if ( reason is null && IsSliding ) reason = "already sliding";

		var cc = CharacterController;
		var flat = cc.IsValid() ? cc.Velocity.WithZ( 0 ) : Vector3.Zero;
		if ( reason is null && !cc.IsOnGround ) reason = "in the air";
		if ( reason is null && flat.Length < SlideMinStartSpeed ) reason = $"too slow ({flat.Length:F0} u/s)";
		if ( reason is null && !ignoreInput && _slideCooldown.Relative > 0f ) reason = "cooling down";

		if ( reason is not null )
		{
			if ( log ) Log.Info( $"Slide: {reason}" );
			return false;
		}

		var speed = MathF.Min( flat.Length + SlideBoost, SlideMaxSpeed );
		cc.Velocity = flat.Normal * speed;
		if ( log ) Log.Info( $"Slide: from {flat.Length:F0} to {speed:F0} u/s" );

		IsSliding = true;
		_slideTime = 0;

		// Out of the sprint: the gun comes up as it does when a sprint stops.
		WantsToggleSprint = false;
		if ( IsSprinting )
		{
			IsSprinting = false;
			OnSprintChanged( true, false );
		}

		PlaySlideSound( WorldPosition );
		return true;
	}

	private string CanSlide( bool ignoreInput )
	{
		if ( HealthComponent.State != LifeState.Alive ) return "dead";
		if ( IsProne || IsFallKnockedDown ) return "lying down";
		if ( IsMantling || IsPipeClimbing ) return "climbing";
		if ( IsNoclipping || IsFrozen || _isTouchingLadder || IsPilotingDrone ) return "can't move";
		if ( HasEquipmentTag( "planting" ) ) return "planting";
		if ( ZombiesPlayerState.For( this ) is { IsDowned: true } ) return "downed";
		if ( !ignoreInput && IsSlowWalking ) return "walking";
		return null;
	}

	private void StopSlide()
	{
		if ( !IsSliding ) return;
		IsSliding = false;
		_slideCooldown = SlideCooldown;
	}

	/// <summary>
	/// The slope's pull along the ground: walking, the legs hold you against it, but a slide only has friction. Called on
	/// the ground, before friction.
	/// </summary>
	private void ApplySlideSlope()
	{
		var tr = Scene.Trace.Ray( WorldPosition + Vector3.Up * 4f, WorldPosition + Vector3.Down * 8f )
			.IgnoreGameObjectHierarchy( GameObject )
			.WithoutTags( "corpse", "ragdoll", "player" )
			.Run();

		if ( !tr.Hit ) return;

		var n = tr.Normal;
		if ( n.z >= 0.999f || n.z <= 0f ) return;

		// Gravity's part along the plane, horizontally: g n.z (n.x, n.y), pointing downhill.
		CharacterController.Velocity += Global.Gravity.z * n.z * n.WithZ( 0 ) * SlideSlopeHelp * Time.Delta;
	}

	/// <summary>Dropping onto the ground at a run: the landing for whatever it's made of, a little softer.</summary>
	[Rpc.Broadcast]
	private void PlaySlideSound( Vector3 position )
	{
		var tr = Scene.Trace.Ray( position + Vector3.Up * 8f, position + Vector3.Down * 16f )
			.IgnoreGameObjectHierarchy( GameObject )
			.WithoutTags( "corpse", "ragdoll" )
			.Run();

		var sound = (tr.Hit ? WorldSounds.Landing( WorldSounds.SurfaceAt( tr ) ) : null) ?? LandSound;
		if ( sound is null ) return;

		var snd = Sound.Play( sound, tr.Hit ? tr.HitPosition : position );
		if ( !snd.IsValid() ) return;

		snd.Volume *= 0.7f;
		snd.SpacialBlend = IsViewer ? 0 : snd.SpacialBlend;
	}
}
