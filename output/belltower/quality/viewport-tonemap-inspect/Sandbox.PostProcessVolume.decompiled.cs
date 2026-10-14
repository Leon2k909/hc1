using Sandbox.Internal;
using Sandbox.Volumes;

namespace Sandbox;

/// <summary>
/// A volume that defines a region in the scene where post processing effects will be applied.
/// </summary>
[EditorHandle(Icon = "contrast")]
[Category("Post Processing")]
[Icon("contrast")]
[Description("A volume that defines a region in the scene where post processing effects will be applied.")]
[SourceLocation("Scene\\Components\\PostProcessing\\PostProcessVolume.cs", 8)]
public class PostProcessVolume : VolumeComponent, Component.ExecuteInEditor
{
	/// <summary>
	/// Higher priority volumes override lower priority ones. The default priority is 0.
	/// </summary>
	[Property]
	[DefaultValue(0)]
	[Description("Higher priority volumes override lower priority ones. The default priority is 0.")]
	[SourceLocation("Scene\\Components\\PostProcessing\\PostProcessVolume.cs", 16)]
	public int Priority { get; set; }

	/// <summary>
	/// Allows fading in and out
	/// </summary>
	[Property]
	[Range(0f, 1f)]
	[DefaultValue(1f)]
	[Description("Allows fading in and out")]
	[SourceLocation("Scene\\Components\\PostProcessing\\PostProcessVolume.cs", 22)]
	public float BlendWeight { get; set; } = 1f;

	/// <summary>
	/// Distance from the edge of the volume where blending starts.
	/// 0 means hard edge, higher values create softer transitions.
	/// </summary>
	[Property]
	[Range(0f, 500f)]
	[HideIf("IsInfinite", true)]
	[DefaultValue(50f)]
	[Description("Distance from the edge of the volume where blending starts. 0 means hard edge, higher values create softer transitions.")]
	[SourceLocation("Scene\\Components\\PostProcessing\\PostProcessVolume.cs", 30)]
	public float BlendDistance { get; set; } = 50f;

	/// <summary>
	/// Preview the post processing when this object is selected in the editor, or when the editor camera is inside the volume.
	/// </summary>
	[Property]
	[DefaultValue(true)]
	[Description("Preview the post processing when this object is selected in the editor, or when the editor camera is inside the volume.")]
	[SourceLocation("Scene\\Components\\PostProcessing\\PostProcessVolume.cs", 38)]
	public bool EditorPreview { get; set; } = true;

	/// <summary>
	/// Get weight based on position
	/// </summary>
	[Description("Get weight based on position")]
	[SourceLocation("Scene\\Components\\PostProcessing\\PostProcessVolume.cs", 44)]
	public float GetWeight(Vector3 pos)
	{
		if (IsInfinite)
		{
			return BlendWeight;
		}
		return GetEdgeDistance(pos).Remap(0f, BlendDistance, 0f, BlendWeight);
	}
}
