using System;
using System.IO;
using System.Reflection;
using System.Runtime.CompilerServices;
using Sandbox.Internal;
using Sandbox.VR;

namespace Sandbox.Rendering;

/// <summary>
/// Cameras render their scene's world through the managed scene renderer when <c>r_managed_scene</c> is on. The
/// managed renderer owns the camera's whole frame: native's post processing, UI and command lists don't run for
/// it, and engine overlays (the console, debug overlays) are drawn over it afterwards. See
/// docs/managed/scene-renderer.md, <i>The GameObject bridge</i>.
/// </summary>
[Description("Cameras render their scene's world through the managed scene renderer when <code style=\"color: #DCDCDC; background-color: #111111; padding: 4px;\">r_managed_scene</code> is on. The managed renderer owns the camera's whole frame: native's post processing, UI and command lists don't run for it, and engine overlays (the console, debug overlays) are drawn over it afterwards. See docs/managed/scene-renderer.md, <i>The GameObject bridge</i>.")]
[SourceLocation("Systems\\Render\\ManagedScene\\ManagedFrameCounters.cs", 62)]
[SourceLocation("Systems\\Render\\ManagedScene\\ManagedSceneRendering.cs", 54)]
internal static class ManagedSceneRendering
{
	[SourceLocation("Systems\\Render\\ManagedScene\\ManagedFrameCounters.cs", 64)]
	private static ManagedFrameCounters thisFrame;

	[SourceLocation("Systems\\Render\\ManagedScene\\ManagedSceneRendering.cs", 76)]
	private static bool loadTried;

	[SourceLocation("Systems\\Render\\ManagedScene\\ManagedSceneRendering.cs", 154)]
	private static string pendingCompare;

	[SourceLocation("Systems\\Render\\ManagedScene\\ManagedSceneRendering.cs", 155)]
	private static int pendingFrames;

	[SourceLocation("Systems\\Render\\ManagedScene\\ManagedSceneRendering.cs", 156)]
	private static bool quitAfterCompare;

	/// <summary>
	/// How many camera renders before a compare native renders the camera as well (<see cref="M:Sandbox.Rendering.ManagedSceneRendering.TryRender(Sandbox.CameraComponent,SwapChainHandle_t,System.Nullable{Vector2})" />): enough for
	/// volumetric fog's temporal history to settle.
	/// </summary>
	[SourceLocation("Systems\\Render\\ManagedScene\\ManagedSceneRendering.cs", 162)]
	private const int CompareWarmFrames = 120;

	[SourceLocation("Systems\\Render\\ManagedScene\\ManagedSceneRendering.cs", 191)]
	private static CameraComponent compareCamera;

	[SourceLocation("Systems\\Render\\ManagedScene\\ManagedSceneRendering.cs", 192)]
	private static string compareFolder;

	[SkipHotload]
	private static Action<bool> __Enabled_ConVarAttribute__CachedSetter = null;

	[SkipHotload]
	private static Func<bool> __Enabled_ConVarAttribute__CachedSetterGetter = null;

	[SkipHotload]
	private static Func<bool> __Enabled_ConVarAttribute__CachedGetter = null;

	[SkipHotload]
	private static readonly Attribute[] __Enabled__Attrs = new Attribute[2]
	{
		new ConVarAttribute("r_managed_scene", ConVarFlags.Protected)
		{
			Help = "Render cameras through the managed scene renderer (experimental: no post processing, UI, particles, decals or map geometry yet)"
		},
		new ConVarAttribute("r_managed_scene", ConVarFlags.Protected)
		{
			Help = "Render cameras through the managed scene renderer (experimental: no post processing, UI, particles, decals or map geometry yet)"
		}
	};

	[SkipHotload]
	private static Action<bool> __AsyncCompute_ConVarAttribute__CachedSetter = null;

	[SkipHotload]
	private static Func<bool> __AsyncCompute_ConVarAttribute__CachedSetterGetter = null;

	[SkipHotload]
	private static Func<bool> __AsyncCompute_ConVarAttribute__CachedGetter = null;

	[SkipHotload]
	private static readonly Attribute[] __AsyncCompute__Attrs = new Attribute[2]
	{
		new ConVarAttribute("r_managed_async_compute")
		{
			Help = "Run the managed scene renderer's depth chain, contact shadows and AO on the async compute queue, beside shadow rendering"
		},
		new ConVarAttribute("r_managed_async_compute")
		{
			Help = "Run the managed scene renderer's depth chain, contact shadows and AO on the async compute queue, beside shadow rendering"
		}
	};

