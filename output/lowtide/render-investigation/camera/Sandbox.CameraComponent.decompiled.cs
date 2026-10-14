using System;
using System.Buffers;
using System.Collections.Generic;
using System.Linq;
using System.Numerics;
using System.Text.Json.Serialization;
using System.Threading;
using NativeEngine;
using Sandbox.Diagnostics;
using Sandbox.Engine;
using Sandbox.Internal;
using Sandbox.Rendering;
using Sandbox.UI;
using Sandbox.Utility;

namespace Sandbox;

/// <summary>
/// Every scene should have at least one Camera.
/// </summary>
[Description("Every scene should have at least one Camera.")]
[SourceLocation("Scene\\Components\\Camera\\CameraComponent.AutoExposureSetup.cs", 3)]
[SourceLocation("Scene\\Components\\Camera\\CameraComponent.Commands.cs", 8)]
[Expose]
[Title("Camera")]
[Category("Rendering")]
[Icon("videocam")]
[EditorHandle("materials/gizmo/camera.png")]
[SourceLocation("Scene\\Components\\Camera\\CameraComponent.cs", 13)]
[SourceLocation("Scene\\Components\\Camera\\CameraComponent.Effects.cs", 3)]
[SourceLocation("Scene\\Components\\Camera\\CameraComponent.Hud.cs", 5)]
[SourceLocation("Scene\\Components\\Camera\\CameraComponent.PostProcess.cs", 5)]
public sealed class CameraComponent : Component, Component.ExecuteInEditor, Component.ISceneStage
{
	[SourceLocation("Scene\\Components\\Camera\\CameraComponent.AutoExposureSetup.cs", 5)]
	public class AutoExposureSetup
	{
		[DefaultValue(false)]
		[SourceLocation("Scene\\Components\\Camera\\CameraComponent.AutoExposureSetup.cs", 7)]
		public bool Enabled { get; set; }

		[DefaultValue(0f)]
		[SourceLocation("Scene\\Components\\Camera\\CameraComponent.AutoExposureSetup.cs", 8)]
		public float Compensation { get; set; }

		[DefaultValue(1f)]
		[SourceLocation("Scene\\Components\\Camera\\CameraComponent.AutoExposureSetup.cs", 9)]
		public float MinimumExposure { get; set; } = 1f;

		[DefaultValue(3f)]
		[SourceLocation("Scene\\Components\\Camera\\CameraComponent.AutoExposureSetup.cs", 10)]
		public float MaximumExposure { get; set; } = 3f;

		[DefaultValue(1f)]
		[SourceLocation("Scene\\Components\\Camera\\CameraComponent.AutoExposureSetup.cs", 11)]
		public float Rate { get; set; } = 1f;

		[SourceLocation("Scene\\Components\\Camera\\CameraComponent.AutoExposureSetup.cs", 13)]
		internal void Apply(SceneCamera scenecam)
		{
			if (!Enabled)
			{
				scenecam.Tonemap.Enabled = false;
				return;
			}
			scenecam.Tonemap.Enabled = true;
			scenecam.Tonemap.ExposureCompensation = Compensation;
			scenecam.Tonemap.MinExposure = MinimumExposure;
			scenecam.Tonemap.MaxExposure = MaximumExposure;
			scenecam.Tonemap.Rate = Rate;
			scenecam.Tonemap.Fade = 1f;
		}
	}

	private readonly record struct CommandListEntry(int Priority, CommandList List);

	public enum Axis
	{
		/// <summary>
		/// Fits the view within the x-axis.
		/// </summary>
		[Icon("panorama_horizontal")]
		[Description("Fits the view within the x-axis.")]
		Horizontal,
		/// <summary>
		/// Fits the view within the y-axis.
		/// </summary>
		[Icon("panorama_vertical")]
		[Description("Fits the view within the y-axis.")]
		Vertical
	}

	[SourceLocation("Scene\\Components\\Camera\\CameraComponent.Commands.cs", 16)]
	private readonly Lock _commandListLock = new Lock();

	[SourceLocation("Scene\\Components\\Camera\\CameraComponent.Commands.cs", 17)]
	private readonly Dictionary<Stage, List<CommandListEntry>> commandlists = new Dictionary<Stage, List<CommandListEntry>>();

	[SourceLocation("Scene\\Components\\Camera\\CameraComponent.Commands.cs", 106)]
	private static Superluminal _executeCommandList = new Superluminal("ExecuteCommandList", Color.Cyan);

	[SourceLocation("Scene\\Components\\Camera\\CameraComponent.cs", 20)]
	private SceneCamera sceneCamera;

	[SourceLocation("Scene\\Components\\Camera\\CameraComponent.cs", 34)]
	private bool _isMainCamera = true;

	[SourceLocation("Scene\\Components\\Camera\\CameraComponent.cs", 35)]
	private int _priority = 1;

	/// <summary>
	/// If specified, this camera will render to this RenderTexture instead of the screen.
	/// This can then be used in other stuff like materials.
	/// </summary>
	[Property]
	[SourceLocation("Scene\\Components\\Camera\\CameraComponent.cs", 141)]
	public RenderTextureAsset RenderTexture;

	/// <summary>
	/// Since we are rendering to a texture, better to generate mipmaps for it.
	/// </summary>
	[SourceLocation("Scene\\Components\\Camera\\CameraComponent.cs", 147)]
	private CommandList _renderTextureMipGenCommandList;

	[SourceLocation("Scene\\Components\\Camera\\CameraComponent.cs", 159)]
	private Texture _renderTarget;

	[SourceLocation("Scene\\Components\\Camera\\CameraComponent.cs", 275)]
	private bool _composed;

	[SourceLocation("Scene\\Components\\Camera\\CameraComponent.cs", 276)]
	private CameraView _composedBase;

	[SourceLocation("Scene\\Components\\Camera\\CameraComponent.cs", 277)]
	private CameraView _renderView;

	/// <summary>
	/// Update a SceneCamera with the settings from this component
	/// </summary>
	[SourceLocation("Scene\\Components\\Camera\\CameraComponent.cs", 390)]
	private Action<Stage, SceneCamera> executeCommandListsHook;

	[SourceLocation("Scene\\Components\\Camera\\CameraComponent.cs", 391)]
	private Func<bool> wantsDepthNormalsHook;

	[SourceLocation("Scene\\Components\\Camera\\CameraComponent.cs", 392)]
	private Func<Stage, bool> hasAsyncComputeHook;

	[SourceLocation("Scene\\Components\\Camera\\CameraComponent.cs", 393)]
	private Action<Stage> renderAsyncComputeHook;

	[SourceLocation("Scene\\Components\\Camera\\CameraComponent.cs", 555)]
	internal bool IsSceneEditorCamera;

	[SourceLocation("Scene\\Components\\Camera\\CameraComponent.Hud.cs", 7)]
	private CommandList _hudCommandList = new CommandList("Hud")
	{
		Flags = CommandList.Flag.Hud
	};

	[SourceLocation("Scene\\Components\\Camera\\CameraComponent.Hud.cs", 22)]
	private CommandList _overlayCommandList = new CommandList("Overlay")
	{
		Flags = CommandList.Flag.Hud
	};

	/// <summary>
	/// Enables and configures auto exposure on the camera. This is usually controlled
	/// by the Tonemapping component. But if you're not using that, it can be controlled manually here.
	/// </summary>
	[Description("Enables and configures auto exposure on the camera. This is usually controlled by the Tonemapping component. But if you're not using that, it can be controlled manually here.")]
	[SourceLocation("Scene\\Components\\Camera\\CameraComponent.AutoExposureSetup.cs", 40)]
	public AutoExposureSetup AutoExposure { get; } = new AutoExposureSetup();

	/// <summary>
	/// The clear flags for this camera.
	/// </summary>
	[Property]
	[DefaultValue(ClearFlags.All)]
	[Description("The clear flags for this camera.")]
	[SourceLocation("Scene\\Components\\Camera\\CameraComponent.cs", 25)]
	public ClearFlags ClearFlags { get; set; } = ClearFlags.All;

