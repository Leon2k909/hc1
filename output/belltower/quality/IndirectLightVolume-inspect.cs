using System;
using System.Linq;
using System.Text.Json.Nodes;
using System.Threading;
using System.Threading.Tasks;
using Editor;
using Sandbox.Internal;

namespace Sandbox;

/// <summary>
/// Dynamic Diffuse Global Illumination volume that provides indirect lighting using a 3D probe grid.
/// Probes store irradiance and distance data in volume textures that can be sampled by shaders.
/// </summary>
/// <summary>
/// Probe relocation functionality for DDGI volumes.
/// Moves probes out of geometry to unfuck artifacts.
/// </summary>
[Expose]
[Title("Indirect Light Volume (DDGI)")]
[Category("Light")]
[Icon("grid_view")]
[EditorHandle("materials/gizmo/lpv.png")]
[Alias(new string[] { "DDGIVolume" })]
[Description("Dynamic Diffuse Global Illumination volume that provides indirect lighting using a 3D probe grid. Probes store irradiance and distance data in volume textures that can be sampled by shaders.")]
[SourceLocation("Scene\\Components\\IndirectLighting\\IndirectLightVolume.cs", 13)]
[SourceLocation("Scene\\Components\\IndirectLighting\\IndirectLightVolume.Relocation.cs", 10)]
public sealed class IndirectLightVolume : Component, Component.ExecuteInEditor, Component.DontExecuteOnServer
{
	/// <summary>
	/// Behavior when a probe is detected inside geometry.
	/// Relocation attempts to move the probe out of geometry, while Deactivate excludes it from lighting.
	/// </summary>
	[Description("Behavior when a probe is detected inside geometry. Relocation attempts to move the probe out of geometry, while Deactivate excludes it from lighting.")]
	public enum InsideGeometryBehavior
	{
		/// <summary>
		/// Probe is deactivated and won't contribute to lighting.
		/// </summary>
		[Icon("block")]
		[Description("Probe is deactivated and won't contribute to lighting.")]
		Deactivate,
		/// <summary>
		/// Probe is relocated to escape the geometry.
		/// </summary>
		[Icon("open_with")]
		[Description("Probe is relocated to escape the geometry.")]
		Relocate
	}

	/// <summary>
	/// Per-probe data including position offset and active state.
	/// </summary>
	[Description("Per-probe data including position offset and active state.")]
	[SourceLocation("Scene\\Components\\IndirectLighting\\IndirectLightVolume.cs", 43)]
	public sealed class Probe
	{
		/// <summary>
		/// World-space displacement from the probe's grid position.
		/// </summary>
		[Description("World-space displacement from the probe's grid position.")]
		[SourceLocation("Scene\\Components\\IndirectLighting\\IndirectLightVolume.cs", 48)]
		public Vector3 Offset { get; set; }

		/// <summary>
		/// Whether this probe contributes to indirect lighting.
		/// </summary>
		[DefaultValue(true)]
		[Description("Whether this probe contributes to indirect lighting.")]
		[SourceLocation("Scene\\Components\\IndirectLighting\\IndirectLightVolume.cs", 53)]
		public bool Active { get; set; } = true;
	}

	internal struct DDGIVolumeGpuData
	{
		[SourceLocation("Scene\\Components\\IndirectLighting\\IndirectLightVolume.cs", 554)]
		public Matrix Transform;

		[SourceLocation("Scene\\Components\\IndirectLighting\\IndirectLightVolume.cs", 555)]
		public Vector3 BBoxMin;

		[SourceLocation("Scene\\Components\\IndirectLighting\\IndirectLightVolume.cs", 556)]
		public Vector3 BBoxMax;

		[SourceLocation("Scene\\Components\\IndirectLighting\\IndirectLightVolume.cs", 557)]
		public float NormalBias;

		[SourceLocation("Scene\\Components\\IndirectLighting\\IndirectLightVolume.cs", 558)]
		public Vector3 ProbeSpacing;

		/// <summary>
		/// World-space cell diagonal used to bound captured probe distances.
		/// </summary>
		[SourceLocation("Scene\\Components\\IndirectLighting\\IndirectLightVolume.cs", 563)]
		public float ProbeCellDiagonal;

		[SourceLocation("Scene\\Components\\IndirectLighting\\IndirectLightVolume.cs", 564)]
		public Vector3 ReciprocalSpacing;

		[SourceLocation("Scene\\Components\\IndirectLighting\\IndirectLightVolume.cs", 565)]
		public int IrradianceTextureIndex;

		[SourceLocation("Scene\\Components\\IndirectLighting\\IndirectLightVolume.cs", 566)]
		public Vector3 ReciprocalCountsMinusOne;

		[SourceLocation("Scene\\Components\\IndirectLighting\\IndirectLightVolume.cs", 567)]
		public int DistanceTextureIndex;

		[SourceLocation("Scene\\Components\\IndirectLighting\\IndirectLightVolume.cs", 568)]
		public Vector3Int ProbeCounts;

		[SourceLocation("Scene\\Components\\IndirectLighting\\IndirectLightVolume.cs", 569)]
		public int RelocationTextureIndex;

		/// <summary>
		/// Selects legacy visibility or normalized distance-moment decoding in the shader.
		/// </summary>
		[SourceLocation("Scene\\Components\\IndirectLighting\\IndirectLightVolume.cs", 574)]
		public int BakeVersion;

		/// <summary>
		/// Transforms grid positions to the world space used by captures and relocation offsets.
		/// </summary>
		[SourceLocation("Scene\\Components\\IndirectLighting\\IndirectLightVolume.cs", 579)]
		public Matrix ProbeToWorldTransform;

		/// <summary>
		/// World-space sampling bias toward the camera, used by versioned bakes.
		/// </summary>
		[SourceLocation("Scene\\Components\\IndirectLighting\\IndirectLightVolume.cs", 584)]
		public float ViewBias;

		/// <summary>
		/// Contrast applied after sampling, neutral during probe captures.
		/// </summary>
		[SourceLocation("Scene\\Components\\IndirectLighting\\IndirectLightVolume.cs", 589)]
		public float RuntimeContrast;

		/// <summary>
		/// Saturation applied after sampling, neutral during probe captures.
		/// </summary>
		[SourceLocation("Scene\\Components\\IndirectLighting\\IndirectLightVolume.cs", 594)]
		public float RuntimeSaturation;

		/// <summary>
		/// Intensity multiplier, neutral during probe captures.
		/// </summary>
		[SourceLocation("Scene\\Components\\IndirectLighting\\IndirectLightVolume.cs", 599)]
		public float RuntimeIntensity;

		/// <summary>
		/// RGB tint multiplier, white during probe captures.
		/// </summary>
		[SourceLocation("Scene\\Components\\IndirectLighting\\IndirectLightVolume.cs", 604)]
		public Vector3 RuntimeTint;

