using System;
using System.Collections.Generic;
using System.Linq;
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
[SourceLocation("Scene\\Components\\PostProcessing\\PostProcessSystem.cs", 12)]
public sealed class PostProcessSystem : GameObjectSystem<PostProcessSystem>, Component.ISceneStage, Component.IRenderThread
{
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
		List<WeightedEffect> list = (from x in cc.GetComponentsInChildren<BasePostProcess>()
			select new WeightedEffect
			{
				Effect = x,
				Weight = 1f
			}).ToList();
		foreach (PostProcessVolume item in (Scene.GetSystem<VolumeSystem>()?.FindAll<PostProcessVolume>(vector)).OrderBy((PostProcessVolume x) => x.Priority))
		{
			float weight = item.GetWeight(vector);
			list.AddRange(from x in item.GetComponentsInChildren<BasePostProcess>()
				select new WeightedEffect
				{
					Effect = x,
					Weight = weight
				});
		}
		foreach (IGrouping<Type, WeightedEffect> item2 in from x in list
			group x by x.Effect.GetType())
		{
			WeightedEffect weightedEffect = item2.First();
			PostProcessContext ctx = new PostProcessContext
			{
				Camera = cc,
				Components = item2.ToArray()
			};
			weightedEffect.Effect.Build(ctx);
		}
	}

	/// <summary>
	/// Called in editor mode, when a volume is selected
	/// </summary>
	[Description("Called in editor mode, when a volume is selected")]
	[SourceLocation("Scene\\Components\\PostProcessing\\PostProcessSystem.cs", 134)]
	private void PreviewVolume(PostProcessVolume volume)
	{
		_ = Scene.Camera.PostProcess;
		_ = volume.WorldPosition;
		foreach (IGrouping<Type, WeightedEffect> item in from x in (from x in volume.GetComponentsInChildren<BasePostProcess>()
				select new WeightedEffect
				{
					Effect = x,
					Weight = 1f
				}).ToList()
			group x by x.Effect.GetType())
		{
			WeightedEffect weightedEffect = item.First();
			PostProcessContext ctx = new PostProcessContext
			{
				Camera = Scene.Camera,
				Components = item.ToArray()
			};
			weightedEffect.Effect.Build(ctx);
		}
	}

	/// <summary>
	/// Called whenever a camera is rendering a specific stage. This is called on the render thread.
	/// </summary>
	[Description("Called whenever a camera is rendering a specific stage. This is called on the render thread.")]
	[SourceLocation("Scene\\Components\\PostProcessing\\PostProcessSystem.cs", 158)]
	void Component.IRenderThread.OnRenderStage(CameraComponent camera, Sandbox.Rendering.Stage stage)
	{
		if (EnablePostProcess && Graphics.PostProcessEnabled && (Graphics.ToolsVisMode == 0 || stage < Sandbox.Rendering.Stage.BeforePostProcess || stage > Sandbox.Rendering.Stage.AfterPostProcess))
		{
			camera.PostProcess.OnRenderStage(stage);
		}
	}
}
