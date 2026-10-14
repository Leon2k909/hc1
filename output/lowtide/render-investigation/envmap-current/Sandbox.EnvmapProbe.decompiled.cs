using System;
using System.Linq;
using System.Text.Json.Nodes;
using System.Threading;
using System.Threading.Tasks;
using Editor;
using Sandbox.Diagnostics;
using Sandbox.Internal;

namespace Sandbox;

/// <summary>
/// A cubemap probe that captures the environment around it.
/// </summary>
[Description("A cubemap probe that captures the environment around it.")]
[SourceLocation("Scene\\Components\\Light\\EnvmapProbe.Baking.cs", 6)]
[Expose]
[Title("Envmap Probe")]
[Category("Light")]
[Icon("radio_button_unchecked")]
[Alias(new string[] { "EnvmapComponent" })]
[SourceLocation("Scene\\Components\\Light\\EnvmapProbe.cs", 8)]
[SourceLocation("Scene\\Components\\Light\\EnvmapProbe.Gizmo.cs", 3)]
[SourceLocation("Scene\\Components\\Light\\EnvmapProbe.Upgrade.cs", 5)]
public sealed class EnvmapProbe : Component, Component.ExecuteInEditor, Component.DontExecuteOnServer, IUpdateSubscriber
{
	[Expose]
	public enum EnvmapProbeMode
	{
		[Icon("\ud83e\udd56")]
		Baked,
		[Icon("\ud83d\udcf9")]
		Realtime,
		[Icon("\ud83d\udcc4")]
		CustomTexture
	}

	[Expose]
	public enum CubemapResolution
	{
		[Title("128x128")]
		Small = 0x80,
		[Title("256x256")]
		Medium = 0x100,
		[Title("512x512")]
		Large = 0x200,
		[Title("1024x1024")]
		Huge = 0x400
	}

	[Expose]
	public enum CubemapDynamicUpdate
	{
		/// <summary>
		/// Update once, when the cubemap is enabled
		/// </summary>
		[Description("Update once, when the cubemap is enabled")]
		OnEnabled,
		/// <summary>
		/// Update every frame (slow, not recommended)
		/// </summary>
		[Description("Update every frame (slow, not recommended)")]
		EveryFrame,
		/// <summary>
		/// Update every x frames
		/// </summary>
		[Description("Update every x frames")]
		FrameInterval,
		/// <summary>
		/// Update on a time based interval
		/// </summary>
		[Description("Update on a time based interval")]
		TimeInterval
	}

	[SourceLocation("Scene\\Components\\Light\\EnvmapProbe.cs", 68)]
	private SceneCubemap _sceneObject;

	[SourceLocation("Scene\\Components\\Light\\EnvmapProbe.cs", 69)]
	private Texture _dynamicTexture;

	[SourceLocation("Scene\\Components\\Light\\EnvmapProbe.cs", 70)]
	private int _bouncesLeft;

	[SourceLocation("Scene\\Components\\Light\\EnvmapProbe.cs", 71)]
	private int _queuedFrames;

	[SourceLocation("Scene\\Components\\Light\\EnvmapProbe.cs", 72)]
	private float _queuedTime;

	[SourceLocation("Scene\\Components\\Light\\EnvmapProbe.cs", 74)]
	public bool Dirty;

	[Property]
	[EnumButtonGroup]
	[WideMode(HasLabel = false)]
	[SourceLocation("Scene\\Components\\Light\\EnvmapProbe.cs", 76)]
	public EnvmapProbeMode Mode
	{
		get;
		set
		{
			if (field != value)
			{
				field = value;
				UpdateSceneObject();
			}
		}
	}

	[Property]
	[Space(22f)]
	[SourceLocation("Scene\\Components\\Light\\EnvmapProbe.cs", 89)]
	public SceneCubemap.ProjectionMode Projection
	{
		get;
		set
		{
			if (field != value)
			{
				field = value;
				UpdateSceneObject();
			}
		}
	}

