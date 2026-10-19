using System;
using System.Collections.Generic;
using System.Linq;
using System.Runtime.InteropServices;
using NativeEngine;
using Sandbox.Diagnostics;
using Sandbox.Engine;
using Sandbox.Internal;
using Sandbox.Rendering;

namespace Sandbox;

/// <summary>
/// Renders a model in the world
/// </summary>
[SourceLocation("Scene\\Components\\Render\\ModelRenderer.Attachments.cs", 3)]
[Description("Renders a model in the world")]
[SourceLocation("Scene\\Components\\Render\\ModelRenderer.Bounds.cs", 3)]
[Title("Model Renderer")]
[Category("Rendering")]
[Icon("free_breakfast")]
[Alias(new string[] { "ModelComponentMate", "ModelComponent" })]
[SourceLocation("Scene\\Components\\Render\\ModelRenderer.cs", 8)]
[SourceLocation("Scene\\Components\\Render\\ModelRenderer.Deformations.cs", 5)]
[SourceLocation("Scene\\Components\\Render\\ModelRenderer.Materials.cs", 12)]
public class ModelRenderer : Renderer, Component.ExecuteInEditor, Component.ITintable, Component.IMaterialSetter, Component.IHasBounds, IHasModel, MaterialAccessor.ITarget
{
	public enum ShadowRenderType
	{
		[Icon("wb_shade")]
		On,
		[Icon("wb_twilight")]
		Off,
		[Icon("hide_source")]
		[Title("Shadows Only")]
		ShadowsOnly
	}

	[SourceLocation("Scene\\Components\\Render\\ModelRenderer.Attachments.cs", 5)]
	private bool _createAttachments;

	[SourceLocation("Scene\\Components\\Render\\ModelRenderer.Attachments.cs", 7)]
	internal readonly Dictionary<ModelAttachments.Attachment, GameObject> attachmentToGameObject = new Dictionary<ModelAttachments.Attachment, GameObject>();

	[SourceLocation("Scene\\Components\\Render\\ModelRenderer.cs", 14)]
	private ulong _bodyGroups = ulong.MaxValue;

	[SourceLocation("Scene\\Components\\Render\\ModelRenderer.cs", 41)]
	private Color _tint = "#FFFFFF";

	[SourceLocation("Scene\\Components\\Render\\ModelRenderer.cs", 117)]
	private int? _lodOverride;

	[SourceLocation("Scene\\Components\\Render\\ModelRenderer.cs", 214)]
	internal SceneObject _sceneObject;

	[SourceLocation("Scene\\Components\\Render\\ModelRenderer.cs", 227)]
	internal Action ModelChanged;

	[SourceLocation("Scene\\Components\\Render\\ModelRenderer.Deformations.cs", 8)]
	private readonly List<SceneDeformationVolumeData> _effectiveVolumes = new List<SceneDeformationVolumeData>();

	[SourceLocation("Scene\\Components\\Render\\ModelRenderer.Deformations.cs", 9)]
	private readonly List<ModelDeformer> _orderedDeformers = new List<ModelDeformer>();

	[SourceLocation("Scene\\Components\\Render\\ModelRenderer.Deformations.cs", 17)]
	private readonly HashSet<ModelRenderer> _deformationSources = new HashSet<ModelRenderer>();

	[SourceLocation("Scene\\Components\\Render\\ModelRenderer.Deformations.cs", 18)]
	private bool _hasActiveDeformations;

	[SourceLocation("Scene\\Components\\Render\\ModelRenderer.Deformations.cs", 97)]
	private Transform? _restOffset;

	[SourceLocation("Scene\\Components\\Render\\ModelRenderer.Deformations.cs", 98)]
	private (Model Model, Model Target) _restOffsetModels;

	[SourceLocation("Scene\\Components\\Render\\ModelRenderer.Materials.cs", 28)]
	private Dictionary<string, Material> taggedMaterialOverrides;

	[SourceLocation("Scene\\Components\\Render\\ModelRenderer.Materials.cs", 82)]
	private MaterialAccessor _materialAccessor;

