namespace Facepunch;

/// <summary>
/// Lying prone. The body lies along <see cref="ProneYaw"/> (its feet to its head) and the view turns over it: within
/// <see cref="ProneFreeArc"/> either way the body stays put, past that it pivots after the view at
/// <see cref="ProneTurnRate"/>, and a look further round than <see cref="RollOverAngle"/> rolls it onto its back
/// (<see cref="IsSupine"/>), looking down along itself at its feet, as Black Ops 6's supine prone does. Looking back
/// over the head rolls it face down again. The camera stays at the lying head (<see cref="PlaceHeadForProne"/>), and
/// <see cref="ThirdPersonPronePose"/> lays the body out under it, the first-person legs included. Crawling rolls
/// the player face down and brings the legs behind the view, with alternating footsteps driven by ground speed.
/// </summary>
public sealed partial class PlayerPawn
{
	/// <summary>The eyes' drop when lying down, from standing.</summary>
	public const float ProneEyeOffset = -40f;

	/// <summary>How far either side of the body's heading the view turns before the body pivots after it.</summary>
	public const float ProneFreeArc = 45f;

	/// <summary>How fast a lying body pivots on its elbows (or its back) after the view, in degrees a second.</summary>
	public const float ProneTurnRate = 90f;

	/// <summary>A crawler turns to face the camera much faster than someone looking around while lying still.</summary>
	public const float ProneCrawlTurnRate = 480f;

	/// <summary>Looking further round than this from the body's heading rolls it over: a quick look behind.</summary>
	public const float RollOverAngle = 110f;

	/// <summary>How long rolling over takes.</summary>
	public const float RollTime = 0.4f;

	/// <summary>The first-person legs show once the body is this far down, clear of the camera.</summary>
	public const float FirstPersonLegsBlend = 0.9f;

	/// <summary>The heading from a lying body's feet to its head. The owner turns it, and every machine lays the body by it.</summary>
	[Sync] public float ProneYaw { get; set; }

	/// <summary>Lying on the back, looking along the body at the feet.</summary>
	[Sync] public bool IsSupine { get; set; }

	/// <summary>How far down the body is, 0 standing to 1 lying, eased at the eyes' pace on every machine.</summary>
	public float ProneBlend { get; private set; }

	/// <summary>How far the body has rolled onto its back, 0 face down to 1 on its back.</summary>
	public float SupineBlend { get; private set; }

	/// <summary>How strongly the legs crawl, based on actual horizontal movement instead of input alone.</summary>
	public float ProneCrawlBlend { get; private set; }

	/// <summary>Alternating leg cycle shared by the normal body and the first-person legs.</summary>
	public float ProneCrawlPhase { get; private set; }

	private Vector3? _headRest;

	/// <summary>Turn the lying body after the view, and roll it over for a look behind. Only the owner turns it.</summary>
	private void UpdateProneFacing()
	{
		if ( !IsLocallyControlled ) return;

		var view = EyeAngles.yaw;
		if ( !IsProne || HealthComponent.State != LifeState.Alive )
		{
			// Getting up, the body rises where it lay; once up it faces the view again.
			if ( ProneBlend <= 0f )
			{
				ProneYaw = view;
				IsSupine = false;
			}
			return;
		}

		// When moving, get off the back and bring the feet behind the camera again. Otherwise a supine player
		// can glide along the ground with both boots still stretched out in front of their view.
		if ( !IsFallKnockedDown && !IsFrozen && IsGrounded && WishMove.WithZ( 0f ).LengthSquared > 0.02f )
		{
			IsSupine = false;
			var towardView = Wrap( view - ProneYaw );
			ProneYaw = Wrap( ProneYaw + MathF.Sign( towardView ) *
				MathF.Min( MathF.Abs( towardView ), ProneCrawlTurnRate * Time.Delta ) );
			return;
		}

		var turn = Wrap( view - ProneYaw );
		if ( IsSupine )
		{
			if ( MathF.Abs( turn ) < 180f - RollOverAngle )
			{
				IsSupine = false;
				return;
			}
			// On the back the view looks along the body at the feet: that's what it turns about.
			turn = Wrap( turn - 180f );
		}
		else if ( MathF.Abs( turn ) > RollOverAngle )
		{
			IsSupine = true;
			return;
		}

		if ( MathF.Abs( turn ) > ProneFreeArc )
			ProneYaw = Wrap( ProneYaw + MathF.Sign( turn ) * MathF.Min( MathF.Abs( turn ) - ProneFreeArc, ProneTurnRate * Time.Delta ) );
	}