	[Property]
	[SourceLocation("Scene\\Components\\Light\\EnvmapProbe.cs", 102)]
	public Color TintColor
	{
		get;
		set
		{
			if (!(field == value))
			{
				field = value;
				UpdateSceneObject();
			}
		}
	} = Color.White;

	[Property]
	[SourceLocation("Scene\\Components\\Light\\EnvmapProbe.cs", 115)]
	public BBox Bounds
	{
		get;
		set
		{
			if (!(field == value))
			{
				field = value;
				UpdateSceneObject();
			}
		}
	} = BBox.FromPositionAndSize((Vector3)0f, 1024f);

	[Property]
	[Range(-32f, 32f)]
	[DefaultValue(8f)]
	[SourceLocation("Scene\\Components\\Light\\EnvmapProbe.cs", 128)]
	public float Feathering
	{
		get;
		set
		{
			if (field != value)
			{
				field = value;
				UpdateSceneObject();
			}
		}
	} = 8f;

	/// <summary>
	/// Gets or sets the priority level for the object.
	/// </summary>
	[Property]
	[Range(0f, 100f)]
	[DefaultValue(0)]
	[Description("Gets or sets the priority level for the object.")]
	[SourceLocation("Scene\\Components\\Light\\EnvmapProbe.cs", 144)]
	public int Priority
	{
		get;
		set
		{
			if (field != value)
			{
				field = value;
				if (_sceneObject.IsValid())
				{
					_sceneObject.Priority = field;
				}
			}
		}
	}

	/// <summary>
	/// If this is set, the EnvmapProbe will use a custom cubemap texture instead of rendering dynamically
	/// </summary>
	[Property]
	[ShowIf("Mode", EnvmapProbeMode.CustomTexture)]
	[Description("If this is set, the EnvmapProbe will use a custom cubemap texture instead of rendering dynamically")]
	[SourceLocation("Scene\\Components\\Light\\EnvmapProbe.cs", 164)]
	public Texture Texture
	{
		get;
		set
		{
			if (field != value)
			{
				field = value;
				UpdateSceneObject();
			}
		}
	}

	/// <summary>
	/// The texture that was baked for this envmap probe
	/// </summary>
	[Property]
	[Hide]
	[Description("The texture that was baked for this envmap probe")]
	[SourceLocation("Scene\\Components\\Light\\EnvmapProbe.cs", 181)]
	public Texture BakedTexture { get; set; }

	[Obsolete("Use Mode to select the update mode")]
	[Hide]
	[SourceLocation("Scene\\Components\\Light\\EnvmapProbe.cs", 184)]
	public bool RenderDynamically
	{
		get
		{
			return Mode == EnvmapProbeMode.Realtime;
		}
		set
		{
			Mode = (value ? EnvmapProbeMode.Realtime : EnvmapProbeMode.CustomTexture);
		}
	}

	/// <summary>
	/// Resolution of the cubemap texture
	/// </summary>
	[Header("Rendering")]
	[HideIf("Mode", EnvmapProbeMode.CustomTexture)]
	[Property]
	[EnumButtonGroup]
	[DefaultValue(CubemapResolution.Small)]
	[Description("Resolution of the cubemap texture")]
	[SourceLocation("Scene\\Components\\Light\\EnvmapProbe.cs", 194)]
	public CubemapResolution Resolution
	{
		get;
		set
		{
			if (field != value)
			{
				field = value;
				UpdateSceneObject();
			}
		}
	} = CubemapResolution.Small;

	[HideIf("Mode", EnvmapProbeMode.CustomTexture)]
	[Property]
	[DefaultValue(16)]
	[SourceLocation("Scene\\Components\\Light\\EnvmapProbe.cs", 210)]
	public float ZNear
	{
		get;
		set
		{
			if (field != value)
			{
				field = value;
				UpdateSceneObject();
			}
		}
	} = 16f;

	[HideIf("Mode", EnvmapProbeMode.CustomTexture)]
	[Property]
	[DefaultValue(4096)]
	[SourceLocation("Scene\\Components\\Light\\EnvmapProbe.cs", 224)]
	public float ZFar
	{
		get;
		set
		{
			if (field != value)
			{
				field = value;
				UpdateSceneObject();
			}
		}
	} = 4096f;