		/// <summary>
		/// Outward fade distance in world units, disabled during probe captures.
		/// </summary>
		[SourceLocation("Scene\\Components\\IndirectLighting\\IndirectLightVolume.cs", 609)]
		public float BlendDistance;
	}

	/// <summary>
	/// Result of tracing a single ray for relocation purposes.
	/// </summary>
	[Description("Result of tracing a single ray for relocation purposes.")]
	private readonly struct RelocationRayHit(float distance, bool isBackface, bool didHit)
	{
		[SourceLocation("Scene\\Components\\IndirectLighting\\IndirectLightVolume.Relocation.cs", 52)]
		public readonly float Distance = distance;

		[SourceLocation("Scene\\Components\\IndirectLighting\\IndirectLightVolume.Relocation.cs", 53)]
		public readonly bool IsBackface = isBackface;

		[SourceLocation("Scene\\Components\\IndirectLighting\\IndirectLightVolume.Relocation.cs", 54)]
		public readonly bool DidHit = didHit;

		[SourceLocation("Scene\\Components\\IndirectLighting\\IndirectLightVolume.Relocation.cs", 63)]
		public static RelocationRayHit Miss => new RelocationRayHit(float.MaxValue, isBackface: false, didHit: false);
	}

	/// <summary>
	/// Aggregated statistics from tracing all rays for a single probe.
	/// </summary>
	[Description("Aggregated statistics from tracing all rays for a single probe.")]
	private readonly struct ProbeTraceResult(int closestBackfaceIndex, int closestFrontfaceIndex, int farthestFrontfaceIndex, float closestBackfaceDistance, float closestFrontfaceDistance, float farthestFrontfaceDistance, int backfaceCount, int totalHits)
	{
		[SourceLocation("Scene\\Components\\IndirectLighting\\IndirectLightVolume.Relocation.cs", 71)]
		public readonly int ClosestBackfaceIndex = closestBackfaceIndex;

		[SourceLocation("Scene\\Components\\IndirectLighting\\IndirectLightVolume.Relocation.cs", 72)]
		public readonly int ClosestFrontfaceIndex = closestFrontfaceIndex;

		[SourceLocation("Scene\\Components\\IndirectLighting\\IndirectLightVolume.Relocation.cs", 73)]
		public readonly int FarthestFrontfaceIndex = farthestFrontfaceIndex;

		[SourceLocation("Scene\\Components\\IndirectLighting\\IndirectLightVolume.Relocation.cs", 74)]
		public readonly float ClosestBackfaceDistance = closestBackfaceDistance;

		[SourceLocation("Scene\\Components\\IndirectLighting\\IndirectLightVolume.Relocation.cs", 75)]
		public readonly float ClosestFrontfaceDistance = closestFrontfaceDistance;

		[SourceLocation("Scene\\Components\\IndirectLighting\\IndirectLightVolume.Relocation.cs", 76)]
		public readonly float FarthestFrontfaceDistance = farthestFrontfaceDistance;

		[SourceLocation("Scene\\Components\\IndirectLighting\\IndirectLightVolume.Relocation.cs", 77)]
		public readonly int BackfaceCount = backfaceCount;

		[SourceLocation("Scene\\Components\\IndirectLighting\\IndirectLightVolume.Relocation.cs", 78)]
		public readonly int TotalHits = totalHits;

		[SourceLocation("Scene\\Components\\IndirectLighting\\IndirectLightVolume.Relocation.cs", 100)]
		public float BackfaceRatio
		{
			get
			{
				if (TotalHits <= 0)
				{
					return 0f;
				}
				return (float)BackfaceCount / (float)TotalHits;
			}
		}

		[SourceLocation("Scene\\Components\\IndirectLighting\\IndirectLightVolume.Relocation.cs", 101)]
		public bool HasBackfaceHit => ClosestBackfaceIndex >= 0;

		[SourceLocation("Scene\\Components\\IndirectLighting\\IndirectLightVolume.Relocation.cs", 102)]
		public bool HasFrontfaceHit => ClosestFrontfaceIndex >= 0;

		[SourceLocation("Scene\\Components\\IndirectLighting\\IndirectLightVolume.Relocation.cs", 103)]
		public bool HasFarthestFrontface => FarthestFrontfaceIndex >= 0;
	}

	[SourceLocation("Scene\\Components\\IndirectLighting\\IndirectLightVolume.cs", 272)]
	private const int CurrentBakeVersion = 1;

	[SourceLocation("Scene\\Components\\IndirectLighting\\IndirectLightVolume.cs", 293)]
	private (Texture Irradiance, Texture Distance, Texture Relocation)? _bakePreview;

	/// <summary>
	/// Cancellation source for the current bake operation.
	/// </summary>
	[SourceLocation("Scene\\Components\\IndirectLighting\\IndirectLightVolume.cs", 298)]
	private CancellationTokenSource _bakeCts;

	[SourceLocation("Scene\\Components\\IndirectLighting\\IndirectLightVolume.cs", 443)]
	private IDisposable _boundsUndoScope;

	/// <summary>
	/// Number of ray directions to cast per probe for relocation analysis.
	/// </summary>
	[SourceLocation("Scene\\Components\\IndirectLighting\\IndirectLightVolume.Relocation.cs", 15)]
	private const int RelocationRayCount = 128;

	/// <summary>
	/// Number of iterative refinement steps when computing relocation.
	/// </summary>
	[SourceLocation("Scene\\Components\\IndirectLighting\\IndirectLightVolume.Relocation.cs", 20)]
	private const int RefinementSteps = 12;

	/// <summary>
	/// Threshold for backface hit ratio to consider probe inside geometry.
	/// </summary>
	[SourceLocation("Scene\\Components\\IndirectLighting\\IndirectLightVolume.Relocation.cs", 25)]
	private const float BackfaceThreshold = 0.25f;

	/// <summary>
	/// Minimum distance (as fraction of min spacing) a probe should maintain from frontface geometry.
	/// </summary>
	[SourceLocation("Scene\\Components\\IndirectLighting\\IndirectLightVolume.Relocation.cs", 30)]
	private const float MinFrontfaceDistanceFactor = 0.2f;

	/// <summary>
	/// Maximum offset as fraction of probe spacing (forms ellipsoid constraint).
	/// </summary>
	[SourceLocation("Scene\\Components\\IndirectLighting\\IndirectLightVolume.Relocation.cs", 35)]
	private const float MaxOffsetFactor = 0.45f;

	/// <summary>
	/// How far to trace rays as a multiple of the probe cell diagonal.
	/// </summary>
	[SourceLocation("Scene\\Components\\IndirectLighting\\IndirectLightVolume.Relocation.cs", 40)]
	private const float TraceDistanceFactor = 1f;

