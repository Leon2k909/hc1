using System;
using System.Collections.Generic;
using Sandbox.Internal;
using Sandbox.Rendering;
using Sandbox.Volumes;

namespace Sandbox;

/// <summary>
/// Manages post-processing effects for cameras and volumes within a scene, handling their application during rendering
/// and editor preview stages.
/// </summary>
/// <remarks>This system coordinates the collection and application of post-process effects based on camera
/// position and active post-process volumes. In editor mode, it supports previewing effects for selected volumes or
/// cameras. Implements both scene stage and render thread interfaces to integrate with the rendering
/// pipeline.</remarks>
[Description("Manages post-processing effects for cameras and volumes within a scene, handling their application during rendering and editor preview stages.")]
[SourceLocation("Scene\\Components\\PostProcessing\\PostProcessSystem.BuildScratch.cs", 3)]
[SourceLocation("Scene\\Components\\PostProcessing\\PostProcessSystem.cs", 12)]
public sealed class PostProcessSystem : GameObjectSystem<PostProcessSystem>, Component.ISceneStage, Component.IRenderThread
{
	[SourceLocation("Scene\\Components\\PostProcessing\\PostProcessSystem.BuildScratch.cs", 16)]
	private sealed class BuildScratch
	{
		[SourceLocation("Scene\\Components\\PostProcessing\\PostProcessSystem.BuildScratch.cs", 18)]
		public readonly List<(PostProcessVolume Volume, int Priority, int Index)> Volumes = new List<(PostProcessVolume, int, int)>();

		[SourceLocation("Scene\\Components\\PostProcessing\\PostProcessSystem.BuildScratch.cs", 19)]
		private readonly List<BasePostProcess> _components = new List<BasePostProcess>();

		[SourceLocation("Scene\\Components\\PostProcessing\\PostProcessSystem.BuildScratch.cs", 20)]
		private readonly Dictionary<Type, int> _groupIndices = new Dictionary<Type, int>();

		[SourceLocation("Scene\\Components\\PostProcessing\\PostProcessSystem.BuildScratch.cs", 21)]
		private readonly List<List<WeightedEffect>> _groups = new List<List<WeightedEffect>>();

		[SourceLocation("Scene\\Components\\PostProcessing\\PostProcessSystem.BuildScratch.cs", 23)]
		public void AddEffects(GameObject gameObject, float weight)
		{
			_components.Clear();
			gameObject.Components.GetAll(_components, FindMode.EnabledInSelfAndDescendants);
			foreach (BasePostProcess component in _components)
			{
				Type type = component.GetType();
				if (!_groupIndices.TryGetValue(type, out var value))
				{
					value = _groupIndices.Count;
					_groupIndices.Add(type, value);
					if (value == _groups.Count)
					{
						_groups.Add(new List<WeightedEffect>());
					}
				}
				_groups[value].Add(new WeightedEffect
				{
					Effect = component,
					Weight = weight
				});
			}
		}

		[SourceLocation("Scene\\Components\\PostProcessing\\PostProcessSystem.BuildScratch.cs", 41)]
		public void Build(CameraComponent camera)
		{
			for (int i = 0; i < _groupIndices.Count; i++)
			{
				List<WeightedEffect> list = _groups[i];
				list[0].Effect.Build(new PostProcessContext
				{
					Camera = camera,
					Components = list
				});
			}
		}

		[SourceLocation("Scene\\Components\\PostProcessing\\PostProcessSystem.BuildScratch.cs", 52)]
		public void Clear()
		{
			Volumes.Clear();
			_components.Clear();
			for (int i = 0; i < _groupIndices.Count; i++)
			{
				_groups[i].Clear();
			}
			_groupIndices.Clear();
		}
	}

	[SourceLocation("Scene\\Components\\PostProcessing\\PostProcessSystem.BuildScratch.cs", 6)]
	private readonly Stack<BuildScratch> _buildScratch = new Stack<BuildScratch>();

	[SkipHotload]
	private static Action<bool> __EnablePostProcess_ConVarAttribute__CachedSetter = null;

	[SkipHotload]
	private static Func<bool> __EnablePostProcess_ConVarAttribute__CachedSetterGetter = null;

	[SkipHotload]
	private static Func<bool> __EnablePostProcess_ConVarAttribute__CachedGetter = null;

	[SkipHotload]
	private static readonly Attribute[] __EnablePostProcess__Attrs = new Attribute[2]
	{
		new ConVarAttribute("r_postprocess", ConVarFlags.Saved)
		{
			Help = "Enable or disable post process effects."
		},
		new ConVarAttribute("r_postprocess", ConVarFlags.Saved)
		{
			Help = "Enable or disable post process effects."
		}
	};

	[ConVar("r_postprocess", ConVarFlags.Saved, Help = "Enable or disable post process effects.")]
	[DefaultValue(true)]
	[SourceLocation("Scene\\Components\\PostProcessing\\PostProcessSystem.cs", 14)]
	internal static bool EnablePostProcess
	{
		get
		{
			WrappedPropertyGet<bool> p = new WrappedPropertyGet<bool>
			{
				Value = ((Func<bool>)(() => field))(),
				Object = null,
				IsStatic = true,
				TypeName = "Sandbox.PostProcessSystem",
				PropertyName = "EnablePostProcess",
				MemberIdent = 381851885,
				Attributes = __EnablePostProcess__Attrs
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
				Getter = () => EnablePostProcess,
				IsStatic = true,
				TypeName = "Sandbox.PostProcessSystem",
				PropertyName = "EnablePostProcess",
				MemberIdent = 381851885,
				Attributes = __EnablePostProcess__Attrs
			};
			ConsoleSystem.OnWrappedSet(in p);
		}
	} = true;

