namespace Facepunch;

/// <summary>A short receiver-centred inspection shared by the two viewmodel systems.</summary>
public sealed class WeaponInspectAnimation
{
	public const string InputAction = "InspectWeapon";
	public const float Duration = 4.3f;
	private const float CancelDuration = 0.12f;

	public bool IsPlaying { get; private set; }
	public bool IsActive => IsPlaying || _returning;
	public Transform Pose { get; private set; } = new();

	private float _elapsed;
	private bool _returning;
	private float _returnElapsed;
	private Transform _returnPose;

	public void Update( bool pressed, bool blocked, float delta, float poseScale = 1f, float rotationScale = 1f )
	{
		if ( blocked )
			Cancel();
		else if ( pressed && !IsActive )
		{
			IsPlaying = true;
			_elapsed = 0f;
		}

		if ( IsPlaying )
		{
			_elapsed += delta;
			Pose = Evaluate( _elapsed, poseScale, rotationScale );
			if ( _elapsed >= Duration ) Reset();
		}
		else if ( _returning )
		{
			_returnElapsed += delta;
			var blend = Ease( _returnElapsed / CancelDuration );
			Pose = new Transform( _returnPose.Position * (1f - blend), Rotation.Lerp( _returnPose.Rotation, Rotation.Identity, blend ) );
			if ( _returnElapsed >= CancelDuration ) Reset();
		}
	}

	public void Cancel()
	{
		if ( !IsPlaying ) return;
		IsPlaying = false;
		_returning = true;
		_returnElapsed = 0f;
		_returnPose = Pose;
	}

	public void Reset()
	{
		IsPlaying = false;
		_returning = false;
		_elapsed = 0f;
		Pose = new Transform();
	}

	// time, position, pitch/yaw/roll. Right side, swing over to the left side, tip up to check the top, return.
	private static readonly (float Time, Vector3 Position, Angles Angles)[] Keys =
	{
		(0.00f, Vector3.Zero, Angles.Zero),
		(0.45f, new Vector3( 5f, 2f, 1.5f ), new Angles( 2f, -30f, -12f )),
		(1.30f, new Vector3( 6f, 2.5f, 2f ), new Angles( 4f, -36f, -18f )),
		(1.95f, new Vector3( 6f, -1f, 2.5f ), new Angles( -4f, 22f, 26f )),
		(2.80f, new Vector3( 6f, -1.5f, 2.5f ), new Angles( -6f, 28f, 32f )),
		(3.35f, new Vector3( 4f, 0f, 3f ), new Angles( -14f, 4f, 6f )),
		(3.80f, new Vector3( 2f, 0f, 1.5f ), new Angles( -10f, 0f, 2f )),
		(Duration, Vector3.Zero, Angles.Zero),
	};

	public static Transform Evaluate( float time, float poseScale = 1f, float rotationScale = 1f )
	{
		var i = 1;
		while ( i < Keys.Length - 1 && time > Keys[i].Time ) i++;
		var (t0, p0, a0) = Keys[i - 1];
		var (t1, p1, a1) = Keys[i];
		var blend = Ease( (time - t0) / (t1 - t0) );
		poseScale = poseScale.Clamp( 0f, 1f );

		var angleScale = poseScale * rotationScale.Clamp( 0f, 1f );
		var angles = new Angles( a0.pitch.LerpTo( a1.pitch, blend ) * angleScale, a0.yaw.LerpTo( a1.yaw, blend ) * angleScale, a0.roll.LerpTo( a1.roll, blend ) * angleScale );
		var rotation = angles.ToRotation();
		// Rotate around the receiver rather than the viewmodel origin, so the stock stays off the near plane.
		var pivot = new Vector3( 16f, -4f, -4f );
		var position = p0.LerpTo( p1, blend ) * poseScale + pivot - rotation * pivot;
		return new Transform( position, rotation );
	}

	private static float Ease( float value )
	{
		var t = value.Clamp( 0f, 1f );
		return t * t * (3f - 2f * t);
	}
}
