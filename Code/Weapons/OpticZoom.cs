using Facepunch.Gunsmith;

namespace Facepunch;

/// <summary>
/// MW2022-style picture-in-picture magnified optics. While aiming, the view only zooms slightly and the gun,
/// hands and optic housing stay in view; a second camera renders the magnified world into a texture that
/// <see cref="UI.ScopeOverlay"/> draws inside the optic's lens.
/// </summary>
public sealed class OpticZoom : Component
{
	/// <summary>How much the whole view zooms while aiming a magnified optic.</summary>
	public const float ViewMagnification = 1.2f;

	/// <summary>0..1 aim-in progress of the local player on a magnified optic. 0 when not using one.</summary>
	public static float ScopeBlend { get; private set; }

	/// <summary>Magnified view for the lens, or null when inactive.</summary>
	public static Texture LensTexture { get; private set; }

	/// <summary>Lens diameter as a fraction of screen height. Set by the overlay; drives the lens camera FOV.</summary>
	public static float LensDiameter { get; set; } = 0.3f;

	/// <summary>Eyepiece offset from screen centre as a fraction of screen height (x right, y down), from sway/recoil.</summary>
	public static Vector2 ScopeOffset { get; private set; }

	[Property] public CameraController CameraController { get; set; }

	/// <summary>On-screen size of the lens relative to its size when aimed (grows/shrinks as the optic moves).</summary>
	public static float LensScale { get; private set; } = 1f;

	/// <summary>0..1, how well the optic lines up with the eye. The lens picture fades out as the gun is pulled away.</summary>
	public static float LensVisibility { get; private set; }

	/// <summary>Distance in front of the eye where the lens is anchored to the optic (roughly the rear glass).</summary>
	private const float AnchorDistance = 4f;

	private CameraComponent _lensCamera;
	private CameraComponent _main;
	private GameObject _optic;
	private float _magnification = 1f;
	private bool _reloading;

	// Where the eye's line of sight passes through the optic, and the aim direction, in the optic's own space.
	// Learned while fully aimed, so the lens can then be drawn wherever the optic actually is (reloads, sway, recoil).
	private Vector3 _anchorLocal;
	private Rotation _aimLocal;
	private bool _calibrated;
	private GameObject _calibratedFor;

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

		var aimFov = Equipment.ZoomFov( baseFov + equipment.AimFovOffset, ViewMagnification );
		ScopeBlend = equipment.HasTag( "aiming" )
			? ((baseFov - main.FieldOfView) / MathF.Max( baseFov - aimFov, 0.01f )).Clamp( 0f, 1f )
			: 0f;

		if ( ScopeBlend <= 0f )
		{
			Deactivate();
			return;
		}

		viewModel.GameObject.Tags.Add( "optic_viewmodel" );
		_main = main;
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
	protected override void OnPreRender()
	{
		if ( !_lensCamera.IsValid() || !_lensCamera.Enabled || !_main.IsValid() ) return;
		if ( !_optic.IsValid() ) { LensVisibility = 0f; return; }

		var cam = _main.WorldTransform;
		var optic = _optic.WorldTransform;

		// Learn (and slowly refine) how the optic sits in front of the eye while properly aimed in.
		if ( ScopeBlend >= 0.98f && !_reloading )
		{
			var anchor = optic.PointToLocal( cam.Position + cam.Rotation.Forward * AnchorDistance );
			var aim = optic.Rotation.Inverse * cam.Rotation;
			if ( !_calibrated )
			{
				_anchorLocal = anchor;
				_aimLocal = aim;
				_calibrated = true;
			}
			else
			{
				var t = (Time.Delta * 2f).Clamp( 0f, 1f );
				_anchorLocal = Vector3.Lerp( _anchorLocal, anchor, t );
				_aimLocal = Rotation.Slerp( _aimLocal, aim, t );
			}
		}

		var lensRotation = cam.Rotation;
		var lensPoint = cam.Position + cam.Rotation.Forward * AnchorDistance;
		if ( _calibrated )
		{
			lensRotation = optic.Rotation * _aimLocal;
			lensPoint = optic.PointToWorld( _anchorLocal );
		}

		// Project the anchor onto the screen (x forward, y left, z up in camera space).
		var focal = 0.5f * Screen.Width / MathF.Tan( _main.FieldOfView.Clamp( 1f, 170f ).DegreeToRadian() * 0.5f );
		var local = cam.PointToLocal( lensPoint );
		var depth = MathF.Max( local.x, 0.5f );
		ScopeOffset = new Vector2( -local.y / depth * focal / Screen.Height, -local.z / depth * focal / Screen.Height );
		LensScale = (AnchorDistance / depth).Clamp( 0.3f, 2f );

		// Fade the picture out as the optic turns away from the eye (e.g. tilted for a reload).
		var angle = Vector3.GetAngle( lensRotation.Forward, cam.Rotation.Forward );
		var visible = local.x > 0.5f ? (1f - (angle - 2f) / 6f).Clamp( 0f, 1f ) : 0f;
		LensVisibility = LensVisibility.Approach( visible, Time.Delta * 10f );

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
		_optic = null;
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
