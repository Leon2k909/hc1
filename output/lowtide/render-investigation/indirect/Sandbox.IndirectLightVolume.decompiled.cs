using System;
using System.Linq;
using System.Runtime.CompilerServices;
using System.Threading;
using System.Threading.Tasks;
using Editor;
using Facepunch.ActionGraphs;
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
[Facepunch.ActionGraphs.Title("Indirect Light Volume (DDGI)")]
[Category("Light")]
[Facepunch.ActionGraphs.Icon("grid_view")]
[EditorHandle("materials/gizmo/lpv.png")]
[Alias(new string[] { "DDGIVolume" })]
[Facepunch.ActionGraphs.Description("Dynamic Diffuse Global Illumination volume that provides indirect lighting using a 3D probe grid. Probes store irradiance and distance data in volume textures that can be sampled by shaders.")]
[SourceLocation("Scene\\Components\\IndirectLighting\\IndirectLightVolume.cs", 13)]
[SourceLocation("Scene\\Components\\IndirectLighting\\IndirectLightVolume.Relocation.cs", 10)]
public sealed class IndirectLightVolume : Component, Component.ExecuteInEditor, Component.DontExecuteOnServer
{
	/// <summary>
	/// Behavior when a probe is detected inside geometry.
	/// Relocation moves the probe out of geometry to reduce artifacts, while Deactivate simply disables the occluded probe, sealing leaks entirely.
	/// </summary>
	[Facepunch.ActionGraphs.Description("Behavior when a probe is detected inside geometry. Relocation moves the probe out of geometry to reduce artifacts, while Deactivate simply disables the occluded probe, sealing leaks entirely.")]
	public enum InsideGeometryBehavior
	{
		/// <summary>
		/// Probe is deactivated and won't contribute to lighting.
		/// </summary>
		[Facepunch.ActionGraphs.Icon("block")]
		[Facepunch.ActionGraphs.Description("Probe is deactivated and won't contribute to lighting.")]
		Deactivate,
		/// <summary>
		/// Probe is relocated to escape the geometry.
		/// </summary>
		[Facepunch.ActionGraphs.Icon("open_with")]
		[Facepunch.ActionGraphs.Description("Probe is relocated to escape the geometry.")]
		Relocate
	}

	/// <summary>
	/// Per-probe data including position offset and active state.
	/// </summary>
	[Facepunch.ActionGraphs.Description("Per-probe data including position offset and active state.")]
	[SourceLocation("Scene\\Components\\IndirectLighting\\IndirectLightVolume.cs", 43)]
	public sealed class Probe
	{
		[SourceLocation("Scene\\Components\\IndirectLighting\\IndirectLightVolume.cs", 45)]
		public Vector3 Offset { get; set; }

		[DefaultValue(true)]
		[SourceLocation("Scene\\Components\\IndirectLighting\\IndirectLightVolume.cs", 46)]
		public bool Active { get; set; } = true;
	}

	internal struct DDGIVolumeGpuData
	{
		[SourceLocation("Scene\\Components\\IndirectLighting\\IndirectLightVolume.cs", 395)]
		public Matrix Transform;

		[SourceLocation("Scene\\Components\\IndirectLighting\\IndirectLightVolume.cs", 396)]
		public Vector3 BBoxMin;

		[SourceLocation("Scene\\Components\\IndirectLighting\\IndirectLightVolume.cs", 397)]
		public Vector3 BBoxMax;

		[SourceLocation("Scene\\Components\\IndirectLighting\\IndirectLightVolume.cs", 398)]
		public float NormalBias;

		[SourceLocation("Scene\\Components\\IndirectLighting\\IndirectLightVolume.cs", 399)]
		public Vector3 ProbeSpacing;

		[SourceLocation("Scene\\Components\\IndirectLighting\\IndirectLightVolume.cs", 400)]
		public float BlendDistance;

		[SourceLocation("Scene\\Components\\IndirectLighting\\IndirectLightVolume.cs", 401)]
		public Vector3 ReciprocalSpacing;

