using System;
using System.Collections.Generic;
using System.Linq;
using NativeEngine;
using Sandbox;
using Sandbox.Engine.Settings;

namespace Editor;

/// <summary>
/// Render a scene to a native widget. This replaces NativeRenderingWidget. 
/// </summary>
public class SceneRenderingWidget : Frame
{
	private static readonly HashSet<SceneRenderingWidget> All = new HashSet<SceneRenderingWidget>();

	internal SwapChainHandle_t SwapChain;

	private bool renderingStopped;

	private bool _sizeLockedForRecording;

	private Vector2 _savedMinSize;

	private Vector2 _savedMaxSize;

	/// <summary>
	/// The active scene that we're rendering
	/// </summary>
	public Scene Scene { get; set; }

	/// <summary>
	/// The camera to render from. We will fallback to Scene.Camera if this is null
	/// </summary>
	public CameraComponent Camera { get; set; }

	/// <summary>
	/// This widget manages it's own gizmo instance.
	/// </summary>
	public Gizmo.Instance GizmoInstance { get; private set; } = new Gizmo.Instance();

	public bool EnableEngineOverlays { get; set; }

	/// <summary>
	/// Return a ray for the current cursor position
	/// </summary>
	public Ray CursorRay => GetRay(Application.CursorPosition - ScreenPosition);

	/// <inheritdoc cref="M:Editor.SceneRenderingWidget.PreFrame" />
	public event Action OnPreFrame;

	public SceneRenderingWidget(Widget parent = null)
		: base(parent)
	{
		SetFlag(Flag.WA_NativeWindow, b: true);
		SetFlag(Flag.WA_PaintOnScreen, b: true);
		SetFlag(Flag.WA_NoSystemBackground, b: true);
		SetFlag(Flag.WA_OpaquePaintEvent, b: true);
		OnPaintOverride = () => true;
		SwapChain = WidgetUtil.CreateSwapChain(_widget, RenderSettings.Instance.AntiAliasQuality.ToEngine());
		RenderSettings.Instance.OnVideoSettingsChanged += HandleVideoChanged;
		FocusMode = FocusMode.Click;
		All.Add(this);
	}

	internal override void OnDestroyingLater()
	{
		ReleaseSwapChain();
		base.OnDestroyingLater();
	}

	internal override void NativeDestroying()
	{
		ReleaseSwapChain();
	}

	internal static void ShutdownRendering()
	{
		SceneRenderingWidget[] array = All.ToArray();
		for (int i = 0; i < array.Length; i++)
		{
			array[i].ReleaseSwapChain();
		}
	}

	private void ReleaseSwapChain()
	{
		if (!renderingStopped)
		{
			renderingStopped = true;
			if (GameMode.IsPlayWidget(this))
			{
				GameMode.ClearPlayMode();
			}
			RenderSettings.Instance.OnVideoSettingsChanged -= HandleVideoChanged;
			if ((nint)SwapChain != 0L)
			{
				g_pRenderDevice.Flush();
				g_pRenderDevice.ForceFlushGPU(SwapChain);
				g_pRenderDevice.DestroySwapChain(SwapChain);
				SwapChain = default;
			}
		}
	}

	internal override void NativeShutdown()
	{
		base.NativeShutdown();
		All.Remove(this);
		GizmoInstance?.Dispose();
		GizmoInstance = null;
	}

	/// <summary>
	/// Create a hidden scene editor camera, post processing will be copied from a main camera in the scene.
	/// </summary>
	public CameraComponent CreateSceneEditorCamera()
	{
		if (Scene == null)
		{
			return null;
		}
		using (Scene.Push())
		{
			CameraComponent cameraComponent = new GameObject(enabled: true, "editor_camera")
			{
				Flags = (GameObjectFlags.Hidden | GameObjectFlags.NotSaved | GameObjectFlags.EditorOnly | GameObjectFlags.Absolute)
			}.AddComponent<CameraComponent>();
			cameraComponent.RenderExcludeTags.Add("hidden");
			cameraComponent.IsMainCamera = false;
			cameraComponent.IsSceneEditorCamera = true;
			return cameraComponent;
		}
	}

