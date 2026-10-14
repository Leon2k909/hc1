namespace Facepunch;

/// <summary>
/// Sliding. Press Duck while sprinting on the ground and you drop onto a hip and slide on, faster than the sprint, holding
/// most of that speed for the first half of the slide and then slowing until you come up in a crouch (or standing, if
/// Duck isn't held). A tap is enough: letting go of Duck doesn't stop it. Press Duck again to cancel it and stand straight
/// back into the sprint. Jump ends it in a jump that keeps the speed, Prone ends it on the floor. Duck pressed just before
/// landing from a sprint slides as you land. Downhill keeps it going and uphill stops it sooner. Only the owner moves the
/// pawn; everyone else sees the third-person hip slide and hears it go down.
/// </summary>
public partial class PlayerPawn
{
	/// <summary>The eye's offset in a slide: lower than a crouch (-16), sat back on one hip.</summary>
	private const float SlideEyeOffset = -24f;

	/// <summary>How fast the eyes drop into a slide, as a lerp rate per second (a stance change's is 10): most of the way in ~0.1 s.</summary>
	private const float SlideDropRate = 24f;

	/// <summary>
	/// How fast a slide bleeds speed (a crouch's is 4). It starts almost free (<see cref="SlideFrictionStart"/>), holds
	/// that for <see cref="SlideHoldTime"/>, then rises to <see cref="SlideFrictionEnd"/> over <see cref="SlideFrictionRamp"/>.
	/// A rifle's 285 u/s sprint slides off at 400 and is still at ~370 half a second in; the slide lasts ~1.15 s and goes
	/// ~375 units (9.5 m).
	/// </summary>
	private const float SlideFrictionStart = 0.12f;
	private const float SlideFrictionEnd = 1.6f;
	private const float SlideHoldTime = 0.35f;
	private const float SlideFrictionRamp = 0.7f;

	/// <summary>How much the keys steer a slide: barely.</summary>
	private const float SlideAcceleration = 1.5f;

	/// <summary>The push the drop gives on top of the sprint's speed, at least to <see cref="SlideStartFloor"/> and at most <see cref="SlideMaxSpeed"/>.</summary>
	private const float SlideBoost = 115f;
	private const float SlideStartFloor = 340f;
	private const float SlideMaxSpeed = 430f;

	/// <summary>Slower than this over the ground and Duck only crouches.</summary>
	private const float SlideMinStartSpeed = 180f;

	/// <summary>The slide ends below this speed: about where a sprint picks up again.</summary>
	private const float SlideEndSpeed = 180f;

	/// <summary>The longest a slide lasts, even downhill.</summary>
	private const float SlideMaxTime = 1.5f;

	/// <summary>How long after a slide ends before another can start.</summary>
	private const float SlideCooldown = 0.4f;

	/// <summary>How soon into a slide a second Duck press cancels it (so the press that started it doesn't).</summary>
	private const float SlideCancelDelay = 0.15f;

	/// <summary>How long before landing a Duck press at a sprint still slides as you land.</summary>
	private const float SlideLandingBuffer = 0.25f;

	/// <summary>How long after a slide a toggled sprint waits to pick up again (you're getting up, or still crouched).</summary>
	private const float SlideSprintResumeWindow = 0.5f;

	/// <summary>The share of the slope's pull a slide gets: downhill keeps it going, uphill stops it sooner.</summary>
	private const float SlideSlopeHelp = 0.5f;

	/// <summary>Down on one hip, sliding. Holds crouched movement, silences footsteps and drives the third-person pose.</summary>
	[Sync] public bool IsSliding { get; private set; }

	/// <summary>0 to 1, eased in and out with <see cref="IsSliding"/> on every machine: the viewmodel and third-person pose follow it.</summary>
	public float SlideBlend { get; private set; }

	private TimeSince _slideTime;
	private TimeUntil _slideCooldown;
	private TimeUntil _slideBuffered;