		[SourceLocation("Scene\\Components\\IndirectLighting\\IndirectLightVolume.cs", 402)]
		public int IrradianceTextureIndex;

		[SourceLocation("Scene\\Components\\IndirectLighting\\IndirectLightVolume.cs", 403)]
		public Vector3 ReciprocalCountsMinusOne;

		[SourceLocation("Scene\\Components\\IndirectLighting\\IndirectLightVolume.cs", 404)]
		public int DistanceTextureIndex;

		[SourceLocation("Scene\\Components\\IndirectLighting\\IndirectLightVolume.cs", 405)]
		public Vector3Int ProbeCounts;

		[SourceLocation("Scene\\Components\\IndirectLighting\\IndirectLightVolume.cs", 406)]
		public int RelocationTextureIndex;
	}

	/// <summary>
	/// Result of tracing a single ray for relocation purposes.
	/// </summary>
	[Description("Result of tracing a single ray for relocation purposes.")]
	private readonly struct RelocationRayHit(float distance, bool isBackface, bool didHit)
	{
		[SourceLocation("Scene\\Components\\IndirectLighting\\IndirectLightVolume.Relocation.cs", 58)]
		public readonly float Distance = distance;

		[SourceLocation("Scene\\Components\\IndirectLighting\\IndirectLightVolume.Relocation.cs", 59)]
		public readonly bool IsBackface = isBackface;

		[SourceLocation("Scene\\Components\\IndirectLighting\\IndirectLightVolume.Relocation.cs", 60)]
		public readonly bool DidHit = didHit;

		[SourceLocation("Scene\\Components\\IndirectLighting\\IndirectLightVolume.Relocation.cs", 69)]
		public static RelocationRayHit Miss => new RelocationRayHit(float.MaxValue, isBackface: false, didHit: false);
	}

	/// <summary>
	/// Aggregated statistics from tracing all rays for a single probe.
	/// </summary>
	[Description("Aggregated statistics from tracing all rays for a single probe.")]
	private readonly struct ProbeTraceResult(int closestBackfaceIndex, int closestFrontfaceIndex, int farthestFrontfaceIndex, float closestBackfaceDistance, float closestFrontfaceDistance, float farthestFrontfaceDistance, int backfaceCount, int totalHits)
	{
		[SourceLocation("Scene\\Components\\IndirectLighting\\IndirectLightVolume.Relocation.cs", 77)]
		public readonly int ClosestBackfaceIndex = closestBackfaceIndex;

		[SourceLocation("Scene\\Components\\IndirectLighting\\IndirectLightVolume.Relocation.cs", 78)]
		public readonly int ClosestFrontfaceIndex = closestFrontfaceIndex;

		[SourceLocation("Scene\\Components\\IndirectLighting\\IndirectLightVolume.Relocation.cs", 79)]
		public readonly int FarthestFrontfaceIndex = farthestFrontfaceIndex;

		[SourceLocation("Scene\\Components\\IndirectLighting\\IndirectLightVolume.Relocation.cs", 80)]
		public readonly float ClosestBackfaceDistance = closestBackfaceDistance;

		[SourceLocation("Scene\\Components\\IndirectLighting\\IndirectLightVolume.Relocation.cs", 81)]
		public readonly float ClosestFrontfaceDistance = closestFrontfaceDistance;

		[SourceLocation("Scene\\Components\\IndirectLighting\\IndirectLightVolume.Relocation.cs", 82)]
		public readonly float FarthestFrontfaceDistance = farthestFrontfaceDistance;

		[SourceLocation("Scene\\Components\\IndirectLighting\\IndirectLightVolume.Relocation.cs", 83)]
		public readonly int BackfaceCount = backfaceCount;

		[SourceLocation("Scene\\Components\\IndirectLighting\\IndirectLightVolume.Relocation.cs", 84)]
		public readonly int TotalHits = totalHits;

		[SourceLocation("Scene\\Components\\IndirectLighting\\IndirectLightVolume.Relocation.cs", 106)]
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

		[SourceLocation("Scene\\Components\\IndirectLighting\\IndirectLightVolume.Relocation.cs", 107)]
		public bool HasBackfaceHit => ClosestBackfaceIndex >= 0;

		[SourceLocation("Scene\\Components\\IndirectLighting\\IndirectLightVolume.Relocation.cs", 108)]
		public bool HasFrontfaceHit => ClosestFrontfaceIndex >= 0;

		[SourceLocation("Scene\\Components\\IndirectLighting\\IndirectLightVolume.Relocation.cs", 109)]
		public bool HasFarthestFrontface => FarthestFrontfaceIndex >= 0;
	}

