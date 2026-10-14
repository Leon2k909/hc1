using System;
using Sandbox.Internal;

namespace Sandbox;

/// <summary>
/// A directional light that casts shadows, like the sun.
/// </summary>
[Expose]
[Title("Directional Light")]
[Category("Light")]
[Icon("light_mode")]
[EditorHandle("materials/gizmo/directionallight.png")]
[Alias(new string[] { "DirectionalLightComponent" })]
[Description("A directional light that casts shadows, like the sun.")]
[SourceLocation("Scene\\Components\\Light\\DirectionalLight.cs", 6)]
public class DirectionalLight : Light
{
	[SourceLocation("Scene\\Components\\Light\\DirectionalLight.cs", 23)]
	public class CascadeVisualizer
	{
		[SourceLocation("Scene\\Components\\Light\\DirectionalLight.cs", 25)]
		public Action Update;
	}

	[SourceLocation("Scene\\Components\\Light\\DirectionalLight.cs", 14)]
	private SceneDirectionalLight _so;

	/// <summary>
	/// Color of the ambient sky color
	/// This is kept for long term support, the recommended way to do this is with an Ambient Light component.
	/// </summary>
	[Property]
	[Description("Color of the ambient sky color This is kept for long term support, the recommended way to do this is with an Ambient Light component.")]
	[SourceLocation("Scene\\Components\\Light\\DirectionalLight.cs", 20)]
	public Color SkyColor { get; set; }

	/// <summary>
	/// Number of cascades to split the view frustum into for the whole scene dynamic shadow.  
	/// More cascades result in better shadow resolution, but adds significant rendering cost.
	///
	/// User settings will set a maximum.
	/// </summary>
	[Property]
	[Group("Shadows")]
	[Title("Cascade Count")]
	[Range(1f, 4f)]
	[InfoBox("More cascades gives better detail at the cost of performance. User quality settings override this.", "info", EditorTint.Blue)]
	[DefaultValue(4)]
	[Description("Number of cascades to split the view frustum into for the whole scene dynamic shadow. More cascades result in better shadow resolution, but adds significant rendering cost. User settings will set a maximum.")]
	[SourceLocation("Scene\\Components\\Light\\DirectionalLight.cs", 34)]
	public int ShadowCascadeCount
	{
		get;
		set
		{
			if (field != value)
			{
				field = value;
				if (_so.IsValid())
				{
					_so.ShadowCascadeCount = value;
				}
				Visualizer?.Update?.Invoke();
			}
		}
	} = 4;

	/// <summary>
	/// Controls how cascades 2+ are distributed between the first cascade boundary and the far clip.
	/// 0 is uniform, 1 is fully logarithmic.
	/// </summary>
	[Property]
	[Group("Shadows")]
	[Title("Split ratio")]
	[Range(0f, 1f)]
	[HideIf("ShadowCascadeCount", 1)]
	[DefaultValue(0.91f)]
	[Description("Controls how cascades 2+ are distributed between the first cascade boundary and the far clip. 0 is uniform, 1 is fully logarithmic.")]
	[SourceLocation("Scene\\Components\\Light\\DirectionalLight.cs", 55)]
	public float ShadowCascadeSplitRatio
	{
		get;
		set
		{
			if (field != value)
			{
				field = value;
				if (_so.IsValid())
				{
					_so.ShadowCascadeSplitRatio = value;
				}
				Visualizer?.Update?.Invoke();
			}
		}
	} = 0.91f;

	[Property]
	[Group("Shadows")]
	[HideIf("ShadowCascadeCount", 1)]
	[SourceLocation("Scene\\Components\\Light\\DirectionalLight.cs", 71)]
	public CascadeVisualizer Visualizer { get; set; } = new CascadeVisualizer();

	/// <summary>
	/// Add small-scale screen-space contact shadows on top of the cascaded shadow maps. Captures
	/// fine contact detail the shadow maps miss, at some GPU cost.
	/// </summary>
	[Property]
	[Group("Shadows")]
	[Title("Contact Shadows")]
	[Advanced]
	[DefaultValue(true)]
	[Description("Add small-scale screen-space contact shadows on top of the cascaded shadow maps. Captures fine contact detail the shadow maps miss, at some GPU cost.")]
	[SourceLocation("Scene\\Components\\Light\\DirectionalLight.cs", 78)]
	public bool ContactShadows
	{
		get;
		set
		{
			field = value;
			if (_so.IsValid())
			{
				_so.ContactShadows = value;
			}
		}
	} = true;

	[SourceLocation("Scene\\Components\\Light\\DirectionalLight.cs", 91)]
	protected override SceneLight CreateSceneObject()
	{
		SceneDirectionalLight sceneDirectionalLight = new SceneDirectionalLight(Scene.SceneWorld, WorldRotation, LightColor)
		{
			ShadowCascadeCount = ShadowCascadeCount,
			ShadowCascadeSplitRatio = ShadowCascadeSplitRatio,
			ContactShadows = ContactShadows
		};
		SceneDirectionalLight result = sceneDirectionalLight;
		_so = sceneDirectionalLight;
		return result;
	}

	[SourceLocation("Scene\\Components\\Light\\DirectionalLight.cs", 101)]
	protected override void OnAwake()
	{
		Tags.Add("light_directional");
		base.OnAwake();
	}

	[SourceLocation("Scene\\Components\\Light\\DirectionalLight.cs", 108)]
	protected override void DrawGizmos()
	{
		using (Gizmo.Scope($"light-{GetHashCode()}"))
		{
			Gizmo.Draw.Color = LightColor;
			int num = 12;
			for (int i = 0; i < num; i++)
			{
				float x = (float)Math.PI * 2f * (float)i / (float)num;
				Vector3 a = (MathF.Sin(x) * Vector3.Left + MathF.Cos(x) * Vector3.Up) * 5f;
				Gizmo.Draw.Line(in a, a + Vector3.Forward * 30f);
			}
		}
	}
}
