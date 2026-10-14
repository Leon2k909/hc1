using System;
using System.Collections.Generic;
using Sandbox.Internal;
using Sandbox.MovieMaker;

namespace Sandbox;

/// <summary>
/// Like BasePostProcess but enables access to helper methods for accessing from multiple instances using GetWeighted.
/// </summary>
[Description("Like BasePostProcess but enables access to helper methods for accessing from multiple instances using GetWeighted.")]
[SourceLocation("Scene\\Components\\PostProcessing\\BasePostProcess.cs", 156)]
public abstract class BasePostProcess<T> : BasePostProcess where T : BasePostProcess
{
	/// <summary>
	/// Helper to get a weighted value from all active post process volumes
	/// </summary>
	[Description("Helper to get a weighted value from all active post process volumes")]
	[SourceLocation("Scene\\Components\\PostProcessing\\BasePostProcess.cs", 161)]
	protected U GetWeighted<U>(Func<T, U> value, U defaultVal = default(U), bool onlyLerpBetweenVolumes = false)
	{
		U val = defaultVal;
		IInterpolator<U> interpolator = Interpolator.GetDefault<U>();
		IReadOnlyList<WeightedEffect> components = context.Components;
		for (int i = 0; i < components.Count; i++)
		{
			WeightedEffect weightedEffect = components[i];
			U val2 = value((T)weightedEffect.Effect);
			val = interpolator.Interpolate(val, val2, weightedEffect.Weight);
			if (onlyLerpBetweenVolumes && i == 0)
			{
				val = val2;
			}
		}
		return val;
	}
}