	/// <summary>
	/// The background color of this camera's view if there's no 2D Sky in the scene.
	/// </summary>
	[Property]
	[DefaultValue("#557685")]
	[Description("The background color of this camera's view if there's no 2D Sky in the scene.")]
	[SourceLocation("Scene\\Components\\Camera\\CameraComponent.cs", 31)]
	public Color BackgroundColor { get; set; } = "#557685";

	/// <summary>
	/// Returns true if this is the main game camera.
	/// </summary>
	[Property]
	[Description("Returns true if this is the main game camera.")]
	[SourceLocation("Scene\\Components\\Camera\\CameraComponent.cs", 40)]
	public bool IsMainCamera
	{
		get
		{
			return _isMainCamera;
		}
		set
		{
			if (_isMainCamera != value)
			{
				_isMainCamera = value;
				Scene.UpdateMainCamera();
			}
		}
	}

	/// <summary>
	/// The axis to use for the field of view.
	/// </summary>
	[Property]
	[Title("FOV Axis")]
	[HideIf("Orthographic", true)]
	[DefaultValue(Axis.Horizontal)]
	[Description("The axis to use for the field of view.")]
	[SourceLocation("Scene\\Components\\Camera\\CameraComponent.cs", 57)]
	public Axis FovAxis { get; set; }

	/// <summary>
	/// The field of view of this camera.
	/// </summary>
	[Property]
	[Range(1f, 179f)]
	[HideIf("Orthographic", true)]
	[DefaultValue(60)]
	[Description("The field of view of this camera.")]
	[SourceLocation("Scene\\Components\\Camera\\CameraComponent.cs", 63)]
	public float FieldOfView { get; set; } = 60f;

	/// <summary>
	/// The camera's near clip plane distance. This is the closest distance this camera will be able to render.
	/// A good value for this is about 5. Below 5 and particularly below 1 you're going to start to see
	/// a lot of artifacts like z-fighting.
	/// </summary>
	[Property]
	[Range(1f, 1000f)]
	[Step(1f)]
	[DefaultValue(10)]
	[Description("The camera's near clip plane distance. This is the closest distance this camera will be able to render. A good value for this is about 5. Below 5 and particularly below 1 you're going to start to see a lot of artifacts like z-fighting.")]
	[SourceLocation("Scene\\Components\\Camera\\CameraComponent.cs", 71)]
	public float ZNear { get; set; } = 10f;

	/// <summary>
	/// The camera's far clip plane distance. This is the furthest distance this camera will be able to render.
	/// This value totally depends on the game you're making. Shorter the better, sensible ranges would be
	/// between about 1000 and 30000, but if you want it to be further out you can balance that out by making
	/// ZNear larger.
	/// </summary>
	[Property]
	[Range(1f, 100000f)]
	[Step(1f)]
	[DefaultValue(10000)]
	[Description("The camera's far clip plane distance. This is the furthest distance this camera will be able to render. This value totally depends on the game you're making. Shorter the better, sensible ranges would be between about 1000 and 30000, but if you want it to be further out you can balance that out by making ZNear larger.")]
	[SourceLocation("Scene\\Components\\Camera\\CameraComponent.cs", 80)]
	public float ZFar { get; set; } = 10000f;

	/// <summary>
	/// The priority of this camera. Dictates which camera gets rendered on top of another. Higher means it'll be rendered on top.
	/// </summary>
	[Property]
	[Range(1f, 16f)]
	[Description("The priority of this camera. Dictates which camera gets rendered on top of another. Higher means it'll be rendered on top.")]
	[SourceLocation("Scene\\Components\\Camera\\CameraComponent.cs", 86)]
	public int Priority
	{
		get
		{
			return _priority;
		}
		set
		{
			if (_priority != value)
			{
				_priority = value;
				Scene.UpdateMainCamera();
			}
		}
	}

	/// <summary>
	/// Whether or not to use orthographic projection instead of perspective.
	/// </summary>
	[Property]
	[Description("Whether or not to use orthographic projection instead of perspective.")]
	[SourceLocation("Scene\\Components\\Camera\\CameraComponent.cs", 102)]
	public bool Orthographic { get; set; }

	/// <summary>
	/// The orthographic size for this camera while <see cref="P:Sandbox.CameraComponent.Orthographic" /> is set to true.
	/// </summary>
	[Property]
	[DefaultValue(1204)]
	[Description("The orthographic size for this camera while <span style=\"color: #4EC9B0;\">CameraComponent</span>.<span style=\"color: #DCDCDC;\">Orthographic</span> is set to true.")]
	[SourceLocation("Scene\\Components\\Camera\\CameraComponent.cs", 108)]
	public float OrthographicHeight { get; set; } = 1204f;

	/// <summary>
	/// The HMD eye that this camera is targeting.
	/// Use <see cref="F:Sandbox.StereoTargetEye.None" /> for the user's monitor (i.e. the companion window).
	/// </summary>
	[Property]
	[DefaultValue(StereoTargetEye.None)]
	[Description("The HMD eye that this camera is targeting. Use <span style=\"color: #86C691;\">StereoTargetEye</span>.<span style=\"color: #DCDCDC;\">None</span> for the user's monitor (i.e. the companion window).")]
	[SourceLocation("Scene\\Components\\Camera\\CameraComponent.cs", 115)]
	public StereoTargetEye TargetEye { get; set; }

	/// <summary>
	/// A list of tags that will be checked to include specific game objects when rendering this camera.
	/// If none are set, it will include everything.
	/// </summary>
	[Property]
	[Description("A list of tags that will be checked to include specific game objects when rendering this camera. If none are set, it will include everything.")]
	[SourceLocation("Scene\\Components\\Camera\\CameraComponent.cs", 122)]
	public TagSet RenderTags { get; set; } = new TagSet();

	/// <summary>
	/// A list of tags that will be checked to exclude specific game objects when rendering this camera.
	/// </summary>
	[Property]
	[Description("A list of tags that will be checked to exclude specific game objects when rendering this camera.")]
	[SourceLocation("Scene\\Components\\Camera\\CameraComponent.cs", 128)]
	public TagSet RenderExcludeTags { get; set; } = new TagSet();

	/// <summary>
	/// The size of the camera represented on the screen. Normalized between 0 and 1.
	/// </summary>
	[Property]
	[Range(0f, 1f, true, false)]
	[Description("The size of the camera represented on the screen. Normalized between 0 and 1.")]
	[SourceLocation("Scene\\Components\\Camera\\CameraComponent.cs", 134)]
	public Vector4 Viewport { get; set; } = new Vector4(0f, 0f, 1f, 1f);

	/// <summary>
	/// The texture to draw this camera to.
	/// Requires <see cref="M:Sandbox.Texture.CreateRenderTarget" />
	/// </summary>
	[JsonIgnore]
	[Hide]
	[SourceLocation("Scene\\Components\\Camera\\CameraComponent.cs", 165)]
	public Texture RenderTarget
	{
		get
		{
			return RenderTexture?.Texture ?? _renderTarget;
		}
		set
		{
			if (_renderTarget != value)
			{
				if (value != null && !value.Desc.m_nFlags.HasFlag(RuntimeTextureSpecificationFlags.TSPEC_RENDER_TARGET))
				{
					throw new Exception("RenderTarget texture needs to be a render target");
				}
				_renderTarget = value;
			}
		}
	}

	/// <summary>
	/// Render this camera using a different render mode
	/// </summary>
	[JsonIgnore]
	[Hide]
	[Description("Render this camera using a different render mode")]
	[SourceLocation("Scene\\Components\\Camera\\CameraComponent.cs", 187)]
	public SceneCameraDebugMode DebugMode { get; set; }

	/// <summary>
	/// Render this camera using a wireframe view.
	/// </summary>
	[JsonIgnore]
	[Hide]
	[Description("Render this camera using a wireframe view.")]
	[SourceLocation("Scene\\Components\\Camera\\CameraComponent.cs", 193)]
	public bool WireframeMode { get; set; }