	[SourceLocation("Scene\\Components\\Render\\ModelRenderer.Bounds.cs", 5)]
	BBox IHasBounds.LocalBounds => LocalBounds;

	[SourceLocation("Scene\\Components\\Render\\ModelRenderer.Bounds.cs", 7)]
	public BBox Bounds => GetWorldBoundsInternal();

	[SourceLocation("Scene\\Components\\Render\\ModelRenderer.Bounds.cs", 9)]
	public BBox LocalBounds => GetLocalBoundsInternal();

	[Property]
	[SourceLocation("Scene\\Components\\Render\\ModelRenderer.cs", 16)]
	public Model Model
	{
		get;
		set
		{
			if (field == value)
			{
				return;
			}
			field = value;
			if (!GameObject.Flags.Contains(GameObjectFlags.Deserializing))
			{
				_bodyGroups = ulong.MaxValue;
				if (field != null && field.native.GetNumMeshGroups() > 0)
				{
					_bodyGroups = field.native.GetDefaultMeshGroupMask();
				}
			}
			UpdateObject();
			OnModelChanged();
		}
	}

	[Property]
	[SourceLocation("Scene\\Components\\Render\\ModelRenderer.cs", 43)]
	public Color Tint
	{
		get
		{
			return _tint;
		}
		set
		{
			if (!(_tint == value))
			{
				_tint = value;
				if (_sceneObject.IsValid())
				{
					_sceneObject.ColorTint = Tint;
				}
			}
		}
	}

	[Property]
	[SourceLocation("Scene\\Components\\Render\\ModelRenderer.cs", 59)]
	public bool CreateAttachments
	{
		get
		{
			return _createAttachments;
		}
		set
		{
			if (_createAttachments != value)
			{
				_createAttachments = value;
				UpdateObject();
			}
		}
	}

	[Property]
	[Model.BodyGroupMask]
	[ShowIf("HasBodyGroups", true)]
	[DefaultValue(ulong.MaxValue)]
	[SourceLocation("Scene\\Components\\Render\\ModelRenderer.cs", 72)]
	public ulong BodyGroups
	{
		get
		{
			return _bodyGroups;
		}
		set
		{
			if (_bodyGroups != value)
			{
				_bodyGroups = value;
				Update();
			}
		}
	}

	[SourceLocation("Scene\\Components\\Render\\ModelRenderer.cs", 86)]
	public bool HasBodyGroups
	{
		get
		{
			Model model = Model;
			if (model == null)
			{
				return false;
			}
			return model.Parts.All.Sum((Model.BodyPart x) => x.Choices.Count) > 1;
		}
	}

	[Property]
	[Model.MaterialGroup]
	[ShowIf("HasMaterialGroups", true)]
	[DefaultValue(null)]
	[SourceLocation("Scene\\Components\\Render\\ModelRenderer.cs", 88)]
	public string MaterialGroup
	{
		get;
		set
		{
			if (!(field == value))
			{
				field = value;
				Update();
			}
		}
	}

	[SourceLocation("Scene\\Components\\Render\\ModelRenderer.cs", 102)]
	public bool HasMaterialGroups
	{
		get
		{
			Model model = Model;
			if (model != null && model.MaterialGroupCount > 0)
			{
				return MaterialOverride == null;
			}
			return false;
		}
	}

	[Title("Cast Shadows")]
	[Property]
	[Category("Lighting")]
	[DefaultValue(ShadowRenderType.On)]
	[SourceLocation("Scene\\Components\\Render\\ModelRenderer.cs", 104)]
	public ShadowRenderType RenderType
	{
		get;
		set
		{
			if (field != value)
			{
				field = value;
				Update();
			}
		}
	}

	/// <summary>
	/// Force a level of detail. Unset uses automatic LOD.
	/// </summary>
	[Property]
	[Title("LOD Override")]
	[Description("Force a level of detail. Unset uses automatic LOD.")]
	[SourceLocation("Scene\\Components\\Render\\ModelRenderer.cs", 122)]
	public int? LodOverride
	{
		get
		{
			return _lodOverride;
		}
		set
		{
			if (_lodOverride != value)
			{
				_lodOverride = value;
				if (_sceneObject.IsValid())
				{
					_sceneObject.LodOverride = _lodOverride ?? (-1);
				}
			}
		}
	}

