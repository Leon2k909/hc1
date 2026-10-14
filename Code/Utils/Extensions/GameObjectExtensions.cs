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
		
		var damaged = false;
		// A canister has its own hit volume even when its forklift is part of a merged map mesh.
		if ( go.GetComponentInParent<LpgCanister>() is { } canister )
		{
			canister.TakeDamage( damageInfo );
			return true;
		}
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

		// Zombies and other engine damage receivers don't have a HealthComponent.
		// Resolve upward from the hit object so child meshes reach their owner,
		// and only use this fallback when the existing handlers haven't dealt damage.
		if ( !damaged )
		{
			var engineDamage = Tec.Utils.CreateDamageInfo( damageInfo );
			foreach ( var receiver in go.GetComponentsInParent<Component.IDamageable>().Distinct() )
			{
				receiver.OnDamage( engineDamage );
				damaged = true;
			}
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
