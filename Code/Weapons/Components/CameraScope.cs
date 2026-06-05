using System.Text.Json.Serialization;

namespace Facepunch;

[Title( "3D Scope" ), Group( "Weapon Components" )]
public class CameraScope : Component
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

	protected override void OnPreRender()
	{
		if ( !GameSettingsSystem.Current.PictureInPictureScopes )
		{
			DisableRender();
			return;
		}

		if ( !EnsureInitialized() )
			return;

		if ( !Scene.Camera.IsValid() )
			return;

		var isFarAway = Renderer.WorldPosition.Distance( Scene.Camera.WorldPosition ) > 5f;
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

		MyTexture.Clear( Color.Black );
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
		var eyePos = Scene.Camera.WorldPosition;

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

		MyTexture ??= Texture.CreateRenderTarget( $"3d_scope_{GetHashCode()}", ImageFormat.RGBA8888, 512 );
		if ( MyTexture is null )
		{
			Renderer.Tint = Renderer.Tint.WithAlpha( 0f );
			return false;
		}

		MyTexture.Clear( Color.Black );

		RuntimeScopeMaterial ??= ScopeMaterial?.CreateCopy();
		if ( RuntimeScopeMaterial is not null )
		{
			RuntimeScopeMaterial.Set( "ReflectionTexture", MyTexture );
			RuntimeScopeMaterial.Set( "TextureColor", MyTexture );
			Renderer.SetMaterial( RuntimeScopeMaterial );
		}
		else if ( ScopeMaterial is not null )
		{
			Renderer.SetMaterial( ScopeMaterial );
		}

		RenderCamera.RenderTarget = MyTexture;

		if ( RenderCamera.GameObject.IsValid() )
			RenderCamera.GameObject.SetParent( GameObject );

		Renderer.Tint = Renderer.Tint.WithAlpha( 1f );
		ApplyScopeAttributes();

		return true;
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