	[SourceLocation("Scene\\Components\\Render\\ModelRenderer.cs", 215)]
	public SceneObject SceneObject => _sceneObject;

	[SourceLocation("Scene\\Components\\Render\\ModelRenderer.cs", 217)]
	Color ITintable.Color
	{
		get
		{
			return Tint;
		}
		set
		{
			Tint = value;
		}
	}

	[SourceLocation("Scene\\Components\\Render\\ModelRenderer.Deformations.cs", 7)]
	internal List<ModelDeformer> ModelDeformers { get; } = new List<ModelDeformer>();

	[SourceLocation("Scene\\Components\\Render\\ModelRenderer.Deformations.cs", 10)]
	internal virtual ModelRenderer DeformationSource => null;

	/// <summary>
	/// A model-space point per model bone that deformations move each bone's part of the model by, without reshaping it -
	/// or none, to deform it as usual.
	/// </summary>
	[Description("A model-space point per model bone that deformations move each bone's part of the model by, without reshaping it - or none, to deform it as usual.")]
	[SourceLocation("Scene\\Components\\Render\\ModelRenderer.Deformations.cs", 16)]
	internal virtual ReadOnlySpan<Vector4> DeformationAnchors => default;

	[Property]
	[SourceLocation("Scene\\Components\\Render\\ModelRenderer.Materials.cs", 15)]
	public Material MaterialOverride
	{
		get;
		set
		{
			if (field != value)
			{
				field = value;
				UpdateObject();
			}
		}
	}

	/// <summary>
	/// Access to the materials 
	/// </summary>
	[Property]
	[Group("Materials", StartFolded = true)]
	[Description("Access to the materials")]
	[SourceLocation("Scene\\Components\\Render\\ModelRenderer.Materials.cs", 87)]
	public MaterialAccessor Materials => _materialAccessor ?? (_materialAccessor = new MaterialAccessor(this));

	/// <summary>
	/// Get the GameObject of a specific attachment.
	/// </summary>
	[Description("Get the GameObject of a specific attachment.")]
	[SourceLocation("Scene\\Components\\Render\\ModelRenderer.Attachments.cs", 12)]
	public GameObject GetAttachmentObject(string name)
	{
		if (Model == null)
		{
			return null;
		}
		ModelAttachments.Attachment attachment = Model.Attachments.Get(name);
		return GetAttachmentObject(attachment);
	}

	/// <summary>
	/// Get the GameObject of a specific attachment.
	/// </summary>
	[Description("Get the GameObject of a specific attachment.")]
	[SourceLocation("Scene\\Components\\Render\\ModelRenderer.Attachments.cs", 23)]
	public GameObject GetAttachmentObject(ModelAttachments.Attachment attachment)
	{
		if (attachment == null)
		{
			return null;
		}
		return attachmentToGameObject.GetValueOrDefault(attachment);
	}

	[SourceLocation("Scene\\Components\\Render\\ModelRenderer.Attachments.cs", 30)]
	public virtual GameObject GetBoneObject(BoneCollection.Bone bone)
	{
		return null;
	}

	[SourceLocation("Scene\\Components\\Render\\ModelRenderer.Attachments.cs", 35)]
	private void BuildAttachmentHierarchy()
	{
		ClearAttachmentHierarchy();
		if (Model == null || !CreateAttachments)
		{
			return;
		}
		foreach (ModelAttachments.Attachment item in Model.Attachments.All)
		{
			attachmentToGameObject[item] = CreateAttachment(item);
		}
	}

