using Sandbox.Diagnostics;
using Scene = Sandbox.Scene;

namespace Facepunch;

public static partial class GameObjectExtensions
{
	/// <summary>
	/// Take damage. Only the host can call this.
	/// </summary>
	/// <param name="go"></param>
	/// <param name="damageInfo"></param>
	public static bool TakeDamage( this GameObject go, DamageInfo damageInfo )
	{
		if ( !Networking.IsHost )
		{
			Log.Warning( $"Tried to run TakeDamage on {go}, but we're not the host." );
			return false;
		}
		
		// foreach ( var damageable in go.Root.GetComponents<Component.IDamageable>() )
		// {
		// 	damageable.OnDamage( Tec.Utils.CreateDamageInfo(damageInfo));
		// }

		var damaged = false;
		var healthComponent = go.Root.GetComponentInChildren<HealthComponent>();
		var prop = go.Root.GetComponentInChildren<Prop>();

		if ( healthComponent.IsValid() )
		{
			healthComponent.TakeDamage( damageInfo );
			damaged = true;
		}
		
		if ( prop.IsValid() )
		{
			prop.OnDamage( Tec.Utils.CreateDamageInfo(damageInfo) );
			damaged = true;
		}

		return damaged;
	}

	public static void CopyPropertiesTo( this Component src, Component dst )
	{
		var json = src.Serialize().AsObject();
		json.Remove( "__guid" );
		dst.DeserializeImmediately( json );
	}

	public static string GetScenePath( this GameObject go )
	{
		return go is Scene ? "" : $"{go.Parent.GetScenePath()}/{go.Name}";
	}
}