	/// <summary>
	/// CPU-side probe data indexed by flattened probe index.
	/// </summary>
	[Description("CPU-side probe data indexed by flattened probe index.")]
	[SourceLocation("Scene\\Components\\IndirectLighting\\IndirectLightVolume.cs", 59)]
	internal Probe[] Probes { get; set; }

	/// <summary>
	/// Local-space bounding box that defines the volume coverage area.
	/// </summary>
	[Property]
	[Description("Local bounds covered by the probe grid. Enclose the area that needs indirect lighting. Changing the bounds requires a rebake.")]
	[SourceLocation("Scene\\Components\\IndirectLighting\\IndirectLightVolume.cs", 68)]
	public BBox Bounds
	{
		get;
		set
		{
			if (!(field == value))
			{
				field = value;
				MarkDirty();
			}
		}
	} = BBox.FromPositionAndSize(Vector3.Zero, new Vector3(512f));

	/// <summary>
	/// Number of probe intervals per 1024 local units. Higher values increase probe resolution.
	/// </summary>
	[Header("Probes")]
	[Property]
	[Range(1f, 15f)]
	[Description("Controls how closely probes are spaced inside the volume. Higher values capture smaller lighting details but increase bake time and memory use. Requires a rebake.")]
	[DefaultValue(8)]
	[SourceLocation("Scene\\Components\\IndirectLighting\\IndirectLightVolume.cs", 85)]
	public int ProbeDensity
	{
		get;
		set
		{
			if (field != value)
			{
				field = value;
				MarkDirty();
			}
		}
	} = 8;

	/// <summary>
	/// How to handle probes detected inside geometry.
	/// </summary>
	[Property]
	[Description("Controls probes found inside geometry when baking. Relocate tries to move them into nearby free space and excludes them if they remain inside; Deactivate excludes them without moving them. Requires a rebake.")]
	[DefaultValue(InsideGeometryBehavior.Relocate)]
	[SourceLocation("Scene\\Components\\IndirectLighting\\IndirectLightVolume.cs", 103)]
	public InsideGeometryBehavior InsideGeometry { get; set; } = InsideGeometryBehavior.Relocate;

	/// <summary>
	/// Objects with any of these tags will be excluded when baking probes for this volume.
	/// </summary>
	[Property]
	[Description("Objects with any of these tags are omitted from probe captures and relocation. Use this to exclude objects that should not affect baked lighting. Requires a rebake.")]
	[SourceLocation("Scene\\Components\\IndirectLighting\\IndirectLightVolume.cs", 110)]
	public TagSet RenderExcludeTags { get; set; } = new TagSet();

	/// <summary>
	/// World-space bias along surface normals to prevent self-occlusion artifacts.
	/// </summary>
	[Header("Sampling")]
	[Property]
	[Range(-0f, 50f)]
	[Advanced]
	[Description("Moves the lighting sample away from the surface, in world units. Increase to reduce dark edge artifacts; too much can leak light through nearby geometry. Updates immediately without rebaking.")]
	[DefaultValue(10f)]
	[SourceLocation("Scene\\Components\\IndirectLighting\\IndirectLightVolume.cs", 117)]
	public float NormalBias
	{
		get;
		set
		{
			if (field != value)
			{
				field = value;
				MarkDirty();
			}
		}
	} = 10f;

	/// <summary>
	/// World-space bias toward the viewing position to reduce self-occlusion at corners in new bakes.
	/// </summary>
	[Property]
	[Range(0f, 50f)]
	[Advanced]
	[Description("Moves the lighting sample toward the camera, in world units. Helps reduce dark corners, but too much can cause light leaks or changes as the camera moves. Updates immediately. Legacy bakes must be rebaked to use view bias.")]
	[DefaultValue(20f)]
	[SourceLocation("Scene\\Components\\IndirectLighting\\IndirectLightVolume.cs", 135)]
	public float ViewBias
	{
		get;
		set
		{
			if (field != value)
			{
				field = value;
				MarkDirty();
			}
		}
	} = 20f;

	/// <summary>
	/// Multiplies sampled indirect lighting by an RGB tint. Alpha is ignored.
	/// </summary>
	[Header("Runtime Adjustments")]
	[Property]
	[ColorUsage(false, false)]
	[Title("Tint")]
	[Description("Tints this volume's indirect lighting. White is unchanged. Updates immediately and is not baked into probes.")]
	[SourceLocation("Scene\\Components\\IndirectLighting\\IndirectLightVolume.cs", 151)]
	public Color RuntimeTint
	{
		get;
		set
		{
			if (!(field == value))
			{
				field = value;
				MarkDirty();
			}
		}
	} = Color.White;

	/// <summary>
	/// Multiplies sampled indirect lighting without changing the baked textures.
	/// </summary>
	[Property]
	[Range(0f, 4f)]
	[Title("Intensity")]
	[Description("Multiplies this volume's indirect lighting. One is unchanged and zero removes its light contribution. Updates immediately and is not baked into probes.")]
	[DefaultValue(1f)]
	[SourceLocation("Scene\\Components\\IndirectLighting\\IndirectLightVolume.cs", 169)]
	public float RuntimeIntensity
	{
		get;
		set
		{
			if (field != value)
			{
				field = value;
				MarkDirty();
			}
		}
	} = 1f;

	/// <summary>
	/// Adjusts sampled indirect lighting around 0.18 in linear light. One is unchanged.
	/// Applies immediately without rebaking and is excluded from probe captures.
	/// </summary>
	[Property]
	[Range(0f, 2f)]
	[Title("Contrast")]
	[Description("Adjusts this volume's indirect lighting around a linear brightness of 0.18. One is unchanged; higher values deepen darks and brighten highlights, while lower values flatten contrast. Updates immediately and is not baked into probes.")]
	[DefaultValue(1f)]
	[SourceLocation("Scene\\Components\\IndirectLighting\\IndirectLightVolume.cs", 187)]
	public float RuntimeContrast
	{
		get;
		set
		{
			if (field != value)
			{
				field = value;
				MarkDirty();
			}
		}
	} = 1f;

	/// <summary>
	/// Adjusts the color of sampled indirect lighting. Zero is grayscale; one is unchanged.
	/// Applies immediately without rebaking and is excluded from probe captures.
	/// </summary>
	[Property]
	[Range(0f, 2f)]
	[Title("Saturation")]
	[Description("Adjusts the color intensity of this volume's indirect lighting. Zero removes color, one is unchanged, and higher values strengthen color bleed. Updates immediately and is not baked into probes.")]
	[DefaultValue(1f)]
	[SourceLocation("Scene\\Components\\IndirectLighting\\IndirectLightVolume.cs", 205)]
	public float RuntimeSaturation
	{
		get;
		set
		{
			if (field != value)
			{
				field = value;
				MarkDirty();
			}
		}
	} = 1f;

