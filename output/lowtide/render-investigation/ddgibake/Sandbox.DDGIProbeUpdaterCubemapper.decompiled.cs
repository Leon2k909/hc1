using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading;
using System.Threading.Tasks;
using Editor;
using Sandbox.Diagnostics;
using Sandbox.Internal;
using Sandbox.Rendering;

namespace Sandbox;

/// <summary>
/// Probe updater implementation using Cubermapper for probe radiance collection.
/// </summary>
[Description("Probe updater implementation using Cubermapper for probe radiance collection.")]
[SourceLocation("Scene\\Components\\IndirectLighting\\DDGIVolumeUpdater.cs", 9)]
internal class DDGIProbeUpdaterCubemapper : IDisposable
{
	[SourceLocation("Scene\\Components\\IndirectLighting\\DDGIVolumeUpdater.cs", 11)]
	private readonly IndirectLightVolume _volume;

	[SourceLocation("Scene\\Components\\IndirectLighting\\DDGIVolumeUpdater.cs", 12)]
	private readonly SceneCamera _camera;

	[SourceLocation("Scene\\Components\\IndirectLighting\\DDGIVolumeUpdater.cs", 13)]
	private List<Vector3Int> _pendingProbes;

	[SourceLocation("Scene\\Components\\IndirectLighting\\DDGIVolumeUpdater.cs", 14)]
	private Texture _captureTexture;

	[SourceLocation("Scene\\Components\\IndirectLighting\\DDGIVolumeUpdater.cs", 15)]
	private Texture _captureDepth;

	[SourceLocation("Scene\\Components\\IndirectLighting\\DDGIVolumeUpdater.cs", 27)]
	private int _renderedFace;

	[SourceLocation("Scene\\Components\\IndirectLighting\\DDGIVolumeUpdater.cs", 28)]
	private Vector3Int _renderedIndex = 0;

	[SourceLocation("Scene\\Components\\IndirectLighting\\DDGIVolumeUpdater.cs", 30)]
	private static ComputeShader DepthCopyShader = new ComputeShader("common/DDGI/ddgi_depth_copy_cs");

	[SourceLocation("Scene\\Components\\IndirectLighting\\DDGIVolumeUpdater.cs", 31)]
	private static ComputeShader IntegrateShader = new ComputeShader("common/DDGI/ddgi_integrate_cs");

	/// <summary>
	/// Whether to do a second pass on probes that are inside geometry so they have accurate bounces.
	/// </summary>
	[SourceLocation("Scene\\Components\\IndirectLighting\\DDGIVolumeUpdater.cs", 36)]
	private readonly bool BakeWithTwoPasses = true;

	/// <summary>
	/// Volume texture storing probe irradiance data (color).
	/// </summary>
	[Description("Volume texture storing probe irradiance data (color).")]
	[SourceLocation("Scene\\Components\\IndirectLighting\\DDGIVolumeUpdater.cs", 20)]
	public Texture GeneratedIrradianceTexture { get; set; }

	/// <summary>
	/// Volume texture storing probe distance/visibility data.
	/// </summary>
	[Description("Volume texture storing probe distance/visibility data.")]
	[SourceLocation("Scene\\Components\\IndirectLighting\\DDGIVolumeUpdater.cs", 25)]
	public Texture GeneratedDistanceTexture { get; set; }

	public DDGIProbeUpdaterCubemapper(IndirectLightVolume volume)
	{
		_volume = volume;
		_pendingProbes = new List<Vector3Int>();
		_camera = new SceneCamera
		{
			World = volume.Scene.SceneWorld,
			Rotation = Rotation.Identity,
			ClearFlags = ClearFlags.All,
			BackgroundColor = Color.Black,
			AmbientLightColor = Color.Black
		};
		if (volume.RenderExcludeTags != null)
		{
			_camera.ExcludeTags.SetFrom(volume.RenderExcludeTags);
		}
		SceneCamera camera = _camera;
		camera.OnRenderStageHook = (Action<Stage, SceneCamera>)Delegate.Combine(camera.OnRenderStageHook, (Action<Stage, SceneCamera>)((Stage stage, SceneCamera sceneCamera) =>
		{
			if (stage == Stage.AfterTransparent)
			{
				Texture texture = Texture.FromNative(Graphics.SceneLayer.GetDepthTarget());
				CopyDepthToColor(texture, _captureDepth, _renderedFace);
				texture.Dispose();
				_renderedFace++;
				if (_renderedFace == 6)
				{
					OnRenderFinish(_renderedIndex);
				}
			}
		}));
		InitializeCaptureTexture();
		InitializeProbeQueue();
		EnsureResources();
	}

