namespace Facepunch;

/// <summary>Transient eye/weapon lag during turns, measured in eyepiece radii.</summary>
public sealed class ScopeEyeMotion
{
	private Rotation _lastView;
	private bool _hasView;
	public Vector2 Offset { get; private set; }
	public float TurnSpeed { get; private set; }

	public Vector2 Update( Rotation view, float delta )
	{
		if ( !_hasView || delta <= 0f || delta > 0.1f )
		{
			_lastView = view;
			_hasView = true;
			TurnSpeed = 0f;
			Offset = Vector2.Zero;
			return Offset;
		}

		// Project the previous direction into the new view. This handles yaw wrap and looking vertically without
		// Euler-angle jumps; positive x/y means the eye turned right/down relative to the weapon.
		var previous = view.Inverse * _lastView.Forward;
		var turn = new Vector2( MathF.Atan2( previous.y, previous.x ),
			MathF.Atan2( previous.z, MathF.Sqrt( previous.x * previous.x + previous.y * previous.y ) ) ) * (180f / MathF.PI);
		_lastView = view;
		var velocity = turn / delta;
		TurnSpeed = velocity.Length;

		// Fine tracking keeps the eye in the pupil. A fast sweep moves it toward the edge, with a short settling tail.
		var target = velocity.Normal * ((TurnSpeed - 20f) * 0.0014f).Clamp( 0f, 0.72f );
		var response = target.Length > Offset.Length ? 0.018f : 0.06f;
		Offset = Offset.LerpTo( target, 1f - MathF.Exp( -delta / response ) );
		return Offset;
	}

	public void Reset()
	{
		_hasView = false;
		Offset = Vector2.Zero;
		TurnSpeed = 0f;
	}
}