	/// <summary>
	/// Distance in world units over which the volume fades outward from its bounds.
	/// Remaining influence passes to overlapping volumes in the existing volume order.
	/// </summary>
	[Property]
	[Range(0f, 512f)]
	[Description("Keeps indirect lighting at full strength inside the volume and fades it out beyond the bounds, in world units. Use overlapping volumes for smooth transitions between areas. Zero keeps a hard boundary. Updates immediately without rebaking.")]
	[SourceLocation("Scene\\Components\\IndirectLighting\\IndirectLightVolume.cs", 223)]
	public float BlendDistance
	{
		get;
		set
		{
			if (field != value)
			{
				field = value;
				MarkDirty();
			}
		}
	}

	/// <summary>
	/// Calculated probe count along each axis based on bounds and density.
	/// </summary>
	[Description("Calculated probe count along each axis based on bounds and density.")]
	[SourceLocation("Scene\\Components\\IndirectLighting\\IndirectLightVolume.cs", 240)]
	public Vector3Int ProbeCounts => ComputeProbeCounts();

	/// <summary>
	/// Maximum world-space distance from an unrelocated probe to a point in its grid cell.
	/// </summary>
	[Description("Maximum world-space distance from an unrelocated probe to a point in its grid cell.")]
	[SourceLocation("Scene\\Components\\IndirectLighting\\IndirectLightVolume.cs", 245)]
	internal float ProbeCellDiagonal => (ComputeSpacing(ProbeCounts) * WorldScale.Abs()).Length;

	/// <summary>
	/// Volume texture storing probe irradiance data (color).
	/// </summary>
	[Property]
	[Hide]
	[Description("Volume texture storing probe irradiance data (color).")]
	[SourceLocation("Scene\\Components\\IndirectLighting\\IndirectLightVolume.cs", 250)]
	public Texture IrradianceTexture { get; set; }

	/// <summary>
	/// Volume texture storing probe distance/visibility data.
	/// </summary>
	[Property]
	[Hide]
	[Description("Volume texture storing probe distance/visibility data.")]
	[SourceLocation("Scene\\Components\\IndirectLighting\\IndirectLightVolume.cs", 256)]
	public Texture DistanceTexture { get; set; }

	/// <summary>
	/// Volume texture storing probe relocation offsets (XYZ = offset, W = active).
	/// </summary>
	[Property]
	[Hide]
	[Description("Volume texture storing probe relocation offsets (XYZ = offset, W = active).")]
	[SourceLocation("Scene\\Components\\IndirectLighting\\IndirectLightVolume.cs", 262)]
	public Texture RelocationTexture { get; set; }

	/// <summary>
	/// Encoding of the saved probe data. Missing versions use legacy visibility;
	/// version 1 stores normalized mean distance and standard deviation.
	/// </summary>
	[Property]
	[Hide]
	[Description("Encoding of the saved probe data. Missing versions use legacy visibility; version 1 stores normalized mean distance and standard deviation.")]
	[SourceLocation("Scene\\Components\\IndirectLighting\\IndirectLightVolume.cs", 269)]
	public int BakeVersion { get; set; }

	/// <summary>
	/// Versions serialized probe settings while preserving existing scenes.
	/// </summary>
	[Description("Versions serialized probe settings while preserving existing scenes.")]
	[SourceLocation("Scene\\Components\\IndirectLighting\\IndirectLightVolume.cs", 277)]
	public override int ComponentVersion => 2;

	[Expose]
	[Hide]
	[SourceLocation("Scene\\Components\\IndirectLighting\\IndirectLightVolume.cs", 331)]
	internal bool IsSceneSaved => Scene?.Editor?.GetSceneFolder() != null;

	/// <summary>
	/// Volume texture storing probe relocation offsets (XYZ = offset, W = active).
	/// </summary>
	[Description("Volume texture storing probe relocation offsets (XYZ = offset, W = active).")]
	[SourceLocation("Scene\\Components\\IndirectLighting\\IndirectLightVolume.Relocation.cs", 45)]
	private Texture GeneratedRelocationTexture { get; set; }

	[Expose]
	[JsonUpgrader(typeof(IndirectLightVolume), 1)]
	[SourceLocation("Scene\\Components\\IndirectLighting\\IndirectLightVolume.cs", 279)]
	private static void UpgradeLegacyBakeVersion(JsonObject obj)
	{
		if (obj["BakeVersion"] == null)
		{
			JsonNode jsonNode = (obj["BakeVersion"] = 0);
		}
	}

	[Expose]
	[JsonUpgrader(typeof(IndirectLightVolume), 2)]
	[SourceLocation("Scene\\Components\\IndirectLighting\\IndirectLightVolume.cs", 285)]
	private static void UpgradeLegacyBiasDefaults(JsonObject obj)
	{
		JsonObject jsonObject = obj;
		if (jsonObject["NormalBias"] == null)
		{
			JsonNode jsonNode = (jsonObject["NormalBias"] = 5f);
		}
		jsonObject = obj;
		if (jsonObject["ViewBias"] == null)
		{
			JsonNode jsonNode = (jsonObject["ViewBias"] = 5f);
		}
	}

	[SourceLocation("Scene\\Components\\IndirectLighting\\IndirectLightVolume.cs", 304)]
	protected override void OnEnabled()
	{
		base.OnEnabled();
		GameTransform transform = Transform;
		transform.OnTransformChanged = (Action)Delegate.Combine(transform.OnTransformChanged, new Action(MarkDirty));
		LoadProbesFromRelocationTexture();
		MarkDirty();
	}

	[SourceLocation("Scene\\Components\\IndirectLighting\\IndirectLightVolume.cs", 313)]
	protected override void OnDisabled()
	{
		base.OnDisabled();
		GameTransform transform = Transform;
		transform.OnTransformChanged = (Action)Delegate.Remove(transform.OnTransformChanged, new Action(MarkDirty));
		_bakeCts?.Cancel();
		MarkDirty();
	}

	[SourceLocation("Scene\\Components\\IndirectLighting\\IndirectLightVolume.cs", 323)]
	private void MarkDirty()
	{
		Scene?.Get<DDGIVolumeSystem>()?.MarkDirty();
	}

	/// <summary>
	/// Explains why baking is unavailable until the scene has been saved.
	/// </summary>
	[Header("Actions")]
	[ShowIf("IsSceneSaved", false)]
	[InfoBox("Save the scene before baking indirect light volumes.", "warning", EditorTint.Yellow)]
	[Button("Bake", "lightbulb")]
	[ReadOnly]
	[Description("Explains why baking is unavailable until the scene has been saved.")]
	[SourceLocation("Scene\\Components\\IndirectLighting\\IndirectLightVolume.cs", 337)]
	public void BakeProbesUnavailableMessage()
	{
	}

