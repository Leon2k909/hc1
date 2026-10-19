using System.Text.Json.Serialization;

namespace Facepunch;

[Title( "3D Scope" ), Group( "Weapon Components" )]
public class CameraScope : Component, ICameraSetup
{
	[Property] public Material ScopeMaterial { get; set; }
	[Property] public CameraComponent RenderCamera { get; set; }
	[RequireComponent] public ModelRenderer Renderer { get; set; }

	public Equipment Equipment => GetComponentInParent<Equipment>();

	[Property]
	public Texture ReticleTexture { get; set; }

	[Property, JsonIgnore]
	public Texture MyTexture { get; set; }

	[Property, JsonIgnore]
	private Material RuntimeScopeMaterial { get; set; }

	[Property]
	public float Forward { get; set; } = 20;

	protected override void OnEnabled()
	{
		// Cloned viewmodels can enable this component before referenced children/properties
		// are fully resolved. Initialization is retried in OnPreRender.
		try
		{
			if ( !GameSettingsSystem.Current.PictureInPictureScopes )
			{
				DisableRender();
				return;
			}

			EnsureInitialized();
		}
		catch ( Exception e )
		{
			Log.Warning( $"CameraScope delayed initialization: {e.Message}" );
		}
	}

	private TimeSince _sinceCameraSetup = 10f;

	protected override void OnPreRender()
	{
		// On the player's gun the scope is worked out in LateSetup instead. This can run before the camera has put the
		// gun in front of the eye this frame, and then the eye was measured against where the gun was a frame ago: moving
		// sideways read as the eye being far off the scope's axis, and the picture went black.
		if ( _sinceCameraSetup < 0.25f )
			return;

		UpdateScope( Scene.Camera );
	}

	void ICameraSetup.LateSetup( CameraComponent cc )
	{
		if ( cc != Scene.Camera )
			return;

		_sinceCameraSetup = 0;
		UpdateScope( cc );
	}

	private void UpdateScope( CameraComponent eye )
	{
		if ( !GameSettingsSystem.Current.PictureInPictureScopes )
		{
			DisableRender();
			return;
		}

		if ( !EnsureInitialized() )
			return;

		if ( !eye.IsValid() )
			return;

		// The lens is within 5 of the eye only while the scope is up to it: the M700's sits 9.7 away at the hip and 3.7
		// aimed. Further off, the scope's own scene isn't drawn and the lens is hidden.
		var isFarAway = Renderer.WorldPosition.Distance( eye.WorldPosition ) > 5f;
		RenderCamera.Enabled = !isFarAway;
		Renderer.Tint = Renderer.Tint.WithAlpha( isFarAway ? 0.0f : 1.0f );

		if ( isFarAway )
			return;

		var origin = GameObject.WorldPosition;
		var forward = RenderCamera.WorldRotation.Forward;
		var tr = Scene.Trace.Ray( origin, origin + forward * Forward )
			.IgnoreGameObjectHierarchy( Equipment?.Owner?.GameObject )
			.Radius( 1 )
			.Run();

		RenderCamera.WorldPosition = tr.EndPosition;

		//DebugOverlay.Line( new Line( tr.StartPosition, tr.EndPosition ), Color.Red, 0f );
		//DebugOverlay.Sphere( new Sphere( tr.EndPosition, 1.5f ), Color.Red, 0f );

		// The camera clears its picture as it draws (ClearFlags All), so the texture needn't be cleared first.
		ApplyScopeAttributes();

		// Are we aiming?
		if ( Equipment.IsValid() && Equipment.HasTag( "aiming" ) )
		{
			var wheel = Input.MouseWheel;
			var wantsToZoom = Input.Keyboard.Down( "ALT" ) && !wheel.IsNearZeroLength;

			if ( wantsToZoom )
			{
				// TODO: Configurable per weapon speed
				RenderCamera.FieldOfView += -wheel.y * Time.Delta * 100f;
			}

			// TODO: Configurable per weapon
			RenderCamera.FieldOfView = RenderCamera.FieldOfView.Clamp( 10, 30 );

			// Dampen aiming, TODO: configurable per weapon
			if ( Equipment.Owner.IsValid() )
				Equipment.Owner.AimDampening /= 1 - RenderCamera.FieldOfView.Remap( 10, 30, 0, 1 ) + 1;
		}

		float fov = RenderCamera.FieldOfView;
		Renderer.SceneObject.Attributes.Set( "ScopeFOV", fov );

		// Get world-space scope data
		var scopePos = RenderCamera.WorldPosition;
		var scopeForward = RenderCamera.WorldRotation.Forward;
		var scopeRight = RenderCamera.WorldRotation.Right;
		var scopeUp = RenderCamera.WorldRotation.Up;

		// Get player eye position
		var eyePos = eye.WorldPosition;

		// Vector from scope to eye
		var toEye = eyePos - scopePos;

		// Project onto local axes
		float localX = toEye.Dot( scopeRight );
		float localY = toEye.Dot( scopeUp );
		float apertureRadius = 0.5f;
		float localOffsetX = Math.Clamp( localX / apertureRadius, -5.0f, 5.0f );
		float localOffsetY = Math.Clamp( localY / apertureRadius, -5.0f, 5.0f );

		// Send to shader
		Renderer.SceneObject.Attributes.Set( "ScopeEyeOffset", new Vector2( localOffsetX, localOffsetY ) );

		// DebugOverlay.Texture( MyTexture, new Rect( 20, Screen.Height * 0.5f ), Color.White );
	}

