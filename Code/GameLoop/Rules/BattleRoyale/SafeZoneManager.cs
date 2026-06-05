using Sandbox;
using Sandbox.Events;
using System.Linq;
using System;

namespace Facepunch;

/// <summary>
/// Handles the shrinking safe zone in Battle Royale.
/// </summary>
public sealed class SafeZoneManager : Component
{
	[Property] public float InitialRadius { get; set; } = 8000f;
	[Property] public float FinalRadius { get; set; } = 100f;
	[Property] public float ShrinkTime { get; set; } = 300f; // 5 minutes to fully shrink
	[Property] public float DamagePerSecond { get; set; } = 10f;
	[Property, Sync] public Vector3 ZoneCenter { get; set; } = Vector3.Zero;

	[Sync] public float CurrentRadius { get; private set; }

	private TimeSince _timeSinceStart;
	private TimeSince _timeSinceDamageTick;

	protected override void OnStart()
	{
		_timeSinceStart = 0;
		_timeSinceDamageTick = 0;
		CurrentRadius = InitialRadius;
	}

	protected override void OnUpdate()
	{
		if ( !Networking.IsHost ) return;

		// Calculate current radius based on lerp
		float fraction = Math.Clamp( _timeSinceStart / ShrinkTime, 0f, 1f );
		CurrentRadius = float.Lerp( InitialRadius, FinalRadius, fraction );

		// Apply damage to players outside the zone every ~0.16s
		if ( _timeSinceDamageTick >= 0.16f )
		{
			_timeSinceDamageTick = 0;

			foreach ( var player in GameUtils.PlayerPawns )
			{
				if ( player.HealthComponent is null || player.HealthComponent.State != LifeState.Alive )
					continue;

				// Check 2D distance for standard BR cylinder zone
				float dist = player.WorldPosition.WithZ( 0 ).Distance( ZoneCenter.WithZ( 0 ) );
				if ( dist > CurrentRadius )
				{
					// Out of bounds — attacker is null (zone damage), inflictor is null
					var dmg = new DamageInfo( null, DamagePerSecond * 0.16f );
					player.HealthComponent.TakeDamage( dmg );
				}
			}
		}
	}
}
