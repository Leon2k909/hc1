using System.Text.Json.Nodes;
using Sandbox.Internal;
using Sandbox.Rendering;

namespace Sandbox;

/// <summary>
/// Applies a tonemapping effect to the camera.
/// </summary>
[Title("Tone Mapping")]
[Category("Post Processing")]
[Icon("exposure")]
[Description("Applies a tonemapping effect to the camera.")]
[SourceLocation("Scene\\Components\\PostProcessing\\Effects\\Tonemapping.cs", 9)]
public class Tonemapping : BasePostProcess<Tonemapping>
{
	/// <summary>
	/// Options to select a tonemapping algorithm to use for color grading.
	/// </summary>
	[Description("Options to select a tonemapping algorithm to use for color grading.")]
	public enum TonemappingMode
	{
		/// <summary>
		/// John Hable's filmic tonemapping algorithm.
		/// Matches the default curve Source 2 uses based on Uncharted 2.
		/// </summary>
		[Description("John Hable's filmic tonemapping algorithm. Matches the default curve Source 2 uses based on Uncharted 2.")]
		HableFilmic = 1,
		/// <summary>
		/// The most realistic tonemapper at handling bright light, desaturating light as it becomes brighter.
		/// This is slightly more expensive than other options.
		/// </summary>
		[Description("The most realistic tonemapper at handling bright light, desaturating light as it becomes brighter. This is slightly more expensive than other options.")]
		ACES,
		/// <summary>
		/// Reinhard's tonemapper, which is a simple and fast tonemapper.
		/// </summary>
		[Description("Reinhard's tonemapper, which is a simple and fast tonemapper.")]
		ReinhardJodie,
		/// <summary>
		/// Linear tonemapper, only applies autoexposure.
		/// </summary>
		[Description("Linear tonemapper, only applies autoexposure.")]
		Linear,
		/// <summary>
		/// Similar to ACES - very realistic, but handles lower and higher brightness ranges better.
		/// Uses the Punchy AgX look.
		/// </summary>
		[Description("Similar to ACES - very realistic, but handles lower and higher brightness ranges better. Uses the Punchy AgX look.")]
		AgX
	}

	public enum ExposureColorSpaceEnum
	{
		RGB,
		Luminance
	}

	[SourceLocation("Scene\\Components\\PostProcessing\\Effects\\Tonemapping.cs", 58)]
	private static Material Shader = Material.FromShader("shaders/tonemapping/tonemapping.shader");

	/// <summary>
	/// Which tonemapping algorithm to use for color grading.
	/// </summary>
	[Property]
	[DefaultValue(TonemappingMode.HableFilmic)]
	[Description("Which tonemapping algorithm to use for color grading.")]
	[SourceLocation("Scene\\Components\\PostProcessing\\Effects\\Tonemapping.cs", 53)]
	public TonemappingMode Mode { get; set; } = TonemappingMode.HableFilmic;

	[ShowIf("Mode", TonemappingMode.HableFilmic)]
	[Property]
	[DefaultValue(ExposureColorSpaceEnum.RGB)]
	[SourceLocation("Scene\\Components\\PostProcessing\\Effects\\Tonemapping.cs", 55)]
	public ExposureColorSpaceEnum ExposureMethod { get; set; }

	[Property]
	[Group("Auto Exposure")]
	[DefaultValue(true)]
	[SourceLocation("Scene\\Components\\PostProcessing\\Effects\\Tonemapping.cs", 75)]
	public bool AutoExposureEnabled { get; set; } = true;

	[Property]
	[Group("Auto Exposure")]
	[Range(0f, 3f)]
	[ShowIf("AutoExposureEnabled", true)]
	[DefaultValue(1f)]
	[SourceLocation("Scene\\Components\\PostProcessing\\Effects\\Tonemapping.cs", 78)]
	public float MinimumExposure { get; set; } = 1f;

	[Property]
	[Group("Auto Exposure")]
	[Range(0f, 5f)]
	[ShowIf("AutoExposureEnabled", true)]
	[DefaultValue(3f)]
	[SourceLocation("Scene\\Components\\PostProcessing\\Effects\\Tonemapping.cs", 81)]
	public float MaximumExposure { get; set; } = 3f;

