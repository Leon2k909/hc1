using System;
using NativeEngine;
using Sandbox.Diagnostics;
using Sandbox.Internal;

namespace Sandbox;

[Expose]
[SourceLocation("Scene\\Components\\Light\\Light.cs", 6)]
public abstract class Light : Component, Component.IColorProvider, Component.ExecuteInEditor, Component.ITintable
{
	/// <summary>
	/// Backend carrier for map light settings that aren't exposed as component properties yet.
	/// </summary>
	[Description("Backend carrier for map light settings that aren't exposed as component properties yet.")]
	internal struct LegacyLightData
	{
		[SourceLocation("Scene\\Components\\Light\\Light.cs", 25)]
		public int DirectLight;

		[SourceLocation("Scene\\Components\\Light\\Light.cs", 26)]
		public int BakeLightIndex;

		[SourceLocation("Scene\\Components\\Light\\Light.cs", 27)]
		public float BakeLightIndexScale;

		[SourceLocation("Scene\\Components\\Light\\Light.cs", 28)]
		public bool BakedLightIndexing;

		[SourceLocation("Scene\\Components\\Light\\Light.cs", 29)]
		public float FogContributionStrength;

		[SourceLocation("Scene\\Components\\Light\\Light.cs", 30)]
		public bool RenderDiffuse;

		[SourceLocation("Scene\\Components\\Light\\Light.cs", 31)]
		public bool RenderSpecular;

		[SourceLocation("Scene\\Components\\Light\\Light.cs", 32)]
		public int FogLighting;

		[SourceLocation("Scene\\Components\\Light\\Light.cs", 35)]
		public float? ConstantAttenuation;

		[SourceLocation("Scene\\Components\\Light\\Light.cs", 36)]
		public float? LinearAttenuation;

		[SourceLocation("Scene\\Components\\Light\\Light.cs", 37)]
		public float? QuadraticAttenuation;

		[SourceLocation("Scene\\Components\\Light\\Light.cs", 38)]
		public float? FallOff;

		[SourceLocation("Scene\\Components\\Light\\Light.cs", 39)]
		public Texture Cookie;

		[SourceLocation("Scene\\Components\\Light\\Light.cs", 41)]
		public readonly void ApplyTo(CSceneLightObject light)
		{
			switch (DirectLight)
			{
			case 3:
				light.SetLightFlags(light.GetLightFlags() | 0x10);
				light.SetLightFlags(light.GetLightFlags() | 0x20);
				break;
			case 1:
				light.SetLightFlags(light.GetLightFlags() | 0x20);
				break;
			}
			light.SetBakeLightIndex(BakeLightIndex);
			light.SetBakeLightIndexScale(BakeLightIndexScale);
			light.SetUsesIndexedBakedLighting(BakedLightIndexing);
			light.SetFogContributionStength(FogContributionStrength);
			light.SetRenderDiffuse(RenderDiffuse);
			light.SetRenderSpecular(RenderSpecular);
			light.SetFogLightingMode(FogLighting);
			float? constantAttenuation = ConstantAttenuation;
			if (constantAttenuation.HasValue)
			{
				float valueOrDefault = constantAttenuation.GetValueOrDefault();
				light.SetConstantAttn(valueOrDefault);
			}
			constantAttenuation = LinearAttenuation;
			if (constantAttenuation.HasValue)
			{
				float valueOrDefault2 = constantAttenuation.GetValueOrDefault();
				light.SetLinearAttn(valueOrDefault2);
			}
			constantAttenuation = QuadraticAttenuation;
			if (constantAttenuation.HasValue)
			{
				float valueOrDefault3 = constantAttenuation.GetValueOrDefault();
				light.SetQuadraticAttn(valueOrDefault3);
			}
			constantAttenuation = FallOff;
			if (constantAttenuation.HasValue)
			{
				float valueOrDefault4 = constantAttenuation.GetValueOrDefault();
				light.SetFallOff(valueOrDefault4);
			}
			if (Cookie != null)
			{
				light.SetLightCookie(Cookie.native);
			}
		}
	}

	public enum FogInfluence
	{
		[Icon("blur_off")]
		Disabled = 0,
		[Icon("blur_linear")]
		Enabled = 2,
		[Icon("blur_on")]
		WithoutShadows = 3
	}