	/// <summary>
	/// Starts the probe baking process to capture lighting into the volume textures.
	/// </summary>
	[Header("Actions")]
	[ShowIf("IsSceneSaved", true)]
	[Button("Bake", "lightbulb")]
	[Description("Starts the probe baking process to capture lighting into the volume textures.")]
	[SourceLocation("Scene\\Components\\IndirectLighting\\IndirectLightVolume.cs", 346)]
	public async Task BakeProbes(CancellationToken ct = default(CancellationToken))
	{
		if (Scene?.SceneWorld == null || !IsSceneSaved || _bakeCts != null)
		{
			return;
		}
		using CancellationTokenSource bakeCts = CancellationTokenSource.CreateLinkedTokenSource(ct, GameObject.EnabledToken);
		_bakeCts = bakeCts;
		Probe[] previousProbes = Probes;
		bool completed = false;
		try
		{
			bakeCts.Token.ThrowIfCancellationRequested();
			ComputeProbeRelocation();
			using DDGIProbeUpdaterCubemapper updater = new DDGIProbeUpdaterCubemapper(this);
			_bakePreview = (updater.GeneratedIrradianceTexture, updater.GeneratedDistanceTexture, GeneratedRelocationTexture);
			MarkDirty();
			if (!(await updater.RunAsync(bakeCts.Token)) || !IsSceneSaved)
			{
				return;
			}
			bakeCts.Token.ThrowIfCancellationRequested();
			Graphics.FlushGPU();
			Guid bakeId = Guid.NewGuid();
			Texture irradianceTexture = SaveTexture(updater.GeneratedIrradianceTexture, "Irradiance", bakeId);
			Texture distanceTexture = SaveTexture(updater.GeneratedDistanceTexture, "Distance", bakeId, ImageFormat.BC6H);
			Texture relocationTexture = SaveTexture(GeneratedRelocationTexture, "Relocation", bakeId, ImageFormat.RGBA16161616F);
			IrradianceTexture = irradianceTexture;
			DistanceTexture = distanceTexture;
			RelocationTexture = relocationTexture;
			BakeVersion = 1;
			completed = true;
		}
		finally
		{
			if (!completed)
			{
				Probes = previousProbes;
			}
			_bakePreview = null;
			GeneratedRelocationTexture?.Dispose();
			GeneratedRelocationTexture = null;
			_bakeCts = null;
			MarkDirty();
		}
	}

	/// <summary>
	/// Automatically sizes the volume to encompass all scene geometry.
	/// </summary>
	[Button("Fit to Scene Bounds", "fullscreen")]
	[Description("Automatically sizes the volume to encompass all scene geometry.")]
	[SourceLocation("Scene\\Components\\IndirectLighting\\IndirectLightVolume.cs", 402)]
	public void ExtendToSceneBounds()
	{
		if (Scene == null)
		{
			return;
		}
		WorldScale = 1f;
		WorldRotation = Rotation.Identity;
		BBox bBox = BBox.FromPositionAndSize(WorldPosition);
		foreach (Renderer item in Scene.GetAll<Renderer>())
		{
			if (item is IHasBounds hasBounds)
			{
				bBox = bBox.AddBBox(hasBounds.LocalBounds.Transform(item.WorldTransform));
			}
		}
		foreach (Terrain item2 in Scene.GetAll<Terrain>())
		{
			bool enableCollision = item2.EnableCollision;
			item2.EnableCollision = true;
			bBox = bBox.AddBBox(item2.GetWorldBounds());
			if (!enableCollision)
			{
				item2.EnableCollision = false;
			}
		}
		foreach (MeshComponent item3 in Scene.GetAll<MeshComponent>())
		{
			Model model = item3.Model;
			if (model != null)
			{
				bBox = bBox.AddBBox(model.RenderBounds.Transform(item3.WorldTransform));
			}
		}
		bBox = bBox.Translate(-WorldPosition).Grow(16f);
		Bounds = bBox;
	}

	[SourceLocation("Scene\\Components\\IndirectLighting\\IndirectLightVolume.cs", 445)]
	protected override void DrawGizmos()
	{
		if (!Gizmo.Pressed.Any)
		{
			_boundsUndoScope?.Dispose();
			_boundsUndoScope = null;
		}
		if (!Gizmo.IsSelected)
		{
			return;
		}
		if (Gizmo.Control.BoundingBox("Bounds", Bounds, out var outValue))
		{
			if (_boundsUndoScope == null)
			{
				_boundsUndoScope = Scene.Editor?.UndoScope("Resize Indirect Light Volume").WithComponentChanges(this).Push();
			}
			Bounds = outValue;
		}
		Gizmo.Draw.LineBBox(Bounds);
		Gizmo.Draw.Color = new Color(0.25f, 0.9f, 1f, 0.05f);
		Gizmo.Draw.SolidBox(Bounds);
		Gizmo.Active.FindOrCreate("lpv-grid", () => new LPVDebugGridObject(Gizmo.World)).UpdateGrid(WorldTransform, Bounds, ProbeCounts, 5f, Probes);
	}

	/// <summary>
	/// Saves texture to disk and reloads it.
	/// </summary>
	[Description("Saves texture to disk and reloads it.")]
	[SourceLocation("Scene\\Components\\IndirectLighting\\IndirectLightVolume.cs", 478)]
	private Texture SaveTexture(Texture source, string suffix, Guid bakeId, ImageFormat? format = null)
	{
		if (source == null || source.IsError)
		{
			throw new InvalidOperationException("Cannot save invalid " + suffix + " probe texture.");
		}
		SceneFolder sceneFolder = Scene.Editor.GetSceneFolder();
		string filename = $"/ddgi/{GameObject?.Name ?? "DDGIVolume"}_{suffix}_{Id}_{bakeId:N}.vtex_c";
		byte[] data = source.SaveToVtex(format);
		Texture texture = Texture.Load(sceneFolder.WriteFile(filename, data));
		if (!texture.IsValid() || texture.IsError)
		{
			throw new InvalidOperationException("Could not load saved " + suffix + " probe texture.");
		}
		return texture;
	}