	[Header("Realtime Updates")]
	[ShowIf("Mode", EnvmapProbeMode.Realtime)]
	[Property]
	[SourceLocation("Scene\\Components\\Light\\EnvmapProbe.cs", 238)]
	public CubemapDynamicUpdate UpdateStrategy
	{
		get;
		set
		{
			if (field != value)
			{
				field = value;
				UpdateSceneObject();
			}
		}
	}

	/// <summary>
	/// Only update dynamically if we're this close to it
	/// </summary>
	[ShowIf("Mode", EnvmapProbeMode.Realtime)]
	[Property]
	[DefaultValue(512)]
	[Description("Only update dynamically if we're this close to it")]
	[SourceLocation("Scene\\Components\\Light\\EnvmapProbe.cs", 256)]
	public float MaxDistance { get; set; } = 512f;

	[ShowIf("Mode", EnvmapProbeMode.Realtime)]
	[ShowIf("UpdateStrategy", CubemapDynamicUpdate.TimeInterval)]
	[Property]
	[Range(0f, 10f)]
	[DefaultValue(0.1f)]
	[SourceLocation("Scene\\Components\\Light\\EnvmapProbe.cs", 260)]
	public float DelayBetweenUpdates { get; set; } = 0.1f;

	[ShowIf("Mode", EnvmapProbeMode.Realtime)]
	[ShowIf("UpdateStrategy", CubemapDynamicUpdate.FrameInterval)]
	[Property]
	[Range(0f, 16f)]
	[DefaultValue(5)]
	[SourceLocation("Scene\\Components\\Light\\EnvmapProbe.cs", 265)]
	public int FrameInterval { get; set; } = 5;

	/// <summary>
	/// Minimum amount of reflection bounces to render when first enabled before settling, at cost of extra performance on load
	/// Often times you don't need this
	/// </summary>
	[HideIf("Mode", EnvmapProbeMode.CustomTexture)]
	[ShowIf("UpdateStrategy", CubemapDynamicUpdate.OnEnabled)]
	[Property]
	[DefaultValue(false)]
	[Description("Minimum amount of reflection bounces to render when first enabled before settling, at cost of extra performance on load Often times you don't need this")]
	[SourceLocation("Scene\\Components\\Light\\EnvmapProbe.cs", 274)]
	public bool MultiBounce
	{
		get;
		set
		{
			if (field != value)
			{
				field = value;
				UpdateSceneObject();
			}
		}
	}

	/// <summary>
	/// Objects with any of these tags will be excluded when rendering this cubemap.
	/// </summary>
	[HideIf("Mode", EnvmapProbeMode.CustomTexture)]
	[Property]
	[Description("Objects with any of these tags will be excluded when rendering this cubemap.")]
	[SourceLocation("Scene\\Components\\Light\\EnvmapProbe.cs", 292)]
	public TagSet RenderExcludeTags { get; set; } = new TagSet();

	[SourceLocation("Scene\\Components\\Light\\EnvmapProbe.Upgrade.cs", 7)]
	public override int ComponentVersion => 1;