	/// <summary>
	/// What the managed renderer did last frame. <see cref="F:Sandbox.Rendering.ManagedFrameCounters.Renders" /> is 0 when every camera rendered
	/// natively.
	/// </summary>
	[Description("What the managed renderer did last frame. <span style=\"color: #86C691;\">ManagedFrameCounters</span>.<span style=\"color: #DCDCDC;\">Renders</span> is 0 when every camera rendered natively.")]
	[SourceLocation("Systems\\Render\\ManagedScene\\ManagedFrameCounters.cs", 70)]
	public static ManagedFrameCounters LastFrame { get; private set; }

	/// <summary>
	/// Render cameras through Sandbox.SceneRenderer. Experimental: it draws models, skinned models, lights,
	/// environment probes, fog and ambient, and nothing else yet.
	/// </summary>
	[ConVar("r_managed_scene", ConVarFlags.Protected, Help = "Render cameras through the managed scene renderer (experimental: no post processing, UI, particles, decals or map geometry yet)")]
	[Description("Render cameras through Sandbox.SceneRenderer. Experimental: it draws models, skinned models, lights, environment probes, fog and ambient, and nothing else yet.")]
	[SourceLocation("Systems\\Render\\ManagedScene\\ManagedSceneRendering.cs", 60)]
	public static bool Enabled
	{
		get
		{
			WrappedPropertyGet<bool> p = new WrappedPropertyGet<bool>
			{
				Value = ((Func<bool>)(() => field))(),
				Object = null,
				IsStatic = true,
				TypeName = "Sandbox.Rendering.ManagedSceneRendering",
				PropertyName = "Enabled",
				MemberIdent = 867991221,
				Attributes = __Enabled__Attrs
			};
			return ConsoleSystem.OnWrappedGet(in p);
		}
		set
		{
			WrappedPropertySet<bool> p = new WrappedPropertySet<bool>
			{
				Value = value,
				Object = null,
				Setter = (bool v) =>
				{
					field = v;
				},
				Getter = () => Enabled,
				IsStatic = true,
				TypeName = "Sandbox.Rendering.ManagedSceneRendering",
				PropertyName = "Enabled",
				MemberIdent = 867991221,
				Attributes = __Enabled__Attrs
			};
			ConsoleSystem.OnWrappedSet(in p);
		}
	}

	/// <summary>
	/// Run the managed renderer's compute (the depth chain, contact shadows, and AO's command list) on the async compute queue
	/// beside the shadow maps, where the device has one. It saved 0.22 ms of a 6.3 ms frame at 4K, and 0.45 ms with AO
	/// (SceneLab's Heavy Scene, 2026-09-27).
	/// </summary>
	[ConVar("r_managed_async_compute", ConVarFlags.None, Help = "Run the managed scene renderer's depth chain, contact shadows and AO on the async compute queue, beside shadow rendering")]
	[DefaultValue(true)]
	[Description("Run the managed renderer's compute (the depth chain, contact shadows, and AO's command list) on the async compute queue beside the shadow maps, where the device has one. It saved 0.22 ms of a 6.3 ms frame at 4K, and 0.45 ms with AO (SceneLab's Heavy Scene, 2026-09-27).")]
	[SourceLocation("Systems\\Render\\ManagedScene\\ManagedSceneRendering.cs", 68)]
	public static bool AsyncCompute
	{
		get
		{
			WrappedPropertyGet<bool> p = new WrappedPropertyGet<bool>
			{
				Value = ((Func<bool>)(() => field))(),
				Object = null,
				IsStatic = true,
				TypeName = "Sandbox.Rendering.ManagedSceneRendering",
				PropertyName = "AsyncCompute",
				MemberIdent = -1132780126,
				Attributes = __AsyncCompute__Attrs
			};
			return ConsoleSystem.OnWrappedGet(in p);
		}
		set
		{
			WrappedPropertySet<bool> p = new WrappedPropertySet<bool>
			{
				Value = value,
				Object = null,
				Setter = (bool v) =>
				{
					field = v;
				},
				Getter = () => AsyncCompute,
				IsStatic = true,
				TypeName = "Sandbox.Rendering.ManagedSceneRendering",
				PropertyName = "AsyncCompute",
				MemberIdent = -1132780126,
				Attributes = __AsyncCompute__Attrs
			};
			ConsoleSystem.OnWrappedSet(in p);
		}
	} = true;