	/// <summary>
	/// Copies depth texture values to a color texture array slice using a compute shader.
	/// </summary>
	[Description("Copies depth texture values to a color texture array slice using a compute shader.")]
	[SourceLocation("Scene\\Components\\IndirectLighting\\DDGIVolumeUpdater.cs", 88)]
	private void CopyDepthToColor(Texture srcDepth, Texture dstColor, int dstArraySlice)
	{
		int width = srcDepth.Width;
		int height = srcDepth.Height;
		RenderAttributes renderAttributes = RenderAttributes.Pool.Get();
		renderAttributes.Set(StringToken.Literal("SourceDepth", 3290060938u), in srcDepth, -1);
		renderAttributes.Set(StringToken.Literal("DestTextureArray", 3284189597u), in dstColor, -1);
		renderAttributes.Set(StringToken.Literal("TextureSize", 3901650781u), new Vector2Int(width, height));
		renderAttributes.Set(StringToken.Literal("DestArraySlice", 1274824867u), in dstArraySlice);
		DepthCopyShader.DispatchWithAttributes(renderAttributes, width, height, 1);
		RenderAttributes.Pool.Return(renderAttributes);
	}

	[SourceLocation("Scene\\Components\\IndirectLighting\\DDGIVolumeUpdater.cs", 103)]
	private void EnsureResources()
	{
		Vector3Int probeCounts = _volume.ProbeCounts;
		Vector3Int size = new Vector3Int(probeCounts.x * 8, probeCounts.y * 8, probeCounts.z);
		GeneratedIrradianceTexture = CreateVolumeTexture(size, ImageFormat.RGBA16161616F, "Irradiance");
		Vector3Int size2 = new Vector3Int(probeCounts.x * 16, probeCounts.y * 16, probeCounts.z);
		GeneratedDistanceTexture = CreateVolumeTexture(size2, ImageFormat.RGBA16161616F, "Distance");
	}

	[SourceLocation("Scene\\Components\\IndirectLighting\\DDGIVolumeUpdater.cs", 118)]
	private Texture CreateVolumeTexture(Vector3Int size, ImageFormat format, string name)
	{
		return Texture.CreateVolume(size.x, size.y, size.z, format).WithName(name).WithUAVBinding()
			.Finish();
	}

	[SourceLocation("Scene\\Components\\IndirectLighting\\DDGIVolumeUpdater.cs", 126)]
	public async Task<bool> RunAsync(CancellationToken token)
	{
		FastTimer pauseTimer = FastTimer.StartNew();
		using IProgressSection progress = Application.Editor.ProgressSection();
		progress.Title = "Baking Indirect Light Volume";
		progress.TotalCount = _pendingProbes.Count;
		CancellationToken progressToken = progress.GetCancel();
		while (_pendingProbes.Count > 0)
		{
			progress.Subtitle = $"Rendering probe {progress.Current + 1.0:n0} / {progress.TotalCount:n0}";
			if (!(await RenderProbe()))
			{
				return false;
			}
			if (token.IsCancellationRequested || progressToken.IsCancellationRequested)
			{
				progress.Subtitle = "Cancelled!";
				return false;
			}
			progress.Current++;
			if (pauseTimer.ElapsedMilliSeconds > 20.0)
			{
				await Task.Delay(1);
			}
		}
		progress.Subtitle = "Complete!";
		return true;
	}

	[SourceLocation("Scene\\Components\\IndirectLighting\\DDGIVolumeUpdater.cs", 162)]
	private async Task<bool> RenderProbe()
	{
		if (_pendingProbes.Count() == 0)
		{
			return false;
		}
		Vector3Int vector3Int = _pendingProbes.First();
		_pendingProbes.RemoveAt(0);
		_renderedFace = 0;
		_renderedIndex = vector3Int;
		_camera.Position = _volume.GetRelocatedProbeWorldPosition(vector3Int);
		_camera.Attributes.Set(StringToken.Literal("NoPrepassCulling", 2016477381u), true);
		_volume.Scene.RenderAttributes.MergeTo(_camera.Attributes);
		await Task.Yield();
		_camera.RenderToCubeTexture(_captureTexture, default(ViewSetup));
		await Task.Yield();
		return true;
	}