	/// <summary>
	/// Cancellation source for the current bake operation.
	/// </summary>
	[SourceLocation("Scene\\Components\\IndirectLighting\\IndirectLightVolume.cs", 158)]
	private CancellationTokenSource _bakeCts;

	[SourceLocation("Scene\\Components\\IndirectLighting\\IndirectLightVolume.cs", 292)]
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
	/// How far to trace rays as a multiple of the minimum probe spacing.
	/// </summary>
	[SourceLocation("Scene\\Components\\IndirectLighting\\IndirectLightVolume.Relocation.cs", 40)]
	private const float TraceDistanceFactor = 1f;

	/// <summary>
	/// CPU-side probe data indexed by flattened probe index.
	/// </summary>
	[Facepunch.ActionGraphs.Description("CPU-side probe data indexed by flattened probe index.")]
	[SourceLocation("Scene\\Components\\IndirectLighting\\IndirectLightVolume.cs", 52)]
	internal Probe[] Probes { get; set; }

	/// <summary>
	/// World-space bounding box that defines the volume coverage area.
	/// </summary>
	[Property]
	[Facepunch.ActionGraphs.Description("World-space bounding box that defines the volume coverage area.")]
	[SourceLocation("Scene\\Components\\IndirectLighting\\IndirectLightVolume.cs", 61)]
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
	/// Number of probes per 1024 world units. Higher values increase probe resolution.
	/// </summary>
	[Property]
	[Range(1f, 15f)]
	[DefaultValue(8)]
	[Facepunch.ActionGraphs.Description("Number of probes per 1024 world units. Higher values increase probe resolution.")]
	[SourceLocation("Scene\\Components\\IndirectLighting\\IndirectLightVolume.cs", 77)]
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
	/// Bias applied along surface normals to prevent self-occlusion artifacts.
	/// </summary>
	[Facepunch.ActionGraphs.Group("Advanced Settings")]
	[Property]
	[Range(-0f, 50f)]
	[DefaultValue(5f)]
	[Facepunch.ActionGraphs.Description("Bias applied along surface normals to prevent self-occlusion artifacts.")]
	[SourceLocation("Scene\\Components\\IndirectLighting\\IndirectLightVolume.cs", 93)]
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
	} = 5f;

	/// <summary>
	/// Controls how much less energy to conserve during probe integration.
	/// Higher values give a harsher, more contrasty look.
	/// </summary>
	[Property]
	[Range(1f, 2f)]
	[Facepunch.ActionGraphs.Group("Advanced Settings")]
	[DefaultValue(1f)]
	[Facepunch.ActionGraphs.Description("Controls how much less energy to conserve during probe integration. Higher values give a harsher, more contrasty look.")]
	[SourceLocation("Scene\\Components\\IndirectLighting\\IndirectLightVolume.cs", 111)]
	public float Contrast
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
	/// Objects with any of these tags will be excluded when baking probes for this volume.
	/// </summary>
	[Property]
	[Facepunch.ActionGraphs.Group("Advanced Settings")]
	[Facepunch.ActionGraphs.Description("Objects with any of these tags will be excluded when baking probes for this volume.")]
	[SourceLocation("Scene\\Components\\IndirectLighting\\IndirectLightVolume.cs", 128)]
	public TagSet RenderExcludeTags { get; set; } = new TagSet();

	/// <summary>
	/// Calculated probe count along each axis based on bounds and density.
	/// </summary>
	[Facepunch.ActionGraphs.Description("Calculated probe count along each axis based on bounds and density.")]
	[SourceLocation("Scene\\Components\\IndirectLighting\\IndirectLightVolume.cs", 135)]
	public Vector3Int ProbeCounts => ComputeProbeCounts();

	/// <summary>
	/// Volume texture storing probe irradiance data (color).
	/// </summary>
	[Property]
	[Hide]
	[Facepunch.ActionGraphs.Description("Volume texture storing probe irradiance data (color).")]
	[SourceLocation("Scene\\Components\\IndirectLighting\\IndirectLightVolume.cs", 140)]
	public Texture IrradianceTexture { get; set; }

	/// <summary>
	/// Volume texture storing probe distance/visibility data.
	/// </summary>
	[Property]
	[Hide]
	[Facepunch.ActionGraphs.Description("Volume texture storing probe distance/visibility data.")]
	[SourceLocation("Scene\\Components\\IndirectLighting\\IndirectLightVolume.cs", 146)]
	public Texture DistanceTexture { get; set; }

	/// <summary>
	/// Volume texture storing probe relocation offsets (XYZ = offset, W = active).
	/// </summary>
	[Property]
	[Hide]
	[Facepunch.ActionGraphs.Description("Volume texture storing probe relocation offsets (XYZ = offset, W = active).")]
	[SourceLocation("Scene\\Components\\IndirectLighting\\IndirectLightVolume.cs", 152)]
	public Texture RelocationTexture { get; set; }

	[Expose]
	[Hide]
	[SourceLocation("Scene\\Components\\IndirectLighting\\IndirectLightVolume.cs", 193)]
	internal bool IsSceneSaved => Scene?.Editor?.GetSceneFolder() != null;

	/// <summary>
	/// How to handle probes detected inside geometry.
	/// </summary>
	[Property]
	[Group("Advanced Settings")]
	[DefaultValue(InsideGeometryBehavior.Relocate)]
	[Description("How to handle probes detected inside geometry.")]
	[SourceLocation("Scene\\Components\\IndirectLighting\\IndirectLightVolume.Relocation.cs", 45)]
	public InsideGeometryBehavior InsideGeometry { get; set; } = InsideGeometryBehavior.Relocate;

	/// <summary>
	/// Volume texture storing probe relocation offsets (XYZ = offset, W = active).
	/// </summary>
	[Description("Volume texture storing probe relocation offsets (XYZ = offset, W = active).")]
	[SourceLocation("Scene\\Components\\IndirectLighting\\IndirectLightVolume.Relocation.cs", 51)]
	private Texture GeneratedRelocationTexture { get; set; }

	[SourceLocation("Scene\\Components\\IndirectLighting\\IndirectLightVolume.cs", 164)]
	protected override void OnEnabled()
	{
		base.OnEnabled();
		GameTransform transform = Transform;
		transform.OnTransformChanged = (Action)Delegate.Combine(transform.OnTransformChanged, new Action(MarkDirty));
		LoadProbesFromRelocationTexture();
		MarkDirty();
	}

	[SourceLocation("Scene\\Components\\IndirectLighting\\IndirectLightVolume.cs", 173)]
	protected override void OnDisabled()
	{
		base.OnDisabled();
		GameTransform transform = Transform;
		transform.OnTransformChanged = (Action)Delegate.Remove(transform.OnTransformChanged, new Action(MarkDirty));
		_bakeCts?.Cancel();
		_bakeCts?.Dispose();
		_bakeCts = null;
		MarkDirty();
	}

	[SourceLocation("Scene\\Components\\IndirectLighting\\IndirectLightVolume.cs", 185)]
	private void MarkDirty()
	{
		Scene.Get<DDGIVolumeSystem>()?.MarkDirty();
	}

	[ShowIf("IsSceneSaved", false)]
	[InfoBox("Save the scene before baking indirect light volumes.", "warning", EditorTint.Yellow)]
	[Button("Bake", "lightbulb")]
	[ReadOnly]
	[SourceLocation("Scene\\Components\\IndirectLighting\\IndirectLightVolume.cs", 196)]
	public void BakeProbesUnavailableMessage()
	{
	}

	/// <summary>
	/// Starts the probe baking process to capture lighting into the volume textures.
	/// </summary>
	[ShowIf("IsSceneSaved", true)]
	[Button("Bake", "lightbulb")]
	[Facepunch.ActionGraphs.Description("Starts the probe baking process to capture lighting into the volume textures.")]
	[SourceLocation("Scene\\Components\\IndirectLighting\\IndirectLightVolume.cs", 204)]
	public async Task BakeProbes(CancellationToken ct = default(CancellationToken))
	{
		if (Scene?.SceneWorld == null)
		{
			return;
		}
		_bakeCts?.Cancel();
		_bakeCts?.Dispose();
		_bakeCts = new CancellationTokenSource();
		ComputeProbeRelocation();
		using DDGIProbeUpdaterCubemapper updater = new DDGIProbeUpdaterCubemapper(this);
		IrradianceTexture = updater.GeneratedIrradianceTexture;
		DistanceTexture = updater.GeneratedDistanceTexture;
		RelocationTexture = GeneratedRelocationTexture;
		Scene.Get<DDGIVolumeSystem>()?.MarkDirty();
		InlineArray3<CancellationToken> buffer = default;
		buffer[0] = ct;
		buffer[1] = _bakeCts.Token;
		buffer[2] = GameObject.EnabledToken;
		using CancellationTokenSource linkedCt = CancellationTokenSource.CreateLinkedTokenSource(buffer);
		if (!(await updater.RunAsync(linkedCt.Token)))
		{
			IrradianceTexture = null;
			DistanceTexture = null;
			RelocationTexture = null;
		}
		else
		{
			Graphics.FlushGPU();
			IrradianceTexture = SaveTexture(updater.GeneratedIrradianceTexture, "Irradiance");
			DistanceTexture = SaveTexture(updater.GeneratedDistanceTexture, "Distance", ImageFormat.BC6H);
			RelocationTexture = SaveTexture(GeneratedRelocationTexture, "Relocation", ImageFormat.RGBA16161616F);
		}
		Scene.Get<DDGIVolumeSystem>()?.MarkDirty();
	}

	/// <summary>
	/// Automatically sizes the volume to encompass all scene geometry.
	/// </summary>
	[Button("Fit to Scene Bounds", "fullscreen")]
	[Facepunch.ActionGraphs.Description("Automatically sizes the volume to encompass all scene geometry.")]
	[SourceLocation("Scene\\Components\\IndirectLighting\\IndirectLightVolume.cs", 251)]
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

	[SourceLocation("Scene\\Components\\IndirectLighting\\IndirectLightVolume.cs", 294)]
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
		Gizmo.Active.FindOrCreate("lpv-grid", () => new LPVDebugGridObject(Gizmo.World)).UpdateGrid(WorldTransform, Bounds, ProbeCounts, 10f, Probes);
	}

	/// <summary>
	/// Saves texture to disk and reloads it.
	/// </summary>
	[Facepunch.ActionGraphs.Description("Saves texture to disk and reloads it.")]
	[SourceLocation("Scene\\Components\\IndirectLighting\\IndirectLightVolume.cs", 327)]
	private Texture SaveTexture(Texture source, string suffix, ImageFormat? format = null)
	{
		if (source == null || source.IsError)
		{
			return source;
		}
		if (Scene.Editor == null)
		{
			return source;
		}
		SceneFolder sceneFolder = Scene.Editor.GetSceneFolder();
		string filename = $"/ddgi/{GameObject?.Name ?? "DDGIVolume"}_{suffix}_{Id}.vtex_c";
		byte[] data = source.SaveToVtex(format);
		Texture texture = Texture.Load(sceneFolder.WriteFile(filename, data));
		if (texture != null)
		{
			source.Dispose();
		}
		if (texture == null)
		{
			texture = source;
		}
		return texture;
	}

	/// <summary>
	/// Builds GPU-ready structure for shader consumption.
	/// </summary>
	[Facepunch.ActionGraphs.Description("Builds GPU-ready structure for shader consumption.")]
	[SourceLocation("Scene\\Components\\IndirectLighting\\IndirectLightVolume.cs", 355)]
	internal bool BuildData(out DDGIVolumeGpuData data)
	{
		data = default;
		if (!IrradianceTexture.IsValid() || !DistanceTexture.IsValid() || !RelocationTexture.IsValid())
		{
			return false;
		}
		Vector3Int probeCounts = ProbeCounts;
		Vector3 probeSpacing = ComputeSpacing(probeCounts);
		data = new DDGIVolumeGpuData
		{
			Transform = Matrix.FromTransform(WorldTransform).Inverted,
			BBoxMin = Bounds.Mins,
			BBoxMax = Bounds.Maxs,
			NormalBias = NormalBias,
			ProbeSpacing = probeSpacing,
			BlendDistance = 0f,
			ReciprocalSpacing = new Vector3((probeSpacing.x > 0f) ? (1f / probeSpacing.x) : 0f, (probeSpacing.y > 0f) ? (1f / probeSpacing.y) : 0f, (probeSpacing.z > 0f) ? (1f / probeSpacing.z) : 0f),
			ReciprocalCountsMinusOne = new Vector3((probeCounts.x > 1) ? (1f / (float)(probeCounts.x - 1)) : 0f, (probeCounts.y > 1) ? (1f / (float)(probeCounts.y - 1)) : 0f, (probeCounts.z > 1) ? (1f / (float)(probeCounts.z - 1)) : 0f),
			ProbeCounts = probeCounts,
			RelocationTextureIndex = RelocationTexture.Index,
			IrradianceTextureIndex = IrradianceTexture.Index,
			DistanceTextureIndex = DistanceTexture.Index
		};
		return true;
	}

	/// <summary>
	/// Calculates probe count along each axis based on volume size and density.
	/// </summary>
	[Facepunch.ActionGraphs.Description("Calculates probe count along each axis based on volume size and density.")]
	[SourceLocation("Scene\\Components\\IndirectLighting\\IndirectLightVolume.cs", 416)]
	private Vector3Int ComputeProbeCounts()
	{
		Vector3 size = Bounds.Size;
		float density = (float)ProbeDensity * (1f / 1024f);
		return new Vector3Int(ComputeProbeCountForAxis(size.x, density), ComputeProbeCountForAxis(size.y, density), ComputeProbeCountForAxis(size.z, density));
		static int ComputeProbeCountForAxis(float axisSize, float num)
		{
			return Math.Clamp((int)MathF.Ceiling(axisSize * num) + 1, 4, 40);
		}
	}

	/// <summary>
	/// Calculates spacing between probes based on volume size and probe counts.
	/// </summary>
	[Facepunch.ActionGraphs.Description("Calculates spacing between probes based on volume size and probe counts.")]
	[SourceLocation("Scene\\Components\\IndirectLighting\\IndirectLightVolume.cs", 441)]
	internal Vector3 ComputeSpacing(Vector3Int counts)
	{
		Vector3 size = Bounds.Size;
		return new Vector3((counts.x > 1) ? (size.x / (float)(counts.x - 1)) : 0f, (counts.y > 1) ? (size.y / (float)(counts.y - 1)) : 0f, (counts.z > 1) ? (size.z / (float)(counts.z - 1)) : 0f);
	}

	/// <summary>
	/// Gets the local-space position of a probe at the given grid index.
	/// </summary>
	[Facepunch.ActionGraphs.Description("Gets the local-space position of a probe at the given grid index.")]
	[SourceLocation("Scene\\Components\\IndirectLighting\\IndirectLightVolume.cs", 454)]
	internal Vector3 GetProbeLocalPosition(Vector3Int index)
	{
		Vector3 vector = ComputeSpacing(ProbeCounts);
		return Bounds.Mins + index * vector;
	}

	/// <summary>
	/// Gets the world-space position of a probe at the given grid index.
	/// </summary>
	[Facepunch.ActionGraphs.Description("Gets the world-space position of a probe at the given grid index.")]
	[SourceLocation("Scene\\Components\\IndirectLighting\\IndirectLightVolume.cs", 463)]
	internal Vector3 GetProbeWorldPosition(Vector3Int index)
	{
		return WorldTransform.PointToWorld(GetProbeLocalPosition(index));
	}

	/// <summary>
	/// Gets the relocated world position of a probe.
	/// </summary>
	[Facepunch.ActionGraphs.Description("Gets the relocated world position of a probe.")]
	[SourceLocation("Scene\\Components\\IndirectLighting\\IndirectLightVolume.cs", 471)]
	internal Vector3 GetRelocatedProbeWorldPosition(Vector3Int index)
	{
		return GetProbeWorldPosition(index) + (GetProbe(index)?.Offset ?? Vector3.Zero);
	}

	/// <summary>
	/// Gets probe data at the given grid index.
	/// </summary>
	[Facepunch.ActionGraphs.Description("Gets probe data at the given grid index.")]
	[SourceLocation("Scene\\Components\\IndirectLighting\\IndirectLightVolume.cs", 481)]
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
	[SourceLocation("Scene\\Components\\IndirectLighting\\IndirectLightVolume.cs", 495)]
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
	[SourceLocation("Scene\\Components\\IndirectLighting\\IndirectLightVolume.Relocation.cs", 117)]
	public void ComputeProbeRelocation()
	{
		if (Scene?.SceneWorld == null)
		{
			return;
		}
		Vector3Int counts = ProbeCounts;
		int num = counts.x * counts.y * counts.z;
		Vector3 spacing = ComputeSpacing(counts);
		Vector3[] rayDirections = GenerateSphericalDirections(128);
		float minSpacing = MathF.Min(spacing.x, MathF.Min(spacing.y, spacing.z));
		float minFrontfaceDistance = minSpacing * 0.2f;
		float maxTraceDistance = minSpacing * 1f;
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
	[SourceLocation("Scene\\Components\\IndirectLighting\\IndirectLightVolume.Relocation.cs", 196)]
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
	[SourceLocation("Scene\\Components\\IndirectLighting\\IndirectLightVolume.Relocation.cs", 259)]
	private RelocationRayHit TraceRayWithBackfaceDetection(Vector3 origin, Vector3 direction, float maxDistance)
	{
		Vector3 to = origin + direction * maxDistance;
		SceneTraceResult sceneTraceResult = Scene.Trace.Ray(in origin, in to).UsePhysicsWorld(hit: false).UseRenderMeshes(hitFront: true, hitBack: true)
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
	[SourceLocation("Scene\\Components\\IndirectLighting\\IndirectLightVolume.Relocation.cs", 286)]
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
	[SourceLocation("Scene\\Components\\IndirectLighting\\IndirectLightVolume.Relocation.cs", 349)]
	private static bool IsWithinEllipsoidLimit(Vector3 offset, Vector3 spacing, float maxFactor)
	{
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
	[SourceLocation("Scene\\Components\\IndirectLighting\\IndirectLightVolume.Relocation.cs", 364)]
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
	[SourceLocation("Scene\\Components\\IndirectLighting\\IndirectLightVolume.Relocation.cs", 378)]
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
	[SourceLocation("Scene\\Components\\IndirectLighting\\IndirectLightVolume.Relocation.cs", 405)]
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
	[SourceLocation("Scene\\Components\\IndirectLighting\\IndirectLightVolume.Relocation.cs", 451)]
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