	/// <summary>
	/// Set by Sandbox.SceneRenderer's module initializer when the assembly loads.
	/// </summary>
	[Description("Set by Sandbox.SceneRenderer's module initializer when the assembly loads.")]
	[SourceLocation("Systems\\Render\\ManagedScene\\ManagedSceneRendering.cs", 74)]
	public static IManagedSceneRenderer Renderer { get; set; }

	/// <summary>
	/// Add a camera's frame - called by the managed renderer on the main thread, after each frame it renders.
	/// </summary>
	[Description("Add a camera's frame - called by the managed renderer on the main thread, after each frame it renders.")]
	[SourceLocation("Systems\\Render\\ManagedScene\\ManagedFrameCounters.cs", 75)]
	internal static void Report(in ManagedFrameCounters counters)
	{
		thisFrame.Add(in counters);
	}

	/// <summary>
	/// Called once a frame, before the overlays draw: what was reported since the last call becomes <see cref="P:Sandbox.Rendering.ManagedSceneRendering.LastFrame" />.
	/// </summary>
	[Description("Called once a frame, before the overlays draw: what was reported since the last call becomes <span style=\"color: #4EC9B0;\">ManagedSceneRendering</span>.<span style=\"color: #DCDCDC;\">LastFrame</span>.")]
	[SourceLocation("Systems\\Render\\ManagedScene\\ManagedFrameCounters.cs", 80)]
	internal static void EndFrame()
	{
		LastFrame = thisFrame;
		thisFrame = default;
	}

	/// <summary>
	/// Called at engine shutdown: the managed renderer frees what it holds while native is still there.
	/// </summary>
	[Description("Called at engine shutdown: the managed renderer frees what it holds while native is still there.")]
	[SourceLocation("Systems\\Render\\ManagedScene\\ManagedSceneRendering.cs", 81)]
	internal static void Shutdown()
	{
		Renderer?.Shutdown();
		Renderer = null;
	}

	/// <summary>
	/// Called when a camera is destroyed: the managed renderer frees what it made for it, if it's loaded.
	/// </summary>
	[Description("Called when a camera is destroyed: the managed renderer frees what it made for it, if it's loaded.")]
	[SourceLocation("Systems\\Render\\ManagedScene\\ManagedSceneRendering.cs", 90)]
	internal static void Forget(CameraComponent camera)
	{
		Renderer?.Forget(camera);
	}

	/// <summary>
	/// Called when a scene world is deleted: the managed renderer frees its mirror of it, if it's loaded.
	/// </summary>
	[Description("Called when a scene world is deleted: the managed renderer frees its mirror of it, if it's loaded.")]
	[SourceLocation("Systems\\Render\\ManagedScene\\ManagedSceneRendering.cs", 95)]
	internal static void Forget(SceneWorld world)
	{
		Renderer?.Forget(world);
	}

	/// <summary>
	/// The managed renderer, loading its assembly the first time it's wanted. Null if it isn't there.
	/// </summary>
	[Description("The managed renderer, loading its assembly the first time it's wanted. Null if it isn't there.")]
	[SourceLocation("Systems\\Render\\ManagedScene\\ManagedSceneRendering.cs", 100)]
	private static IManagedSceneRenderer Load()
	{
		if (Renderer != null || loadTried)
		{
			return Renderer;
		}
		loadTried = true;
		try
		{
			RuntimeHelpers.RunModuleConstructor(Assembly.Load("Sandbox.SceneRenderer").ManifestModule.ModuleHandle);
		}
		catch (Exception ex)
		{
			GlobalSystemNamespace.Log.Warning(ex, $"r_managed_scene: couldn't load Sandbox.SceneRenderer - {ex.Message}");
		}
		if (Renderer == null)
		{
			GlobalSystemNamespace.Log.Warning("r_managed_scene: Sandbox.SceneRenderer didn't register a renderer");
		}
		return Renderer;
	}