	[SourceLocation("Scene\\Components\\PostProcessing\\PostProcessSystem.BuildScratch.cs", 8)]
	private BuildScratch RentBuildScratch()
	{
		if (!_buildScratch.TryPop(out var result))
		{
			return new BuildScratch();
		}
		return result;
	}

	[SourceLocation("Scene\\Components\\PostProcessing\\PostProcessSystem.BuildScratch.cs", 10)]
	private void ReturnBuildScratch(BuildScratch scratch)
	{
		scratch.Clear();
		_buildScratch.Push(scratch);
	}

	public PostProcessSystem(Scene scene)
		: base(scene)
	{
	}

	/// <summary>
	/// Called at the very end of the scene update, after all other components have been ticked.
	/// We use it to update our post processing effects for each camera.
	/// </summary>
	[Description("Called at the very end of the scene update, after all other components have been ticked. We use it to update our post processing effects for each camera.")]
	[SourceLocation("Scene\\Components\\PostProcessing\\PostProcessSystem.cs", 26)]
	void Component.ISceneStage.End()
	{
		if (!EnablePostProcess || Application.IsDedicatedServer)
		{
			return;
		}
		if (Scene.IsEditor)
		{
			UpdateEditorScene();
			return;
		}
		foreach (CameraComponent item in Scene.Query<CameraComponent>())
		{
			UpdateCamera(item);
		}
	}

	[SourceLocation("Scene\\Components\\PostProcessing\\PostProcessSystem.cs", 49)]
	private void UpdateEditorScene()
	{
		if (Scene.Camera == null)
		{
			return;
		}
		Scene.Camera.PostProcess.Clear();
		Scene.Camera.AutoExposure.Enabled = true;
		Scene.Camera.AutoExposure.Compensation = 0f;
		Scene.Camera.AutoExposure.Rate = 20f;
		Scene.Camera.AutoExposure.MinimumExposure = 1f;
		Scene.Camera.AutoExposure.MaximumExposure = 2f;
		GameObject gameObject = Scene.Editor?.SelectedGameObject;
		if (gameObject != null)
		{
			CameraComponent componentInParent = gameObject.GetComponentInParent<CameraComponent>();
			if (componentInParent != null)
			{
				UpdateCamera(componentInParent);
				return;
			}
			PostProcessVolume componentInParent2 = gameObject.GetComponentInParent<PostProcessVolume>();
			if (componentInParent2 != null && componentInParent2.EditorPreview)
			{
				PreviewVolume(componentInParent2);
				return;
			}
		}
		CameraComponent camera = Scene.Camera;
		if (camera != null)
		{
			UpdateCamera(camera);
		}
	}

	[SourceLocation("Scene\\Components\\PostProcessing\\PostProcessSystem.cs", 97)]
	private void UpdateCamera(CameraComponent cc)
	{
		cc.PostProcess.Clear();
		if (!cc.EnablePostProcessing)
		{
			return;
		}
		Vector3 vector = (cc.PostProcessAnchor.IsValid() ? cc.PostProcessAnchor.WorldPosition : cc.WorldPosition);
		BuildScratch buildScratch = RentBuildScratch();
		try
		{
			buildScratch.AddEffects(cc.GameObject, 1f);
			foreach (PostProcessVolume item in Scene.Query<PostProcessVolume>())
			{
				if (((VolumeSystem.IVolume)item).Test(vector))
				{
					buildScratch.Volumes.Add((item, item.Priority, buildScratch.Volumes.Count));
				}
			}
			buildScratch.Volumes.Sort(((PostProcessVolume Volume, int Priority, int Index) a, (PostProcessVolume Volume, int Priority, int Index) b) =>
			{
				int num = a.Priority.CompareTo(b.Priority);
				return (num == 0) ? a.Index.CompareTo(b.Index) : num;
			});
			foreach (var volume in buildScratch.Volumes)
			{
				buildScratch.AddEffects(volume.Volume.GameObject, volume.Volume.GetWeight(vector));
			}
			buildScratch.Build(cc);
		}
		finally
		{
			ReturnBuildScratch(buildScratch);
		}
	}

	/// <summary>
	/// Called in editor mode, when a volume is selected
	/// </summary>
	[Description("Called in editor mode, when a volume is selected")]
	[SourceLocation("Scene\\Components\\PostProcessing\\PostProcessSystem.cs", 137)]
	private void PreviewVolume(PostProcessVolume volume)
	{
		BuildScratch buildScratch = RentBuildScratch();
		try
		{
			buildScratch.AddEffects(volume.GameObject, 1f);
			buildScratch.Build(Scene.Camera);
		}
		finally
		{
			ReturnBuildScratch(buildScratch);
		}
	}

	/// <summary>
	/// Called whenever a camera is rendering a specific stage. This is called on the render thread.
	/// </summary>
	[Description("Called whenever a camera is rendering a specific stage. This is called on the render thread.")]
	[SourceLocation("Scene\\Components\\PostProcessing\\PostProcessSystem.cs", 154)]
	void Component.IRenderThread.OnRenderStage(CameraComponent camera, Sandbox.Rendering.Stage stage)
	{
		if (EnablePostProcess && Graphics.PostProcessEnabled && (Graphics.ToolsVisMode == 0 || stage < Sandbox.Rendering.Stage.BeforePostProcess || stage > Sandbox.Rendering.Stage.AfterPostProcess))
		{
			camera.PostProcess.OnRenderStage(stage);
		}
	}
}