	/// <summary>
	/// Bake this envmap now. This will stop it being dynamic if it was.
	/// </summary>
	[Order(10000)]
	[Button("Bake Texture", "panorama_photosphere")]
	[WideMode(HasLabel = false)]
	[HideIf("Mode", 2)]
	[Description("Bake this envmap now. This will stop it being dynamic if it was.")]
	[SourceLocation("Scene\\Components\\Light\\EnvmapProbe.Baking.cs", 11)]
	public async Task Bake(CancellationToken ct = default(CancellationToken))
	{
		if (Scene.Editor == null)
		{
			GlobalSystemNamespace.Log.Warning("EnvmapProbe.Bake is an editor feature.");
			return;
		}
		SceneFolder sceneFolder = Scene.Editor.GetSceneFolder();
		if (sceneFolder == null)
		{
			return;
		}
		int resolution = (int)Resolution;
		using Texture tex = Texture.CreateCube(resolution, resolution).WithUAVBinding().WithMips(7)
			.WithFormat(ImageFormat.RGBA16161616F)
			.Finish();
		if (ct.IsCancellationRequested)
		{
			return;
		}
		RenderCubemap(tex, CubemapRendering.GGXFilterType.Quality, RenderExcludeTags);
		if (!ct.IsCancellationRequested)
		{
			string filename = $"/envmap/bake_{Id}.vtex_c";
			byte[] data = await tex.SaveToVtexAsync();
			if (!ct.IsCancellationRequested)
			{
				BakedTexture = await Texture.LoadAsync(sceneFolder.WriteFile(filename, data));
				Mode = EnvmapProbeMode.Baked;
				UpdateSceneObject();
			}
		}
	}

	[Menu("Editor", "Scene/Bake Envmaps", "panorama_photosphere", Priority = 1000)]
	[SourceLocation("Scene\\Components\\Light\\EnvmapProbe.Baking.cs", 58)]
	public static async Task BakeAll()
	{
		if (Application.Editor != null)
		{
			EnvmapProbe[] list = (from x in Application.Editor.Scene.GetAll<EnvmapProbe>()
				where x.Mode == EnvmapProbeMode.Baked
				select x).ToArray();
			await Application.Editor.ForEachAsync(list, "Baking EnvMap Probes", (EnvmapProbe x, CancellationToken ct) => x.Bake(ct));
		}
	}

	[SourceLocation("Scene\\Components\\Light\\EnvmapProbe.cs", 296)]
	protected override void OnEnabled()
	{
		Assert.True(!_sceneObject.IsValid());
		Assert.NotNull(Scene);
		_sceneObject = new SceneCubemap(Scene.SceneWorld, null, Bounds, WorldTransform, TintColor, Feathering, (int)Projection);
		_sceneObject.Tags.SetFrom(Tags);
		_sceneObject.Priority = Priority;
		GameTransform transform = Transform;
		transform.OnTransformChanged = (Action)Delegate.Combine(transform.OnTransformChanged, new Action(OnTransformChanged));
		UpdateSceneObject();
	}

	[SourceLocation("Scene\\Components\\Light\\EnvmapProbe.cs", 309)]
	protected override void OnDisabled()
	{
		GameTransform transform = Transform;
		transform.OnTransformChanged = (Action)Delegate.Remove(transform.OnTransformChanged, new Action(OnTransformChanged));
		Dirty = false;
		_sceneObject?.Delete();
		_sceneObject = null;
		_dynamicTexture?.Dispose();
		_dynamicTexture = null;
	}

	[SourceLocation("Scene\\Components\\Light\\EnvmapProbe.cs", 322)]
	protected override async Task OnLoad(LoadingContext context)
	{
		if (!Graphics.IsAvailable)
		{
			return;
		}
		if (Mode == EnvmapProbeMode.Realtime && Active && _dynamicTexture == null)
		{
			Dirty = true;
		}
		if (Dirty)
		{
			context.Title = "Rendering Envmap";
			while (Dirty)
			{
				await Task.DelayRealtime(10);
			}
		}
	}

	[SourceLocation("Scene\\Components\\Light\\EnvmapProbe.cs", 343)]
	private void OnTransformChanged()
	{
		UpdateSceneObject();
	}

