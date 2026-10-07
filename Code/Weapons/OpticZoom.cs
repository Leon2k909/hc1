using Facepunch.Gunsmith;

namespace Facepunch;

/// <summary>
/// MW2022-style picture-in-picture magnified optics. While aiming, the view only zooms slightly and the gun,
/// hands and optic housing stay in view; a second camera renders the magnified world into a texture that
/// <see cref="UI.ScopeOverlay"/> draws inside the optic's lens.
/// </summary>
public sealed class OpticZoom : Component, ICameraSetup
{
	/// <summary>How much the whole view zooms while aiming a magnified optic.</summary>
	public const float ViewMagnification = 1.2f;

	/// <summary>
	/// 0..1, how far the local player's sights are up on a magnified optic (<see cref="ViewModel.AimProgress"/>), and
	/// still going while they come down. 0 when not using one.
	/// </summary>
	public static float ScopeBlend { get; private set; }

	/// <summary>Magnified view for the lens, or null when inactive.</summary>
	public static Texture LensTexture { get; private set; }

	/// <summary>Lens diameter as a fraction of screen height. Set by the overlay; drives the lens camera FOV.</summary>
	public static float LensDiameter { get; set; } = 0.3f;
	public static bool OverlayDotVisible { get; private set; } = true;

	/// <summary>Eyepiece offset from screen centre as a fraction of screen height (x right, y down), from sway/recoil.</summary>
	public static Vector2 ScopeOffset { get; private set; }

	[Property] public CameraController CameraController { get; set; }

	/// <summary>On-screen size of the lens relative to its size when aimed (grows/shrinks as the optic moves).</summary>
	public static float LensScale { get; private set; } = 1f;

	/// <summary>
	/// 0..1, how well the optic lines up with the eye: <see cref="UI.ScopeOverlay"/>'s opacity. The picture shows as the
	/// eyepiece comes in front of the eye, and goes as the gun is pulled away.
	/// </summary>
	public static float LensVisibility { get; private set; }

	/// <summary>Distance in front of the eye where the lens is anchored to an optic whose eyepiece isn't known.</summary>
	private const float AnchorDistance = 4f;

	/// <summary>
	/// The picture is all there while the line of sight passes this share of the eyepiece's radius from its centre, and
	/// gone once it's off the glass. Off to the side a real scope shows black, and the sway of a hard turn while aimed stays
	/// inside it.
	/// </summary>
	private const float FullOnAxis = 0.35f;

	/// <summary>How long the aim has to have settled before the optic's place in front of the eye is learned from it.</summary>
	private const float SettleTime = 0.15f;

	private CameraComponent _lensCamera;
	private CameraComponent _main;
	private ViewModel _viewModel;
	private GameObject _optic;
	private float _magnification = 1f;
	private bool _reloading;

	// The eyepiece's rear glass in the optic's own space, and its diameter (GunsmithPart.OpticEyepiece). 0 when not known.
	private Vector3 _eyepiece;
	private float _eyepieceDiameter;

	// Where the eye's line of sight passes through the optic, and the aim direction, in the optic's own space.
	// Learned while fully aimed, so the lens can then be drawn wherever the optic actually is (reloads, sway, recoil).
	private Vector3 _anchorLocal;
	private Rotation _aimLocal;
	private bool _calibrated;
	private GameObject _calibratedFor;
	private float _settledFor;

	protected override void OnDisabled() => Deactivate();

	protected override void OnDestroy()
	{
		Deactivate();
		if ( _lensCamera.IsValid() ) _lensCamera.GameObject.Destroy();
	}