	/// <summary>
	/// Accessor for getting this Camera Component's SceneCamera
	/// </summary>
	[Description("Accessor for getting this Camera Component's SceneCamera")]
	[SourceLocation("Scene\\Components\\Camera\\CameraComponent.cs", 199)]
	internal SceneCamera SceneCamera => sceneCamera;

	/// <summary>
	/// The view this camera composed this frame - the base transform reshaped by every
	/// <see cref="T:Sandbox.ICameraModifier" />, before transient render effects. Query
	/// <see cref="F:Sandbox.CameraView.FieldOfView" /> from here for zoom-aware logic like scaling look
	/// sensitivity while scoped. Final from the camera stage of the tick (after Update, before
	/// PreRender) - reading it during Update gives the previous frame's composition.
	/// </summary>
	[Description("The view this camera composed this frame - the base transform reshaped by every <span style=\"color: #4EC9B0;\">ICameraModifier</span>, before transient render effects. Query <span style=\"color: #86C691;\">CameraView</span>.<span style=\"color: #DCDCDC;\">FieldOfView</span> from here for zoom-aware logic like scaling look sensitivity while scoped. Final from the camera stage of the tick (after Update, before PreRender) - reading it during Update gives the previous frame's composition.")]
	[SourceLocation("Scene\\Components\\Camera\\CameraComponent.cs", 273)]
	public CameraView View { get; private set; }

	[SourceLocation("Scene\\Components\\Camera\\CameraComponent.cs", 344)]
	private CameraView RawView => new CameraView
	{
		Position = WorldPosition,
		Rotation = WorldRotation,
		FieldOfView = FieldOfView,
		ZNear = ZNear,
		ZFar = ZFar
	};

	/// <summary>
	/// The size of the viewport, in screen coordinates
	/// </summary>
	[Description("The size of the viewport, in screen coordinates")]
	[SourceLocation("Scene\\Components\\Camera\\CameraComponent.cs", 629)]
	public Rect ScreenRect
	{
		get
		{
			Vector2 vector = CustomSize ?? Screen.Size;
			return new Rect(vector.x * Viewport.x, vector.y * Viewport.y, vector.x * Viewport.z, vector.y * Viewport.w);
		}
	}

	/// <summary>
	/// Allows specifying a custom projection matrix for this camera
	/// </summary>
	[Description("Allows specifying a custom projection matrix for this camera")]
	[SourceLocation("Scene\\Components\\Camera\\CameraComponent.cs", 824)]
	public Matrix? CustomProjectionMatrix
	{
		get
		{
			return SceneCamera.CustomProjectionMatrix;
		}
		set
		{
			SceneCamera.CustomProjectionMatrix = value;
		}
	}

	/// <summary>
	/// Allows specifying a custom aspect ratio for this camera.
	/// By default (or when null) the camera size is screen size or render target size.
	/// </summary>
	[JsonIgnore]
	[Hide]
	[Description("Allows specifying a custom aspect ratio for this camera. By default (or when null) the camera size is screen size or render target size.")]
	[SourceLocation("Scene\\Components\\Camera\\CameraComponent.cs", 834)]
	public Vector2? CustomSize { get; set; }

	/// <summary>
	/// Get frustum projection matrix.
	/// </summary>
	[Description("Get frustum projection matrix.")]
	[SourceLocation("Scene\\Components\\Camera\\CameraComponent.cs", 840)]
	public Matrix ProjectionMatrix => sceneCamera.ProjectionMatrix;

	/// <summary>
	/// Allows drawing on the camera after post processing.
	/// </summary>
	[Obsolete("Use BeginHud() instead. Dispose the painter to submit its drawing.")]
	[Description("Allows drawing on the camera after post processing.")]
	[SourceLocation("Scene\\Components\\Camera\\CameraComponent.Hud.cs", 12)]
	public HudPainter Hud => new HudPainter(_hudCommandList);

	/// <summary>
	/// Used to draw to the screen. This is drawn on top of everything, so is good for debug overlays etc.
	/// </summary>
	[Obsolete("Use BeginOverlay() instead. Dispose the painter to submit its drawing.")]
	[Description("Used to draw to the screen. This is drawn on top of everything, so is good for debug overlays etc.")]
	[SourceLocation("Scene\\Components\\Camera\\CameraComponent.Hud.cs", 27)]
	public HudPainter Overlay => new HudPainter(_overlayCommandList);

	/// <summary>
	/// Commands drawn after post processing. Reset at the start of each frame.
	/// </summary>
	[Description("Commands drawn after post processing. Reset at the start of each frame.")]
	[SourceLocation("Scene\\Components\\Camera\\CameraComponent.Hud.cs", 40)]
	public CommandList HudCommandList => _hudCommandList;

	/// <summary>
	/// Commands drawn after UI. Reset at the start of each frame.
	/// </summary>
	[Description("Commands drawn after UI. Reset at the start of each frame.")]
	[SourceLocation("Scene\\Components\\Camera\\CameraComponent.Hud.cs", 45)]
	public CommandList OverlayCommandList => _overlayCommandList;

	[SourceLocation("Scene\\Components\\Camera\\CameraComponent.PostProcess.cs", 7)]
	internal PostProcessLayers PostProcess { get; private set; } = new PostProcessLayers();

	/// <summary>
	/// Enable or disable post processing for this camera.
	/// </summary>
	[Header("Post Processing")]
	[Property]
	[DefaultValue(true)]
	[Description("Enable or disable post processing for this camera.")]
	[SourceLocation("Scene\\Components\\Camera\\CameraComponent.PostProcess.cs", 32)]
	public bool EnablePostProcessing { get; set; } = true;

	/// <summary>
	/// If set then we'll trigger post process volumes from this position, instead of the camera's position.
	/// </summary>
	[Property]
	[Description("If set then we'll trigger post process volumes from this position, instead of the camera's position.")]
	[SourceLocation("Scene\\Components\\Camera\\CameraComponent.PostProcess.cs", 39)]
	public GameObject PostProcessAnchor { get; set; }

	/// <summary>
	/// Add a command list to the render
	/// </summary>
	[Description("Add a command list to the render")]
	[SourceLocation("Scene\\Components\\Camera\\CameraComponent.Commands.cs", 22)]
	public void AddCommandList(CommandList buffer, Stage stage, int order = 0)
	{
		using (_commandListLock.EnterScope())
		{
			if (!commandlists.TryGetValue(stage, out var value))
			{
				value = new List<CommandListEntry>();
				commandlists[stage] = value;
			}
			int num = value.Count;
			while (num > 0 && value[num - 1].Priority > order)
			{
				num--;
			}
			value.Insert(num, new CommandListEntry(order, buffer));
		}
	}

	/// <summary>
	/// Remove an entry
	/// </summary>
	[Description("Remove an entry")]
	[SourceLocation("Scene\\Components\\Camera\\CameraComponent.Commands.cs", 44)]
	public void RemoveCommandList(CommandList buffer, Stage stage)
	{
		using (_commandListLock.EnterScope())
		{
			if (commandlists.TryGetValue(stage, out var value))
			{
				RemoveCommandListEntries(value, buffer);
			}
		}
	}

	/// <summary>
	/// Remove an entry
	/// </summary>
	[Description("Remove an entry")]
	[SourceLocation("Scene\\Components\\Camera\\CameraComponent.Commands.cs", 58)]
	public void RemoveCommandList(CommandList buffer)
	{
		using (_commandListLock.EnterScope())
		{
			foreach (List<CommandListEntry> value in commandlists.Values)
			{
				RemoveCommandListEntries(value, buffer);
			}
		}
	}

	/// <summary>
	/// Remove matching registrations without allocating a capturing predicate. Caller holds the lock.
	/// </summary>
	[Description("Remove matching registrations without allocating a capturing predicate. Caller holds the lock.")]
	[SourceLocation("Scene\\Components\\Camera\\CameraComponent.Commands.cs", 72)]
	private static void RemoveCommandListEntries(List<CommandListEntry> list, CommandList buffer)
	{
		for (int num = list.Count - 1; num >= 0; num--)
		{
			if (list[num].List == buffer)
			{
				list.RemoveAt(num);
			}
		}
	}

