using System;
using System.Collections.Concurrent;
using System.IO;
using NativeEngine;
using Sandbox.Engine.Settings;
using Sandbox.Internal;
using Sandbox.Rendering;
using Sandbox.Services;
using Sandbox.UI;

namespace Sandbox;

/// <summary>
/// Provides functionality to capture and save screenshots in various formats.
/// </summary>
[Description("Provides functionality to capture and save screenshots in various formats.")]
[SourceLocation("Systems\\Render\\Multimedia\\ScreenshotService.cs", 12)]
internal static class ScreenshotService
{
	private record ScreenshotRequest(string FilePath);

	[SourceLocation("Systems\\Render\\Multimedia\\ScreenshotService.cs", 19)]
	private static readonly ConcurrentQueue<ScreenshotRequest> _pendingRequests = new ConcurrentQueue<ScreenshotRequest>();

	[SkipHotload]
	private static Action<string> __ScreenshotPrefix_ConVarAttribute__CachedSetter = null;

	[SkipHotload]
	private static Func<string> __ScreenshotPrefix_ConVarAttribute__CachedSetterGetter = null;

	[SkipHotload]
	private static Func<string> __ScreenshotPrefix_ConVarAttribute__CachedGetter = null;

	[SkipHotload]
	private static readonly Attribute[] __ScreenshotPrefix__Attrs = new Attribute[2]
	{
		new ConVarAttribute("screenshot_prefix")
		{
			Help = "Prefix for auto-generated screenshot filenames"
		},
		new ConVarAttribute("screenshot_prefix")
		{
			Help = "Prefix for auto-generated screenshot filenames"
		}
	};

	[ConVar("screenshot_prefix", ConVarFlags.None, Help = "Prefix for auto-generated screenshot filenames")]
	[DefaultValue("sbox")]
	[SourceLocation("Systems\\Render\\Multimedia\\ScreenshotService.cs", 14)]
	public static string ScreenshotPrefix
	{
		get
		{
			WrappedPropertyGet<string> p = new WrappedPropertyGet<string>
			{
				Value = ((Func<string>)(() => field))(),
				Object = null,
				IsStatic = true,
				TypeName = "Sandbox.ScreenshotService",
				PropertyName = "ScreenshotPrefix",
				MemberIdent = -611701555,
				Attributes = __ScreenshotPrefix__Attrs
			};
			return ConsoleSystem.OnWrappedGet(in p);
		}
		set
		{
			WrappedPropertySet<string> p = new WrappedPropertySet<string>
			{
				Value = value,
				Object = null,
				Setter = (string v) =>
				{
					field = v;
				},
				Getter = () => ScreenshotPrefix,
				IsStatic = true,
				TypeName = "Sandbox.ScreenshotService",
				PropertyName = "ScreenshotPrefix",
				MemberIdent = -611701555,
				Attributes = __ScreenshotPrefix__Attrs
			};
			ConsoleSystem.OnWrappedSet(in p);
		}
	} = "sbox";

	/// <summary>
	/// Captures the screen and saves it as a PNG file.
	/// </summary>
	[Description("Captures the screen and saves it as a PNG file.")]
	[SourceLocation("Systems\\Render\\Multimedia\\ScreenshotService.cs", 24)]
	internal static string RequestCapture()
	{
		string text = ScreenCaptureUtility.GenerateScreenshotFilename("png");
		_pendingRequests.Enqueue(new ScreenshotRequest(text));
		return text;
	}

	[SourceLocation("Systems\\Render\\Multimedia\\ScreenshotService.cs", 33)]
	internal static void ProcessFrame(IRenderContext context, ITexture nativeTexture)
	{
		if (!nativeTexture.IsNull && nativeTexture.IsStrongHandleValid())
		{
			ScreenshotRequest result;
			while (_pendingRequests.TryDequeue(out result))
			{
				CaptureRenderTexture(context, nativeTexture, result.FilePath);
			}
		}
	}

	/// <summary>
	/// Captures the current render target and saves it to the specified file.
	/// </summary>
	[Description("Captures the current render target and saves it to the specified file.")]
	[SourceLocation("Systems\\Render\\Multimedia\\ScreenshotService.cs", 47)]
	private static void CaptureRenderTexture(IRenderContext context, ITexture nativeTexture, string filePath)
	{
		try
		{
			Bitmap bitmap = null;
			context.ReadTextureAsync(nativeTexture, (Span<byte> pData, ImageFormat format, int mipLevel, int width, int height, Action _) =>
			{
				try
				{
					bitmap = new Bitmap(width, height);
					pData.CopyTo(bitmap.GetBuffer());
					Screenshots.AddScreenshotToLibrary(bitmap.ToFormat(ImageFormat.RGB888), width, height);
					string directoryName = Path.GetDirectoryName(filePath);
					if (directoryName != null)
					{
						Directory.CreateDirectory(directoryName);
					}
					byte[] bytes = bitmap.ToPng();
					File.WriteAllBytes(filePath, bytes);
				}
				catch (Exception ex2)
				{
					GlobalSystemNamespace.Log.Error($"Error creating bitmap from texture: {ex2.Message}");
				}
			});
			GlobalSystemNamespace.Log.Info($"Screenshot saved to: {filePath}");
		}
		catch (Exception ex)
		{
			GlobalSystemNamespace.Log.Error($"Error capturing screenshot: {ex.Message}");
		}
	}

