namespace Facepunch;

/// <summary>Learn a neutral scope pose only after the eye and the fully raised weapon have settled together.</summary>
public sealed class ScopeEyeAlignment
{
	private const float SettleTime = 0.15f;
	/// <summary>How fast a held-still eye re-centres (1/s): a steady offset is mostly gone in a second.</summary>
	private const float SettleRate = 2.5f;
	private bool _hasCandidate;
	private bool _ready;
	private Vector3 _candidateEye;
	private Rotation _candidateAim;
	private float _settledFor;

	public bool Calibrated { get; private set; }
	public Vector3 AnchorLocal { get; private set; }
	public Rotation AimLocal { get; private set; } = Rotation.Identity;
	public Vector3 NeutralEyeLocal { get; private set; }
	public float Blend { get; private set; }

	public void Update( Transform camera, Transform optic, Rotation cant, float anchorDistance, float glassRadius,
		bool fullyAimed, bool quiet, float delta )
	{
		if ( !fullyAimed )
		{
			BeginAim();
			return;
		}
		if ( _ready )
		{
			Blend = Blend.Approach( 1f, delta * 12f );
			// A shooter's head settles into the eye box. Held still, the neutral pose follows the eye, so a sight line
			// learned slightly off (an idle pose that kept easing, a stance change) can't black the picture out for good;
			// turns, recoil and sway still shade it while they last.
			if ( quiet && delta > 0f && delta <= 0.1f )
			{
				var follow = 1f - MathF.Exp( -delta * SettleRate );
				NeutralEyeLocal = NeutralEyeLocal.LerpTo( optic.PointToLocal( camera.Position ), follow );
				AimLocal = Rotation.Slerp( AimLocal, optic.Rotation.Inverse * camera.Rotation * cant, follow );
			}
			return;
		}
		if ( !quiet || delta <= 0f || delta > 0.1f )
		{
			_hasCandidate = false;
			_settledFor = 0f;
			return;
		}

		var eye = optic.PointToLocal( camera.Position );
		var aim = optic.Rotation.Inverse * camera.Rotation * cant;
		// AimProgress and the manual offset can finish before the animation's optic/camera bones do. Require a
		// stable relative pose too, so a remaining dip, recoil or mouse flick cannot become the neutral eye position.
		if ( !_hasCandidate || eye.Distance( _candidateEye ) > MathF.Max( glassRadius * 0.025f, 0.005f )
			|| aim.Distance( _candidateAim ) > 0.15f )
		{
			_candidateEye = eye;
			_candidateAim = aim;
			_hasCandidate = true;
			_settledFor = 0f;
			return;
		}

		_settledFor += delta;
		if ( _settledFor < SettleTime ) return;
		AnchorLocal = optic.PointToLocal( camera.Position + camera.Rotation.Forward * anchorDistance );
		AimLocal = aim;
		NeutralEyeLocal = eye;
		Calibrated = true;
		_ready = true;
	}

	public Vector3 Displacement( Transform camera, Transform optic, Rotation lensRotation ) => Calibrated
		? lensRotation.Inverse * (camera.Position - optic.PointToWorld( NeutralEyeLocal )) * Blend
		: Vector3.Zero;

	/// <summary>Lowering the gun clears transition shading but keeps its fitted optic's learned sight line.</summary>
	public void BeginAim()
	{
		_ready = false;
		_hasCandidate = false;
		_settledFor = 0f;
		Blend = 0f;
	}

	public void Reset()
	{
		BeginAim();
		Calibrated = false;
		AnchorLocal = Vector3.Zero;
		NeutralEyeLocal = Vector3.Zero;
		AimLocal = Rotation.Identity;
	}
}
