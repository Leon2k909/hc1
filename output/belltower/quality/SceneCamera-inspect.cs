using System;
using System.Collections.Generic;
using System.Runtime.CompilerServices;
using Sandbox.Internal;
using Sandbox.Rendering;
using Sandbox.VR;

namespace Sandbox;

/// <summary>
/// Represents a camera and holds render hooks. This camera can be used to draw tool windows and scene panels.
/// </summary>
[Description("Represents a camera and holds render hooks. This camera can be used to draw tool windows and scene panels.")]
[SourceLocation("Systems\\SceneSystem\\SceneCamera.Bloom.cs", 5)]
[Expose]
[SourceLocation("Systems\\SceneSystem\\SceneCamera.cs", 9)]
[SourceLocation("Systems\\SceneSystem\\SceneCamera.Tonemap.cs", 3)]
public sealed class SceneCamera : IDisposable, IManagedCamera
{
	[SourceLocation("Systems\\SceneSystem\\SceneCamera.Bloom.cs", 12)]
	public class BloomAccessor
	{
		[Expose]
		public enum BloomMode
		{
			Additive,
			Screen,
			Blur
		}

		[SourceLocation("Systems\\SceneSystem\\SceneCamera.Bloom.cs", 14)]
		private readonly SceneCamera Camera;

		[SourceLocation("Systems\\SceneSystem\\SceneCamera.Bloom.cs", 15)]
		internal PostProcessingBloomParameters_t Parameters;

		/// <summary>
		/// Enable or disable exposure.
		/// </summary>
		[DefaultValue(false)]
		[Description("Enable or disable exposure.")]
		[SourceLocation("Systems\\SceneSystem\\SceneCamera.Bloom.cs", 32)]
		public bool Enabled { get; set; }

		[SourceLocation("Systems\\SceneSystem\\SceneCamera.Bloom.cs", 43)]
		public BloomMode Mode
		{
			get
			{
				return (BloomMode)Parameters.m_blendMode;
			}
			set
			{
				Parameters.m_blendMode = (PostProcessingBloomParameters_t.BloomBlendMode_t)value;
			}
		}

		[SourceLocation("Systems\\SceneSystem\\SceneCamera.Bloom.cs", 50)]
		public float Strength
		{
			get
			{
				return Parameters.m_flBloomStrength;
			}
			set
			{
				Parameters.m_flBloomStrength = value;
				Parameters.m_flScreenBloomStrength = value;
				Parameters.m_flBlurBloomStrength = value;
			}
		}

		[SourceLocation("Systems\\SceneSystem\\SceneCamera.Bloom.cs", 61)]
		public float Threshold
		{
			get
			{
				return Parameters.m_flBloomThreshold;
			}
			set
			{
				Parameters.m_flBloomThreshold = value;
			}
		}

		[SourceLocation("Systems\\SceneSystem\\SceneCamera.Bloom.cs", 67)]
		public float ThresholdWidth
		{
			get
			{
				return Parameters.m_flBloomThresholdWidth;
			}
			set
			{
				Parameters.m_flBloomThresholdWidth = value;
			}
		}

		[SourceLocation("Systems\\SceneSystem\\SceneCamera.Bloom.cs", 73)]
		public float SkyboxStrength
		{
			get
			{
				return Parameters.m_flSkyboxBloomStrength;
			}
			set
			{
				Parameters.m_flSkyboxBloomStrength = value;
			}
		}

		[SourceLocation("Systems\\SceneSystem\\SceneCamera.Bloom.cs", 79)]
		public float BlurWeight0
		{
			get
			{
				return Parameters.m_flBlurWeight0;
			}
			set
			{
				Parameters.m_flBlurWeight0 = value;
			}
		}

		[SourceLocation("Systems\\SceneSystem\\SceneCamera.Bloom.cs", 85)]
		public float BlurWeight1
		{
			get
			{
				return Parameters.m_flBlurWeight1;
			}
			set
			{
				Parameters.m_flBlurWeight1 = value;
			}
		}

		[SourceLocation("Systems\\SceneSystem\\SceneCamera.Bloom.cs", 91)]
		public float BlurWeight2
		{
			get
			{
				return Parameters.m_flBlurWeight2;
			}
			set
			{
				Parameters.m_flBlurWeight2 = value;
			}
		}

		[SourceLocation("Systems\\SceneSystem\\SceneCamera.Bloom.cs", 97)]
		public float BlurWeight3
		{
			get
			{
				return Parameters.m_flBlurWeight3;
			}
			set
			{
				Parameters.m_flBlurWeight3 = value;
			}
		}

		[SourceLocation("Systems\\SceneSystem\\SceneCamera.Bloom.cs", 103)]
		public float BlurWeight4
		{
			get
			{
				return Parameters.m_flBlurWeight4;
			}
			set
			{
				Parameters.m_flBlurWeight4 = value;
			}
		}

		[SourceLocation("Systems\\SceneSystem\\SceneCamera.Bloom.cs", 109)]
		public Color BlurTint0
		{
			get
			{
				return Parameters.m_vBlurTint0;
			}
			set
			{
				Parameters.m_vBlurTint0 = value;
			}
		}

		[SourceLocation("Systems\\SceneSystem\\SceneCamera.Bloom.cs", 115)]
		public Color BlurTint1
		{
			get
			{
				return Parameters.m_vBlurTint1;
			}
			set
			{
				Parameters.m_vBlurTint1 = value;
			}
		}

		[SourceLocation("Systems\\SceneSystem\\SceneCamera.Bloom.cs", 121)]
		public Color BlurTint2
		{
			get
			{
				return Parameters.m_vBlurTint2;
			}
			set
			{
				Parameters.m_vBlurTint2 = value;
			}
		}

		[SourceLocation("Systems\\SceneSystem\\SceneCamera.Bloom.cs", 127)]
		public Color BlurTint3
		{
			get
			{
				return Parameters.m_vBlurTint3;
			}
			set
			{
				Parameters.m_vBlurTint3 = value;
			}
		}

		[SourceLocation("Systems\\SceneSystem\\SceneCamera.Bloom.cs", 133)]
		public Color BlurTint4
		{
			get
			{
				return Parameters.m_vBlurTint4;
			}
			set
			{
				Parameters.m_vBlurTint4 = value;
			}
		}

		internal BloomAccessor(SceneCamera camera)
		{
			Camera = camera;
			Parameters = new PostProcessingBloomParameters_t();
			BlurTint0 = Color.White;
			BlurTint1 = Color.White;
			BlurTint2 = Color.White;
			BlurTint3 = Color.White;
			BlurTint4 = Color.White;
		}
	}

	[SourceLocation("Systems\\SceneSystem\\SceneCamera.cs", 16)]
	internal ToneMapping ToneMapping = (Graphics.IsAvailable ? new ToneMapping() : null);

	[SourceLocation("Systems\\SceneSystem\\SceneCamera.cs", 17)]
	internal VolumetricFog VolumetricFogImpl;

