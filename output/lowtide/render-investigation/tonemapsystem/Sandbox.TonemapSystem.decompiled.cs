using System;
using Sandbox.Internal;

namespace Sandbox;

[SourceLocation("Systems\\SceneSystem\\SceneCamera.Tonemap.cs", 11)]
internal class TonemapSystem
{
	[SourceLocation("Systems\\SceneSystem\\SceneCamera.Tonemap.cs", 13)]
	private readonly SceneCamera Camera;

	[SourceLocation("Systems\\SceneSystem\\SceneCamera.Tonemap.cs", 14)]
	private ITonemapSystem System;

	[SourceLocation("Systems\\SceneSystem\\SceneCamera.Tonemap.cs", 15)]
	private SceneTonemapParameters_t Parameters = new SceneTonemapParameters_t();

	/// <summary>
	/// Enable or disable exposure.
	/// </summary>
	[DefaultValue(false)]
	[Description("Enable or disable exposure.")]
	[SourceLocation("Systems\\SceneSystem\\SceneCamera.Tonemap.cs", 38)]
	public bool Enabled { get; set; }

	/// <summary>
	/// The rate of change for exposure.
	/// </summary>
	[Description("The rate of change for exposure.")]
	[SourceLocation("Systems\\SceneSystem\\SceneCamera.Tonemap.cs", 43)]
	public float Rate
	{
		get
		{
			return Parameters.m_flRate;
		}
		set
		{
			Parameters.m_flRate = value;
			Update();
		}
	}

	/// <summary>
	/// Set the speed at which exposure fades downwards (diminishes) in response to light changes.
	/// </summary>
	[Description("Set the speed at which exposure fades downwards (diminishes) in response to light changes.")]
	[SourceLocation("Systems\\SceneSystem\\SceneCamera.Tonemap.cs", 56)]
	public float Fade
	{
		get
		{
			return Parameters.m_flAccelerateExposureDown;
		}
		set
		{
			Parameters.m_flAccelerateExposureDown = value;
			Update();
		}
	}

	/// <summary>
	/// Minimum auto exposure scale
	/// </summary>
	[Description("Minimum auto exposure scale")]
	[SourceLocation("Systems\\SceneSystem\\SceneCamera.Tonemap.cs", 69)]
	public float MinExposure
	{
		get
		{
			return Parameters.m_flAutoExposureMin;
		}
		set
		{
			Parameters.m_flAutoExposureMin = value;
			Update();
		}
	}

	/// <summary>
	/// Maximum auto exposure scale
	/// </summary>
	[Description("Maximum auto exposure scale")]
	[SourceLocation("Systems\\SceneSystem\\SceneCamera.Tonemap.cs", 82)]
	public float MaxExposure
	{
		get
		{
			return Parameters.m_flAutoExposureMax;
		}
		set
		{
			Parameters.m_flAutoExposureMax = value;
			Update();
		}
	}

	/// <summary>
	/// Number of stops to adjust auto-exposure by
	/// </summary>
	[Description("Number of stops to adjust auto-exposure by")]
	[SourceLocation("Systems\\SceneSystem\\SceneCamera.Tonemap.cs", 95)]
	public float ExposureCompensation
	{
		get
		{
			return MathF.Log(Parameters.m_flExposureCompensationScalar, 2f);
		}
		set
		{
			Parameters.m_flExposureCompensationScalar = MathF.Pow(2f, value);
			Update();
		}
	}

	/// <summary>
	/// Set a custom brightness target to go along with 'Target Bright Pixel Percentage'. (-1 for default engine behavior)
	/// </summary>
	[Description("Set a custom brightness target to go along with 'Target Bright Pixel Percentage'. (-1 for default engine behavior)")]
	[SourceLocation("Systems\\SceneSystem\\SceneCamera.Tonemap.cs", 108)]
	public float PercentTarget
	{
		get
		{
			return Parameters.m_flTonemapPercentTarget;
		}
		set
		{
			Parameters.m_flTonemapPercentTarget = value;
			Update();
		}
	}

	/// <summary>
	/// Set a target for percentage of pixels above a certain brightness. (-1 for default engine behavior)
	/// </summary>
	[Description("Set a target for percentage of pixels above a certain brightness. (-1 for default engine behavior)")]
	[SourceLocation("Systems\\SceneSystem\\SceneCamera.Tonemap.cs", 121)]
	public float PercentBrightPixels
	{
		get
		{
			return Parameters.m_flTonemapPercentBrightPixels;
		}
		set
		{
			Parameters.m_flTonemapPercentBrightPixels = value;
			Update();
		}
	}

	/// <summary>
	/// Set the minimum average luminance. This ensures that certain regions aren't too dim after tonemapping
	/// </summary>
	[Description("Set the minimum average luminance. This ensures that certain regions aren't too dim after tonemapping")]
	[SourceLocation("Systems\\SceneSystem\\SceneCamera.Tonemap.cs", 134)]
	public float MinAverageLuminance
	{
		get
		{
			return Parameters.m_flTonemapMinAvgLum;
		}
		set
		{
			Parameters.m_flTonemapMinAvgLum = value;
			Update();
		}
	}

	internal TonemapSystem(SceneCamera camera)
	{
		Camera = camera;
		System = Camera.ToneMapping?.GetNative() ?? default(ITonemapSystem);
		if (System.IsValid)
		{
			SceneTonemapParameters_t pParams = new SceneTonemapParameters_t();
			System.SetTonemapParameters(ref pParams);
		}
	}

	[SourceLocation("Systems\\SceneSystem\\SceneCamera.Tonemap.cs", 29)]
	internal void SetTonemapParameters(SceneTonemapParameters_t parameters)
	{
		Parameters = parameters;
		Update();
	}

	[SourceLocation("Systems\\SceneSystem\\SceneCamera.Tonemap.cs", 144)]
	private void Update()
	{
		if (System.IsValid)
		{
			System.SetTonemapParameters(ref Parameters);
		}
	}
}