	/// <summary>
	/// Builds GPU-ready structure for shader consumption.
	/// </summary>
	[Description("Builds GPU-ready structure for shader consumption.")]
	[SourceLocation("Scene\\Components\\IndirectLighting\\IndirectLightVolume.cs", 503)]
	internal bool BuildData(out DDGIVolumeGpuData data, bool usePreview = true, bool applyAdjustments = true)
	{
		data = default;
		(Texture, Texture, Texture)? tuple = (usePreview ? _bakePreview : (((Texture, Texture, Texture)?)null));
		var (texture, texture2, texture3) = tuple ?? (IrradianceTexture, DistanceTexture, RelocationTexture);
		if (!texture.IsValid() || !texture2.IsValid() || !texture3.IsValid())
		{
			return false;
		}
		Vector3Int probeCounts = ProbeCounts;
		Vector3 probeSpacing = ComputeSpacing(probeCounts);
		Matrix probeToWorldTransform = Matrix.FromTransform(WorldTransform);
		data = new DDGIVolumeGpuData
		{
			Transform = probeToWorldTransform.Inverted,
			ProbeToWorldTransform = probeToWorldTransform,
			BBoxMin = Bounds.Mins,
			BBoxMax = Bounds.Maxs,
			NormalBias = NormalBias,
			ViewBias = ViewBias,
			RuntimeContrast = (applyAdjustments ? RuntimeContrast : 1f),
			RuntimeSaturation = (applyAdjustments ? RuntimeSaturation : 1f),
			RuntimeIntensity = (applyAdjustments ? MathF.Max(RuntimeIntensity, 0f) : 1f),
			RuntimeTint = (applyAdjustments ? RuntimeTint : Color.White),
			BlendDistance = (applyAdjustments ? MathF.Max(BlendDistance, 0f) : 0f),
			ProbeSpacing = probeSpacing,
			ProbeCellDiagonal = ProbeCellDiagonal,
			ReciprocalSpacing = new Vector3((probeSpacing.x > 0f) ? (1f / probeSpacing.x) : 0f, (probeSpacing.y > 0f) ? (1f / probeSpacing.y) : 0f, (probeSpacing.z > 0f) ? (1f / probeSpacing.z) : 0f),
			ReciprocalCountsMinusOne = new Vector3((probeCounts.x > 1) ? (1f / (float)(probeCounts.x - 1)) : 0f, (probeCounts.y > 1) ? (1f / (float)(probeCounts.y - 1)) : 0f, (probeCounts.z > 1) ? (1f / (float)(probeCounts.z - 1)) : 0f),
			ProbeCounts = probeCounts,
			RelocationTextureIndex = texture3.Index,
			IrradianceTextureIndex = texture.Index,
			DistanceTextureIndex = texture2.Index,
			BakeVersion = (tuple.HasValue ? 1 : BakeVersion)
		};
		return true;
	}

	/// <summary>
	/// Calculates probe count along each axis based on volume size and density.
	/// </summary>
	[Description("Calculates probe count along each axis based on volume size and density.")]
	[SourceLocation("Scene\\Components\\IndirectLighting\\IndirectLightVolume.cs", 619)]
	private Vector3Int ComputeProbeCounts()
	{
		int maxProbes = ((ComponentVersion >= 2) ? 128 : 40);
		Vector3 size = Bounds.Size;
		float density = (float)ProbeDensity * (1f / 1024f);
		return new Vector3Int(ComputeProbeCountForAxis(size.x, density), ComputeProbeCountForAxis(size.y, density), ComputeProbeCountForAxis(size.z, density));
		int ComputeProbeCountForAxis(float axisSize, float num)
		{
			return Math.Clamp((int)MathF.Ceiling(axisSize * num) + 1, 4, maxProbes);
		}
	}

	/// <summary>
	/// Calculates spacing between probes based on volume size and probe counts.
	/// </summary>
	[Description("Calculates spacing between probes based on volume size and probe counts.")]
	[SourceLocation("Scene\\Components\\IndirectLighting\\IndirectLightVolume.cs", 644)]
	internal Vector3 ComputeSpacing(Vector3Int counts)
	{
		Vector3 size = Bounds.Size;
		return new Vector3((counts.x > 1) ? (size.x / (float)(counts.x - 1)) : 0f, (counts.y > 1) ? (size.y / (float)(counts.y - 1)) : 0f, (counts.z > 1) ? (size.z / (float)(counts.z - 1)) : 0f);
	}

	/// <summary>
	/// Gets the local-space position of a probe at the given grid index.
	/// </summary>
	[Description("Gets the local-space position of a probe at the given grid index.")]
	[SourceLocation("Scene\\Components\\IndirectLighting\\IndirectLightVolume.cs", 657)]
	internal Vector3 GetProbeLocalPosition(Vector3Int index)
	{
		Vector3 vector = ComputeSpacing(ProbeCounts);
		return Bounds.Mins + index * vector;
	}

	/// <summary>
	/// Gets the world-space position of a probe at the given grid index.
	/// </summary>
	[Description("Gets the world-space position of a probe at the given grid index.")]
	[SourceLocation("Scene\\Components\\IndirectLighting\\IndirectLightVolume.cs", 666)]
	internal Vector3 GetProbeWorldPosition(Vector3Int index)
	{
		return WorldTransform.PointToWorld(GetProbeLocalPosition(index));
	}

	/// <summary>
	/// Gets the relocated world position of a probe.
	/// </summary>
	[Description("Gets the relocated world position of a probe.")]
	[SourceLocation("Scene\\Components\\IndirectLighting\\IndirectLightVolume.cs", 674)]
	internal Vector3 GetRelocatedProbeWorldPosition(Vector3Int index)
	{
		return GetProbeWorldPosition(index) + (GetProbe(index)?.Offset ?? Vector3.Zero);
	}

	/// <summary>
	/// Gets probe data at the given grid index.
	/// </summary>
	[Description("Gets probe data at the given grid index.")]
	[SourceLocation("Scene\\Components\\IndirectLighting\\IndirectLightVolume.cs", 684)]
	internal Probe GetProbe(Vector3Int index)
	{
		if (Probes == null)
		{
			return null;
		}
		Vector3Int probeCounts = ProbeCounts;
		int num = index.x + index.y * probeCounts.x + index.z * probeCounts.x * probeCounts.y;
		if (num < 0 || num >= Probes.Length)
		{
			return null;
		}
		return Probes[num];
	}

	[Menu("Editor", "Scene/Bake Indirect Light Volumes", "snowing", Priority = 1100)]
	[SourceLocation("Scene\\Components\\IndirectLighting\\IndirectLightVolume.cs", 698)]
	public static async Task BakeAll()
	{
		if (Application.Editor != null)
		{
			IndirectLightVolume[] list = Application.Editor.Scene.GetAll<IndirectLightVolume>().ToArray();
			await Application.Editor.ForEachAsync(list, "Baking Indirect Light Volumes in Scene", (IndirectLightVolume x, CancellationToken ct) => x.BakeProbes(ct));
		}
	}