	/// <summary>
	/// This is a c++ object with a ton of useful shit.
	/// Don't access it directly because it might be dirty.
	/// </summary>
	[SourceLocation("Systems\\SceneSystem\\SceneCamera.cs", 23)]
	private CFrustum _frustum;

	/// <summary>
	/// Keep hidden! CommandBuffers only!!
	/// </summary>
	[SourceLocation("Systems\\SceneSystem\\SceneCamera.cs", 69)]
	internal Action<Stage, SceneCamera> OnRenderStageHook;

	/// <summary>
	/// Whether the camera component's post processing reads the depth-normals G-buffer.
	/// </summary>
	[SourceLocation("Systems\\SceneSystem\\SceneCamera.cs", 74)]
	internal Func<bool> WantsDepthNormalsHook;

	/// <summary>
	/// Whether the camera component has effects at a stage that can run on the async compute queue, and running them.
	/// </summary>
	[SourceLocation("Systems\\SceneSystem\\SceneCamera.cs", 85)]
	internal Func<Stage, bool> HasAsyncComputeHook;

	[SourceLocation("Systems\\SceneSystem\\SceneCamera.cs", 86)]
	internal Action<Stage> RenderAsyncComputeHook;

	[SourceLocation("Systems\\SceneSystem\\SceneCamera.cs", 132)]
	private Vector2 _size = new Vector2(512f, 512f);

	/// <summary>
	/// Define the rotations for each of the 6 cube faces (right, left, up, down, front, back)
	/// </summary>
	[SourceLocation("Systems\\SceneSystem\\SceneCamera.cs", 147)]
	internal static readonly Rotation[] CubeRotations = new Rotation[6]
	{
		Rotation.LookAt(Vector3.Backward, Vector3.Right),
		Rotation.LookAt(Vector3.Forward, Vector3.Right),
		Rotation.LookAt(Vector3.Right, Vector3.Up),
		Rotation.LookAt(Vector3.Left, Vector3.Down),
		Rotation.LookAt(Vector3.Down, Vector3.Right),
		Rotation.LookAt(Vector3.Up, Vector3.Right)
	};

	[SourceLocation("Systems\\SceneSystem\\SceneCamera.cs", 169)]
	private bool disposedValue;

	[SourceLocation("Systems\\SceneSystem\\SceneCamera.cs", 205)]
	internal int _cameraId;

	[SourceLocation("Systems\\SceneSystem\\SceneCamera.cs", 265)]
	private HashSet<SceneWorld> _worlds = new HashSet<SceneWorld>();

	[SourceLocation("Systems\\SceneSystem\\SceneCamera.cs", 266)]
	private SceneWorld _world;

	[SourceLocation("Systems\\SceneSystem\\SceneCamera.cs", 294)]
	private Transform _transform = new Transform();

	[SourceLocation("Systems\\SceneSystem\\SceneCamera.cs", 336)]
	private float _fov = 90f;

	[SourceLocation("Systems\\SceneSystem\\SceneCamera.cs", 351)]
	private float _zfar = 100000f;

	[SourceLocation("Systems\\SceneSystem\\SceneCamera.cs", 369)]
	private float _znear = 1f;

	[SourceLocation("Systems\\SceneSystem\\SceneCamera.cs", 386)]
	private bool _ortho;

	[SourceLocation("Systems\\SceneSystem\\SceneCamera.cs", 437)]
	private Rect rect = new Rect(Vector2.Zero, Vector2.One);

	[SourceLocation("Systems\\SceneSystem\\SceneCamera.cs", 507)]
	private static WeakReference<SceneCamera> _recordingCamera;

	/// <summary>
	/// Access tonemapping properties of camera
	/// </summary>
	[Description("Access tonemapping properties of camera")]
	[SourceLocation("Systems\\SceneSystem\\SceneCamera.Bloom.cs", 10)]
	public BloomAccessor Bloom { get; internal set; }

	[SourceLocation("Systems\\SceneSystem\\SceneCamera.cs", 25)]
	internal Matrix ProjectionMatrix => Frustum.GetProj();

	/// <summary>
	/// World to projection matrix using the reverse-Z projection (matches the rendered depth buffer:
	/// far plane = 0, near plane = 1), transposed for row-vector use with <see cref="M:Matrix.Transform(Vector4)" />.
	/// <para>
	/// The engine's native matrices are column-vector (GPU <c>mul( M, v )</c>) while
	/// <see cref="M:Matrix.Transform(Vector4)" /> is row-vector (<c>v · M</c>), so we hand back the transpose.
	/// Transform a homogeneous world point — <c>matrix.Transform( new Vector4( pos, 1 ) )</c> — to get its
	/// reverse-Z clip-space coordinate (before the perspective divide).
	/// </para>
	/// </summary>
	[Description("World to projection matrix using the reverse-Z projection (matches the rendered depth buffer: far plane = 0, near plane = 1), transposed for row-vector use with <span style=\"color: #86C691;\">Matrix</span>.<span style=\"color: #DCDCAA;\">Transform</span>(<span style=\"color: #86C691;\">Vector4</span>). <br/>The engine's native matrices are column-vector (GPU <code style=\"color: #DCDCDC; background-color: #111111; padding: 4px;\">mul( M, v )</code>) while <span style=\"color: #86C691;\">Matrix</span>.<span style=\"color: #DCDCAA;\">Transform</span>(<span style=\"color: #86C691;\">Vector4</span>) is row-vector (<code style=\"color: #DCDCDC; background-color: #111111; padding: 4px;\">v · M</code>), so we hand back the transpose. Transform a homogeneous world point — <code style=\"color: #DCDCDC; background-color: #111111; padding: 4px;\">matrix.Transform( new Vector4( pos, 1 ) )</code> — to get its reverse-Z clip-space coordinate (before the perspective divide).<br/>")]
	[SourceLocation("Systems\\SceneSystem\\SceneCamera.cs", 37)]
	internal Matrix ReverseZViewProjectionMatrix => Frustum.GetReverseZViewProjTranspose();

	[SourceLocation("Systems\\SceneSystem\\SceneCamera.cs", 49)]
	public RenderAttributes Attributes { get; }

	/// <summary>
	/// The name of this camera.. for debugging purposes.
	/// </summary>
	[Description("The name of this camera.. for debugging purposes.")]
	[SourceLocation("Systems\\SceneSystem\\SceneCamera.cs", 54)]
	public string Name { get; set; }

	/// <summary>
	/// Scene objects with any of these tags won't be rendered by this camera.
	/// </summary>
	[Description("Scene objects with any of these tags won't be rendered by this camera.")]
	[SourceLocation("Systems\\SceneSystem\\SceneCamera.cs", 59)]
	public ITagSet ExcludeTags { get; private set; } = new TokenBasedTagSet();