	/// <summary>
	/// Remove all entries in this stage
	/// </summary>
	[Description("Remove all entries in this stage")]
	[SourceLocation("Scene\\Components\\Camera\\CameraComponent.Commands.cs", 84)]
	public void ClearCommandLists(Stage stage)
	{
		using (_commandListLock.EnterScope())
		{
			if (commandlists.TryGetValue(stage, out var value))
			{
				value.Clear();
			}
		}
	}

	/// <summary>
	/// Remove all command list registrations.
	/// </summary>
	[Description("Remove all command list registrations.")]
	[SourceLocation("Scene\\Components\\Camera\\CameraComponent.Commands.cs", 97)]
	public void ClearCommandLists()
	{
		using (_commandListLock.EnterScope())
		{
			foreach (List<CommandListEntry> value in commandlists.Values)
			{
				value.Clear();
			}
		}
	}

	/// <summary>
	/// Called during the render pipeline on a worker thread.
	/// </summary>
	[Description("Called during the render pipeline on a worker thread.")]
	[SourceLocation("Scene\\Components\\Camera\\CameraComponent.Commands.cs", 111)]
	private void ExecuteCommandLists(Stage stage, SceneCamera currentCamera)
	{
		Scene.RunRenderThreadEvent(this, stage);
		int count;
		CommandListEntry[] array;
		using (_commandListLock.EnterScope())
		{
			if (!commandlists.TryGetValue(stage, out var value) || value.Count == 0)
			{
				return;
			}
			count = value.Count;
			array = ArrayPool<CommandListEntry>.Shared.Rent(count);
			value.CopyTo(array);
		}
		try
		{
			for (int i = 0; i < count; i++)
			{
				CommandListEntry commandListEntry = array[i];
				using (_executeCommandList.Start(commandListEntry.List.DebugName, "C:\\actions-runner\\_work\\sbox\\sbox\\engine\\Sandbox.Engine\\Scene\\Components\\Camera\\CameraComponent.Commands.cs", 133, "ExecuteCommandLists"))
				{
					if (!commandListEntry.List.Flags.Contains(CommandList.Flag.PostProcess) || currentCamera.EnablePostProcessing)
					{
						commandListEntry.List.ExecuteOnRenderThread();
					}
				}
			}
		}
		finally
		{
			ArrayPool<CommandListEntry>.Shared.Return(array, clearArray: true);
		}
	}

	[SourceLocation("Scene\\Components\\Camera\\CameraComponent.cs", 149)]
	private CommandList CreateRenderTextureMipGenCommandList()
	{
		CommandList commandList = new CommandList("Generate MipMaps For RenderTexture");
		if (RenderTexture != null && RenderTexture.Texture != null && RenderTexture.Texture.Mips > 1)
		{
			commandList.GenerateMipMaps(RenderTexture.Texture);
		}
		return commandList;
	}

	[SourceLocation("Scene\\Components\\Camera\\CameraComponent.cs", 204)]
	public override void Reset()
	{
		base.Reset();
		RenderTags = new TagSet();
		RenderExcludeTags = new TagSet();
		Viewport = new Vector4(0f, 0f, 1f, 1f);
		ClearFlags = ClearFlags.All;
	}

	[SourceLocation("Scene\\Components\\Camera\\CameraComponent.cs", 214)]
	private void EnsureSceneCameraCreated()
	{
		if (sceneCamera == null)
		{
			Assert.NotNull(Scene);
			if (Game.IsPlaying)
			{
				Assert.AreEqual(Game.ActiveScene, Scene, "Camera scene is not active scene");
			}
			sceneCamera = new SceneCamera(GameObject.Name);
			sceneCamera.OnRenderStageHook = ExecuteCommandLists;
			sceneCamera.WantsDepthNormalsHook = WantsDepthNormals;
			sceneCamera.HasAsyncComputeHook = HasAsyncCompute;
			sceneCamera.RenderAsyncComputeHook = RenderAsyncCompute;
		}
	}

	[SourceLocation("Scene\\Components\\Camera\\CameraComponent.cs", 235)]
	protected override void OnAwake()
	{
		EnsureSceneCameraCreated();
		Scene.Cameras.Add(this);
	}

	[SourceLocation("Scene\\Components\\Camera\\CameraComponent.cs", 241)]
	protected override void OnDestroy()
	{
		Scene.Cameras.Remove(this);
		ManagedSceneRendering.Forget(this);
		sceneCamera?.Dispose();
		sceneCamera = null;
	}

	[SourceLocation("Scene\\Components\\Camera\\CameraComponent.cs", 249)]
	protected override void DrawGizmos()
	{
		if (sceneCamera == null)
		{
			return;
		}
		using (Gizmo.Scope($"{GetHashCode()}"))
		{
			Gizmo.Transform = global::Transform.Zero;
			UpdateSceneCameraTransform(sceneCamera);
			Frustum frustum = sceneCamera.GetFrustum(new Rect(0f, 0f, 1920f, 1080f), new Vector2(1920f, 1080f));
			Gizmo.Draw.Color = Color.White.WithAlpha(0.4f);
			Gizmo.Draw.LineFrustum(in frustum);
		}
	}

	/// <summary>
	/// Compose this camera's view - the base transform reshaped by every <see cref="T:Sandbox.ICameraModifier" />
	/// (published on <see cref="P:Sandbox.CameraComponent.View" />), then transient effects baked on top for the render. The
	/// scene composes every camera once per tick, after Update and bone merging and before PreRender,
	/// so anything in PreRender positions against a settled camera. Call it yourself only when you're rendering
	/// without ticking the scene and want the composition - otherwise a camera moved after composing
	/// just renders from its raw transform.
	/// </summary>
	[Description("Compose this camera's view - the base transform reshaped by every <span style=\"color: #4EC9B0;\">ICameraModifier</span> (published on <span style=\"color: #4EC9B0;\">CameraComponent</span>.<span style=\"color: #DCDCDC;\">View</span>), then transient effects baked on top for the render. The scene composes every camera once per tick, after Update and bone merging and before PreRender, so anything in PreRender positions against a settled camera. Call it yourself only when you're rendering without ticking the scene and want the composition - otherwise a camera moved after composing just renders from its raw transform.")]
	[SourceLocation("Scene\\Components\\Camera\\CameraComponent.cs", 287)]
	public void ComposeView()
	{
		ComposeView(Scene.IsEditor ? null : GatherModifiers(Scene));
	}

	[SourceLocation("Scene\\Components\\Camera\\CameraComponent.cs", 294)]
	internal static ICameraModifier[] GatherModifiers(Scene scene)
	{
		return (from x in scene.GetAll<ICameraModifier>()
			orderby x.CameraOrder
			select x).ToArray();
	}

	[SourceLocation("Scene\\Components\\Camera\\CameraComponent.cs", 297)]
	internal void ComposeView(ICameraModifier[] modifiers)
	{
		CameraView view = RawView;
		if (modifiers != null)
		{
			ICameraModifier[] array = modifiers;
			for (int i = 0; i < array.Length; i++)
			{
				array[i].ModifyCamera(this, ref view);
			}
			View = view;
			array = modifiers;
			for (int i = 0; i < array.Length; i++)
			{
				array[i].PostCameraSetup(this, in view);
			}
		}
		else
		{
			View = view;
		}
		_renderView = view;
		CameraEffectSystem cameraEffectSystem = GameObjectSystem<CameraEffectSystem>.Get(Scene);
		if (cameraEffectSystem != null)
		{
			cameraEffectSystem.QueryOffsets(this, out var position, out var angles, out var fieldOfView);
			_renderView.Position += _renderView.Rotation * position;
			_renderView.Rotation *= (Rotation)angles;
			_renderView.FieldOfView = (_renderView.FieldOfView + fieldOfView).Clamp(1f, 179f);
		}
		_composedBase = RawView;
		_composed = true;
	}