	/// <summary>
	/// Which lighting terms a light is allowed to contribute to.
	/// </summary>
	[Flags]
	[Description("Which lighting terms a light is allowed to contribute to.")]
	public enum LightContribution
	{
		/// <summary>
		/// Soft, even shading across a surface.
		/// </summary>
		[Icon("wb_sunny")]
		[Description("Soft, even shading across a surface.")]
		Diffuse = 1,
		/// <summary>
		/// Glossy highlights and reflections.
		/// </summary>
		[Icon("auto_awesome")]
		[Description("Glossy highlights and reflections.")]
		Specular = 2,
		/// <summary>
		/// Light passing through surfaces (translucency / subsurface).
		/// </summary>
		[Icon("opacity")]
		[Description("Light passing through surfaces (translucency / subsurface).")]
		Transmissive = 4
	}

	[SourceLocation("Scene\\Components\\Light\\Light.cs", 9)]
	private SceneLight _sceneObject;

	[SourceLocation("Scene\\Components\\Light\\Light.cs", 11)]
	internal SceneLight SceneObject => _sceneObject;

	/// <summary>
	/// Advanced settings imported from legacy map data that don't have public properties yet
	/// (baking, bounce, shadow texture size, raw attenuation). Applied to the native light when it's
	/// created. Internal for now - we may expose some of these as proper properties later.
	/// </summary>
	[Description("Advanced settings imported from legacy map data that don't have public properties yet (baking, bounce, shadow texture size, raw attenuation). Applied to the native light when it's created. Internal for now - we may expose some of these as proper properties later.")]
	[SourceLocation("Scene\\Components\\Light\\Light.cs", 18)]
	internal LegacyLightData? LegacyData { get; set; }

	/// <summary>
	/// The main color of the light
	/// </summary>
	[Property]
	[DefaultValue("#E9FAFF")]
	[Description("The main color of the light")]
	[SourceLocation("Scene\\Components\\Light\\Light.cs", 75)]
	public Color LightColor
	{
		get;
		set
		{
			if (!(field == value))
			{
				field = value;
				if (_sceneObject.IsValid())
				{
					_sceneObject.LightColor = value;
				}
			}
		}
	} = "#E9FAFF";

	[Property]
	[Category("Fog Settings")]
	[DefaultValue(FogInfluence.Enabled)]
	[SourceLocation("Scene\\Components\\Light\\Light.cs", 89)]
	public FogInfluence FogMode
	{
		get;
		set
		{
			if (field != value)
			{
				field = value;
				if (_sceneObject.IsValid())
				{
					_sceneObject.FogLighting = (SceneLight.FogLightingMode)value;
				}
			}
		}
	} = FogInfluence.Enabled;

	[Property]
	[Range(0f, 1f)]
	[Category("Fog Settings")]
	[DefaultValue(1f)]
	[SourceLocation("Scene\\Components\\Light\\Light.cs", 103)]
	public float FogStrength
	{
		get;
		set
		{
			if (field != value)
			{
				field = value;
				if (_sceneObject.IsValid())
				{
					_sceneObject.FogStrength = value;
				}
			}
		}
	} = 1f;

	/// <summary>
	/// Should this light cast shadows?
	/// </summary>
	[Property]
	[Category("Shadows")]
	[Order(-10)]
	[DefaultValue(true)]
	[Description("Should this light cast shadows?")]
	[SourceLocation("Scene\\Components\\Light\\Light.cs", 120)]
	public bool Shadows
	{
		get;
		set
		{
			if (field != value)
			{
				field = value;
				if (_sceneObject.IsValid())
				{
					_sceneObject.ShadowsEnabled = value;
				}
			}
		}
	} = true;

	[Property]
	[Range(0f, 1f)]
	[Category("Shadows")]
	[Advanced]
	[DefaultValue(0f)]
	[SourceLocation("Scene\\Components\\Light\\Light.cs", 134)]
	public float ShadowBias
	{
		get;
		set
		{
			if (field != value)
			{
				field = value;
				if (_sceneObject.IsValid())
				{
					_sceneObject.ShadowBias = value;
				}
			}
		}
	}

	[Property]
	[Range(0f, 1f)]
	[Category("Shadows")]
	[DefaultValue(0f)]
	[SourceLocation("Scene\\Components\\Light\\Light.cs", 148)]
	public float ShadowHardness
	{
		get;
		set
		{
			if (field != value)
			{
				field = value;
				if (_sceneObject.IsValid())
				{
					_sceneObject.ShadowHardness = value;
				}
			}
		}
	}