	/// <summary>
	/// Only scene objects with one of these tags will be rendered by this camera.
	/// </summary>
	[Description("Only scene objects with one of these tags will be rendered by this camera.")]
	[SourceLocation("Systems\\SceneSystem\\SceneCamera.cs", 64)]
	public ITagSet RenderTags { get; private set; } = new TokenBasedTagSet();

	/// <summary>
	/// Whether something in this camera's frame reads the normals and roughness G-buffer of the depth-normals prepass
	/// (AO, SSR). Native always draws it; the managed scene renderer only when this says so.
	/// </summary>
	[Description("Whether something in this camera's frame reads the normals and roughness G-buffer of the depth-normals prepass (AO, SSR). Native always draws it; the managed scene renderer only when this says so.")]
	[SourceLocation("Systems\\SceneSystem\\SceneCamera.cs", 80)]
	internal bool WantsDepthNormals => WantsDepthNormalsHook?.Invoke() ?? false;

	/// <summary>
	/// Called when rendering the transparent pass
	/// </summary>
	[Obsolete]
	[Description("Called when rendering the transparent pass")]
	[SourceLocation("Systems\\SceneSystem\\SceneCamera.cs", 103)]
	public Action OnRenderTransparent { get; set; }

	[SourceLocation("Systems\\SceneSystem\\SceneCamera.cs", 106)]
	internal Action OnRenderOverlay { get; set; }

	[SourceLocation("Systems\\SceneSystem\\SceneCamera.cs", 108)]
	internal Action OnRenderUI { get; set; }

	/// <summary>
	/// Called before post processing, for UI that wants bloom and color grading applied to it.
	/// </summary>
	[Description("Called before post processing, for UI that wants bloom and color grading applied to it.")]
	[SourceLocation("Systems\\SceneSystem\\SceneCamera.cs", 113)]
	internal Action OnRenderUIBeforePostProcess { get; set; }

	/// <summary>
	/// The size of the screen. Allows us to work out aspect ratio.
	/// For now will get updated automatically on render.
	/// </summary>
	[Description("The size of the screen. Allows us to work out aspect ratio. For now will get updated automatically on render.")]
	[SourceLocation("Systems\\SceneSystem\\SceneCamera.cs", 119)]
	public Vector2 Size
	{
		get
		{
			return _size;
		}
		set
		{
			if (!(_size == value))
			{
				_size = value;
				FrustumDirty = true;
			}
		}
	}

	/// <summary>
	/// Control volumetric fog parameters, expect this to take 1-2ms of your GPU frame time.
	/// </summary>
	[Description("Control volumetric fog parameters, expect this to take 1-2ms of your GPU frame time.")]
	[SourceLocation("Systems\\SceneSystem\\SceneCamera.cs", 137)]
	public VolumetricFogParameters VolumetricFog { get; init; } = new VolumetricFogParameters();

	/// <summary>
	/// Control fog based on an image.
	/// </summary>
	[Description("Control fog based on an image.")]
	[SourceLocation("Systems\\SceneSystem\\SceneCamera.cs", 142)]
	public CubemapFogController CubemapFog { get; init; } = new CubemapFogController();

	[SourceLocation("Systems\\SceneSystem\\SceneCamera.cs", 225)]
	private CFrustum Frustum
	{
		get
		{
			if (!_frustum.IsValid)
			{
				_frustum = CFrustum.Create();
			}
			if (FrustumDirty)
			{
				if (Size.y <= 0f)
				{
					Size = new Vector2(1f, 1f);
				}
				float flAspect = Size.x / Size.y;
				if (Ortho)
				{
					float flWidth = Size.x * (OrthoHeight / Size.y);
					_frustum.InitOrthoCamera(Position, Angles, ZNear, ZFar, flWidth, OrthoHeight);
				}
				else
				{
					_frustum.InitCamera(Position, Angles, ZNear, ZFar, FieldOfView, flAspect);
					_frustum.SetCameraWidthHeight(Size.x, Size.y);
				}
				FrustumDirty = false;
			}
			return _frustum;
		}
	}

	[DefaultValue(true)]
	[SourceLocation("Systems\\SceneSystem\\SceneCamera.cs", 259)]
	private bool FrustumDirty { get; set; } = true;

	/// <summary>
	/// The world we're going to render.
	/// </summary>
	[Description("The world we're going to render.")]
	[SourceLocation("Systems\\SceneSystem\\SceneCamera.cs", 271)]
	public SceneWorld World
	{
		get
		{
			return _world;
		}
		set
		{
			if (_world != value)
			{
				_worlds?.Remove(_world);
				_world = value;
				if (_world.IsValid())
				{
					_worlds?.Add(_world);
				}
			}
		}
	}

	/// <summary>
	/// Your camera can render multiple worlds.
	/// </summary>
	[Description("Your camera can render multiple worlds.")]
	[SourceLocation("Systems\\SceneSystem\\SceneCamera.cs", 292)]
	public HashSet<SceneWorld> Worlds => _worlds;

	/// <summary>
	/// The position of the scene's camera.
	/// </summary>
	[Description("The position of the scene's camera.")]
	[SourceLocation("Systems\\SceneSystem\\SceneCamera.cs", 299)]
	public Vector3 Position
	{
		get
		{
			return _transform.Position;
		}
		set
		{
			_transform.Position = value;
			FrustumDirty = true;
		}
	}

	/// <summary>
	/// The rotation of the scene's camera.
	/// </summary>
	[Description("The rotation of the scene's camera.")]
	[SourceLocation("Systems\\SceneSystem\\SceneCamera.cs", 312)]
	public Rotation Rotation
	{
		get
		{
			return _transform.Rotation;
		}
		set
		{
			_transform.Rotation = value;
			FrustumDirty = true;
		}
	}

	/// <summary>
	/// The rotation of the scene's camera.
	/// </summary>
	[Description("The rotation of the scene's camera.")]
	[SourceLocation("Systems\\SceneSystem\\SceneCamera.cs", 325)]
	public Angles Angles
	{
		get
		{
			return _transform.Rotation;
		}
		set
		{
			_transform.Rotation = value;
			FrustumDirty = true;
		}
	}

	/// <summary>
	/// The horizontal field of view of the Camera in degrees.
	/// </summary>
	[Description("The horizontal field of view of the Camera in degrees.")]
	[SourceLocation("Systems\\SceneSystem\\SceneCamera.cs", 341)]
	public float FieldOfView
	{
		get
		{
			return _fov;
		}
		set
		{
			_fov = value;
			FrustumDirty = true;
		}
	}

	/// <summary>
	/// The camera's zFar distance. This is the furthest distance this camera will be able to render.
	/// This value totally depends on the game you're making. Shorter the better, sensible ranges would be
	/// between about 1000 and 30000, but if you want it to be further out you can balance that out by making
	/// znear larger.
	/// </summary>
	[Description("The camera's zFar distance. This is the furthest distance this camera will be able to render. This value totally depends on the game you're making. Shorter the better, sensible ranges would be between about 1000 and 30000, but if you want it to be further out you can balance that out by making znear larger.")]
	[SourceLocation("Systems\\SceneSystem\\SceneCamera.cs", 359)]
	public float ZFar
	{
		get
		{
			return _zfar;
		}
		set
		{
			_zfar = value;
			FrustumDirty = true;
		}
	}

