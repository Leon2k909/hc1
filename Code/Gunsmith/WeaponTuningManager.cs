namespace Facepunch;

/// <summary>
/// Client-local per-weapon tuning. Persists via Game.Cookies.
/// Each stat value ranges from -10 to +10.
/// Tuning is off for now: the gunsmith's TUNING button and modal are commented out, and the gameplay reads
/// (Shootable, ShootRecoil, Reloadable, Aimable, WeaponAmmo, GunsmithStats) ignore saved tunings. Each is marked
/// "Put back with tuning". This class and WeaponTuningPanel are kept for when it comes back.
/// </summary>
public static class WeaponTuningManager
{
	public sealed class WeaponTuning
	{
		/// <summary>+10 = +25% damage, -10 = -25% damage</summary>
		public int Damage;
		/// <summary>+10 = faster fire rate, -10 = slower</summary>
		public int FireRate;
		/// <summary>+10 = 15% faster reload, -10 = 15% slower</summary>
		public int Reload;
		/// <summary>+10 = +20% ADS walk speed, -10 = -20%</summary>
		public int AdsMoveSpeed;
		/// <summary>+10 = -15% recoil, -10 = +15% recoil</summary>
		public int Recoil;
		/// <summary>+10 = +40% mag size, -10 = -40% mag size</summary>
		public int MagSize;
	}

	public static WeaponTuning GetTuning( string weaponId )
	{
		if ( string.IsNullOrEmpty( weaponId ) )
			return new WeaponTuning();

		return new WeaponTuning
		{
			Damage       = GetCookie( weaponId, "damage" ),
			FireRate     = GetCookie( weaponId, "firerate" ),
			Reload       = GetCookie( weaponId, "reload" ),
			AdsMoveSpeed = GetCookie( weaponId, "adsmove" ),
			Recoil       = GetCookie( weaponId, "recoil" ),
			MagSize      = GetCookie( weaponId, "magsize" ),
		};
	}

	public static void AdjustTuning( string weaponId, string stat, int delta )
	{
		if ( string.IsNullOrEmpty( weaponId ) || string.IsNullOrEmpty( stat ) )
			return;

		var key = stat.ToLowerInvariant();
		var current = GetCookie( weaponId, key );
		SetCookie( weaponId, key, Math.Clamp( current + delta, -10, 10 ) );
	}

	/// <summary>
	/// Serialise all tuning to a string for network transmission.
	/// </summary>
	public static string GetPayload()
	{
		var weapons = EquipmentResource.All
			.Where( r => r.Slot is EquipmentSlot.Primary or EquipmentSlot.Secondary );

		return string.Join( ";", weapons.Select( w =>
		{
			var t = GetTuning( w.ResourceName );
			return $"{w.ResourceName}:{t.Damage},{t.FireRate},{t.Reload},{t.AdsMoveSpeed},{t.Recoil},{t.MagSize}";
		} ) );
	}

	/// <summary>
	/// Deserialise a single weapon's tuning from a network payload.
	/// </summary>
	public static WeaponTuning GetTuningFromPayload( string payload, string weaponId )
	{
		if ( string.IsNullOrEmpty( payload ) || string.IsNullOrEmpty( weaponId ) )
			return new WeaponTuning();

		foreach ( var entry in payload.Split( ';', StringSplitOptions.RemoveEmptyEntries ) )
		{
			var parts = entry.Split( ':', 2, StringSplitOptions.RemoveEmptyEntries );
			if ( parts.Length != 2 || !parts[0].Equals( weaponId, StringComparison.OrdinalIgnoreCase ) )
				continue;

			var vals = parts[1].Split( ',', StringSplitOptions.RemoveEmptyEntries );
			if ( vals.Length < 6 ) return new WeaponTuning();

			return new WeaponTuning
			{
				Damage       = ParseVal( vals[0] ),
				FireRate     = ParseVal( vals[1] ),
				Reload       = ParseVal( vals[2] ),
				AdsMoveSpeed = ParseVal( vals[3] ),
				Recoil       = ParseVal( vals[4] ),
				MagSize      = ParseVal( vals[5] ),
			};
		}

		return new WeaponTuning();
	}

	// ---- helpers -------------------------------------------------------

	private static string CookieKey( string weaponId, string stat ) =>
		$"hc1.tune.{weaponId}.{stat}";

	private static int GetCookie( string weaponId, string stat )
	{
		var raw = Game.Cookies.Get( CookieKey( weaponId, stat ), "0" );
		return int.TryParse( raw, out var v ) ? v : 0;
	}

	private static void SetCookie( string weaponId, string stat, int val ) =>
		Game.Cookies.Set( CookieKey( weaponId, stat ), val.ToString() );

	private static int ParseVal( string s ) =>
		int.TryParse( s, out var v ) ? Math.Clamp( v, -10, 10 ) : 0;
}
