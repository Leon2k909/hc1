using Sandbox.Rendering;

namespace Facepunch.UI;

/// <summary>
/// Lets the first-person gun draw over the HUD's world markers (<see cref="MarkerSystem"/>). The markers are UI, which
/// draws after the whole scene, viewmodel included, so they're masked out wherever the gun covers the view instead.
/// </summary>
/// <remarks>
/// Every frame the viewer's viewmodel is drawn again, with its own materials, into a half-size depth target on the
/// main camera, and <c>hc1_viewmodel_mask.shader</c> turns that into the mask: white where the view is open, black
/// where the gun, its parts or the arms cover it. Only surfaces that write depth cover it, and reticles and lens glass
/// don't (<c>m4_optic_lens.shader</c>), so markers still show through a red dot's window, the iron sights' aperture and
/// see-through magazines. A magnified optic's picture writes depth, so it hides them.
/// </remarks>
public sealed class ViewModelMask : IDisposable
{
	/// <summary>The mask is this fraction of the screen's size.</summary>
	private const int Downscale = 2;

	private static Material _material;
	private static Material MaskMaterial => _material ??= Material.FromShader( "shaders/hc1_viewmodel_mask.shader" );

	private readonly CommandList _commands = new( "Marker Mask" );
	private readonly RenderAttributes _blitAttributes = new();
	private readonly List<ModelRenderer> _renderers = new();

	private CameraComponent _camera;
	private Texture _texture;
	private Texture _retired;
	private RenderTarget _target;

	/// <summary>
	/// This frame's mask, or null when there's no first-person gun on screen to hide the markers behind.
	/// </summary>
	public Texture Texture { get; private set; }

	/// <summary>
	/// Records this frame's mask on the scene's main camera. A null scene turns it off.
	/// </summary>
	public void Update( Scene scene )
	{
		// A texture replaced last frame is no longer drawn with.
		_retired?.Dispose();
		_retired = null;

		var camera = scene?.Camera;
		if ( !camera.IsValid() || !FindRenderers( camera ) )
		{
			Detach();
			Texture = null;
			return;
		}

		var width = Math.Max( 1, (int)Screen.Width / Downscale );
		var height = Math.Max( 1, (int)Screen.Height / Downscale );

		// Returns the same texture while the size holds.
		var texture = Texture.CreateRenderTarget( "hc1_marker_mask", ImageFormat.RGBA8888, new Vector2( width, height ), _texture );
		if ( texture != _texture )
		{
			_retired = _texture;
			_texture = texture;
			_target = RenderTarget.From( texture );
		}

		Record( width, height );

		if ( _camera != camera )
		{
			Detach();
			camera.AddCommandList( _commands, Stage.AfterTransparent, 0 );
			_camera = camera;
		}

		Texture = _texture;
	}

	/// <summary>
	/// The viewmodel's renderers that the camera draws: the gun, its parts and the arms.
	/// </summary>
	private bool FindRenderers( CameraComponent camera )
	{
		_renderers.Clear();

		var viewModel = Client.Viewer?.PlayerPawn?.CurrentEquipment?.ViewModel;
		if ( !viewModel.IsValid() )
			return false;

		var excluded = (ITagSet)camera.RenderExcludeTags;
		foreach ( var renderer in viewModel.GameObject.Components.GetAll<ModelRenderer>( FindMode.EnabledInSelfAndDescendants ) )
		{
			if ( renderer.RenderType == ModelRenderer.ShadowRenderType.ShadowsOnly )
				continue;

			if ( !renderer.SceneObject.IsValid() || !renderer.SceneObject.RenderingEnabled )
				continue;

			if ( renderer.GameObject.Tags.HasAny( excluded ) )
				continue;

			_renderers.Add( renderer );
		}

		return _renderers.Count > 0;
	}

	private void Record( int width, int height )
	{
		_commands.Reset();

		// The depth of the viewmodel alone, drawn with the camera's view and projection.
		var depth = _commands.GetRenderTarget( "hc1_marker_mask_depth", width, height, ImageFormat.RGBA8888, ImageFormat.D24S8, MultisampleAmount.MultisampleNone, 1 );
		_commands.SetRenderTarget( depth );
		_commands.Clear( Color.Black );

		foreach ( var renderer in _renderers )
		{
			_commands.DrawRenderer( renderer );
		}

		_commands.SetRenderTarget( _target );
		_commands.Attributes.Set( "GunDepth", depth.DepthTexture, 0 );
		_commands.Blit( MaskMaterial, _blitAttributes );
		_commands.ClearRenderTarget();
		_commands.ReleaseRenderTarget( depth );
	}

	private void Detach()
	{
		if ( _camera.IsValid() )
			_camera.RemoveCommandList( _commands );

		_camera = null;
	}

	public void Dispose()
	{
		Detach();
		_commands.Reset();
		_renderers.Clear();

		_retired?.Dispose();
		_retired = null;
		_texture?.Dispose();
		_texture = null;
		_target = null;
		Texture = null;
	}
}