	/// <summary>
	/// The camera's zNear distance. This is the closest distance this camera will be able to render.
	/// A good value for this is about 5. Below 5 and particularly below 1 you're going to start to see
	/// a lot of artifacts like z-fighting.
	/// </summary>
	[Description("The camera's zNear distance. This is the closest distance this camera will be able to render. A good value for this is about 5. Below 5 and particularly below 1 you're going to start to see a lot of artifacts like z-fighting.")]
	[SourceLocation("Systems\\SceneSystem\\SceneCamera.cs", 376)]
	public float ZNear
	{
		get
		{
			return _znear;
		}
		set
		{
			_znear = value;
			FrustumDirty = true;
		}
	}

	/// <summary>
	/// Whether to use orthographic projection.
	/// </summary>
	[Description("Whether to use orthographic projection.")]
	[SourceLocation("Systems\\SceneSystem\\SceneCamera.cs", 391)]
	public bool Ortho
	{
		get
		{
			return _ortho;
		}
		set
		{
			_ortho = value;
			FrustumDirty = true;
		}
	}

	/// <summary>
	/// Height of the ortho when <see cref="P:Sandbox.SceneCamera.Ortho" /> is enabled.
	/// </summary>
	[Description("Height of the ortho when <span style=\"color: #4EC9B0;\">SceneCamera</span>.<span style=\"color: #DCDCDC;\">Ortho</span> is enabled.")]
	[SourceLocation("Systems\\SceneSystem\\SceneCamera.cs", 404)]
	public float OrthoHeight
	{
		get
		{
			return Attributes.GetFloat(StringToken.Literal("cam.orthoHeight", 3108411710u), 0f);
		}
		set
		{
			Attributes.Set(StringToken.Literal("cam.orthoHeight", 3108411710u), in value);
			FrustumDirty = true;
		}
	}

	/// <summary>
	/// Render this camera using a different render mode
	/// </summary>
	[Description("Render this camera using a different render mode")]
	[SourceLocation("Systems\\SceneSystem\\SceneCamera.cs", 417)]
	public SceneCameraDebugMode DebugMode
	{
		get
		{
			return (SceneCameraDebugMode)Attributes.GetInt(StringToken.Literal("ToolsVisMode", 3329653539u), 0);
		}
		set
		{
			RenderAttributes attributes = Attributes;
			StringToken k = StringToken.Literal("ToolsVisMode", 3329653539u);
			int value2 = (int)value;
			attributes.Set(in k, in value2);
		}
	}

	/// <summary>
	/// Render this camera using a wireframe view.
	/// </summary>
	[Description("Render this camera using a wireframe view.")]
	[SourceLocation("Systems\\SceneSystem\\SceneCamera.cs", 426)]
	public bool WireframeMode
	{
		get
		{
			return Attributes.GetInt(StringToken.Literal("Wireframe", 4234123335u), 0) >= 1;
		}
		set
		{
			Attributes.Set(StringToken.Literal("Wireframe", 4234123335u), (int)(value ? 1 : 0));
		}
	}

	/// <summary>
	/// What kind of clearing should we do before we begin?
	/// </summary>
	[DefaultValue(ClearFlags.All)]
	[Description("What kind of clearing should we do before we begin?")]
	[SourceLocation("Systems\\SceneSystem\\SceneCamera.cs", 435)]
	public ClearFlags ClearFlags { get; set; } = ClearFlags.All;

	/// <summary>
	/// The rect of the screen to render to. This is normalized, between 0 and 1.
	/// </summary>
	[Description("The rect of the screen to render to. This is normalized, between 0 and 1.")]
	[SourceLocation("Systems\\SceneSystem\\SceneCamera.cs", 442)]
	public Rect Rect
	{
		get
		{
			return rect;
		}
		set
		{
			Rect rect = value;
			rect.Left = rect.Left.Clamp(0f, 1f);
			rect.Top = rect.Top.Clamp(0f, 1f);
			this.rect = rect;
		}
	}

	/// <summary>
	/// Color the scene camera clears the render target to.
	/// </summary>
	[Description("Color the scene camera clears the render target to.")]
	[SourceLocation("Systems\\SceneSystem\\SceneCamera.cs", 458)]
	public Color BackgroundColor { get; set; }

	/// <summary>
	/// The color of the ambient light. Set it to black for no ambient light, alpha is used for lerping between IBL and constant color.
	/// </summary>
	[Description("The color of the ambient light. Set it to black for no ambient light, alpha is used for lerping between IBL and constant color.")]
	[SourceLocation("Systems\\SceneSystem\\SceneCamera.cs", 463)]
	public Color AmbientLightColor { get; set; } = Color.Transparent;

	/// <summary>
	/// Enable or disable anti-aliasing for this render.
	/// </summary>
	[Description("Enable or disable anti-aliasing for this render.")]
	[SourceLocation("Systems\\SceneSystem\\SceneCamera.cs", 472)]
	public bool AntiAliasing
	{
		get
		{
			return Attributes.GetInt(StringToken.Literal("msaa", 1290850361u), 4) == 4;
		}
		set
		{
			Attributes.Set(StringToken.Literal("msaa", 1290850361u), value ? 4 : 0);
		}
	}

	/// <summary>
	/// Toggle all post processing effects for this camera. The default is on.
	/// </summary>
	[DefaultValue(true)]
	[Description("Toggle all post processing effects for this camera. The default is on.")]
	[SourceLocation("Systems\\SceneSystem\\SceneCamera.cs", 481)]
	public bool EnablePostProcessing { get; set; } = true;

	/// <summary>
	/// Should this camera render engine overlays, you'd only want this on the main camera.
	/// </summary>
	[DefaultValue(false)]
	[Description("Should this camera render engine overlays, you'd only want this on the main camera.")]
	[SourceLocation("Systems\\SceneSystem\\SceneCamera.cs", 486)]
	internal bool EnableEngineOverlays { get; set; }

	/// <summary>
	/// Whether the UI stage layer should be created for this camera render.
	/// When false, the native pipeline will skip the UI layer entirely.
	/// </summary>
	[DefaultValue(true)]
	[Description("Whether the UI stage layer should be created for this camera render. When false, the native pipeline will skip the UI layer entirely.")]
	[SourceLocation("Systems\\SceneSystem\\SceneCamera.cs", 492)]
	internal bool RenderUI { get; set; } = true;

	/// <summary>
	/// When true, rendering from this camera won't request higher mip levels from
	/// the texture streaming system. Used by cubemap rendering to prevent envmap probes
	/// from pulling in full-resolution textures across the entire map.
	/// </summary>
	[Description("When true, rendering from this camera won't request higher mip levels from the texture streaming system. Used by cubemap rendering to prevent envmap probes from pulling in full-resolution textures across the entire map.")]
	[SourceLocation("Systems\\SceneSystem\\SceneCamera.cs", 499)]
	internal bool ExcludeFromTextureStreaming { get; set; }