	[SourceLocation("Scene\\Components\\Camera\\CameraComponent.cs", 353)]
	internal void UpdateSceneCameraTransform(SceneCamera camera)
	{
		CameraView rawView = RawView;
		if (!_composed || rawView != _composedBase)
		{
			_renderView = rawView;
		}
		camera.Position = _renderView.Position;
		camera.Rotation = _renderView.Rotation;
		camera.ZNear = _renderView.ZNear;
		camera.ZFar = _renderView.ZFar;
		camera.Rect = new Rect(Viewport.x, Viewport.y, Viewport.z, Viewport.w);
		camera.Size = ScreenRect.Size;
		camera.Ortho = Orthographic;
		camera.OrthoHeight = OrthographicHeight;
		if (FovAxis == Axis.Vertical && ScreenRect.Height > 0f)
		{
			camera.FieldOfView = Screen.CreateVerticalFieldOfView(_renderView.FieldOfView, ScreenRect.Width / ScreenRect.Height);
		}
		else
		{
			camera.FieldOfView = _renderView.FieldOfView;
		}
	}

	[SourceLocation("Scene\\Components\\Camera\\CameraComponent.cs", 381)]
	internal void UpdateSceneCameraStereo(SceneCamera camera)
	{
		camera.TargetEye = TargetEye;
		camera.WantsStereoSubmit = !Scene.IsEditor;
	}

	[SourceLocation("Scene\\Components\\Camera\\CameraComponent.cs", 395)]
	public void UpdateSceneCamera(SceneCamera camera, bool includeTags = true)
	{
		if (Scene == null)
		{
			GlobalSystemNamespace.Log.Warning($"Trying to update camera from {this} but has no scene");
			return;
		}
		UpdateSceneCameraTransform(camera);
		camera.World = Scene.SceneWorld;
		camera.ClearFlags = ClearFlags;
		camera.Worlds.Clear();
		camera.Worlds.Add(Scene.DebugSceneWorld);
		if (Gizmo.Active != null)
		{
			camera.Worlds.Add(Gizmo.Active.World);
		}
		CopyPostProcessing(camera);
		if (includeTags)
		{
			camera.RenderTags.SetFrom(RenderTags);
			camera.ExcludeTags.SetFrom(RenderExcludeTags);
		}
		Scene.RenderAttributes.MergeTo(camera.Attributes);
		camera.DebugMode = DebugMode;
		camera.WireframeMode = WireframeMode;
		camera.EnablePostProcessing = EnablePostProcessing;
		camera.BackgroundColor = (ClearFlags.Contains(ClearFlags.Color) ? BackgroundColor : Color.Transparent);
	}

	[SourceLocation("Scene\\Components\\Camera\\CameraComponent.cs", 433)]
	internal void CopyPostProcessing(SceneCamera camera)
	{
		if (Scene == null)
		{
			GlobalSystemNamespace.Log.Warning($"Trying to update camera from {this} but has no scene");
			return;
		}
		camera.CubemapFog.Enabled = false;
		camera.Bloom.Enabled = false;
		AutoExposure.Apply(camera);
		if (ClearFlags.Contains(ClearFlags.Color))
		{
			camera.VolumetricFog.Enabled = Scene.Get<VolumetricFogVolume>() != null;
			camera.VolumetricFog.DrawDistance = 4096f;
			camera.VolumetricFog.FadeInStart = 64f;
			camera.VolumetricFog.FadeInEnd = 256f;
			camera.VolumetricFog.IndirectStrength = 1f;
			camera.VolumetricFog.Anisotropy = 1f;
			camera.VolumetricFog.Scattering = 1f;
			camera.VolumetricFog.BakedIndirectTexture = Scene.Get<VolumetricFogController>()?.BakedFogTexture;
		}
		camera.OnRenderStageHook = ExecuteCommandLists;
		camera.WantsDepthNormalsHook = WantsDepthNormals;
		camera.HasAsyncComputeHook = HasAsyncCompute;
		camera.RenderAsyncComputeHook = RenderAsyncCompute;
		foreach (CubemapFog item in Scene.Query<CubemapFog>())
		{
			if (!item.Tags.HasAny(RenderExcludeTags))
			{
				item.SetupCamera(this, camera);
			}
		}
	}

	/// <summary>
	/// Update the SceneCamera UI with the settings from this component
	/// </summary>
	[Description("Update the SceneCamera UI with the settings from this component")]
	[SourceLocation("Scene\\Components\\Camera\\CameraComponent.cs", 486)]
	private void UpdateSceneCameraUI(SceneCamera camera)
	{
		if (Scene != null)
		{
			camera.OnRenderUI = () =>
			{
				OnCameraRenderUI(camera, ScreenPanel.RenderTiming.AfterPostProcess);
			};
			camera.OnRenderUIBeforePostProcess = () =>
			{
				OnCameraRenderUI(camera, ScreenPanel.RenderTiming.BeforePostProcess);
			};
		}
	}

	[Obsolete("Use CommandList")]
	[SourceLocation("Scene\\Components\\Camera\\CameraComponent.cs", 495)]
	public IDisposable AddHookAfterOpaque(string debugName, int order, Action<SceneCamera> renderEffect)
	{
		return null;
	}

	/// <summary>
	/// Obsolete 09/06/2025
	/// </summary>
	[Obsolete("Use CommandList")]
	[Description("Obsolete 09/06/2025")]
	[SourceLocation("Scene\\Components\\Camera\\CameraComponent.cs", 501)]
	public IDisposable AddHookAfterTransparent(string debugName, int order, Action<SceneCamera> renderEffect)
	{
		return null;
	}

	/// <summary>
	/// Obsolete 09/06/2025
	/// </summary>
	[Obsolete("Use CommandList")]
	[Description("Obsolete 09/06/2025")]
	[SourceLocation("Scene\\Components\\Camera\\CameraComponent.cs", 507)]
	public IDisposable AddHookBeforeOverlay(string debugName, int order, Action<SceneCamera> renderEffect)
	{
		return null;
	}

	/// <summary>
	/// Obsolete 02/10/2025
	/// </summary>
	[Obsolete("Use CommandList")]
	[Description("Obsolete 02/10/2025")]
	[SourceLocation("Scene\\Components\\Camera\\CameraComponent.cs", 513)]
	public IDisposable AddHookAfterUI(string debugName, int order, Action<SceneCamera> renderEffect)
	{
		return null;
	}

	/// <summary>
	/// Anything to draw at <see cref="F:Sandbox.Rendering.Stage.EarlyUI" />? The pipeline skips that layer's passes otherwise.
	/// </summary>
	[Description("Anything to draw at <span style=\"color: #86C691;\">Stage</span>.<span style=\"color: #DCDCDC;\">EarlyUI</span>? The pipeline skips that layer's passes otherwise.")]
	[SourceLocation("Scene\\Components\\Camera\\CameraComponent.cs", 519)]
	private bool HasEarlyUI()
	{
		using (_commandListLock.EnterScope())
		{
			if (commandlists.TryGetValue(Stage.EarlyUI, out var value) && value.Count > 0)
			{
				return true;
			}
		}
		foreach (ScreenPanel renderScreenPanel in Scene.renderScreenPanels)
		{
			if (renderScreenPanel.Active && renderScreenPanel.Timing == ScreenPanel.RenderTiming.BeforePostProcess && (renderScreenPanel.TargetCamera ?? (IsMainCamera ? this : null)) == this)
			{
				return true;
			}
		}
		return false;
	}

	[SourceLocation("Scene\\Components\\Camera\\CameraComponent.cs", 536)]
	private void OnCameraRenderUI(SceneCamera camera, ScreenPanel.RenderTiming timing)
	{
		if (Scene == null)
		{
			return;
		}
		foreach (ScreenPanel renderScreenPanel in Scene.renderScreenPanels)
		{
			if (renderScreenPanel.Active && renderScreenPanel.Timing == timing && (renderScreenPanel.TargetCamera ?? (IsMainCamera ? this : null)) == this && !RenderExcludeTags.HasAny(renderScreenPanel.GameObject.Tags))
			{
				renderScreenPanel.Render();
			}
		}
	}