	[SourceLocation("Scene\\Components\\Render\\ModelRenderer.Attachments.cs", 51)]
	private void ClearAttachmentHierarchy()
	{
		if (attachmentToGameObject.Count == 0)
		{
			return;
		}
		foreach (KeyValuePair<ModelAttachments.Attachment, GameObject> item in attachmentToGameObject)
		{
			if (item.Value.IsValid())
			{
				item.Value.Flags &= ~GameObjectFlags.Attachment;
			}
		}
		attachmentToGameObject.Clear();
	}

	[SourceLocation("Scene\\Components\\Render\\ModelRenderer.Attachments.cs", 67)]
	private GameObject CreateAttachment(ModelAttachments.Attachment a)
	{
		Assert.NotNull(a);
		GameObject gameObject = GameObject;
		GameObject gameObject2 = gameObject.Children.FirstOrDefault((GameObject x) => a.IsNamed(x.Name) && !x.Flags.Contains(GameObjectFlags.Bone));
		if (!gameObject2.IsValid())
		{
			gameObject2 = Scene.CreateObject();
		}
		gameObject2.Parent = gameObject;
		gameObject2.Name = a.Name;
		gameObject2.Flags |= GameObjectFlags.Attachment;
		gameObject2.LocalTransform = a.WorldTransform;
		return gameObject2;
	}

	[SourceLocation("Scene\\Components\\Render\\ModelRenderer.Bounds.cs", 11)]
	internal virtual BBox GetWorldBoundsInternal()
	{
		return LocalBounds.Transform(WorldTransform);
	}

	[SourceLocation("Scene\\Components\\Render\\ModelRenderer.Bounds.cs", 16)]
	internal virtual BBox GetLocalBoundsInternal()
	{
		if (_sceneObject is SceneModel sceneModel)
		{
			return sceneModel.animNative.m_localBounds;
		}
		if (Model == null)
		{
			return BBox.FromPositionAndSize(WorldPosition, 16f);
		}
		return Model.RenderBounds;
	}

	/// <summary>
	/// Set body group value by name
	/// </summary>
	[Description("Set body group value by name")]
	[SourceLocation("Scene\\Components\\Render\\ModelRenderer.cs", 141)]
	public void SetBodyGroup(string name, int value)
	{
		if (Model != null && !Model.native.IsNull)
		{
			int bodyPartForName = Model.native.GetBodyPartForName(name);
			if (bodyPartForName >= 0)
			{
				SetBodyGroup(bodyPartForName, value);
			}
		}
	}

	/// <summary>
	/// Set body group value by name and choice
	/// </summary>
	[Description("Set body group value by name and choice")]
	[SourceLocation("Scene\\Components\\Render\\ModelRenderer.cs", 155)]
	public void SetBodyGroup(string name, string choice)
	{
		if (Model == null || Model.native.IsNull)
		{
			return;
		}
		int bodyPartForName = Model.native.GetBodyPartForName(name);
		if (bodyPartForName < 0)
		{
			return;
		}
		ModelParts parts = Model.Parts;
		if (bodyPartForName < parts.Count)
		{
			int choiceIndex = parts.All[bodyPartForName].GetChoiceIndex(choice);
			if (choiceIndex >= 0)
			{
				SetBodyGroup(bodyPartForName, choiceIndex);
			}
		}
	}

	/// <summary>
	/// Set body group value by index
	/// </summary>
	[Description("Set body group value by index")]
	[SourceLocation("Scene\\Components\\Render\\ModelRenderer.cs", 174)]
	public void SetBodyGroup(int part, int value)
	{
		if (Model != null && !Model.native.IsNull)
		{
			ulong bodyPartMask = Model.native.GetBodyPartMask(part);
			ulong bodyPartMeshMask = Model.native.GetBodyPartMeshMask(part, value);
			ulong bodyGroups = BodyGroups;
			bodyGroups &= ~bodyPartMask;
			bodyGroups |= bodyPartMeshMask;
			BodyGroups = bodyGroups;
		}
	}

	/// <summary>
	/// Get body group value by name
	/// </summary>
	[Description("Get body group value by name")]
	[SourceLocation("Scene\\Components\\Render\\ModelRenderer.cs", 192)]
	public int GetBodyGroup(string name)
	{
		if (Model == null || Model.native.IsNull)
		{
			throw new ArgumentException("Invalid Model");
		}
		return GetBodyGroup(Model.native.GetBodyPartForName(name));
	}