	/// <summary>
	/// Render as a tools view (<c>SVF_TOOL_VIEW</c>), as native's tools render theirs: tools materials draw in the pipeline's
	/// ToolsUtil layers. Off by default, as every camera has been.
	/// </summary>
	[Description("Render as a tools view (<code style=\"color: #DCDCDC; background-color: #111111; padding: 4px;\">SVF_TOOL_VIEW</code>), as native's tools render theirs: tools materials draw in the pipeline's ToolsUtil layers. Off by default, as every camera has been.")]
	[SourceLocation("Systems\\SceneSystem\\SceneCamera.cs", 505)]
	internal bool ToolsView { get; set; }

	/// <summary>
	/// The camera currently used for video/screenshot recording.
	/// </summary>
	[Description("The camera currently used for video/screenshot recording.")]
	[SourceLocation("Systems\\SceneSystem\\SceneCamera.cs", 512)]
	internal static SceneCamera RecordingCamera
	{
		get
		{
			WeakReference<SceneCamera> recordingCamera = _recordingCamera;
			if (recordingCamera == null || !recordingCamera.TryGetTarget(out var target))
			{
				return null;
			}
			return target;
		}
		set
		{
			_recordingCamera = ((value != null) ? new WeakReference<SceneCamera>(value) : null);
		}
	}

	[SourceLocation("Systems\\SceneSystem\\SceneCamera.cs", 518)]
	internal bool IsRecordingCamera => RecordingCamera == this;

	/// <summary>
	/// The HMD eye that this camera is targeting.
	/// Use <see cref="F:Sandbox.StereoTargetEye.None" /> for the user's monitor (i.e. the companion window).
	/// </summary>
	[DefaultValue(StereoTargetEye.None)]
	[Description("The HMD eye that this camera is targeting. Use <span style=\"color: #86C691;\">StereoTargetEye</span>.<span style=\"color: #DCDCDC;\">None</span> for the user's monitor (i.e. the companion window).")]
	[SourceLocation("Systems\\SceneSystem\\SceneCamera.cs", 524)]
	public StereoTargetEye TargetEye { get; set; }

	/// <summary>
	/// Set this to false if you don't want the stereo renderer to submit this camera's texture to the compositor.
	/// This option isn't considered if <see cref="P:Sandbox.SceneCamera.TargetEye" /> is <see cref="F:Sandbox.StereoTargetEye.None" />.
	/// </summary>
	[DefaultValue(false)]
	[Description("Set this to false if you don't want the stereo renderer to submit this camera's texture to the compositor. This option isn't considered if <span style=\"color: #4EC9B0;\">SceneCamera</span>.<span style=\"color: #DCDCDC;\">TargetEye</span> is <span style=\"color: #86C691;\">StereoTargetEye</span>.<span style=\"color: #DCDCDC;\">None</span>.")]
	[SourceLocation("Systems\\SceneSystem\\SceneCamera.cs", 530)]
	public bool WantsStereoSubmit { get; set; }

	/// <summary>
	/// Enable or disable direct lighting
	/// </summary>
	[Description("Enable or disable direct lighting")]
	[SourceLocation("Systems\\SceneSystem\\SceneCamera.cs", 535)]
	public bool EnableDirectLighting
	{
		get
		{
			return Attributes.GetBool(StringToken.Literal("directLighting", 529534021u), false);
		}
		set
		{
			Attributes.Set(StringToken.Literal("directLighting", 529534021u), in value);
		}
	}

	/// <summary>
	/// Enable or disable indirect lighting
	/// </summary>
	[Description("Enable or disable indirect lighting")]
	[SourceLocation("Systems\\SceneSystem\\SceneCamera.cs", 544)]
	public bool EnableIndirectLighting
	{
		get
		{
			return Attributes.GetBool(StringToken.Literal("indirectLighting", 3678441746u), false);
		}
		set
		{
			Attributes.Set(StringToken.Literal("indirectLighting", 3678441746u), in value);
		}
	}

	/// <summary>
	/// This camera only draws UI - skip the scene rendering pipeline entirely and put the UI
	/// straight onto its target. For a window that is nothing but panels, which is what a
	/// launcher window is: the pipeline's passes and render targets are all for a scene that
	/// isn't there.
	/// </summary>
	[Description("This camera only draws UI - skip the scene rendering pipeline entirely and put the UI straight onto its target. For a window that is nothing but panels, which is what a launcher window is: the pipeline's passes and render targets are all for a scene that isn't there.")]
	[SourceLocation("Systems\\SceneSystem\\SceneCamera.cs", 556)]
	internal bool UIOnly { get; set; }

	/// <summary>
	/// Allows specifying a custom projection matrix for this camera
	/// </summary>
	[Description("Allows specifying a custom projection matrix for this camera")]
	[SourceLocation("Systems\\SceneSystem\\SceneCamera.cs", 974)]
	public Matrix? CustomProjectionMatrix { get; set; }

	/// <summary>
	/// Access tonemapping properties of camera
	/// </summary>
	[Description("Access tonemapping properties of camera")]
	[SourceLocation("Systems\\SceneSystem\\SceneCamera.Tonemap.cs", 8)]
	internal TonemapSystem Tonemap { get; set; }

	/// <summary>
	/// Returns the normalized screen coverage (0-1) of a sphere at the given origin and radius.
	/// </summary>
	[Description("Returns the normalized screen coverage (0-1) of a sphere at the given origin and radius.")]
	[SourceLocation("Systems\\SceneSystem\\SceneCamera.cs", 42)]
	internal float ComputeScreenSize(Vector3 origin, float radius)
	{
		return Frustum.ComputeScreenSize(origin, radius);
	}

	/// <summary>
	/// Returns the screen width in pixels of a sphere at the given origin and radius.
	/// </summary>
	[Description("Returns the screen width in pixels of a sphere at the given origin and radius.")]
	[SourceLocation("Systems\\SceneSystem\\SceneCamera.cs", 47)]
	internal float ComputeScreenSizeInPixels(Vector3 origin, float radius)
	{
		return Frustum.ComputeScreenSize(origin, radius) * Size.x;
	}

	/// <summary>
	/// Whether something at <paramref name="stage" /> can run on the async compute queue ahead of the stage
	/// (<see cref="P:Sandbox.BasePostProcess.AsyncCompute" />: AO at <c>AfterDepthPrepass</c>), for the managed scene renderer.
	/// </summary>
	[Description("Whether something at <span style=\"color: #9CDCFE;\">stage</span> can run on the async compute queue ahead of the stage (<span style=\"color: #4EC9B0;\">BasePostProcess</span>.<span style=\"color: #DCDCDC;\">AsyncCompute</span>: AO at <code style=\"color: #DCDCDC; background-color: #111111; padding: 4px;\">AfterDepthPrepass</code>), for the managed scene renderer.")]
	[SourceLocation("Systems\\SceneSystem\\SceneCamera.cs", 92)]
	internal bool HasAsyncCompute(Stage stage)
	{
		return HasAsyncComputeHook?.Invoke(stage) ?? false;
	}