	[SourceLocation("Scene\\Components\\Camera\\CameraComponent.cs", 557)]
	internal void InitializeRendering(bool renderUI = true)
	{
		using (Scene.Push())
		{
			EnsureSceneCameraCreated();
			if (IsSceneEditorCamera)
			{
				UpdateSceneCamera(sceneCamera);
				Scene.Camera?.CopyPostProcessing(sceneCamera);
			}
			else
			{
				UpdateSceneCamera(sceneCamera);
			}
			UpdateSceneCameraUI(sceneCamera);
			sceneCamera.RenderUI = renderUI;
			sceneCamera.Attributes.Set(StringToken.Literal("enableEarlyUI", 3319412064u), HasEarlyUI());
			UpdateSceneCameraStereo(sceneCamera);
		}
	}

	/// <summary>
	/// This should only be called when creating render lists!!
	/// </summary>
	[Description("This should only be called when creating render lists!!")]
	[SourceLocation("Scene\\Components\\Camera\\CameraComponent.cs", 583)]
	internal void AddToRenderList(SwapChainHandle_t swapChain, Vector2? size)
	{
		if (!Active || Viewport.z <= 0f || Viewport.w <= 0f)
		{
			return;
		}
		using (Scene.Push())
		{
			InitializeRendering();
			if (!ManagedSceneRendering.TryRender(this, swapChain, CustomSize ?? size))
			{
				if (RenderTarget != null && RenderTarget.native.IsValid)
				{
					SceneCamera.RenderToTexture(RenderTarget, CustomSize ?? size, default(ViewSetup));
				}
				else
				{
					SceneCamera.AddToRenderList(swapChain, CustomSize ?? size);
				}
			}
		}
	}

	[SourceLocation("Scene\\Components\\Camera\\CameraComponent.cs", 611)]
	public Vector2 PointToScreenNormal(in Vector3 worldPosition)
	{
		EnsureSceneCameraCreated();
		UpdateSceneCameraTransform(sceneCamera);
		return sceneCamera.ToScreenNormal(worldPosition);
	}

	[SourceLocation("Scene\\Components\\Camera\\CameraComponent.cs", 619)]
	public Vector2 PointToScreenPixels(in Vector3 worldPosition)
	{
		Rect screenRect = ScreenRect;
		Vector2 vector = PointToScreenNormal(in worldPosition);
		return new Vector2(vector.x, vector.y) * screenRect.Size;
	}

	/// <summary>
	/// Given a BBox in world space, will return the screen space rect that totally contains the box.
	/// </summary>
	[Description("Given a BBox in world space, will return the screen space rect that totally contains the box.")]
	[SourceLocation("Scene\\Components\\Camera\\CameraComponent.cs", 641)]
	public Rect BBoxToScreenPixels(BBox bounds, out bool isBehind)
	{
		Vector2[] array = new Vector2[8];
		Vector3 mins = bounds.Mins;
		Vector3 maxs = bounds.Maxs;
		isBehind = true;
		array[0] = PointToScreenPixels(new Vector3(mins.x, mins.y, mins.z));
		array[1] = PointToScreenPixels(new Vector3(maxs.x, mins.y, mins.z));
		array[2] = PointToScreenPixels(new Vector3(mins.x, maxs.y, mins.z));
		array[3] = PointToScreenPixels(new Vector3(mins.x, mins.y, maxs.z));
		array[4] = PointToScreenPixels(new Vector3(maxs.x, maxs.y, mins.z));
		array[5] = PointToScreenPixels(new Vector3(mins.x, maxs.y, maxs.z));
		array[6] = PointToScreenPixels(new Vector3(maxs.x, mins.y, maxs.z));
		array[7] = PointToScreenPixels(new Vector3(maxs.x, maxs.y, maxs.z));
		Vector2 a = array[0];
		Vector2 b = array[0];
		for (int i = 1; i < 8; i++)
		{
			a = Vector2.Min(a, array[i]);
			b = Vector2.Max(b, array[i]);
		}
		Vector2 vector = CustomSize ?? Screen.Size;
		if (b.x < 0f)
		{
			isBehind = true;
		}
		if (b.y < 0f)
		{
			isBehind = true;
		}
		if (a.x > vector.x)
		{
			isBehind = true;
		}
		if (a.y > vector.y)
		{
			isBehind = true;
		}
		return Rect.FromPoints(in a, in b);
	}

	[SourceLocation("Scene\\Components\\Camera\\CameraComponent.cs", 678)]
	public Vector2 PointToScreenPixels(Vector3 worldPosition, out bool isBehind)
	{
		EnsureSceneCameraCreated();
		UpdateSceneCameraTransform(sceneCamera);
		Rect screenRect = ScreenRect;
		Vector3 vector = sceneCamera.ToScreenWithDirection(worldPosition);
		isBehind = vector.z <= 0f;
		return new Vector2(vector.x, vector.y) * screenRect.Size;
	}

	[SourceLocation("Scene\\Components\\Camera\\CameraComponent.cs", 689)]
	public Vector2 PointToScreenNormal(Vector3 worldPosition, out bool isBehind)
	{
		EnsureSceneCameraCreated();
		UpdateSceneCameraTransform(sceneCamera);
		Vector3 vector = sceneCamera.ToScreenWithDirection(worldPosition);
		isBehind = vector.z <= 0f;
		return new Vector2(vector.x, vector.y);
	}

	[SourceLocation("Scene\\Components\\Camera\\CameraComponent.cs", 699)]
	public Ray ScreenPixelToRay(Vector2 pixelPosition)
	{
		EnsureSceneCameraCreated();
		UpdateSceneCameraTransform(sceneCamera);
		return sceneCamera.GetRay(pixelPosition, ScreenRect.Size);
	}

	[SourceLocation("Scene\\Components\\Camera\\CameraComponent.cs", 707)]
	public Ray ScreenNormalToRay(Vector3 normalPosition)
	{
		Vector3 vector = new Vector3(normalPosition.x * ScreenRect.Size.x, normalPosition.y * ScreenRect.Size.y, normalPosition.z);
		return ScreenPixelToRay(vector);
	}

	/// <summary>
	/// Convert from screen coords to world coords on the near frustum plane.
	/// </summary>
	[Description("Convert from screen coords to world coords on the near frustum plane.")]
	[SourceLocation("Scene\\Components\\Camera\\CameraComponent.cs", 720)]
	public Vector3 ScreenToWorld(Vector2 screen)
	{
		EnsureSceneCameraCreated();
		UpdateSceneCameraTransform(sceneCamera);
		return sceneCamera.ToWorld(screen);
	}

	[SourceLocation("Scene\\Components\\Camera\\CameraComponent.cs", 728)]
	protected override void OnEnabled()
	{
		Scene?.UpdateMainCamera();
		AddCommandList(_hudCommandList, Stage.AfterPostProcess, 5000);
		AddCommandList(_overlayCommandList, Stage.AfterUI, 5000);
		if (RenderTexture != null)
		{
			_renderTextureMipGenCommandList = CreateRenderTextureMipGenCommandList();
			AddCommandList(_renderTextureMipGenCommandList, Stage.AfterPostProcess, 10000);
		}
	}

	[SourceLocation("Scene\\Components\\Camera\\CameraComponent.cs", 742)]
	protected override void OnDisabled()
	{
		Scene?.UpdateMainCamera();
		RemoveCommandList(_hudCommandList);
		RemoveCommandList(_overlayCommandList);
		if (_renderTextureMipGenCommandList != null)
		{
			RemoveCommandList(_renderTextureMipGenCommandList);
			_renderTextureMipGenCommandList = null;
		}
	}