	/// <summary>
	/// Computes probe relocation offsets for all probes in the volume.
	/// Uses iterative refinement with mesh tracing.
	/// All computations are relative to probe spacing for resolution-independent behavior.
	/// </summary>
	[Button("Compute Relocation", "move")]
	[Hide]
	[Group("Probe Relocation")]
	[Description("Computes probe relocation offsets for all probes in the volume. Uses iterative refinement with mesh tracing. All computations are relative to probe spacing for resolution-independent behavior.")]
	[SourceLocation("Scene\\Components\\IndirectLighting\\IndirectLightVolume.Relocation.cs", 111)]
	public void ComputeProbeRelocation()
	{
		if (Scene?.SceneWorld == null)
		{
			return;
		}
		Vector3Int counts = ProbeCounts;
		int num = counts.x * counts.y * counts.z;
		Vector3 spacing = ComputeSpacing(counts) * WorldScale.Abs();
		Vector3[] rayDirections = GenerateSphericalDirections(128);
		float minSpacing = MathF.Min(spacing.x, MathF.Min(spacing.y, spacing.z));
		float minFrontfaceDistance = minSpacing * 0.2f;
		float maxTraceDistance = spacing.Length * 1f;
		Probes = new Probe[num];
		for (int i = 0; i < num; i++)
		{
			Probes[i] = new Probe();
		}
		Parallel.For(0, counts.z, (int z) =>
		{
			for (int j = 0; j < counts.y; j++)
			{
				for (int k = 0; k < counts.x; k++)
				{
					Vector3Int index = new Vector3Int(k, j, z);
					int num2 = k + j * counts.x + z * counts.x * counts.y;
					Vector3 probeWorldPosition = GetProbeWorldPosition(index);
					Probe probe = Probes[num2];
					Vector3 vector = Vector3.Zero;
					bool flag = true;
					for (int l = 0; (l < 12) & flag; l++)
					{
						Vector3 probePosition = probeWorldPosition + vector;
						ProbeTraceResult traceResult = TraceProbeRays(probePosition, maxTraceDistance, rayDirections);
						(Vector3 newOffset, bool shouldDeactivate) tuple = ComputeRelocationOffset(vector, traceResult, spacing, minSpacing, minFrontfaceDistance, rayDirections);
						var (vector2, _) = tuple;
						if (tuple.shouldDeactivate)
						{
							flag = false;
							break;
						}
						vector = vector2;
					}
					if (flag && InsideGeometry == InsideGeometryBehavior.Relocate)
					{
						flag = TraceProbeRays(probeWorldPosition + vector, maxTraceDistance, rayDirections).BackfaceRatio < 0.25f;
					}
					probe.Offset = vector;
					probe.Active = flag;
				}
			}
		});
		UpdateRelocationTexture();
		Scene.Get<DDGIVolumeSystem>()?.MarkDirty();
	}

	/// <summary>
	/// Traces rays in all provided directions from a probe position.
	/// Uses mesh tracing with CullMode = 0 (no culling) to detect both front and back faces.
	/// </summary>
	[Description("Traces rays in all provided directions from a probe position. Uses mesh tracing with CullMode = 0 (no culling) to detect both front and back faces.")]
	[SourceLocation("Scene\\Components\\IndirectLighting\\IndirectLightVolume.Relocation.cs", 199)]
	private ProbeTraceResult TraceProbeRays(Vector3 probePosition, float maxDistance, Vector3[] directions)
	{
		int closestBackfaceIndex = -1;
		int closestFrontfaceIndex = -1;
		int farthestFrontfaceIndex = -1;
		float num = float.MaxValue;
		float num2 = float.MaxValue;
		float num3 = 0f;
		int num4 = 0;
		int num5 = 0;
		for (int i = 0; i < directions.Length; i++)
		{
			Vector3 direction = directions[i];
			RelocationRayHit relocationRayHit = TraceRayWithBackfaceDetection(probePosition, direction, maxDistance);
			if (!relocationRayHit.DidHit)
			{
				continue;
			}
			num5++;
			if (relocationRayHit.IsBackface)
			{
				num4++;
				if (relocationRayHit.Distance < num)
				{
					num = relocationRayHit.Distance * 0.999f;
					closestBackfaceIndex = i;
				}
				continue;
			}
			if (relocationRayHit.Distance < num2)
			{
				num2 = relocationRayHit.Distance;
				closestFrontfaceIndex = i;
			}
			if (relocationRayHit.Distance > num3)
			{
				num3 = relocationRayHit.Distance;
				farthestFrontfaceIndex = i;
			}
		}
		return new ProbeTraceResult(closestBackfaceIndex, closestFrontfaceIndex, farthestFrontfaceIndex, num, num2, num3, num4, num5);
	}

	/// <summary>
	/// Traces a single ray using mesh tracing and determines if it hit a backface.
	/// Uses CullMode = 0 (no culling) to get all hits, then uses dot product with normal to detect backfaces.
	/// </summary>
	[Description("Traces a single ray using mesh tracing and determines if it hit a backface. Uses CullMode = 0 (no culling) to get all hits, then uses dot product with normal to detect backfaces.")]
	[SourceLocation("Scene\\Components\\IndirectLighting\\IndirectLightVolume.Relocation.cs", 262)]
	private RelocationRayHit TraceRayWithBackfaceDetection(Vector3 origin, Vector3 direction, float maxDistance)
	{
		Vector3 to = origin + direction * maxDistance;
		SceneTraceResult sceneTraceResult = Scene.Trace.Ray(in origin, in to).UsePhysicsWorld(hit: false).WithoutTags(RenderExcludeTags)
			.UseRenderMeshes(hitFront: true, hitBack: true)
			.Run();
		if (!sceneTraceResult.Hit)
		{
			return RelocationRayHit.Miss;
		}
		bool isBackface = Vector3.Dot(in sceneTraceResult.Normal, in direction) > 0f;
		return new RelocationRayHit(sceneTraceResult.Distance, isBackface, didHit: true);
	}

	/// <summary>
	/// Computes the new probe offset for relocation.
	/// Returns the new absolute offset (not delta) and whether the probe should be deactivated.
	/// All distances are computed relative to probe spacing.
	/// </summary>
	[Description("Computes the new probe offset for relocation. Returns the new absolute offset (not delta) and whether the probe should be deactivated. All distances are computed relative to probe spacing.")]
	[SourceLocation("Scene\\Components\\IndirectLighting\\IndirectLightVolume.Relocation.cs", 290)]
	private (Vector3 newOffset, bool shouldDeactivate) ComputeRelocationOffset(Vector3 currentOffset, ProbeTraceResult traceResult, Vector3 spacing, float minSpacing, float minFrontfaceDistance, Vector3[] directions)
	{
		float maxFactor = MathF.Min(0.45f, 0.45f);
		Vector3 vector = currentOffset;
		bool flag = false;
		float num = (traceResult.HasFrontfaceHit ? traceResult.ClosestFrontfaceDistance : float.MaxValue);
		if (traceResult.HasBackfaceHit && traceResult.BackfaceRatio >= 0.25f)
		{
			if (InsideGeometry == InsideGeometryBehavior.Deactivate)
			{
				return (newOffset: Vector3.Zero, shouldDeactivate: true);
			}
			Vector3 vector2 = directions[traceResult.ClosestBackfaceIndex];
			float num2 = traceResult.ClosestBackfaceDistance + minFrontfaceDistance * 0.5f;
			vector = currentOffset + vector2 * num2;
			flag = true;
		}
		else if (traceResult.HasFrontfaceHit && num < minFrontfaceDistance)
		{
			if (traceResult.HasFarthestFrontface && traceResult.FarthestFrontfaceIndex != traceResult.ClosestFrontfaceIndex)
			{
				Vector3 a = directions[traceResult.ClosestFrontfaceIndex];
				Vector3 b = directions[traceResult.FarthestFrontfaceIndex];
				if (Vector3.Dot(in a, in b) <= 0f)
				{
					float num3 = MathF.Min(traceResult.FarthestFrontfaceDistance, minSpacing);
					vector = currentOffset + b * num3;
					flag = true;
				}
			}
			if (!flag && InsideGeometry == InsideGeometryBehavior.Deactivate)
			{
				return (newOffset: Vector3.Zero, shouldDeactivate: true);
			}
		}
		else if (num > minFrontfaceDistance && currentOffset.LengthSquared > 0f)
		{
			float num4 = MathF.Min(num - minFrontfaceDistance, currentOffset.Length);
			if (num4 > 0f)
			{
				Vector3 vector3 = -currentOffset.Normal;
				vector = currentOffset + vector3 * num4;
				flag = true;
			}
		}
		if (flag && IsWithinEllipsoidLimit(vector, spacing, maxFactor))
		{
			return (newOffset: vector, shouldDeactivate: false);
		}
		return (newOffset: currentOffset, shouldDeactivate: false);
	}

