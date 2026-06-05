using Facepunch;

namespace Tec;

public class Exploder : Component
{
	[Property] public float ScreenShakeIntensity { get; set; } = 3f;
	[Property] public float ScreenShakeLifeTime { get; set; } = 1.5f;
	[Property] public Curve DamageFalloff { get; set; } = new Curve( new Curve.Frame( 1.0f, 1.0f ), new Curve.Frame( 0.0f, 0.0f ) );
	
	[Rpc.Broadcast]
	public void Explode(Vector3 point, float damageRadius, float baseDamage, Component attacker = null, Component inflictor = null, Curve damageFalloff = default )
	{
		if ( Networking.IsHost )
			Explosion.AtPoint( point, damageRadius, baseDamage, attacker, this, damageFalloff );
		
		// Log.Info("EXPLODEEEEEEEEEEEEEEEEEEEEEE");

		var screenShaker = ScreenShaker.Main;
		var viewer = Client.Viewer;
		
		if ( screenShaker.IsValid() && viewer.IsValid() )
		{
			var distance = viewer.GameObject.WorldPosition.Distance( WorldPosition );
			var falloff = damageFalloff;
			
			if ( falloff.Frames.IsEmpty )
			{
				falloff = new( new Curve.Frame( 1f, 1f ), new Curve.Frame( 0f, 0f ) );
			}

			var radiusWithPadding = damageRadius * 1.2f;
			
			if ( distance <= radiusWithPadding )
			{
				var scalar = falloff.Evaluate( distance / radiusWithPadding );
				var shake = new ScreenShake.Random( ScreenShakeIntensity * scalar, ScreenShakeLifeTime );
				screenShaker.Add( shake );
			}
		}

		if ( IsProxy ) return;
		GameObject.Destroy();
	}
}