	/// <summary>
	/// Returns the view frustum of the current screen rect.
	/// </summary>
	[Description("Returns the view frustum of the current screen rect.")]
	[SourceLocation("Scene\\Components\\Camera\\CameraComponent.cs", 759)]
	public Frustum GetFrustum()
	{
		UpdateSceneCameraTransform(sceneCamera);
		return sceneCamera.GetFrustum(ScreenRect);
	}

	/// <summary>
	/// Given a pixel rect return a frustum on the current camera.
	/// </summary>
	[Description("Given a pixel rect return a frustum on the current camera.")]
	[SourceLocation("Scene\\Components\\Camera\\CameraComponent.cs", 768)]
	public Frustum GetFrustum(Rect screenRect)
	{
		UpdateSceneCameraTransform(sceneCamera);
		return sceneCamera.GetFrustum(screenRect);
	}

	/// <summary>
	/// Given a pixel rect return a frustum on the current camera. Pass in 1 to ScreenSize to use normalized screen coords.
	/// </summary>
	[Description("Given a pixel rect return a frustum on the current camera. Pass in 1 to ScreenSize to use normalized screen coords.")]
	[SourceLocation("Scene\\Components\\Camera\\CameraComponent.cs", 778)]
	public Frustum GetFrustum(Rect screenRect, Vector3 screenSize)
	{
		UpdateSceneCameraTransform(sceneCamera);
		return sceneCamera.GetFrustum(screenRect, screenSize);
	}

	/// <summary>
	/// Render scene to a texture from this camera's point of view
	/// </summary>
	[Description("Render scene to a texture from this camera's point of view")]
	[SourceLocation("Scene\\Components\\Camera\\CameraComponent.cs", 788)]
	public bool RenderToTexture(Texture target, in ViewSetup config = default(ViewSetup))
	{
		if (target == null || target.native.IsNull)
		{
			return false;
		}
		if (!Graphics.IsActive)
		{
			Scene.PreCameraRender();
			InitializeRendering();
		}
		using CameraRenderer cameraRenderer = new CameraRenderer(GameObject.Name + ".RenderToTexture", sceneCamera._cameraId);
		lock (this)
		{
			cameraRenderer.Configure(sceneCamera, config);
		}
		cameraRenderer.Native.RenderToTexture(target.native, Graphics.SceneView);
		cameraRenderer.Native.ClearSceneWorlds();
		return true;
	}

	/// <summary>
	/// Calculates a projection matrix with an oblique clip-plane defined in world space.
	/// </summary>
	[Description("Calculates a projection matrix with an oblique clip-plane defined in world space.")]
	[SourceLocation("Scene\\Components\\Camera\\CameraComponent.cs", 845)]
	public Matrix CalculateObliqueMatrix(Plane clipPlane)
	{
		Transform worldTransform = WorldTransform;
		Vector3 vector = worldTransform.Rotation.Inverse * clipPlane.Normal;
		vector = new Vector3(vector.y, 0f - vector.z, vector.x).Normal;
		Matrix4x4 matrix4x = ProjectionMatrix;
		Vector4 vector2 = new Vector4
		{
			x = ((float)MathF.Sign(vector.x) - matrix4x.M13) / matrix4x.M11,
			y = ((float)MathF.Sign(vector.y) - matrix4x.M23) / matrix4x.M22,
			z = 1f,
			w = (1f - matrix4x.M33) / matrix4x.M34
		};
		Vector4 c = new Vector4(in vector, Vector3.Dot(worldTransform.Position - clipPlane.Position, in clipPlane.Normal));
		Vector4 vector3 = c * (1f / System.Numerics.Vector4.Dot(c, vector2));
		matrix4x.M31 = 0f - vector3.x;
		matrix4x.M32 = 0f - vector3.y;
		matrix4x.M33 = 0f - vector3.z;
		matrix4x.M34 = vector3.w;
		return matrix4x;
	}

	/// <summary>
	/// Render this camera to the target bitmap.
	/// </summary>
	[Description("Render this camera to the target bitmap.")]
	[SourceLocation("Scene\\Components\\Camera\\CameraComponent.cs", 889)]
	public void RenderToBitmap(Bitmap targetBitmap)
	{
		RenderToBitmap(targetBitmap, renderUI: true);
	}

	/// <summary>
	/// Render this camera to the target bitmap, with the option to include or exclude the drawn UI.
	/// </summary>
	[Description("Render this camera to the target bitmap, with the option to include or exclude the drawn UI.")]
	[SourceLocation("Scene\\Components\\Camera\\CameraComponent.cs", 894)]
	public void RenderToBitmap(Bitmap targetBitmap, bool renderUI)
	{
		if (targetBitmap == null || targetBitmap.Width <= 1 || targetBitmap.Height <= 1 || !this.IsValid())
		{
			return;
		}
		using (Scene.Push())
		{
			Scene.PreCameraRender();
			InitializeRendering(renderUI);
			if (renderUI)
			{
				ResizeUI(targetBitmap.Size);
			}
			SceneCamera.OnPreRender(targetBitmap.Size);
			SceneCamera.RenderToBitmap(targetBitmap, default(ViewSetup));
			if (renderUI)
			{
				ResizeUI(new Vector2(Screen.Width, Screen.Height));
			}
		}
	}

	[SourceLocation("Scene\\Components\\Camera\\CameraComponent.cs", 920)]
	private void ResizeUI(Vector2 size)
	{
		if (Scene == null)
		{
			return;
		}
		bool flag = false;
		foreach (ScreenPanel item in Scene.GetAll<ScreenPanel>())
		{
			if (item.IsValid() && item.Active && (item.TargetCamera ?? (IsMainCamera ? this : null)) == this && !RenderExcludeTags.HasAny(item.GameObject.Tags) && item.GetPanel() is RootPanel rootPanel && rootPanel.IsValid())
			{
				Rect screenSize = new Rect(0f, 0f, size.x, size.y);
				rootPanel.PreLayout(screenSize);
				rootPanel.CalculateLayout();
				rootPanel.PostLayout();
				rootPanel.BuildCommandList();
				flag = true;
			}
		}
		if (flag)
		{
			GlobalContext.Current.UISystem.CombineCommandLists();
		}
	}

	/// <summary>
	/// Add a custom camera effect (a <see cref="T:Sandbox.CameraEffectSystem.BaseEffect" /> subclass), targeted
	/// at this camera.
	/// </summary>
	[Description("Add a custom camera effect (a Sandbox.CameraEffectSystem.BaseEffect subclass), targeted at this camera.")]
	[SourceLocation("Scene\\Components\\Camera\\CameraComponent.Effects.cs", 14)]
	public T AddEffect<T>(T effect) where T : CameraEffectSystem.BaseEffect
	{
		if (effect == null)
		{
			return null;
		}
		effect.Camera = this;
		CameraEffectSystem cameraEffectSystem = GameObjectSystem<CameraEffectSystem>.Get(Scene);
		if (cameraEffectSystem == null)
		{
			return null;
		}
		return cameraEffectSystem.Add(effect);
	}

	/// <summary>
	/// Shake this camera - the classic screen shake (Half-Life's env_shake). Every
	/// 1/<paramref name="frequency" /> seconds a new random offset within <paramref name="amplitude" />
	/// world units, settling to nothing over <paramref name="duration" />. A duration of zero shakes
	/// until <see cref="M:Sandbox.CameraEffectSystem.BaseEffect.Stop" />.
	/// </summary>
	[Description("Shake this camera - the classic screen shake (Half-Life's env_shake). Every 1/<span style=\"color: #9CDCFE;\">frequency</span> seconds a new random offset within <span style=\"color: #9CDCFE;\">amplitude</span> world units, settling to nothing over <span style=\"color: #9CDCFE;\">duration</span>. A duration of zero shakes until Sandbox.CameraEffectSystem.BaseEffect.Stop.")]
	[SourceLocation("Scene\\Components\\Camera\\CameraComponent.Effects.cs", 29)]
	public CameraEffectSystem.BaseEffect AddShake(float amplitude, float frequency, float duration)
	{
		return GameObjectSystem<CameraEffectSystem>.Get(Scene)?.AddShake(this, amplitude, frequency, duration);
	}