	/// <summary>
	/// Run what <see cref="M:Sandbox.SceneCamera.HasAsyncCompute(Sandbox.Rendering.Stage)" /> found, inside a <see cref="T:Sandbox.Graphics" /> block on the compute queue. The stage then
	/// skips it.
	/// </summary>
	[Description("Run what <span style=\"color: #4EC9B0;\">SceneCamera</span>.<span style=\"color: #DCDCAA;\">HasAsyncCompute</span>(<span style=\"color: #86C691;\">Stage</span>) found, inside a <span style=\"color: #4EC9B0;\">Graphics</span> block on the compute queue. The stage then skips it.")]
	[SourceLocation("Systems\\SceneSystem\\SceneCamera.cs", 98)]
	internal void RenderAsyncCompute(Stage stage)
	{
		RenderAsyncComputeHook?.Invoke(stage);
	}

	public SceneCamera(string name = "Unnamed")
	{
		Attributes = new RenderAttributes();
		Name = name;
		InitCommon();
	}

	~SceneCamera()
	{
		Dispose(disposing: false);
	}

	[SourceLocation("Systems\\SceneSystem\\SceneCamera.cs", 171)]
	private void Dispose(bool disposing)
	{
		if (!disposedValue)
		{
			if (_frustum.IsValid)
			{
				_frustum.Delete();
				_frustum = default;
			}
			if (VolumetricFogImpl != null)
			{
				EngineLoop.DisposeAtFrameEnd(VolumetricFogImpl);
				VolumetricFogImpl = null;
			}
			Attributes?.Clear();
			disposedValue = true;
		}
	}

	[SourceLocation("Systems\\SceneSystem\\SceneCamera.cs", 198)]
	public void Dispose()
	{
		Dispose(disposing: true);
		GC.SuppressFinalize(this);
	}

	[SourceLocation("Systems\\SceneSystem\\SceneCamera.cs", 207)]
	internal void InitCommon()
	{
		_cameraId = ((IManagedCamera)this).AllocateCameraId();
		Attributes.Set(StringToken.Literal("renderOpaque", 1699661870u), true);
		Attributes.Set(StringToken.Literal("renderTranslucent", 4162890604u), true);
		Attributes.Set(StringToken.Literal("directLighting", 529534021u), true);
		Attributes.Set(StringToken.Literal("indirectLighting", 3678441746u), true);
		Attributes.Set(StringToken.Literal("renderSun", 3542803140u), true);
		Attributes.Set(StringToken.Literal("drawShadows", 2509230636u), true);
		FieldOfView = 70f;
		Tonemap = new TonemapSystem(this);
		Bloom = new BloomAccessor(this);
	}

	[SourceLocation("Systems\\SceneSystem\\SceneCamera.cs", 263)]
	public override string ToString()
	{
		return "SceneCamera:" + Name;
	}

	/// <summary>
	/// Should be called before a render
	/// </summary>
	[Description("Should be called before a render")]
	[SourceLocation("Systems\\SceneSystem\\SceneCamera.cs", 561)]
	internal void OnPreRender(Vector2 size)
	{
		Size = size;
		ConfigureView(default(ViewSetup));
	}

	/// <summary>
	/// Configure the view immediately before rendering. This will set the camera position
	/// etc on the local camera renderer. This should be called immediately before adding
	/// the views etc.
	/// </summary>
	[Description("Configure the view immediately before rendering. This will set the camera position etc on the local camera renderer. This should be called immediately before adding the views etc.")]
	[SourceLocation("Systems\\SceneSystem\\SceneCamera.cs", 573)]
	private void ConfigureView(in ViewSetup config)
	{
		if (_world.IsValid() && !Graphics.IsActive)
		{
			_world.UpdateObjectsForRendering(Position, ZFar);
		}
	}

	[SourceLocation("Systems\\SceneSystem\\SceneCamera.cs", 581)]
	void IManagedCamera.OnRenderStage(Stage renderStage)
	{
		switch (renderStage)
		{
		case Stage.AfterDepthPrepass:
			ShadowMapperCallbacks.RenderScreenSpaceShadows();
			break;
		case Stage.EarlyUI:
			if (RenderUI)
			{
				OnRenderUIBeforePostProcess?.Invoke();
			}
			break;
		case Stage.AfterPostProcess:
			OnRenderOverlay?.Invoke();
			break;
		case Stage.UI:
			OnRenderUI?.Invoke();
			break;
		}
		OnRenderStageHook?.InvokeWithWarning(renderStage, this);
		if (renderStage == Stage.AfterUI && IsRecordingCamera && Application.IsEditor && !Game.IsPlaying)
		{
			ScreenCaptureUtility.CaptureFrame();
			ScreenCaptureUtility.DrawRecordingBorder();
		}
	}

	/// <summary>
	/// Given a pixel rect return a frustum on the current camera.
	/// </summary>
	[Description("Given a pixel rect return a frustum on the current camera.")]
	[SourceLocation("Systems\\SceneSystem\\SceneCamera.cs", 627)]
	public Frustum GetFrustum(Rect pixelRect)
	{
		return GetFrustum(pixelRect, Size);
	}

	/// <summary>
	/// Given a pixel rect return a frustum on the current camera. Pass in 1 to ScreenSize to use normalized screen coords.
	/// </summary>
	[Description("Given a pixel rect return a frustum on the current camera. Pass in 1 to ScreenSize to use normalized screen coords.")]
	[SourceLocation("Systems\\SceneSystem\\SceneCamera.cs", 632)]
	public Frustum GetFrustum(Rect pixelRect, Vector3 screenSize)
	{
		if (Ortho)
		{
			Vector2 screenMin = Vector2.Min(pixelRect.TopLeft, pixelRect.BottomRight);
			Vector2 screenMax = Vector2.Max(pixelRect.TopLeft, pixelRect.BottomRight);
			return Sandbox.Frustum.FromOrtho(screenMin, screenMax, screenSize, Position, Rotation, OrthoHeight, ZNear, ZFar);
		}
		Vector2 topLeft = pixelRect.TopLeft;
		Vector2 bottomRight = pixelRect.BottomRight;
		Ray tl = GetRay(new Vector2(MathF.Min(topLeft.x, bottomRight.x), MathF.Min(topLeft.y, bottomRight.y)), screenSize);
		Ray tr = GetRay(new Vector2(MathF.Max(topLeft.x, bottomRight.x), MathF.Min(topLeft.y, bottomRight.y)), screenSize);
		Ray bl = GetRay(new Vector2(MathF.Min(topLeft.x, bottomRight.x), MathF.Max(topLeft.y, bottomRight.y)), screenSize);
		return Sandbox.Frustum.FromCorners(in tl, in tr, GetRay(new Vector2(MathF.Max(topLeft.x, bottomRight.x), MathF.Max(topLeft.y, bottomRight.y)), screenSize), in bl, ZNear, ZFar);
	}