	private void RenderScene()
	{
		if (this.IsValid() && (nint)SwapChain != 0L)
		{
			SceneCamera sceneCamera = GetSceneCamera();
			if (sceneCamera != null)
			{
				sceneCamera.EnableEngineOverlays = EnableEngineOverlays;
			}
			if (sceneCamera != null && IsFocused)
			{
				SceneCamera.RecordingCamera = sceneCamera;
			}
			if (ScreenRecorder.IsRecording() && sceneCamera != null && sceneCamera.IsRecordingCamera && !_sizeLockedForRecording)
			{
				_savedMinSize = MinimumSize;
				_savedMaxSize = MaximumSize;
				MinimumSize = Size;
				MaximumSize = Size;
				_sizeLockedForRecording = true;
			}
			else if (!ScreenRecorder.IsRecording() && _sizeLockedForRecording)
			{
				MinimumSize = _savedMinSize;
				MaximumSize = _savedMaxSize;
				_sizeLockedForRecording = false;
			}
			if (Camera.IsValid())
			{
				Camera.Scene?.PreCameraRender();
				Camera.AddToRenderList(SwapChain, Size * DpiScale);
			}
			else if (Scene.IsValid())
			{
				Scene.Render(SwapChain, Size * DpiScale);
			}
		}
	}

	/// <summary>
	/// Called just before rendering.
	/// </summary>
	protected virtual void PreFrame()
	{
		OnPreFrame?.Invoke();
	}

	/// <summary>
	/// Update common inputs for gizmo.
	/// </summary>
	public void UpdateGizmoInputs(bool hasMouseFocus = true)
	{
		SceneCamera sceneCamera = GetSceneCamera();
		if (sceneCamera != null)
		{
			UpdateGizmoInputs(ref GizmoInstance.Input, sceneCamera, hasMouseFocus);
		}
	}

	private void Render()
	{
		if (!Scene.IsValid() || !Visible || (nint)SwapChain == 0L)
		{
			return;
		}
		using (Scene.Push())
		{
			using (GizmoInstance.Push())
			{
				PreFrame();
				RenderScene();
			}
		}
		if ((nint)SwapChain != 0L)
		{
			if (GameMode.IsPlayWidget(this))
			{
				CCameraRenderer.RenderOverlay(SwapChain);
			}
			g_pRenderDevice.Present(SwapChain);
		}
	}

	private void UpdateGizmoInputs(ref Gizmo.Inputs input, SceneCamera camera, bool hasMouseFocus)
	{
		ArgumentNullException.ThrowIfNull(camera, "camera");
		input.Camera = camera;
		input.Modifiers = Application.KeyboardModifiers;
		if (!hasMouseFocus)
		{
			input.CursorRay = default;
			return;
		}
		input.CursorPosition = Application.CursorPosition;
		input.LeftMouse = Application.MouseButtons.HasFlag(MouseButtons.Left);
		input.RightMouse = Application.MouseButtons.HasFlag(MouseButtons.Right);
		input.CursorPosition -= ScreenPosition;
		input.CursorRay = camera.GetRay(input.CursorPosition, Size);
		if (!input.IsHovered)
		{
			input.LeftMouse = false;
			input.RightMouse = false;
		}
	}

	private SceneCamera GetSceneCamera()
	{
		if (Camera.IsValid())
		{
			return Camera.SceneCamera;
		}
		if (!Scene.IsValid())
		{
			return null;
		}
		if (!Scene.Camera.IsValid())
		{
			return null;
		}
		return Scene.Camera.SceneCamera;
	}

	/// <summary>
	/// Given a local widget position, return a Ray
	/// </summary>
	public Ray GetRay(Vector2 localPosition)
	{
		return GetSceneCamera()?.GetRay(localPosition, Size) ?? default(Ray);
	}

	internal void HandleVideoChanged()
	{
		if (!renderingStopped)
		{
			RenderMultisampleType nMSAAAmount = RenderSettings.Instance.AntiAliasQuality.ToEngine();
			if ((nint)SwapChain == 0L)
			{
				SwapChain = WidgetUtil.CreateSwapChain(_widget, nMSAAAmount);
			}
			else
			{
				WidgetUtil.UpdateSwapChainMSAA(SwapChain, nMSAAAmount);
			}
		}
	}

	internal static void RenderAll()
	{
		foreach (SceneRenderingWidget item in All)
		{
			if (item.Visible)
			{
				item.Render();
			}
		}
	}
}