	/// <summary>
	/// Punch this camera along a camera-local direction, oscillating and dying out -
	/// <see cref="F:Vector3.Up" /> bounces the view upward, <paramref name="frequency" /> is how many
	/// oscillations before it lapses.
	/// </summary>
	[Description("Punch this camera along a camera-local direction, oscillating and dying out - <span style=\"color: #86C691;\">Vector3</span>.<span style=\"color: #DCDCDC;\">Up</span> bounces the view upward, <span style=\"color: #9CDCFE;\">frequency</span> is how many oscillations before it lapses.")]
	[SourceLocation("Scene\\Components\\Camera\\CameraComponent.Effects.cs", 39)]
	public CameraEffectSystem.BaseEffect AddPunch(Vector3 direction, float amplitude, float frequency = 1f, float duration = 0.3f, float fovAmplitude = 0f)
	{
		return GameObjectSystem<CameraEffectSystem>.Get(Scene)?.AddPunch(this, direction, amplitude, frequency, duration, fovAmplitude);
	}

	/// <summary>
	/// Punch this camera's view angles - it kicks to <paramref name="angles" /> and bounces back,
	/// oscillating <paramref name="frequency" /> times before it lapses. Melee swings, landings,
	/// launches. Render-only - the player's aim never moves.
	/// </summary>
	[Description("Punch this camera's view angles - it kicks to <span style=\"color: #9CDCFE;\">angles</span> and bounces back, oscillating <span style=\"color: #9CDCFE;\">frequency</span> times before it lapses. Melee swings, landings, launches. Render-only - the player's aim never moves.")]
	[SourceLocation("Scene\\Components\\Camera\\CameraComponent.Effects.cs", 49)]
	public CameraEffectSystem.BaseEffect AddPunch(Angles angles, float frequency = 1f, float duration = 0.3f, float fovAmplitude = 0f)
	{
		return GameObjectSystem<CameraEffectSystem>.Get(Scene)?.AddPunch(this, angles, frequency, duration, fovAmplitude);
	}

	/// <summary>
	/// Tilt this camera by <paramref name="angle" />, eased in over <paramref name="easeTime" /> and
	/// back out before <paramref name="duration" /> ends.
	/// </summary>
	[Description("Tilt this camera by <span style=\"color: #9CDCFE;\">angle</span>, eased in over <span style=\"color: #9CDCFE;\">easeTime</span> and back out before <span style=\"color: #9CDCFE;\">duration</span> ends.")]
	[SourceLocation("Scene\\Components\\Camera\\CameraComponent.Effects.cs", 58)]
	public CameraEffectSystem.BaseEffect AddTilt(Angles angle, float duration, float easeTime = 0.2f)
	{
		return GameObjectSystem<CameraEffectSystem>.Get(Scene)?.AddTilt(this, angle, duration, easeTime);
	}

	/// <summary>
	/// Starts drawing on the camera after post processing. Bounds start at (0, 0) and use the camera's viewport size in pixels.
	/// Dispose the painter to append its drawing. Commands are reset at the start of each frame.
	/// Finish painting before recording other commands into the HUD command list.
	/// </summary>
	[Description("Starts drawing on the camera after post processing. Bounds start at (0, 0) and use the camera's viewport size in pixels. Dispose the painter to append its drawing. Commands are reset at the start of each frame. Finish painting before recording other commands into the HUD command list.")]
	[SourceLocation("Scene\\Components\\Camera\\CameraComponent.Hud.cs", 20)]
	public Painter BeginHud()
	{
		return Painter.Begin(_hudCommandList, new Rect(Vector2.Zero, ScreenRect.Size));
	}

	/// <summary>
	/// Starts drawing on the camera after UI. Bounds start at (0, 0) and use the camera's viewport size in pixels.
	/// Dispose the painter to append its drawing. Commands are reset at the start of each frame.
	/// Finish painting before recording other commands into the overlay command list.
	/// </summary>
	[Description("Starts drawing on the camera after UI. Bounds start at (0, 0) and use the camera's viewport size in pixels. Dispose the painter to append its drawing. Commands are reset at the start of each frame. Finish painting before recording other commands into the overlay command list.")]
	[SourceLocation("Scene\\Components\\Camera\\CameraComponent.Hud.cs", 35)]
	public Painter BeginOverlay()
	{
		return Painter.Begin(_overlayCommandList, new Rect(Vector2.Zero, ScreenRect.Size));
	}

	[SourceLocation("Scene\\Components\\Camera\\CameraComponent.Hud.cs", 47)]
	void ISceneStage.Start()
	{
		_hudCommandList.Reset();
		_overlayCommandList.Reset();
	}

	/// <summary>
	/// Whether this camera's post processing reads the depth-normals prepass's G-buffer (AO, SSR), so the managed scene
	/// renderer draws it.
	/// </summary>
	[Description("Whether this camera's post processing reads the depth-normals prepass's G-buffer (AO, SSR), so the managed scene renderer draws it.")]
	[SourceLocation("Scene\\Components\\Camera\\CameraComponent.PostProcess.cs", 13)]
	private bool WantsDepthNormals()
	{
		return PostProcess.NeedsDepthNormals;
	}

	/// <summary>
	/// Whether post processing at <paramref name="stage" /> can run on the async compute queue (<see cref="P:Sandbox.BasePostProcess.AsyncCompute" />).
	/// </summary>
	[Description("Whether post processing at <span style=\"color: #9CDCFE;\">stage</span> can run on the async compute queue (<span style=\"color: #4EC9B0;\">BasePostProcess</span>.<span style=\"color: #DCDCDC;\">AsyncCompute</span>).")]
	[SourceLocation("Scene\\Components\\Camera\\CameraComponent.PostProcess.cs", 18)]
	private bool HasAsyncCompute(Stage stage)
	{
		if (PostProcessSystem.EnablePostProcess)
		{
			return PostProcess.HasAsyncCompute(stage);
		}
		return false;
	}

	/// <summary>
	/// Run it, under the conditions the stage would (<c>PostProcessSystem.OnRenderStage</c>). On the render thread.
	/// </summary>
	[Description("Run it, under the conditions the stage would (<code style=\"color: #DCDCDC; background-color: #111111; padding: 4px;\">PostProcessSystem.OnRenderStage</code>). On the render thread.")]
	[SourceLocation("Scene\\Components\\Camera\\CameraComponent.PostProcess.cs", 23)]
	private void RenderAsyncCompute(Stage stage)
	{
		if (PostProcessSystem.EnablePostProcess && Graphics.PostProcessEnabled)
		{
			PostProcess.RenderAsyncCompute(stage);
		}
	}

	[SourceLocation("Scene\\Components\\Camera\\CameraComponent.PostProcess.cs", 43)]
	internal void PrintPostProcessDebugOverlay(ref Vector2 pos, Painter painter)
	{
		string text = "";
		foreach (KeyValuePair<Stage, List<PostProcessLayer>> item in PostProcess.Layers.OrderBy((KeyValuePair<Stage, List<PostProcessLayer>> x) => x.Key))
		{
			text += $"{item.Key}\n";
			foreach (PostProcessLayer item2 in item.Value.OrderBy((PostProcessLayer x) => x.Order))
			{
				text += $"\t{item2.Order,6:D}: {item2.Name}\n";
			}
		}
		TextRendering.Scope scope = TextRendering.Scope.Default;
		scope.Text = text;
		scope.FontSize = 11f;
		scope.FontName = "Roboto Mono";
		scope.FontWeight = 600;
		scope.Outline = new TextRendering.Outline
		{
			Enabled = true,
			Color = Color.Black.WithAlpha(0.9f),
			Size = 3f
		};
		scope.Shadow = new TextRendering.Shadow
		{
			Enabled = true,
			Color = Color.Black.WithAlpha(0.5f),
			Offset = 0.0,
			Size = 2f
		};
		pos.y = Sandbox.DebugOverlay.DrawText(painter, in scope, pos).Bottom;
	}
}