	/// <summary>
	/// Given a cursor position get a scene aiming ray.
	/// </summary>
	[Description("Given a cursor position get a scene aiming ray.")]
	[SourceLocation("Systems\\SceneSystem\\SceneCamera.cs", 658)]
	public Ray GetRay(Vector3 cursorPosition)
	{
		return GetRay(cursorPosition, Size);
	}

	/// <summary>
	/// Given a cursor position get a scene aiming ray.
	/// </summary>
	[Description("Given a cursor position get a scene aiming ray.")]
	[SourceLocation("Systems\\SceneSystem\\SceneCamera.cs", 663)]
	public Ray GetRay(Vector2 cursorPosition, Vector3 screenSize)
	{
		if (screenSize.x <= 0f || screenSize.y <= 0f)
		{
			return new Ray(Position, Rotation.Forward);
		}
		if (!Ortho)
		{
			float num = screenSize.x / screenSize.y;
			Vector2 vector = new Vector2(2f * cursorPosition.x / screenSize.x - 1f, 2f * cursorPosition.y / screenSize.y - 1f) * -1f;
			float num2 = MathF.Tan(FieldOfView * (float)Math.PI / 360f);
			float num3 = num2 / num;
			Vector3 vector2 = new Vector3(1f, vector.x / (1f / num2), vector.y / (1f / num3)) * Rotation;
			return new Ray(Position, vector2.Normal);
		}
		float x = cursorPosition.x;
		float y = cursorPosition.y;
		float num4 = OrthoHeight / 2f;
		float num5 = num4 * screenSize.x / screenSize.y;
		float num6 = (2f * x / screenSize.x - 1f) * num5;
		float num7 = (1f - 2f * y / screenSize.y) * num4;
		Vector3 forward = Rotation.Forward;
		return new Ray
		{
			Position = Position + Rotation.Right * num6 + Rotation.Up * num7 + forward * ZNear,
			Forward = forward
		};
	}

	/// <summary>
	/// Convert from world coords to screen coords. The results for x and y will be from 0 to <see cref="P:Sandbox.SceneCamera.Size" />.
	/// </summary>
	[Description("Convert from world coords to screen coords. The results for x and y will be from 0 to <span style=\"color: #4EC9B0;\">SceneCamera</span>.<span style=\"color: #DCDCDC;\">Size</span>.")]
	[SourceLocation("Systems\\SceneSystem\\SceneCamera.cs", 700)]
	public Vector2 ToScreen(Vector3 world)
	{
		Frustum.WorldToView(world, out var pOutViewMinusOneToOne);
		pOutViewMinusOneToOne.x = pOutViewMinusOneToOne.x.Remap(-1f, 1f, 0f, Size.x);
		pOutViewMinusOneToOne.y = pOutViewMinusOneToOne.y.Remap(-1f, 1f, Size.y, 0f);
		return pOutViewMinusOneToOne;
	}

	/// <summary>
	/// Convert from world coords to screen coords. The results for x and y will be from 0 to <see cref="P:Sandbox.SceneCamera.Size" />.
	/// </summary>
	[Description("Convert from world coords to screen coords. The results for x and y will be from 0 to <span style=\"color: #4EC9B0;\">SceneCamera</span>.<span style=\"color: #DCDCDC;\">Size</span>.")]
	[SourceLocation("Systems\\SceneSystem\\SceneCamera.cs", 713)]
	public bool ToScreen(Vector3 world, out Vector2 screen)
	{
		Vector3 vector = ToScreenWithDirection(world);
		screen = new Vector2(vector.x, vector.y) * Size;
		return vector.z > 0f;
	}

	/// <summary>
	/// Convert from world coords to normal screen corrds. The results will be between 0 and 1
	/// </summary>
	[Description("Convert from world coords to normal screen corrds. The results will be between 0 and 1")]
	[SourceLocation("Systems\\SceneSystem\\SceneCamera.cs", 723)]
	public Vector2 ToScreenNormal(Vector3 world)
	{
		Frustum.WorldToView(world, out var pOutViewMinusOneToOne);
		pOutViewMinusOneToOne.x = pOutViewMinusOneToOne.x.Remap(-1f, 1f);
		pOutViewMinusOneToOne.y = pOutViewMinusOneToOne.y.Remap(-1f, 1f, 1f, 0f);
		return pOutViewMinusOneToOne;
	}

	/// <summary>
	/// Convert from world coords to screen coords but the Z component stores whether this vector
	/// is behind the screen (&lt;0) or in front of it (&gt;0). The X and Y components are normalized
	/// from 0 to 1.
	/// </summary>
	/// <param name="world"></param>
	/// <returns></returns>
	[Description("Convert from world coords to screen coords but the Z component stores whether this vector is behind the screen (&lt;0) or in front of it (&gt;0). The X and Y components are normalized from 0 to 1.")]
	[SourceLocation("Systems\\SceneSystem\\SceneCamera.cs", 740)]
	internal Vector3 ToScreenWithDirection(Vector3 world)
	{
		bool flag = Frustum.ScreenTransform(world, out var result);
		if (!Ortho)
		{
			result.x = (result.x + 1f) / 2f;
			result.y = (result.y * -1f + 1f) / 2f;
			result.z = (flag ? (-1f) : 1f);
		}
		else
		{
			result.x = (result.x + 2f) / 2f;
			result.y = (result.y - 2f) / 2f * -1f;
			if (result.x <= 0f || result.x >= 1f || result.y <= 0f || result.y >= 1f)
			{
				result.z = -1f;
			}
			else
			{
				result.z = 1f;
			}
		}
		return result;
	}

	/// <summary>
	/// Convert from screen coords to world coords on the near frustum plane.
	/// </summary>
	[Description("Convert from screen coords to world coords on the near frustum plane.")]
	[SourceLocation("Systems\\SceneSystem\\SceneCamera.cs", 767)]
	public Vector3 ToWorld(Vector2 screen)
	{
		screen.x = screen.x.Remap(0f, Size.x, -1f);
		screen.y = screen.y.Remap(Size.y, 0f, -1f);
		Frustum.ViewToWorld(screen, out var pOutWorld);
		return pOutWorld;
	}

	[SourceLocation("Systems\\SceneSystem\\SceneCamera.cs", 777)]
	internal void GatherVolumetricFog(RenderAttributes attributes)
	{
		if (!VolumetricFog.Enabled)
		{
			if (VolumetricFogImpl != null)
			{
				MainThread.QueueDispose(VolumetricFogImpl);
				VolumetricFogImpl = null;
			}
			return;
		}
		if (VolumetricFogImpl == null)
		{
			VolumetricFogImpl = new VolumetricFog();
		}
		VolumetricFogImpl.Update(VolumetricFog);
		attributes.SetPointer(StringToken.Literal("IVolumetricFog", 3596073060u), (nint)VolumetricFogImpl.native);
	}