	/// <summary>
	/// Get body group value by index
	/// </summary>
	[Description("Get body group value by index")]
	[SourceLocation("Scene\\Components\\Render\\ModelRenderer.cs", 203)]
	public int GetBodyGroup(int part)
	{
		if (Model == null || Model.native.IsNull)
		{
			throw new ArgumentException("Invalid Model");
		}
		if (part < 0 || part >= Model.native.GetNumBodyParts())
		{
			throw new ArgumentOutOfRangeException("part");
		}
		return Model.native.FindMeshIndexForMask(part, BodyGroups);
	}

	[SourceLocation("Scene\\Components\\Render\\ModelRenderer.cs", 219)]
	internal void OnModelReloaded()
	{
		if (Active)
		{
			UpdateObject();
			OnModelChanged();
		}
	}

	[SourceLocation("Scene\\Components\\Render\\ModelRenderer.cs", 229)]
	internal void OnModelChanged()
	{
		ModelChanged?.Invoke();
	}

	[SourceLocation("Scene\\Components\\Render\\ModelRenderer.cs", 234)]
	protected virtual void UpdateObject()
	{
		BuildAttachmentHierarchy();
		if (_sceneObject.IsValid())
		{
			Model model = Model ?? Model.Load("models/dev/box.vmdl");
			_sceneObject.ColorTint = Tint;
			_sceneObject.Model = model;
			_sceneObject.MeshGroupMask = BodyGroups;
			_sceneObject.Flags.CastShadows = RenderType == ShadowRenderType.On || RenderType == ShadowRenderType.ShadowsOnly;
			_sceneObject.Flags.IsStatic = GameObject.IsStatic && !_hasActiveDeformations;
			_sceneObject.RenderingEnabled = model.HasRenderMeshes();
			if (_lodOverride.HasValue)
			{
				_sceneObject.LodOverride = _lodOverride.Value;
			}
			RenderOptions.Apply(_sceneObject);
			if (RenderType == ShadowRenderType.ShadowsOnly)
			{
				_sceneObject.Flags.SetFlag(SceneObjectFlags.ExcludeGameLayer, val: true);
			}
			if (HasMaterialGroups)
			{
				_sceneObject.SetMaterialOverride(null);
				_sceneObject.SetMaterialGroup(MaterialGroup);
			}
			else
			{
				_sceneObject.SetMaterialOverride(MaterialOverride);
			}
		}
	}

	[SourceLocation("Scene\\Components\\Render\\ModelRenderer.cs", 270)]
	protected override void OnEnabled()
	{
		Assert.True(!_sceneObject.IsValid(), "_sceneObject should be null - disable wasn't called");
		Assert.NotNull(Scene, "Scene should not be null");
		Model model = Model ?? Model.Load("models/dev/box.vmdl");
		_sceneObject = CreateSceneObject(model);
		OnSceneObjectCreated(_sceneObject);
		GameTransform transform = Transform;
		transform.OnTransformChanged = (Action)Delegate.Combine(transform.OnTransformChanged, new Action(OnTransformChanged));
	}

	[SourceLocation("Scene\\Components\\Render\\ModelRenderer.cs", 283)]
	internal override void OnSceneObjectCreated(SceneObject o)
	{
		base.OnSceneObjectCreated(o);
		if (o.IsValid())
		{
			o.Transform = WorldTransform;
			o.Component = this;
			o.Tags.SetFrom(GameObject.Tags);
		}
		ApplyMaterialOverrides();
		UpdateObject();
		OnTransformChanged();
	}

	[SourceLocation("Scene\\Components\\Render\\ModelRenderer.cs", 299)]
	internal override void OnDisabledInternal()
	{
		try
		{
			ClearAttachmentHierarchy();
		}
		finally
		{
			GameTransform transform = Transform;
			transform.OnTransformChanged = (Action)Delegate.Remove(transform.OnTransformChanged, new Action(OnTransformChanged));
			BackupRenderAttributes(_sceneObject?.Attributes);
			_sceneObject?.Delete();
			_sceneObject = null;
			ResetDeformations();
		}
		base.OnDisabledInternal();
	}