	/// <summary>Ease the body down and up with the eyes, and over onto its back, on every machine.</summary>
	private void UpdateProneBlend()
	{
		if ( HealthComponent.State != LifeState.Alive )
		{
			ProneBlend = 0f;
			SupineBlend = 0f;
			ProneCrawlBlend = 0f;
			return;
		}

		var lying = IsProne;
		ProneBlend = ProneBlend.LerpTo( lying ? 1f : 0f, Time.Delta * StanceChangeRate( !lying ) );
		if ( ProneBlend < 0.001f ) ProneBlend = 0f;
		else if ( ProneBlend > 0.999f ) ProneBlend = 1f;
		SupineBlend = SupineBlend.Approach( IsSupine ? 1f : 0f, Time.Delta / RollTime );

		// Footwork is driven by actual travel so pressing into a wall doesn't make the character swim on the spot.
		// Remote pawns use the same replicated velocity that drives their other movement animations.
		var local = IsLocallyControlled && CharacterController.IsValid();
		var velocity = local ? CharacterController.Velocity : SyncedVelocity;
		var grounded = local ? CharacterController.IsOnGround : SyncedIsGrounded;
		var speed = velocity.WithZ( 0f ).Length;
		var crawl = IsProne && !IsFallKnockedDown && grounded ? ((speed - 3f) / 18f).Clamp( 0f, 1f ) : 0f;
		ProneCrawlBlend = ProneCrawlBlend.Approach( crawl, Time.Delta * 5f );
		if ( ProneBlend <= 0f )
			ProneCrawlPhase = 0f;
		else if ( crawl > 0f )
			ProneCrawlPhase = (ProneCrawlPhase + MathF.Min( speed, 70f ) * Time.Delta * (2f * MathF.PI / 44f)) % (2f * MathF.PI);
	}

	/// <summary>
	/// Keep the camera at the lying head. Standing it sits ahead of the pawn along the view; lying, along the body's
	/// heading, so it stays put as the view turns over the body and a roll onto the back leaves the head where it was.
	/// </summary>
	private void PlaceHeadForProne()
	{
		if ( !Head.IsValid() ) return;
		_headRest ??= Head.LocalPosition;
		var rest = _headRest.Value;
		if ( ProneBlend <= 0f )
		{
			Head.LocalPosition = rest;
			return;
		}

		var lying = WorldRotation.Inverse * (Rotation.FromYaw( ProneYaw ) * rest.WithZ( 0f ));
		Head.LocalPosition = Vector3.Lerp( rest.WithZ( 0f ), lying.WithZ( 0f ), ProneBlend ).WithZ( rest.z );
	}

	/// <summary>Where the eyes are once the body lies down: the camera's place at the end of the drop.</summary>
	internal Vector3 ProneEyeTarget
	{
		get
		{
			var rest = _headRest ?? (Head.IsValid() ? Head.LocalPosition : new Vector3( 9f, 0f, 60f ));
			return WorldPosition + Rotation.FromYaw( ProneYaw ) * rest.WithZ( 0f ) + Vector3.Up * (rest.z + ProneEyeOffset);
		}
	}

	private static float Wrap( float degrees ) => degrees - 360f * MathF.Floor( (degrees + 180f) / 360f );
}