	[Property]
	[Group("Auto Exposure")]
	[Range(-5f, 5f)]
	[ShowIf("AutoExposureEnabled", true)]
	[DefaultValue(0f)]
	[SourceLocation("Scene\\Components\\PostProcessing\\Effects\\Tonemapping.cs", 84)]
	public float ExposureCompensation { get; set; }

	[Property]
	[Group("Auto Exposure")]
	[Range(1f, 10f)]
	[ShowIf("AutoExposureEnabled", true)]
	[DefaultValue(1f)]
	[SourceLocation("Scene\\Components\\PostProcessing\\Effects\\Tonemapping.cs", 87)]
	public float Rate { get; set; } = 1f;

	[SourceLocation("Scene\\Components\\PostProcessing\\Effects\\Tonemapping.cs", 101)]
	public override int ComponentVersion => 3;

	[SourceLocation("Scene\\Components\\PostProcessing\\Effects\\Tonemapping.cs", 60)]
	public override void Render()
	{
		UpdateExposure(Camera);
		Attributes.SetComboEnum<TonemappingMode>(StringToken.Literal("D_TONEMAPPING", 692918451u), Mode);
		Attributes.SetComboEnum<ExposureColorSpaceEnum>(StringToken.Literal("D_EXPOSUREMETHOD", 567346143u), ExposureMethod);
		BlitMode blit = BlitMode.WithBackbuffer(Shader, Stage.Tonemapping);
		Blit(blit, "Tonemapping");
	}

	[SourceLocation("Scene\\Components\\PostProcessing\\Effects\\Tonemapping.cs", 90)]
	private void UpdateExposure(CameraComponent camera)
	{
		if (camera.IsValid())
		{
			camera.AutoExposure.Enabled = AutoExposureEnabled;
			camera.AutoExposure.Compensation = GetWeighted((Tonemapping x) => x.ExposureCompensation, 0f);
			camera.AutoExposure.MinimumExposure = GetWeighted((Tonemapping x) => x.MinimumExposure, 1f);
			camera.AutoExposure.MaximumExposure = GetWeighted((Tonemapping x) => x.MaximumExposure, 3f);
			camera.AutoExposure.Rate = GetWeighted((Tonemapping x) => x.Rate, 1f);
		}
	}

	/// <summary>
	/// Remove Exposure Bias
	/// this doesn't make much sense since it's tied to only HableFilmic and does the same thing as ExposureCompensation
	/// </summary>
	[Expose]
	[JsonUpgrader(typeof(Tonemapping), 3)]
	[Description("Remove Exposure Bias this doesn't make much sense since it's tied to only HableFilmic and does the same thing as ExposureCompensation")]
	[SourceLocation("Scene\\Components\\PostProcessing\\Effects\\Tonemapping.cs", 107)]
	private static void Upgrader_v3(JsonObject obj)
	{
		if ((!obj.TryGetPropertyValue("Mode", out JsonNode jsonNode) || !(jsonNode.ToString() != "HableFilmic")) && obj.TryGetPropertyValue("ExposureBias", out JsonNode jsonNode2) && obj.TryGetPropertyValue("ExposureCompensation", out JsonNode jsonNode3))
		{
			obj["ExposureCompensation"] = (float)jsonNode2 * 0.5f + (float)jsonNode3;
		}
	}

	/// <summary>
	/// Remap the old "Legacy" mode to HableFilmic 
	/// </summary>
	[Expose]
	[JsonUpgrader(typeof(Tonemapping), 2)]
	[Description("Remap the old \"Legacy\" mode to HableFilmic")]
	[SourceLocation("Scene\\Components\\PostProcessing\\Effects\\Tonemapping.cs", 125)]
	private static void Upgrader_v2(JsonObject obj)
	{
		if (obj.TryGetPropertyValue("Mode", out JsonNode jsonNode) && jsonNode.ToString() == "Legacy")
		{
			obj["Mode"] = 1;
		}
	}
}