	/// <summary>
	/// Returns true if the offset lies within the ellipsoid defined by spacing and the max factor.
	/// </summary>
	[Description("Returns true if the offset lies within the ellipsoid defined by spacing and the max factor.")]
	[SourceLocation("Scene\\Components\\IndirectLighting\\IndirectLightVolume.Relocation.cs", 353)]
	private bool IsWithinEllipsoidLimit(Vector3 offset, Vector3 spacing, float maxFactor)
	{
		offset = WorldRotation.Inverse * offset;
		Vector3 vector = new Vector3((spacing.x > 0f) ? (offset.x / spacing.x) : 0f, (spacing.y > 0f) ? (offset.y / spacing.y) : 0f, (spacing.z > 0f) ? (offset.z / spacing.z) : 0f);
		float num = maxFactor * maxFactor;
		return vector.LengthSquared <= num;
	}

	/// <summary>
	/// Clears all probe relocation offsets.
	/// </summary>
	[Button("Clear Relocation", "clear")]
	[Hide]
	[Group("Probe Relocation")]
	[Description("Clears all probe relocation offsets.")]
	[SourceLocation("Scene\\Components\\IndirectLighting\\IndirectLightVolume.Relocation.cs", 370)]
	public void ClearProbeRelocation()
	{
		Probes = null;
		RelocationTexture?.Dispose();
		RelocationTexture = null;
		Scene?.Get<DDGIVolumeSystem>()?.MarkDirty();
	}

	/// <summary>
	/// Generates evenly distributed directions on a sphere using spherical Fibonacci.
	/// This provides a quasi-uniform distribution with good coverage properties.
	/// </summary>
	[Description("Generates evenly distributed directions on a sphere using spherical Fibonacci. This provides a quasi-uniform distribution with good coverage properties.")]
	[SourceLocation("Scene\\Components\\IndirectLighting\\IndirectLightVolume.Relocation.cs", 384)]
	private static Vector3[] GenerateSphericalDirections(int count)
	{
		Vector3[] array = new Vector3[count];
		float num = (1f + MathF.Sqrt(5f)) / 2f;
		float num2 = (float)Math.PI * 2f * num;
		for (int i = 0; i < count; i++)
		{
			float num3 = (float)i / (float)count;
			float x = MathF.Acos(1f - 2f * num3);
			float x2 = num2 * (float)i;
			float num4 = MathF.Sin(x);
			array[i] = new Vector3(num4 * MathF.Cos(x2), num4 * MathF.Sin(x2), MathF.Cos(x));
		}
		return array;
	}

	/// <summary>
	/// Loads probe data from an existing relocation texture.
	/// This restores the Probes array after a scene reload.
	/// </summary>
	[Description("Loads probe data from an existing relocation texture. This restores the Probes array after a scene reload.")]
	[SourceLocation("Scene\\Components\\IndirectLighting\\IndirectLightVolume.Relocation.cs", 411)]
	private void LoadProbesFromRelocationTexture()
	{
		if (!Application.IsEditor || Probes != null || !RelocationTexture.IsValid())
		{
			return;
		}
		Vector3Int probeCounts = ProbeCounts;
		int num = probeCounts.x * probeCounts.y * probeCounts.z;
		if (RelocationTexture.Width != probeCounts.x || RelocationTexture.Height != probeCounts.y || RelocationTexture.Depth != probeCounts.z)
		{
			GlobalSystemNamespace.Log.Warning($"RelocationTexture dimensions ({RelocationTexture.Width}x{RelocationTexture.Height}x{RelocationTexture.Depth}) don't match probe counts ({probeCounts}), skipping load");
			return;
		}
		Half[] array = new Half[num * 4];
		RelocationTexture.GetPixels3D((X: 0, Y: 0, Z: 0, Width: probeCounts.x, Height: probeCounts.y, Depth: probeCounts.z), 0, array.AsSpan(), ImageFormat.RGBA16161616F);
		Probes = new Probe[num];
		for (int i = 0; i < num; i++)
		{
			int num2 = i * 4;
			Probes[i] = new Probe
			{
				Offset = new Vector3((float)array[num2], (float)array[num2 + 1], (float)array[num2 + 2]),
				Active = ((float)array[num2 + 3] > 0.5f)
			};
		}
	}

	/// <summary>
	/// Creates or updates the relocation texture from CPU offset data.
	/// </summary>
	[Description("Creates or updates the relocation texture from CPU offset data.")]
	[SourceLocation("Scene\\Components\\IndirectLighting\\IndirectLightVolume.Relocation.cs", 457)]
	private void UpdateRelocationTexture()
	{
		if (Probes != null)
		{
			Vector3Int probeCounts = ProbeCounts;
			GeneratedRelocationTexture?.Dispose();
			GeneratedRelocationTexture = Texture.CreateVolume(probeCounts.x, probeCounts.y, probeCounts.z, ImageFormat.RGBA16161616F).WithName("DDGIRelocation").Finish();
			Half[] array = new Half[probeCounts.x * probeCounts.y * probeCounts.z * 4];
			for (int i = 0; i < Probes.Length; i++)
			{
				Probe probe = Probes[i];
				int num = i * 4;
				array[num] = (Half)probe.Offset.x;
				array[num + 1] = (Half)probe.Offset.y;
				array[num + 2] = (Half)probe.Offset.z;
				array[num + 3] = (Half)(probe.Active ? 1f : 0f);
			}
			GeneratedRelocationTexture.Update(array);
		}
	}
}