	/// <summary>Runs after the main camera's FOV is set for this frame.</summary>
	public void UpdateCamera( float baseFov )
	{
		var main = CameraController?.Camera;
		var player = CameraController?.Player;
		var equipment = player?.CurrentEquipment;
		var viewModel = equipment?.ViewModel;

		if ( !main.IsValid() || !viewModel.IsValid() || !player.IsLocallyControlled
			|| CameraController.Mode != CameraMode.FirstPerson
			|| !equipment.TryGetOpticAim( out var optic ) || optic.OpticMagnification <= 1f )
		{
			Deactivate();
			return;
		}
		// With the eyepiece known, PostSetup sizes the lens to its glass each frame.
		_eyepiece = optic.OpticEyepiece;
		_eyepieceDiameter = optic.OpticEyepieceDiameter;
		if ( _eyepieceDiameter <= 0f )
			LensDiameter = optic.OpticLensDiameter.Clamp( 0.05f, 0.5f );
		OverlayDotVisible = optic.OpticOverlayDot;

		// The gun's own aim, not the camera's zoom: that eases in more slowly, so the picture waited ~0.3 s after the scope
		// was at the eye, and only showed fully after 0.6 s.
		ScopeBlend = equipment.HasTag( "aiming" ) ? MathF.Max( viewModel.AimProgress, 0.001f ) : viewModel.AimProgress;

		if ( ScopeBlend <= 0f )
		{
			Deactivate();
			return;
		}

		_settledFor = viewModel.IsAimSettled ? _settledFor + Time.Delta : 0f;

		viewModel.GameObject.Tags.Add( "optic_viewmodel" );
		_main = main;
		_viewModel = viewModel;
		_reloading = equipment.HasTag( "reloading" );
		_magnification = optic.OpticMagnification.Clamp( 1f, 8f ) / ViewMagnification;
		_optic = FindOptic( viewModel );

		if ( _calibratedFor != _optic )
		{
			_calibrated = false;
			_calibratedFor = _optic;
		}

		EnsureLensCamera( main );
		_lensCamera.Enabled = true;
		LensTexture = _lensCamera.RenderTarget;
	}

	private static GameObject FindOptic( ViewModel viewModel ) =>
		viewModel.GameObject.Components.GetAll<GunsmithAttachmentPoint>( FindMode.EverythingInSelfAndDescendants )
			.Where( p => p.Category == GunsmithPartType.Optic && p.CurrentGameObject.IsValid() )
			.Select( p => p.CurrentGameObject ).FirstOrDefault();

