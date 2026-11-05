using System;

namespace Facepunch;

public static class SprayRules
{
	public const float Reach = 96f;
	public const float Cooldown = 10f;
	public const float Lifetime = 120f;
	public const int SceneLimit = 64;
	public static bool Finite( float x, float y, float z ) => float.IsFinite( x ) && float.IsFinite( y ) && float.IsFinite( z );
	public static bool CanPlace( string id, float elapsed, bool alive, bool blocked ) =>
		CosmeticCatalog.FindSpray( id ) is not null && float.IsFinite( elapsed ) && elapsed >= Cooldown && alive && !blocked;
}