	[SourceLocation("Scene\\Components\\IndirectLighting\\DDGIVolumeUpdater.cs", 188)]
	private void InitializeProbeQueue()
	{
		Scene scene = _volume.Scene;
		if (scene == null)
		{
			return;
		}
		Vector3Int probeCounts = _volume.ProbeCounts;
		Vector3 vector = _volume.ComputeSpacing(probeCounts) * _volume.WorldTransform.Scale.Abs();
		BBox bbox = new BBox(-vector, vector);
		List<Vector3Int> list = new List<Vector3Int>();
		List<Vector3Int> list2 = new List<Vector3Int>();
		for (int i = 0; i < probeCounts.z; i++)
		{
			for (int j = 0; j < probeCounts.y; j++)
			{
				for (int k = 0; k < probeCounts.x; k++)
				{
					Vector3Int vector3Int = new Vector3Int(k, j, i);
					Vector3 from = _volume.GetProbeWorldPosition(vector3Int);
					if (scene.Trace.Box(bbox, in from, in from).IgnoreGameObjectHierarchy(_volume.GameObject).Run()
						.Hit)
					{
						list.Add(vector3Int);
					}
					else
					{
						list2.Add(vector3Int);
					}
				}
			}
		}
		if (BakeWithTwoPasses)
		{
			_pendingProbes.AddRange(list);
			Transform worldTransform = Application.Editor.Camera.WorldTransform;
			SceneTraceResult sceneTraceResult = scene.Trace.Ray(in worldTransform.Position, worldTransform.Position + worldTransform.Forward * 10000f).UseRenderMeshes().Run();
			Vector3 hitPos = (sceneTraceResult.Hit ? sceneTraceResult.HitPosition : (worldTransform.Position + worldTransform.Forward * 100f));
			_pendingProbes = _pendingProbes.OrderBy((Vector3Int x) => Vector3.DistanceBetween(_volume.GetProbeWorldPosition(x), in hitPos)).ToList();
			_pendingProbes.AddRange(_pendingProbes);
		}
		else
		{
			_pendingProbes.AddRange(list);
		}
		_pendingProbes.AddRange(list2);
	}

	[SourceLocation("Scene\\Components\\IndirectLighting\\DDGIVolumeUpdater.cs", 251)]
	private void InitializeCaptureTexture()
	{
		int mips = (int)MathF.Log2(64f) + 1;
		_captureTexture = Texture.CreateCube(64, 64).WithUAVBinding().WithMips(mips)
			.WithFormat(ImageFormat.RGBA16161616F)
			.Finish();
		_captureDepth = Texture.CreateCube(64, 64).WithUAVBinding().WithFormat(ImageFormat.R32F)
			.Finish();
	}

	[SourceLocation("Scene\\Components\\IndirectLighting\\DDGIVolumeUpdater.cs", 268)]
	private void OnRenderFinish(Vector3Int probeIndex)
	{
		Integrate(probeIndex);
	}

	[SourceLocation("Scene\\Components\\IndirectLighting\\DDGIVolumeUpdater.cs", 274)]
	private void Integrate(Vector3Int probeIndex)
	{
		RenderAttributes renderAttributes = RenderAttributes.Pool.Get();
		renderAttributes.Set(StringToken.Literal("SourceProbe", 3926396769u), in _captureTexture, -1);
		renderAttributes.Set(StringToken.Literal("SourceDepth", 3290060938u), in _captureDepth, -1);
		renderAttributes.Set(StringToken.Literal("IrradianceVolume", 1618695422u), _volume.IrradianceTexture, -1);
		renderAttributes.Set(StringToken.Literal("DistanceVolume", 624562805u), _volume.DistanceTexture, -1);
		renderAttributes.Set(StringToken.Literal("ProbeIndex", 2430263666u), in probeIndex);
		renderAttributes.Set(StringToken.Literal("ProbeCounts", 672953u), _volume.ProbeCounts);
		renderAttributes.Set(StringToken.Literal("EnergyLoss", 379418457u), _volume.Contrast);
		renderAttributes.SetCombo(StringToken.Literal("D_PASS", 3198036299u), 0);
		IntegrateShader.DispatchWithAttributes(renderAttributes, 1, 1, 1);
		renderAttributes.SetCombo(StringToken.Literal("D_PASS", 3198036299u), 1);
		IntegrateShader.DispatchWithAttributes(renderAttributes, 1, 1, 1);
		RenderAttributes.Pool.Return(renderAttributes);
	}

	[SourceLocation("Scene\\Components\\IndirectLighting\\DDGIVolumeUpdater.cs", 299)]
	public void Dispose()
	{
		_camera?.Dispose();
		_captureTexture?.Dispose();
		_captureDepth?.Dispose();
		GeneratedIrradianceTexture?.Dispose();
		GeneratedDistanceTexture?.Dispose();
	}
}