	/// <summary>A cancelled slide's Duck press: it doesn't crouch until Duck is let go.</summary>
	private bool _slideCancelHeld;

	/// <summary>A toggled sprint the slide stopped, to pick up again when it ends (see <see cref="GetWantsToSprint"/>).</summary>
	private bool _resumeSprintAfterSlide;
	private TimeSince _slideEnded;

	/// <summary>The slide's friction now: almost none at first, rising once it's under way.</summary>
	private float SlideFriction
	{
		get
		{
			var t = ((_slideTime - SlideHoldTime) / SlideFrictionRamp).Clamp( 0f, 1f );
			t = t * t * (3f - 2f * t);
			return SlideFrictionStart + (SlideFrictionEnd - SlideFrictionStart) * t;
		}
	}

	private void UpdateSlideBlend()
	{
		// Quick into the hip, a little slower back up.
		var target = IsSliding ? 1f : 0f;
		SlideBlend = SlideBlend.LerpTo( target, Time.Delta * (IsSliding ? 16f : 7f) );
		if ( MathF.Abs( SlideBlend - target ) < 0.002f ) SlideBlend = target;
	}

	/// <summary>
	/// Start a slide on a Duck press while sprinting, or keep one going until it's slowed down, timed out, left the ground,
	/// or been cancelled, jumped or dropped out of. Runs from <see cref="BuildInput"/>, before the crouch is read.
	/// </summary>
	private void UpdateSlide( bool wasSprinting )
	{
		var cc = CharacterController;

		if ( _slideCancelHeld && !Input.Down( "Duck" ) )
			_slideCancelHeld = false;

		if ( !IsSliding )
		{
			var sprinting = wasSprinting || IsSprinting;
			if ( Input.Pressed( "Duck" ) && sprinting )
			{
				// In the air, the press waits for the landing.
				if ( !cc.IsOnGround ) _slideBuffered = SlideLandingBuffer;
				else TryStartSlide();
			}
			else if ( _slideBuffered.Relative > 0f && cc.IsOnGround && Input.Down( "Duck" ) )
			{
				_slideBuffered = 0;
				TryStartSlide();
			}
			return;
		}

		// A second Duck press stands you up out of it, back into the sprint.
		if ( Input.Pressed( "Duck" ) && _slideTime > SlideCancelDelay )
		{
			_slideCancelHeld = true;
			StopSlide();
			return;
		}

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

		var speed = MathF.Min( MathF.Max( flat.Length + SlideBoost, SlideStartFloor ), SlideMaxSpeed );
		cc.Velocity = flat.Normal * speed;
		if ( log ) Log.Info( $"Slide: from {flat.Length:F0} to {speed:F0} u/s" );

		IsSliding = true;
		_slideTime = 0;
		_slideBuffered = 0;
		_slideCancelHeld = false;

		// Out of the sprint: the gun comes up as it does when a sprint stops. A toggled sprint picks up again afterwards.
		_resumeSprintAfterSlide = WantsToggleSprint;
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
		_slideEnded = 0;
	}

	/// <summary>
	/// For a toggled sprint: whether to pick up the sprint a slide stopped, now that it's ended and you can sprint again.
	/// Run pressed during the slide asks for it too (or takes it back). Gives up once the window's gone (you stayed
	/// crouched).
	/// </summary>
	private bool ResumeSprintAfterSlide()
	{
		if ( IsSliding )
		{
			if ( Input.Pressed( "Run" ) ) _resumeSprintAfterSlide = !_resumeSprintAfterSlide;
			return false;
		}

		if ( !_resumeSprintAfterSlide ) return false;
		if ( _slideEnded > SlideSprintResumeWindow )
		{
			_resumeSprintAfterSlide = false;
			return false;
		}
		if ( !CanSprint ) return false;

		_resumeSprintAfterSlide = false;
		return true;
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