	private void DisableRender()
	{
		Renderer ??= Components.Get<ModelRenderer>();
		RenderCamera ??= Components.GetInChildren<CameraComponent>( true );

		if ( RenderCamera.IsValid() )
			RenderCamera.Enabled = false;

		if ( Renderer.IsValid() )
			Renderer.Tint = Renderer.Tint.WithAlpha( 0f );
	}

	private bool EnsureInitialized()
	{
		Renderer ??= Components.Get<ModelRenderer>();
		RenderCamera ??= Components.GetInChildren<CameraComponent>( true );

		if ( !Renderer.IsValid() )
			return false;

		if ( !RenderCamera.IsValid() )
		{
			Renderer.Tint = Renderer.Tint.WithAlpha( 0f );
			return false;
		}

		if ( Scene.Camera.IsValid() )
			RenderCamera.ZFar = Math.Max( RenderCamera.ZFar, Scene.Camera.ZFar );

		// Made and cleared once, and again only when the screen's size changes; until now it was cleared every frame.
		var size = PictureSize;
		if ( MyTexture is null || MyTexture.Width != size )
		{
			var old = MyTexture;
			MyTexture = Texture.CreateRenderTarget( $"3d_scope_{GetHashCode()}", ImageFormat.RGBA8888, size );
			if ( MyTexture is null )
			{
				MyTexture = old;
				Renderer.Tint = Renderer.Tint.WithAlpha( 0f );
				return false;
			}

			MyTexture.Clear( Color.Black );
			RuntimeScopeMaterial?.Set( "ReflectionTexture", MyTexture );
			RuntimeScopeMaterial?.Set( "TextureColor", MyTexture );
			RenderCamera.RenderTarget = MyTexture;
			old?.Dispose();
		}

		if ( RuntimeScopeMaterial is null && ScopeMaterial is not null )
		{
			RuntimeScopeMaterial = ScopeMaterial.CreateCopy();
			RuntimeScopeMaterial.Set( "ReflectionTexture", MyTexture );
			RuntimeScopeMaterial.Set( "TextureColor", MyTexture );
		}

		// The gunsmith's camo pass clears the lens's material override, so it's put back whenever it's gone.
		var material = RuntimeScopeMaterial ?? ScopeMaterial;
		if ( material is not null && Renderer.MaterialOverride != material )
			Renderer.SetMaterial( material );

		if ( RenderCamera.RenderTarget != MyTexture )
			RenderCamera.RenderTarget = MyTexture;

		if ( RenderCamera.GameObject.IsValid() && RenderCamera.GameObject.Parent != GameObject )
			RenderCamera.GameObject.SetParent( GameObject );

		Renderer.Tint = Renderer.Tint.WithAlpha( 1f );

		return true;
	}

	/// <summary>
	/// The picture's width and height in pixels: the screen's height, rounded up to 128. Aimed, the M700's glass is about
	/// 1.06 screen heights across. It was a fixed 512, which the lens stretched more than twice over at 1080p.
	/// </summary>
	private static int PictureSize => Math.Clamp( ((int)Screen.Height + 127) / 128 * 128, 512, 2048 );

	protected override void OnDestroy()
	{
		// Each viewmodel makes its own picture, so it goes with the viewmodel.
		MyTexture?.Dispose();
		MyTexture = null;
	}

	private void ApplyScopeAttributes()
	{
		if ( !Renderer.IsValid() || MyTexture is null )
			return;

		RuntimeScopeMaterial?.Set( "ReflectionTexture", MyTexture );
		RuntimeScopeMaterial?.Set( "TextureColor", MyTexture );
		Renderer.SceneObject.Attributes.Set( "ReflectionTexture", MyTexture );
	}
};