	/// <summary>
	/// Render a camera through the managed renderer, if it's on and can. Called where the camera would add itself
	/// to native's render list.
	/// </summary>
	[Description("Render a camera through the managed renderer, if it's on and can. Called where the camera would add itself to native's render list.")]
	[SourceLocation("Systems\\Render\\ManagedScene\\ManagedSceneRendering.cs", 123)]
	internal static bool TryRender(CameraComponent camera, SwapChainHandle_t swapChain, Vector2? size)
	{
		if (pendingCompare != null)
		{
			RunPendingCompare(camera);
		}
		if (!Enabled)
		{
			return false;
		}
		if (VRSystem.IsActive && camera.TargetEye != StereoTargetEye.None)
		{
			return false;
		}
		IManagedSceneRenderer managedSceneRenderer = Load();
		if (managedSceneRenderer == null)
		{
			return false;
		}
		bool flag = pendingCompare != null && pendingFrames < 120;
		Texture renderTarget = camera.RenderTarget;
		if (renderTarget != null && renderTarget.native.IsValid)
		{
			if (managedSceneRenderer.RenderToTexture(camera, renderTarget))
			{
				return !flag;
			}
			return false;
		}
		RenderDeviceInfo_t swapChainInfo = g_pRenderDevice.GetSwapChainInfo(swapChain);
		Vector2 size2 = size ?? new Vector2(swapChainInfo.m_DisplayMode.m_nWidth, swapChainInfo.m_DisplayMode.m_nHeight);
		if (!managedSceneRenderer.Render(camera, swapChain, size2))
		{
			return false;
		}
		if (flag)
		{
			return false;
		}
		if (camera.SceneCamera.EnableEngineOverlays)
		{
			CCameraRenderer.RenderOverlay(swapChain);
		}
		return true;
	}

	/// <summary>
	/// Compare the managed renderer with native on the next camera that renders, a few frames from now so the
	/// scene has loaded: both frames and a diff go to <c>screenshots/managed_scene</c>, and the parity numbers to
	/// the console. <c>quit</c> exits afterwards, for scripts.
	/// </summary>
	[ConCmd("r_managed_scene_compare", ConVarFlags.Protected, Help = "Render the next camera through native and the managed scene renderer and compare them: r_managed_scene_compare [frames to wait] [quit]")]
	[Description("Compare the managed renderer with native on the next camera that renders, a few frames from now so the scene has loaded: both frames and a diff go to <code style=\"color: #DCDCDC; background-color: #111111; padding: 4px;\">screenshots/managed_scene</code>, and the parity numbers to the console. <code style=\"color: #DCDCDC; background-color: #111111; padding: 4px;\">quit</code> exits afterwards, for scripts.")]
	[SourceLocation("Systems\\Render\\ManagedScene\\ManagedSceneRendering.cs", 169)]
	internal static void Compare(int frames = 30, string then = "")
	{
		pendingCompare = Path.Combine(Environment.CurrentDirectory, "screenshots", "managed_scene");
		pendingFrames = Math.Max(0, frames);
		quitAfterCompare = then.Equals("quit", StringComparison.OrdinalIgnoreCase);
		GlobalSystemNamespace.Log.Info($"r_managed_scene_compare: comparing the next camera in {pendingFrames} frames");
	}

	[SourceLocation("Systems\\Render\\ManagedScene\\ManagedSceneRendering.cs", 178)]
	private static void RunPendingCompare(CameraComponent camera)
	{
		if (pendingFrames-- <= 0)
		{
			string text = pendingCompare;
			pendingCompare = null;
			compareCamera = camera;
			compareFolder = text;
		}
	}

	/// <summary>
	/// Called at the start of a frame's output, before any views render - where a queued compare runs.
	/// </summary>
	[Description("Called at the start of a frame's output, before any views render - where a queued compare runs.")]
	[SourceLocation("Systems\\Render\\ManagedScene\\ManagedSceneRendering.cs", 197)]
	internal static void BeforeRenderingViews()
	{
		if (compareCamera != null)
		{
			CameraComponent camera = compareCamera;
			string folder = compareFolder;
			compareCamera = null;
			compareFolder = null;
			RunCompare(camera, folder);
		}
	}

	[SourceLocation("Systems\\Render\\ManagedScene\\ManagedSceneRendering.cs", 209)]
	private static void RunCompare(CameraComponent camera, string folder)
	{
		IManagedSceneRenderer managedSceneRenderer = Load();
		if (managedSceneRenderer == null)
		{
			GlobalSystemNamespace.Log.Warning("r_managed_scene_compare: no managed renderer");
		}
		else if (!camera.IsValid())
		{
			GlobalSystemNamespace.Log.Warning("r_managed_scene_compare: the camera went away");
		}
		else
		{
			Directory.CreateDirectory(folder);
			GlobalSystemNamespace.Log.Info($"r_managed_scene_compare: {managedSceneRenderer.Compare(camera, folder)}");
		}
		if (quitAfterCompare)
		{
			ConVarSystem.Run("quit");
		}
	}
}