	[SourceLocation("Scene\\Components\\Render\\ModelRenderer.cs", 318)]
	private void OnTransformChanged()
	{
		if (_sceneObject.IsValid())
		{
			_sceneObject.Transform = Transform.InterpolatedWorld;
		}
	}

	/// <summary>
	/// Tags have been updated - lets update our scene object tags
	/// </summary>
	[Description("Tags have been updated - lets update our scene object tags")]
	[SourceLocation("Scene\\Components\\Render\\ModelRenderer.cs", 329)]
	internal override void OnTagsUpdatedInternal()
	{
		base.OnTagsUpdatedInternal();
		if (_sceneObject.IsValid())
		{
			_sceneObject.Tags.SetFrom(GameObject.Tags);
		}
	}

	[SourceLocation("Scene\\Components\\Render\\ModelRenderer.cs", 352)]
	private void Update()
	{
		UpdateObject();
		ApplyMaterialOverrides();
	}

	[SourceLocation("Scene\\Components\\Render\\ModelRenderer.cs", 358)]
	protected override void OnRenderOptionsChanged()
	{
		if (_sceneObject.IsValid())
		{
			RenderOptions.Apply(_sceneObject);
		}
	}

	[SourceLocation("Scene\\Components\\Render\\ModelRenderer.cs", 366)]
	public void SetMaterial(Material material, int triangle = -1)
	{
		MaterialOverride = material;
	}

	[SourceLocation("Scene\\Components\\Render\\ModelRenderer.cs", 371)]
	public Material GetMaterial(int triangle = -1)
	{
		return MaterialOverride;
	}

	/// <summary>
	/// Copy everything from another renderer
	/// </summary>
	[Description("Copy everything from another renderer")]
	[SourceLocation("Scene\\Components\\Render\\ModelRenderer.cs", 379)]
	public override void CopyFrom(Renderer other)
	{
		base.CopyFrom(other);
		if (other is ModelRenderer modelRenderer)
		{
			Model = modelRenderer.Model;
			Tint = modelRenderer.Tint;
			BodyGroups = modelRenderer.BodyGroups;
			MaterialGroup = modelRenderer.MaterialGroup;
		}
	}

	[SourceLocation("Scene\\Components\\Render\\ModelRenderer.cs", 392)]
	void IHasModel.OnModelReloaded()
	{
		OnModelReloaded();
	}

	[SourceLocation("Scene\\Components\\Render\\ModelRenderer.Deformations.cs", 20)]
	private void ResetDeformations()
	{
		_effectiveVolumes.Clear();
		_orderedDeformers.Clear();
		_deformationSources.Clear();
		_hasActiveDeformations = false;
	}

	[SourceLocation("Scene\\Components\\Render\\ModelRenderer.Deformations.cs", 28)]
	internal void UpdateDeformations()
	{
		if (!Active || !_sceneObject.IsValid())
		{
			return;
		}
		_effectiveVolumes.Clear();
		_orderedDeformers.Clear();
		_deformationSources.Clear();
		ModelRenderer modelRenderer = ((this is SkinnedModelRenderer { DeformationMode: SkinnedModelRenderer.DeformationModeType.None }) ? null : this);
		while (modelRenderer.IsValid() && modelRenderer.Active && _deformationSources.Add(modelRenderer))
		{
			foreach (ModelDeformer modelDeformer in modelRenderer.ModelDeformers)
			{
				if (modelDeformer.Active && modelDeformer.IsActive && (modelRenderer == this || modelDeformer.ApplyToBoneMergedChildren))
				{
					_orderedDeformers.Add(modelDeformer);
				}
			}
			modelRenderer = modelRenderer.DeformationSource;
		}
		_orderedDeformers.Sort((ModelDeformer a, ModelDeformer b) => a.Priority.CompareTo(b.Priority));
		foreach (ModelDeformer orderedDeformer in _orderedDeformers)
		{
			_effectiveVolumes.Add(VolumeFor(orderedDeformer));
		}
		_hasActiveDeformations = _effectiveVolumes.Count > 0;
		if (!(this is SkinnedModelRenderer) && _sceneObject is SceneModel != _hasActiveDeformations)
		{
			RecreateSceneObject();
		}
		if (_sceneObject is SceneModel sceneModel)
		{
			sceneModel.SetDeformationVolumes(CollectionsMarshal.AsSpan(_effectiveVolumes));
			sceneModel.SetDeformationAnchors(_hasActiveDeformations ? DeformationAnchors : default(ReadOnlySpan<Vector4>));
			_sceneObject.Flags.IsStatic = GameObject.IsStatic && !_hasActiveDeformations;
			if (!(this is SkinnedModelRenderer))
			{
				sceneModel.UpdateToBindPose();
			}
		}
	}