	[SourceLocation("Scene\\Components\\Light\\EnvmapProbe.cs", 348)]
	private void UpdateSceneObject()
	{
		if (_sceneObject.IsValid())
		{
			Transform transform = WorldTransform;
			BBox projectionBounds = Bounds;
			if (Mode == EnvmapProbeMode.Realtime)
			{
				transform = transform.WithScale(-1f);
				projectionBounds = new BBox(-Bounds.Maxs, -Bounds.Mins);
			}
			_sceneObject.Transform = transform;
			_sceneObject.Projection = Projection;
			_sceneObject.TintColor = TintColor;
			_sceneObject.ProjectionBounds = projectionBounds;
			_sceneObject.LocalBounds = _sceneObject.ProjectionBounds;
			_sceneObject.Radius = Bounds.Size.Length;
			_sceneObject.Feathering = Feathering;
			if (UpdateStrategy == CubemapDynamicUpdate.OnEnabled)
			{
				_bouncesLeft = (MultiBounce ? 4 : 0);
			}
			if (Mode == EnvmapProbeMode.Baked)
			{
				_sceneObject.Texture = BakedTexture;
			}
			else if (Mode == EnvmapProbeMode.CustomTexture)
			{
				_sceneObject.Texture = Texture;
			}
			else if (Mode == EnvmapProbeMode.Realtime)
			{
				CreateTexture();
				_sceneObject.Texture = _dynamicTexture;
			}
		}
	}

	/// <summary>
	/// Tags have been updated - lets update our tags
	/// </summary>
	[Description("Tags have been updated - lets update our tags")]
	[SourceLocation("Scene\\Components\\Light\\EnvmapProbe.cs", 394)]
	protected override void OnTagsChanged()
	{
		if (_sceneObject.IsValid())
		{
			_sceneObject.Tags.SetFrom(Tags);
			_sceneObject.RenderDirty();
		}
	}

	[SourceLocation("Scene\\Components\\Light\\EnvmapProbe.cs", 403)]
	internal static void InitializeFromLegacy(GameObject go, MapLoader.ObjectEntry kv)
	{
		EnvmapProbe envmapProbe = go.Components.Create<EnvmapProbe>();
		Vector3 value = kv.GetValue("box_mins", new Vector3(-72f, -72f, -72f));
		Vector3 value2 = kv.GetValue("box_maxs", new Vector3(72f, 72f, 72f));
		kv.GetValue("indoor_outdoor_level", 0);
		float value3 = kv.GetValue("cubemap_feathering", 0.25f);
		envmapProbe.Bounds = new BBox(value, value2);
		envmapProbe.Feathering = value3 * 8f;
		if (kv.TypeName == "env_combined_light_probe_volume" || kv.TypeName == "env_cubemap_box")
		{
			envmapProbe.Projection = SceneCubemap.ProjectionMode.Box;
		}
		else
		{
			envmapProbe.Projection = SceneCubemap.ProjectionMode.Sphere;
		}
		envmapProbe.UpdateStrategy = CubemapDynamicUpdate.OnEnabled;
		envmapProbe.Texture = null;
		envmapProbe.Mode = EnvmapProbeMode.Realtime;
	}

	[SourceLocation("Scene\\Components\\Light\\EnvmapProbe.cs", 433)]
	protected override void OnUpdate()
	{
		base.OnUpdate();
		TryToDirty();
	}

	[SourceLocation("Scene\\Components\\Light\\EnvmapProbe.cs", 439)]
	private void TryToDirty()
	{
		if (Mode != EnvmapProbeMode.Realtime)
		{
			_queuedFrames = 0;
			_queuedTime = 0f;
			return;
		}
		_queuedFrames++;
		_queuedTime += Time.Delta;
		if (IsReadyToUpdate())
		{
			Dirty = true;
		}
	}

	[SourceLocation("Scene\\Components\\Light\\EnvmapProbe.cs", 459)]
	internal bool IsReadyToUpdate()
	{
		if (UpdateStrategy == CubemapDynamicUpdate.EveryFrame)
		{
			return true;
		}
		if (UpdateStrategy == CubemapDynamicUpdate.FrameInterval && _queuedFrames > FrameInterval)
		{
			return true;
		}
		if (UpdateStrategy == CubemapDynamicUpdate.TimeInterval && _queuedTime > DelayBetweenUpdates)
		{
			return true;
		}
		SceneCubemap sceneObject = _sceneObject;
		if (sceneObject != null && sceneObject.RequiresUpdate)
		{
			return true;
		}
		if (UpdateStrategy == CubemapDynamicUpdate.OnEnabled && _bouncesLeft > 0)
		{
			return true;
		}
		return false;
	}

