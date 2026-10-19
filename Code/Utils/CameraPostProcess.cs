namespace Facepunch;

/// <summary>Keep secondary views consistent with the player's native camera effects.</summary>
internal static class CameraPostProcess
{
	/// <summary>Copy an effect once, including its enabled state, without reusing its component identity.</summary>
	internal static T Copy<T>( GameObject source, GameObject target ) where T : Component, new()
	{
		var effect = source.GetComponent<T>( true );
		if ( !effect.IsValid() ) return null;
		var copy = target.Components.Create<T>();
		effect.CopyPropertiesTo( copy );
		return copy;
	}

	/// <summary>
	/// Keep active scope and drone views in sync with runtime colour adjustments to the main camera.
	/// Copy these few values directly; serializing whole components every frame would allocate unnecessarily.
	/// </summary>
	internal static void SyncColor( ColorAdjustments source, ColorAdjustments target )
	{
		if ( !target.IsValid() ) return;
		target.Enabled = source.IsValid() && source.Enabled;
		if ( !source.IsValid() ) return;

		target.Brightness = source.Brightness;
		target.Contrast = source.Contrast;
		target.Saturation = source.Saturation;
		target.HueRotate = source.HueRotate;
	}
}