	[SourceLocation("Systems\\SceneSystem\\SceneCamera.cs", 798)]
	internal void GatherTonemapper(RenderAttributes attributes)
	{
		attributes.SetPointer(StringToken.Literal("ITonemapSystem", 1400077339u), Tonemap.Enabled ? ((nint)ToneMapping.GetNative()) : IntPtr.Zero);
	}

	[SourceLocation("Systems\\SceneSystem\\SceneCamera.cs", 803)]
	internal void AddToRenderList(SwapChainHandle_t swapChain, Vector2? size)
	{
		ViewSetup config = new ViewSetup
		{
			ViewHash = HashCode.Combine(this)
		};
		if (WantsToRenderInStereo())
		{
			RenderStereo(in config);
		}
		else
		{
			Render(swapChain, size, in config);
		}
	}

	[SourceLocation("Systems\\SceneSystem\\SceneCamera.cs", 818)]
	private bool WantsToRenderInStereo()
	{
		if (VRSystem.IsActive)
		{
			return TargetEye > StereoTargetEye.None;
		}
		return false;
	}

	[SourceLocation("Systems\\SceneSystem\\SceneCamera.cs", 823)]
	private void Render(SwapChainHandle_t swapChain, Vector2? size, in ViewSetup config = default(ViewSetup))
	{
		if (swapChain.self == 0)
		{
			return;
		}
		Vector2 size2 = size ?? Size;
		if (size2.x <= 0f || size2.y <= 0f)
		{
			return;
		}
		OnPreRender(size2);
		using CameraRenderer cameraRenderer = new CameraRenderer("RenderToSwapChain", _cameraId);
		cameraRenderer.Configure(this, config);
		cameraRenderer.Native.Render(swapChain);
	}

	[SourceLocation("Systems\\SceneSystem\\SceneCamera.cs", 840)]
	internal void RenderToTexture(Texture texture, Vector2? size, in ViewSetup config)
	{
		if (texture == null || texture.native.IsNull)
		{
			return;
		}
		Vector2 vector = size ?? texture.Size;
		if (vector.x <= 0f || vector.y <= 0f)
		{
			return;
		}
		ConfigureView(in config);
		using CameraRenderer cameraRenderer = new CameraRenderer("RenderToTexture", _cameraId);
		cameraRenderer.Configure(this, config);
		cameraRenderer.Native.RenderToTexture(texture.native, Graphics.SceneView);
	}

	[SourceLocation("Systems\\SceneSystem\\SceneCamera.cs", 858)]
	internal unsafe void RenderToBitmap(Bitmap bitmap, in ViewSetup config = default(ViewSetup))
	{
		if (!bitmap.IsValid())
		{
			return;
		}
		Vector2Int size = bitmap.Size;
		if (size.x <= 1 || size.y <= 1)
		{
			return;
		}
		OnPreRender(size);
		using CameraRenderer cameraRenderer = new CameraRenderer("RenderToBitmap", _cameraId);
		cameraRenderer.Configure(this, config);
		cameraRenderer.Native.RenderToBitmap((nint)bitmap.GetPointer(), bitmap.Width, bitmap.Height, bitmap.BytesPerPixel);
	}

	/// <summary>
	/// Renders the scene from the camera position to a cube texture, capturing all 6 directions.
	/// </summary>
	[Description("Renders the scene from the camera position to a cube texture, capturing all 6 directions.")]
	[SourceLocation("Systems\\SceneSystem\\SceneCamera.cs", 883)]
	internal void RenderToCubeTexture(Texture texture, in ViewSetup config = default(ViewSetup))
	{
		if (texture == null || texture.native.IsNull)
		{
			return;
		}
		if (texture.Depth != 6)
		{
			throw new Exception("Expected a texture with 6 depth slices for RenderToCubeTexture");
		}
		Vector2 size = texture.Size;
		if (!(size.x <= 0f) && !(size.y <= 0f))
		{
			OnPreRender(size);
			CameraRenderer cameraRenderer = new CameraRenderer("RenderToCubeTexture", _cameraId);
			cameraRenderer.Configure(this, config);
			cameraRenderer.Native.EnableUI = false;
			for (int i = 0; i < CubeRotations.Length; i++)
			{
				cameraRenderer.Native.CameraRotation = (Rotation * CubeRotations[i]).Angles();
				cameraRenderer.Native.RenderToCubeTexture(texture.native, i);
			}
			cameraRenderer.Dispose();
		}
	}

	[SourceLocation("Systems\\SceneSystem\\SceneCamera.cs", 914)]
	private void RenderStereo(in ViewSetup config = default(ViewSetup))
	{
		if (!TargetEye.Contains(StereoTargetEye.LeftEye) && !TargetEye.Contains(StereoTargetEye.RightEye))
		{
			GlobalSystemNamespace.Log.Warning(FormattableStringFactory.Create("Called {0} but neither eyes were present in {1}?", "RenderStereo", "TargetEye"));
			return;
		}
		CameraRenderer cameraRenderer = new CameraRenderer("RenderStereo", _cameraId);
		try
		{
			cameraRenderer.Configure(this, config);
			CCameraRenderer native = cameraRenderer.Native;
			for (int i = 0; i < 2; i++)
			{
				bool flag = i == 0;
				StereoTargetEye flag2 = (flag ? StereoTargetEye.LeftEye : StereoTargetEye.RightEye);
				VREye vREye = (flag ? VREye.Left : VREye.Right);
				if (TargetEye.Contains(flag2))
				{
					OnPreRender(VRSystem.EyeRenderTargetSize);
					VRSystem.ClipPlanes.ZNear = ZNear;
					VRSystem.ClipPlanes.ZFar = ZFar;
					Transform transformForEye = VRSystem.GetTransformForEye(native.CameraPosition, native.CameraRotation, vREye);
					native.CameraPosition = transformForEye.Position;
					native.CameraRotation = transformForEye.Rotation;
					native.MiddleEyePosition = Position;
					native.MiddleEyeRotation = Rotation.Angles();
					native.OverrideProjection = VRSystem.GetProjectionMatrix(ZNear, ZFar, vREye);
					native.HasOverrideProjection = true;
					native.FieldOfView = 0f;
					native.ClipSpaceBounds = VRSystem.GetClipForEye(vREye);
					bool bSubmitThisEye = WantsStereoSubmit && vREye == VREye.Right;
					native.RenderStereo(i, (int)VRSystem.EyeRenderTargetSize.x, (int)VRSystem.EyeRenderTargetSize.y, bSubmitThisEye);
				}
			}
			VRSystem.IsRendering = WantsStereoSubmit;
			native.HasOverrideProjection = false;
			native.ClearSceneWorlds();
		}
		finally
		{
			cameraRenderer.Dispose();
		}
	}
}
