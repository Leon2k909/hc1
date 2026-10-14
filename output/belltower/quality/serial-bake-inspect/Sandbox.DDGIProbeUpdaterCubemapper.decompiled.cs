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

	[SourceLocation("Scene\\Components\\IndirectLighting\\DDGIVolumeUpdater.cs", 16)]
	private Texture _firstPassIrradiance;

	[SourceLocation("Scene\\Components\\IndirectLighting\\DDGIVolumeUpdater.cs", 17)]
	private GpuBuffer<IndirectLightVolume.DDGIVolumeGpuData> _captureVolumes;

	[SourceLocation("Scene\\Components\\IndirectLighting\\DDGIVolumeUpdater.cs", 18)]
	private readonly List<Texture> _captureTextures = new List<Texture>();

	[SourceLocation("Scene\\Components\\IndirectLighting\\DDGIVolumeUpdater.cs", 19)]
	private int _captureVolumeCount;

	[SourceLocation("Scene\\Components\\IndirectLighting\\DDGIVolumeUpdater.cs", 20)]
	private int _pass;

	[SourceLocation("Scene\\Components\\IndirectLighting\\DDGIVolumeUpdater.cs", 32)]
	private int _renderedFace;

	[SourceLocation("Scene\\Components\\IndirectLighting\\DDGIVolumeUpdater.cs", 33)]
	private Vector3Int _renderedIndex = 0;

	[SourceLocation("Scene\\Components\\IndirectLighting\\DDGIVolumeUpdater.cs", 35)]
	private static ComputeShader DepthCopyShader = new ComputeShader("common/DDGI/ddgi_depth_copy_cs");

	[SourceLocation("Scene\\Components\\IndirectLighting\\DDGIVolumeUpdater.cs", 36)]
	private static ComputeShader IntegrateShader = new ComputeShader("common/DDGI/ddgi_integrate_cs");

	/// <summary>
	/// Volume texture storing probe irradiance data (color).
	/// </summary>
	[Description("Volume texture storing probe irradiance data (color).")]
	[SourceLocation("Scene\\Components\\IndirectLighting\\DDGIVolumeUpdater.cs", 25)]
	public Texture GeneratedIrradianceTexture { get; set; }

	/// <summary>
	/// Volume texture storing probe distance/visibility data.
	/// </summary>
	[Description("Volume texture storing probe distance/visibility data.")]
	[SourceLocation("Scene\\Components\\IndirectLighting\\DDGIVolumeUpdater.cs", 30)]
	public Texture GeneratedDistanceTexture { get; set; }

	/// <summary>
	/// Creates the capture camera and temporary textures for one volume bake.
	/// </summary>
	public DDGIProbeUpdaterCubemapper(IndirectLightVolume volume)
	{
		_volume = volume;
		_pendingProbes = new List<Vector3Int>();
		_camera = new SceneCamera
		{
			World = volume.Scene.SceneWorld,
			Rotation = Rotation.Identity,
			FieldOfView = 90f,
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
	[SourceLocation("Scene\\Components\\IndirectLighting\\DDGIVolumeUpdater.cs", 92)]
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

	[SourceLocation("Scene\\Components\\IndirectLighting\\DDGIVolumeUpdater.cs", 107)]
	private void EnsureResources()
	{
		Vector3Int probeCounts = _volume.ProbeCounts;
		Vector3Int size = new Vector3Int(probeCounts.x * 8, probeCounts.y * 8, probeCounts.z);
		GeneratedIrradianceTexture = CreateVolumeTexture(size, ImageFormat.RGBA16161616F, "Irradiance");
		Vector3Int size2 = new Vector3Int(probeCounts.x * 16, probeCounts.y * 16, probeCounts.z);
		GeneratedDistanceTexture = CreateVolumeTexture(size2, ImageFormat.RGBA16161616F, "Distance");
	}

	[SourceLocation("Scene\\Components\\IndirectLighting\\DDGIVolumeUpdater.cs", 122)]
	private Texture CreateVolumeTexture(Vector3Int size, ImageFormat format, string name)
	{
		return Texture.CreateVolume(size.x, size.y, size.z, format).WithName(name).WithUAVBinding()
			.Finish();
	}

	/// <summary>
	/// Captures direct lighting, then one bounce from the completed first pass.
	/// Returns false when either cancellation source interrupts the bake.
	/// </summary>
	[Description("Captures direct lighting, then one bounce from the completed first pass. Returns false when either cancellation source interrupts the bake.")]
	[SourceLocation("Scene\\Components\\IndirectLighting\\DDGIVolumeUpdater.cs", 134)]
	public async Task<bool> RunAsync(CancellationToken token)
	{
		FastTimer pauseTimer = FastTimer.StartNew();
		using IProgressSection progress = Application.Editor.ProgressSection();
		progress.Title = "Baking Indirect Light Volume";
		progress.TotalCount = _pendingProbes.Count * 2;
		CancellationToken progressToken = progress.GetCancel();
		for (_pass = 0; _pass < 2; _pass++)
		{
			if (_pass == 1)
			{
				Texture generatedIrradianceTexture = CreateVolumeTexture(new Vector3Int(GeneratedIrradianceTexture.Width, GeneratedIrradianceTexture.Height, GeneratedIrradianceTexture.Depth), ImageFormat.RGBA16161616F, "Irradiance");
				_firstPassIrradiance = GeneratedIrradianceTexture;
				GeneratedIrradianceTexture = generatedIrradianceTexture;
			}
			UpdateCaptureVolumes();
			foreach (Vector3Int pendingProbe in _pendingProbes)
			{
				if (token.IsCancellationRequested || progressToken.IsCancellationRequested)
				{
					return false;
				}
				progress.Subtitle = $"Rendering probe {progress.Current + 1.0:n0} / {progress.TotalCount:n0}";
				if (!(await RenderProbe(pendingProbe, token, progressToken)))
				{
					return false;
				}
				if (token.IsCancellationRequested || progressToken.IsCancellationRequested)
				{
					return false;
				}
				progress.Current++;
				if (pauseTimer.ElapsedMilliSeconds > 20.0)
				{
					await Task.Delay(1);
				}
			}
		}
		if (token.IsCancellationRequested || progressToken.IsCancellationRequested)
		{
			return false;
		}
		progress.Subtitle = "Complete!";
		return true;
	}

	/// <summary>
	/// Captures use a fixed set of volume textures for each bounce, independent of editor updates.
	/// </summary>
	[Description("Captures use a fixed set of volume textures for each bounce, independent of editor updates.")]
	[SourceLocation("Scene\\Components\\IndirectLighting\\DDGIVolumeUpdater.cs", 188)]
	private void UpdateCaptureVolumes()
	{
		_captureTextures.Clear();
		List<IndirectLightVolume.DDGIVolumeGpuData> list = new List<IndirectLightVolume.DDGIVolumeGpuData>();
		foreach (IndirectLightVolume item in from x in _volume.Scene.GetAll<IndirectLightVolume>()
			orderby x.Bounds.Volume
			select x)
		{
			if (item.Active && item.Enabled && (_pass != 0 || item != _volume) && item.BuildData(out var data, item == _volume, applyAdjustments: false))
			{
				list.Add(data);
				if (item != _volume)
				{
					_captureTextures.Add(item.IrradianceTexture);
					_captureTextures.Add(item.DistanceTexture);
					_captureTextures.Add(item.RelocationTexture);
				}
			}
		}
		_captureVolumes?.Dispose();
		_captureVolumeCount = list.Count;
		_captureVolumes = new GpuBuffer<IndirectLightVolume.DDGIVolumeGpuData>(Math.Max(1, list.Count));
		if (list.Count > 0)
		{
			_captureVolumes.SetData(list);
		}
	}

	[SourceLocation("Scene\\Components\\IndirectLighting\\DDGIVolumeUpdater.cs", 217)]
	private async Task<bool> RenderProbe(Vector3Int probeIndex, CancellationToken token, CancellationToken progressToken)
	{
		_renderedFace = 0;
		_renderedIndex = probeIndex;
		_camera.Position = _volume.GetRelocatedProbeWorldPosition(probeIndex);
		_camera.Attributes.Set(StringToken.Literal("NoPrepassCulling", 2016477381u), true);
		_volume.Scene.RenderAttributes.MergeTo(_camera.Attributes);
		RenderAttributes attributes = _camera.Attributes;
		StringToken k = StringToken.Literal("DDGI_Volumes", 1039222852u);
		GpuBuffer value = _captureVolumes;
		attributes.Set(in k, in value);
		_camera.Attributes.Set(StringToken.Literal("DDGI_VolumeCount", 1666729117u), in _captureVolumeCount);
		await Task.Yield();
		if (token.IsCancellationRequested || progressToken.IsCancellationRequested)
		{
			return false;
		}
		foreach (Texture captureTexture in _captureTextures)
		{
			captureTexture.MarkUsed();
		}
		_camera.RenderToCubeTexture(_captureTexture, default(ViewSetup));
		await Task.Yield();
		return true;
	}

	[SourceLocation("Scene\\Components\\IndirectLighting\\DDGIVolumeUpdater.cs", 244)]
	private void InitializeProbeQueue()
	{
		Vector3Int probeCounts = _volume.ProbeCounts;
		for (int i = 0; i < probeCounts.z; i++)
		{
			for (int j = 0; j < probeCounts.y; j++)
			{
				for (int k = 0; k < probeCounts.x; k++)
				{
					_pendingProbes.Add(new Vector3Int(k, j, i));
				}
			}
		}
	}

	[SourceLocation("Scene\\Components\\IndirectLighting\\DDGIVolumeUpdater.cs", 259)]
	private void InitializeCaptureTexture()
	{
		int mips = (int)MathF.Log2(64f) + 1;
		_captureTexture = Texture.CreateCube(64, 64).WithUAVBinding().WithMips(mips)
			.WithFormat(ImageFormat.RGBA16161616F)
			.Finish();
		_captureDepth = Texture.CreateCube(64, 64).WithUAVBinding().WithFormat(ImageFormat.R32F)
			.Finish();
	}

	[SourceLocation("Scene\\Components\\IndirectLighting\\DDGIVolumeUpdater.cs", 276)]
	private void OnRenderFinish(Vector3Int probeIndex)
	{
		Integrate(probeIndex);
	}

	[SourceLocation("Scene\\Components\\IndirectLighting\\DDGIVolumeUpdater.cs", 282)]
	private void Integrate(Vector3Int probeIndex)
	{
		RenderAttributes renderAttributes = RenderAttributes.Pool.Get();
		renderAttributes.Set(StringToken.Literal("SourceProbe", 3926396769u), in _captureTexture, -1);
		renderAttributes.Set(StringToken.Literal("SourceDepth", 3290060938u), in _captureDepth, -1);
		renderAttributes.Set(StringToken.Literal("IrradianceVolume", 1618695422u), GeneratedIrradianceTexture, -1);
		renderAttributes.Set(StringToken.Literal("DistanceVolume", 624562805u), GeneratedDistanceTexture, -1);
		renderAttributes.Set(StringToken.Literal("ProbeIndex", 2430263666u), in probeIndex);
		renderAttributes.Set(StringToken.Literal("ProbeCounts", 672953u), _volume.ProbeCounts);
		renderAttributes.Set(StringToken.Literal("ProbeMaxDistance", 3707766355u), Math.Max(1f, _volume.ProbeCellDiagonal + (_volume.GetProbe(probeIndex)?.Offset.Length ?? 0f)));
		renderAttributes.SetCombo(StringToken.Literal("D_PASS", 3198036299u), 0);
		IntegrateShader.DispatchWithAttributes(renderAttributes, 1, 1, 1);
		if (_pass == 0)
		{
			renderAttributes.SetCombo(StringToken.Literal("D_PASS", 3198036299u), 1);
			IntegrateShader.DispatchWithAttributes(renderAttributes, 1, 1, 1);
		}
		RenderAttributes.Pool.Return(renderAttributes);
	}

	/// <summary>
	/// Releases temporary bake resources and references to shared saved textures.
	/// </summary>
	[Description("Releases temporary bake resources and references to shared saved textures.")]
	[SourceLocation("Scene\\Components\\IndirectLighting\\DDGIVolumeUpdater.cs", 315)]
	public void Dispose()
	{
		_camera?.Dispose();
		_captureTexture?.Dispose();
		_captureDepth?.Dispose();
		_captureVolumes?.Dispose();
		_captureTextures.Clear();
		_firstPassIrradiance?.Dispose();
		GeneratedIrradianceTexture?.Dispose();
		GeneratedDistanceTexture?.Dispose();
	}
}