	/// <summary>
	/// Which lighting terms this light is allowed to contribute to. For example,
	/// turn off <see cref="F:Sandbox.Light.LightContribution.Specular" /> to stop a light producing highlights.
	/// </summary>
	[Property]
	[EnumButtonGroup]
	[Title("Contributes")]
	[DefaultValue(LightContribution.Diffuse | LightContribution.Specular | LightContribution.Transmissive)]
	[Description("Which lighting terms this light is allowed to contribute to. For example, turn off Sandbox.Light.LightContribution.Specular to stop a light producing highlights.")]
	[SourceLocation("Scene\\Components\\Light\\Light.cs", 166)]
	public LightContribution Contribution
	{
		get;
		set
		{
			if (field != value)
			{
				field = value;
				ApplyContribution();
			}
		}
	} = LightContribution.Diffuse | LightContribution.Specular | LightContribution.Transmissive;

	[SourceLocation("Scene\\Components\\Light\\Light.cs", 189)]
	Color IColorProvider.ComponentColor => LightColor;

	[SourceLocation("Scene\\Components\\Light\\Light.cs", 191)]
	Color ITintable.Color
	{
		get
		{
			return LightColor;
		}
		set
		{
			LightColor = value;
		}
	}

	[SourceLocation("Scene\\Components\\Light\\Light.cs", 179)]
	private void ApplyContribution()
	{
		if (_sceneObject.IsValid())
		{
			_sceneObject.RenderDiffuse = Contribution.HasFlag(LightContribution.Diffuse);
			_sceneObject.RenderSpecular = Contribution.HasFlag(LightContribution.Specular);
			_sceneObject.RenderTransmissive = Contribution.HasFlag(LightContribution.Transmissive);
		}
	}

	[SourceLocation("Scene\\Components\\Light\\Light.cs", 228)]
	protected override void OnAwake()
	{
		Tags.Add("light");
		base.OnAwake();
	}

	[SourceLocation("Scene\\Components\\Light\\Light.cs", 235)]
	protected override void OnEnabled()
	{
		Assert.True(!_sceneObject.IsValid(), "_sceneObject should be null");
		Assert.NotNull(Scene, "Scene should not be null");
		_sceneObject = CreateSceneObject();
		if (_sceneObject.IsValid())
		{
			_sceneObject.Component = this;
			_sceneObject.LightColor = LightColor;
			_sceneObject.ShadowsEnabled = Shadows;
			_sceneObject.FogLighting = (SceneLight.FogLightingMode)FogMode;
			_sceneObject.FogStrength = FogStrength;
			_sceneObject.ShadowBias = ShadowBias;
			_sceneObject.ShadowHardness = ShadowHardness;
			ApplyContribution();
			LegacyData?.ApplyTo(_sceneObject.lightNative);
			OnTransformChanged();
			OnTagsChanged();
			GameTransform transform = Transform;
			transform.OnTransformChanged = (Action)Delegate.Combine(transform.OnTransformChanged, new Action(OnTransformChanged));
		}
	}

	[SourceLocation("Scene\\Components\\Light\\Light.cs", 264)]
	protected override void OnDisabled()
	{
		GameTransform transform = Transform;
		transform.OnTransformChanged = (Action)Delegate.Remove(transform.OnTransformChanged, new Action(OnTransformChanged));
		_sceneObject?.Delete();
		_sceneObject = null;
	}

	[SourceLocation("Scene\\Components\\Light\\Light.cs", 272)]
	protected abstract SceneLight CreateSceneObject();

	[SourceLocation("Scene\\Components\\Light\\Light.cs", 274)]
	private void OnTransformChanged()
	{
		if (_sceneObject.IsValid())
		{
			_sceneObject.Transform = WorldTransform;
		}
	}

	/// <summary>
	/// Tags have been updated - lets update our light's tags
	/// </summary>
	[Description("Tags have been updated - lets update our light's tags")]
	[SourceLocation("Scene\\Components\\Light\\Light.cs", 285)]
	protected override void OnTagsChanged()
	{
		if (_sceneObject.IsValid())
		{
			_sceneObject?.Tags.SetFrom(Tags);
		}
	}
}