	/// <summary>
	/// A deformer's volume in this model's space. One on the model this is bone merged to is in that model's, which is this
	/// one's too unless this was made turned or moved from it - exported facing another way - when it's taken across.
	/// </summary>
	[Description("A deformer's volume in this model's space. One on the model this is bone merged to is in that model's, which is this one's too unless this was made turned or moved from it - exported facing another way - when it's taken across.")]
	[SourceLocation("Scene\\Components\\Render\\ModelRenderer.Deformations.cs", 82)]
	private SceneDeformationVolumeData VolumeFor(ModelDeformer deformer)
	{
		ModelRenderer owner = deformer.Owner;
		if (owner == this || !owner.IsValid() || owner.Model == null || Model == null)
		{
			return deformer.Data;
		}
		(Model Model, Model Target) restOffsetModels = _restOffsetModels;
		Model item = restOffsetModels.Model;
		Model item2 = restOffsetModels.Target;
		Model model = Model;
		Model model2 = owner.Model;
		if (item != model || item2 != model2)
		{
			_restOffset = RestOffset(Model, owner.Model);
			_restOffsetModels = (Model: Model, Target: owner.Model);
		}
		Transform? restOffset = _restOffset;
		if (!restOffset.HasValue)
		{
			return deformer.Data;
		}
		return deformer.Pack(restOffset.GetValueOrDefault().ToLocal(deformer.Placement));
	}

	/// <summary>
	/// Where a model's rest pose sits in another's, through the first bone they share, or null when it's the same - as a
	/// bone merged model's usually is.
	/// </summary>
	[Description("Where a model's rest pose sits in another's, through the first bone they share, or null when it's the same - as a bone merged model's usually is.")]
	[SourceLocation("Scene\\Components\\Render\\ModelRenderer.Deformations.cs", 104)]
	private static Transform? RestOffset(Model model, Model target)
	{
		foreach (BoneCollection.Bone allBone in model.Bones.AllBones)
		{
			BoneCollection.Bone bone = target.Bones.GetBone(allBone.Name);
			if (bone != null)
			{
				Transform value = bone.LocalTransform.ToWorld(allBone.LocalTransform.ToLocal(in global::Transform.Zero));
				return (value.Position.Length < 0.01f && value.Rotation.Distance(Rotation.Identity) < 0.01f) ? ((Transform?)null) : new Transform?(value);
			}
		}
		return null;
	}

	/// <summary>
	/// Creates the scene representation needed by this renderer's current deformation state.
	/// </summary>
	[Description("Creates the scene representation needed by this renderer's current deformation state.")]
	[SourceLocation("Scene\\Components\\Render\\ModelRenderer.Deformations.cs", 121)]
	protected virtual SceneObject CreateSceneObject(Model model)
	{
		if (_hasActiveDeformations)
		{
			return new SceneModel(Scene.SceneWorld, model, WorldTransform)
			{
				UseAnimGraph = false
			};
		}
		return new SceneObject(Scene.SceneWorld, model, WorldTransform);
	}