	[SourceLocation("Scene\\Components\\Light\\EnvmapProbe.cs", 480)]
	private void CreateTexture()
	{
		int resolution = (int)Resolution;
		int mips = 7;
		if (_dynamicTexture == null || _dynamicTexture.Width != resolution || !_dynamicTexture.UAVAccess)
		{
			_dynamicTexture?.Dispose();
			_dynamicTexture = Texture.CreateCube(resolution, resolution).WithUAVBinding().WithMips(mips)
				.WithFormat(ImageFormat.RGBA16161616F)
				.Finish();
		}
	}

	[SourceLocation("Scene\\Components\\Light\\EnvmapProbe.cs", 498)]
	internal void RenderCubemap()
	{
		RenderCubemap(_dynamicTexture, CubemapRendering.GGXFilterType.Fast, RenderExcludeTags);
	}

	[SourceLocation("Scene\\Components\\Light\\EnvmapProbe.cs", 503)]
	internal void RenderCubemap(Texture target, CubemapRendering.GGXFilterType filterType, TagSet excludeTags = null)
	{
		if (target != null)
		{
			target.Clear(Color.Red);
			if (target.UAVAccess)
			{
				CubemapRendering.Render(Scene.SceneWorld, target, WorldTransform.WithScale(1f), ZNear.Clamp(1f, ZFar), ZFar.Clamp(ZNear, 16384f), filterType, excludeTags);
			}
			SceneCubemap sceneObject = _sceneObject;
			if (sceneObject != null)
			{
				sceneObject.RequiresUpdate = false;
			}
			_queuedFrames = 0;
			_queuedTime = 0f;
			if (_bouncesLeft > 0 && UpdateStrategy == CubemapDynamicUpdate.OnEnabled)
			{
				_bouncesLeft--;
			}
			Dirty = false;
		}
	}

	[SourceLocation("Scene\\Components\\Light\\EnvmapProbe.Gizmo.cs", 5)]
	protected override void DrawGizmos()
	{
		Gizmo.Hitbox.Sphere(new Sphere(0f, 10f));
		bool isHovered = Gizmo.IsHovered;
		bool isSelected = Gizmo.IsSelected;
		SceneModel sceneModel = Gizmo.Draw.Model(Model.Sphere);
		sceneModel.Transform = sceneModel.Transform.WithScale((isHovered && !isSelected) ? 0.3f : 0.25f);
		sceneModel.SetMaterialOverride(Material.Load("materials/dev/dev_metal_rough00.vmat"));
		if (!Gizmo.IsSelected)
		{
			return;
		}
		for (int i = 0; i < 2; i++)
		{
			float num;
			if (i == 0)
			{
				Gizmo.Draw.IgnoreDepth = true;
				num = 0.2f;
			}
			else
			{
				Gizmo.Draw.IgnoreDepth = false;
				num = 1f;
			}
			Gizmo.Draw.Color = TintColor.WithAlpha(1f * num);
			Gizmo.Draw.LineBBox(Bounds);
			Gizmo.Draw.Color = TintColor.WithAlpha(0.05f * num);
			Gizmo.Draw.SolidBox(Bounds);
			Gizmo.Draw.Color = TintColor.WithAlpha(0.2f * num);
			Gizmo.Draw.LineBBox(Bounds.Grow(Feathering));
		}
	}

	/// <summary>
	/// v1
	/// - Changed RenderDynamically bool to Mode enum.
	/// </summary>
	[Expose]
	[JsonUpgrader(typeof(EnvmapProbe), 1)]
	[Description("v1 - Changed RenderDynamically bool to Mode enum.")]
	[SourceLocation("Scene\\Components\\Light\\EnvmapProbe.Upgrade.cs", 13)]
	private static void Upgrader_v1(JsonObject obj)
	{
		if (obj.TryGetPropertyValue("RenderDynamically", out JsonNode jsonNode))
		{
			bool flag = (bool)jsonNode;
			obj["Mode"] = (flag ? "Realtime" : "CustomTexture");
		}
	}
}
