namespace Facepunch;

/// <summary>
/// Known-good iron sight ADS offsets (<see cref="ManualOffset.AimOffset"/>), verified in-game by lining up the rear
/// aperture and front post. The M4's value has been "fixed" back to a wrong value several times (-4,0,-0.5 pushes
/// the rear sight into the camera), so any drift is reported loudly instead of silently shipping broken iron sights.
/// If you intentionally recalibrate a weapon, verify it in-game and update the table here too.
/// </summary>
public static class IronSightCalibration
{
	public static readonly IReadOnlyDictionary<string, Vector3> Expected = new Dictionary<string, Vector3>( StringComparer.OrdinalIgnoreCase )
	{
		["m4a1"] = new Vector3( 0f, 0f, 0f ),
		// The sight picture comes from the CoD ADS pose baked into the animgraph (front post centred in the notch).
		["kastov762"] = new Vector3( 0f, 0f, 0f ),
	};

	private static readonly HashSet<string> _reported = new( StringComparer.OrdinalIgnoreCase );

	/// <summary>Logs an error once per weapon if its prefab aim offset differs from the calibrated value.</summary>
	public static void Verify( Equipment equipment, ManualOffset offset )
	{
		var name = equipment?.Resource?.ResourceName;
		if ( name is null || !Expected.TryGetValue( name, out var expected ) ) return;
		if ( offset.AimOffset.Distance( expected ) < 0.01f || !_reported.Add( name ) ) return;

		Log.Error( $"[IronSightCalibration] {name} AimOffset is {offset.AimOffset}, expected {expected}. " +
			"Iron sights will be misaligned. See Code/Weapons/IronSightCalibration.cs before changing this." );
	}
}