	[SourceLocation("Scene\\Components\\Render\\ModelRenderer.Deformations.cs", 131)]
	private void RecreateSceneObject()
	{
		BackupRenderAttributes(_sceneObject.Attributes);
		_sceneObject.Delete();
		_sceneObject = CreateSceneObject(Model ?? Model.Load("models/dev/box.vmdl"));
		OnSceneObjectCreated(_sceneObject);
	}

	/// <summary>
	/// Completely stop overriding materials
	/// </summary>
	[Description("Completely stop overriding materials")]
	[SourceLocation("Scene\\Components\\Render\\ModelRenderer.Materials.cs", 33)]
	public void ClearMaterialOverrides()
	{
		taggedMaterialOverrides = null;
		MaterialOverride = null;
		_sceneObject?.ClearMaterialOverride();
	}

	/// <summary>
	/// Set a material override for a material with a specific attribute set. For example, if you have a model with lots of different materials, but one of them has an attribute "skin" set to "1", then 
	/// calling this with a material and "skin" will override only that material.
	/// </summary>
	[Description("Set a material override for a material with a specific attribute set. For example, if you have a model with lots of different materials, but one of them has an attribute \"skin\" set to \"1\", then calling this with a material and \"skin\" will override only that material.")]
	[SourceLocation("Scene\\Components\\Render\\ModelRenderer.Materials.cs", 44)]
	public void SetMaterialOverride(Material material, string target)
	{
		if (material != null || taggedMaterialOverrides != null)
		{
			if (taggedMaterialOverrides == null)
			{
				taggedMaterialOverrides = new Dictionary<string, Material>();
			}
			if (material == null)
			{
				taggedMaterialOverrides.Remove(target);
				_sceneObject?.SetMaterialOverride(null, target);
			}
			else
			{
				taggedMaterialOverrides[target] = material;
			}
			ApplyMaterialOverrides();
		}
	}

	/// <summary>
	/// Apply any saved material overrides to the scene object.
	/// </summary>
	[Description("Apply any saved material overrides to the scene object.")]
	[SourceLocation("Scene\\Components\\Render\\ModelRenderer.Materials.cs", 67)]
	private void ApplyMaterialOverrides()
	{
		if (!_sceneObject.IsValid())
		{
			return;
		}
		if (taggedMaterialOverrides != null)
		{
			foreach (KeyValuePair<string, Material> taggedMaterialOverride in taggedMaterialOverrides)
			{
				_sceneObject.SetMaterialOverride(taggedMaterialOverride.Value, taggedMaterialOverride.Key);
			}
		}
		_materialAccessor?.Apply();
	}

	[SourceLocation("Scene\\Components\\Render\\ModelRenderer.Materials.cs", 90)]
	int MaterialAccessor.ITarget.GetMaterialCount()
	{
		if (!Model.IsValid())
		{
			return 0;
		}
		return Model.Materials.Length;
	}

	[SourceLocation("Scene\\Components\\Render\\ModelRenderer.Materials.cs", 96)]
	Material MaterialAccessor.ITarget.Get(int index)
	{
		if (!Model.IsValid())
		{
			return null;
		}
		if (index < 0)
		{
			return null;
		}
		if (index >= Model.Materials.Length)
		{
			return null;
		}
		return Model.Materials[index];
	}

	[SourceLocation("Scene\\Components\\Render\\ModelRenderer.Materials.cs", 105)]
	void MaterialAccessor.ITarget.SetOverride(int index, Material material)
	{
		if (_sceneObject.IsValid())
		{
			_sceneObject.native.SetMaterialOverrideByIndex(index, material?.native ?? default(IMaterial));
			_sceneObject.NotifyChanged(SceneObjectChange.Material);
		}
	}

	[SourceLocation("Scene\\Components\\Render\\ModelRenderer.Materials.cs", 113)]
	void MaterialAccessor.ITarget.ClearOverrides()
	{
		if (_sceneObject.IsValid())
		{
			_sceneObject.native.ClearMaterialOverrideList();
			_sceneObject.NotifyChanged(SceneObjectChange.Material);
		}
	}
}