	[SourceLocation("Systems\\Render\\Multimedia\\ScreenshotService.cs", 86)]
	public static void TakeHighResScreenshot(Scene scene, int width, int height)
	{
		if (!scene.IsValid())
		{
			GlobalSystemNamespace.Log.Warning("No valid scene available for high-res screenshot.");
			return;
		}
		Vector2 vector = new Vector2(width, height);
		if (width <= 0 || height <= 0)
		{
			GlobalSystemNamespace.Log.Warning("screenshot_highres requires width and height greater than zero.");
			return;
		}
		if (width > 16384 || height > 16384)
		{
			GlobalSystemNamespace.Log.Warning($"screenshot_highres maximum dimension is {16384}px.");
			return;
		}
		CameraComponent camera = scene.Camera;
		if (camera == null || !camera.IsValid())
		{
			GlobalSystemNamespace.Log.Warning("Active scene does not have a main camera to capture from.");
			return;
		}
		Bitmap bitmap = null;
		RenderTarget renderTarget = null;
		Vector2? customSize = camera.CustomSize;
		Vector2 size = Screen.Size;
		bool flag = size != vector;
		try
		{
			if (flag)
			{
				Screen.Size = vector;
			}
			camera.CustomSize = vector;
			ResizeUI(camera, vector);
			renderTarget = RenderTarget.GetTemporary(width, height, ImageFormat.Default, ImageFormat.Default, RenderSettings.Instance.AntiAliasQuality, 1, "HighResScreenshot");
			if (renderTarget == null)
			{
				GlobalSystemNamespace.Log.Warning("Failed to create render target for high-res screenshot.");
				return;
			}
			if (!camera.RenderToTexture(renderTarget.ColorTarget, default(ViewSetup)))
			{
				GlobalSystemNamespace.Log.Warning("Camera failed to render to texture for high-res screenshot.");
				return;
			}
			bitmap = renderTarget.ColorTarget.GetBitmap();
			if (bitmap == null || !bitmap.IsValid)
			{
				GlobalSystemNamespace.Log.Warning("Failed to read pixels from render target for high-res screenshot.");
				return;
			}
			string text = ScreenCaptureUtility.GenerateScreenshotFilename("png");
			string directoryName = Path.GetDirectoryName(text);
			if (!string.IsNullOrEmpty(directoryName))
			{
				Directory.CreateDirectory(directoryName);
			}
			byte[] bytes = bitmap.ToPng();
			File.WriteAllBytes(text, bytes);
			GlobalSystemNamespace.Log.Info($"High-res screenshot saved to: {text} ({width}x{height})");
		}
		catch (Exception ex)
		{
			GlobalSystemNamespace.Log.Error($"Failed to capture high-res screenshot: {ex.Message}");
		}
		finally
		{
			camera.CustomSize = customSize;
			renderTarget?.Dispose();
			bitmap?.Dispose();
			if (flag)
			{
				Screen.Size = size;
				ResizeUI(camera, size);
			}
			if (camera.IsValid())
			{
				camera.InitializeRendering();
			}
		}
	}

	[SourceLocation("Systems\\Render\\Multimedia\\ScreenshotService.cs", 191)]
	private static void ResizeUI(CameraComponent camera, Vector2 size)
	{
		if (!camera.IsValid() || !camera.Scene.IsValid())
		{
			return;
		}
		foreach (ScreenPanel item in camera.Scene.GetAll<ScreenPanel>())
		{
			if (item.IsValid() && item.Active && (item.TargetCamera ?? (camera.IsMainCamera ? camera : null)) == camera && !camera.RenderExcludeTags.HasAny(item.GameObject.Tags) && item.GetPanel() is RootPanel rootPanel && rootPanel.IsValid() && (rootPanel.PanelBounds.Width != size.x || rootPanel.PanelBounds.Height != size.y))
			{
				Rect screenSize = new Rect(0f, 0f, size.x, size.y);
				rootPanel.PreLayout(screenSize);
				rootPanel.CalculateLayout();
				rootPanel.PostLayout();
				rootPanel.BuildCommandList();
			}
		}
	}
}