	// Viewmodel animation and camera effects are final by now; place the lens on the optic right before rendering.
	void ICameraSetup.PostSetup( CameraComponent camera )
	{
		if ( camera != _main ) return;
		if ( !_lensCamera.IsValid() || !_lensCamera.Enabled || !_main.IsValid() ) return;
		if ( !_optic.IsValid() ) { LensVisibility = 0f; return; }

		var cam = _main.WorldTransform;
		var optic = _optic.WorldTransform;

		// Corner slicing cants the gun about the line of sight (ViewModel.CornerSlicing.cs). Measure the optic against the
		// canted view, and turn the lens back, so the magnified picture stays level (as a real scope's does) while the gun cants.
		var cant = Rotation.FromRoll( _viewModel.IsValid() ? _viewModel.CornerRoll : 0f );

		// The lens is anchored where the line of sight crosses the eyepiece's glass, or a guess at it.
		var fitted = _eyepieceDiameter > 0f;
		var eyepiece = optic.PointToWorld( _eyepiece );
		var anchorDistance = fitted ? MathF.Max( cam.PointToLocal( eyepiece ).x, 0.5f ) : AnchorDistance;

		// Learn (and slowly refine) how the optic sits in front of the eye while properly aimed in.
		if ( _settledFor >= SettleTime && !_reloading )
		{
			var anchor = optic.PointToLocal( cam.Position + cam.Rotation.Forward * anchorDistance );
			var aim = optic.Rotation.Inverse * cam.Rotation * cant;
			if ( !_calibrated )
			{
				_anchorLocal = anchor;
				_aimLocal = aim;
				_calibrated = true;
			}
		}

		var lensRotation = cam.Rotation;
		var lensPoint = fitted ? eyepiece : cam.Position + cam.Rotation.Forward * AnchorDistance;
		if ( _calibrated )
		{
			lensRotation = optic.Rotation * _aimLocal * cant.Inverse;
			// Known eyepieces follow their glass, never a screen-centred calibration sampled during sway.
			if ( !fitted ) lensPoint = optic.PointToWorld( _anchorLocal );
		}

		// Project the anchor onto the screen (x forward, y left, z up in camera space).
		var focal = 0.5f * Screen.Width / MathF.Tan( _main.FieldOfView.Clamp( 1f, 170f ).DegreeToRadian() * 0.5f );
		var local = cam.PointToLocal( lensPoint );
		var depth = MathF.Max( local.x, 0.5f );
		ScopeOffset = new Vector2( -local.y / depth * focal / Screen.Height, -local.z / depth * focal / Screen.Height );
		if ( fitted )
		{
			// The picture fills the eyepiece's glass: its diameter over its distance from the eye, on screen.
			LensDiameter = (_eyepieceDiameter / depth * focal / Screen.Height).Clamp( 0.05f, 1.5f );
			LensScale = 1f;
		}
		else
		{
			LensScale = (AnchorDistance / depth).Clamp( 0.3f, 2f );
		}

		// The picture shows while the eye is behind the eyepiece: the optic pointing along the view (not tilted for a
		// reload), and its glass on the line of sight. Before the optic's aim is learned, its own axis stands in for it.
		var axis = _calibrated ? lensRotation.Forward : optic.Rotation.Forward;
		var angle = Vector3.GetAngle( axis, cam.Rotation.Forward );
		var visible = local.x > 0.5f ? (1f - (angle - 2f) / 6f).Clamp( 0f, 1f ) : 0f;
		if ( fitted )
		{
			var radius = _eyepieceDiameter * 0.5f;
			var offAxis = MathF.Sqrt( local.y * local.y + local.z * local.z );
			visible *= (1f - (offAxis - radius * FullOnAxis) / (radius * (1f - FullOnAxis))).Clamp( 0f, 1f );
		}
		else
		{
			// Its glass isn't known, so only how far the sights are up says when the eye is behind it.
			visible *= ((ScopeBlend - 0.75f) / 0.2f).Clamp( 0f, 1f );
		}
		LensVisibility = LensVisibility.Approach( visible, Time.Delta * 20f );

		// The lens shows the world magnified relative to what surrounds it: the angle the lens covers on screen,
		// divided by the magnification, looking along the optic.
		var radiusPx = LensDiameter * LensScale * 0.5f * Screen.Height;
		_lensCamera.FieldOfView = (2f * MathF.Atan( radiusPx / (focal * _magnification) )).RadianToDegree();
		_lensCamera.WorldPosition = cam.Position;
		_lensCamera.WorldRotation = lensRotation;
	}

	private void Deactivate()
	{
		ScopeBlend = 0f;
		ScopeOffset = Vector2.Zero;
		LensScale = 1f;
		LensVisibility = 0f;
		LensTexture = null;
		OverlayDotVisible = true;
		_optic = null;
		_settledFor = 0f;
		if ( _lensCamera.IsValid() ) _lensCamera.Enabled = false;
	}

	private void EnsureLensCamera( CameraComponent main )
	{
		if ( _lensCamera.IsValid() )
			return;

		var go = new GameObject( GameObject, false, "Optic Lens Camera" ) { Flags = GameObjectFlags.NotSaved | GameObjectFlags.NotNetworked | GameObjectFlags.Hidden };
		_lensCamera = go.Components.Create<CameraComponent>();
		_lensCamera.IsMainCamera = false;
		_lensCamera.ZNear = main.ZNear;
		_lensCamera.ZFar = main.ZFar;
		_lensCamera.RenderExcludeTags.Add( "viewer" );
		_lensCamera.RenderExcludeTags.Add( "viewmodel" );
		_lensCamera.RenderExcludeTags.Add( "optic_viewmodel" );
		_lensCamera.RenderTarget = Texture.CreateRenderTarget( "optic_lens", ImageFormat.RGBA8888, new Vector2( 1024, 1024 ) );
		go.Enabled = true;
	}
}
