namespace Facepunch;

public static class Explosion
{
	public static void AtPoint( Vector3 point, float radius, float baseDamage, Component attacker = null, Component inflictor = null, Curve falloff = default )
	{
		if ( falloff.Frames.IsEmpty )
		{
			falloff = new Curve( new Curve.Frame( 1.0f, 1.0f ), new Curve.Frame( 0.0f, 0.0f ) );
		}

		var scene = Game.ActiveScene;
		if ( !scene.IsValid() ) return;

		var objectsInArea = scene.FindInPhysics( new Sphere( point, radius ) ).ToList();
		var inflictorRoot = inflictor?.GameObject?.Root;

		// Window glass doesn't shield anyone from a blast: it breaks. Nor do player clips, which only stop players.
		var trace = scene.Trace
			.WithoutTags( "trigger", "ragdoll", "playerclip", BreakableGlass.Tag );

		if ( inflictorRoot.IsValid() )
			trace = trace.IgnoreGameObjectHierarchy( inflictorRoot );

		BreakableGlass.BreakInBlast( objectsInArea, point, trace );

		var damagedRoots = new HashSet<GameObject>();

		foreach ( var obj in objectsInArea )
		{
			if ( obj.GetComponentInParent<LpgCanister>() is { } canister )
			{
				if ( !damagedRoots.Add( canister.GameObject ) ) continue;
				var hit = trace.Ray( point, canister.WorldPosition ).Run();
				if ( hit.Hit && hit.GameObject != canister.GameObject ) continue;
				var amount = baseDamage * falloff.Evaluate( Math.Min( point.Distance( canister.WorldPosition ) / radius, 1f ) );
				canister.TakeDamage( new DamageInfo( attacker, amount, inflictor, point, canister.WorldPosition - point, Flags: DamageFlags.Explosion ) );
				continue;
			}
			var hc = obj.Root.GetComponentInChildren<HealthComponent>();
			var prop = obj.Root.GetComponentInChildren<Prop>();

			if ( hc == null && prop == null)
			{
				if ( damagedRoots.Add( obj.Root ) )
					DamageReceiver( obj.Root, trace, point, radius, baseDamage, attacker, inflictor, falloff );
				continue;
			}

			// If the object isn't in line of sight, fuck it off
			var tr = trace.Ray( point, obj.WorldPosition ).Run();
			if ( tr.Hit && tr.GameObject.IsValid() )
			{
				if ( !obj.Root.IsDescendant( tr.GameObject ) )
					continue;
			}

			var distance = obj.WorldPosition.Distance( point );
			var damage = baseDamage * falloff.Evaluate( distance / radius );
			var direction = (obj.WorldPosition - point).Normal;
			var force = direction * distance * 50f;

			DamageInfo damageInfo =
				new DamageInfo( attacker, damage, inflictor, point, force, Flags: DamageFlags.Explosion )
				{
					SeveredLimbs = hc.IsValid() && damage > 0f
						? BlastDismemberment.Select( hc, point, trace ) : BlastLimb.None
				};
			
			hc?.TakeDamage(damageInfo);
			prop?.OnDamage( Tec.Utils.CreateDamageInfo(damageInfo) );
		}
	}

	/// <summary>
	/// Something with no <see cref="HealthComponent"/> that takes the engine's damage instead (a zombie), once however
	/// many of its colliders are in the blast. Measured at its middle rather than its feet, and only walls shield it,
	/// not other zombies or players. Hit in the body, so a blast is never a headshot.
	/// </summary>
	private static void DamageReceiver( GameObject root, SceneTrace trace, Vector3 point, float radius, float baseDamage,
		Component attacker, Component inflictor, Curve falloff )
	{
		var receivers = root.GetComponents<Component.IDamageable>().ToList();
		if ( receivers.Count == 0 ) return;

		var centre = root.WorldPosition + Vector3.Up * 30f;
		var tr = trace.WithoutTags( "enemy", "player" ).Ray( point, centre ).Run();
		if ( tr.Hit && !(tr.GameObject.IsValid() && tr.GameObject.Root == root) ) return;

		var distance = centre.Distance( point );
		var damage = baseDamage * falloff.Evaluate( Math.Min( distance / radius, 1f ) );
		if ( damage <= 0f ) return;

		var info = Tec.Utils.CreateDamageInfo( new DamageInfo( attacker, damage, inflictor, centre,
			(centre - point).Normal * distance * 50f, Flags: DamageFlags.Explosion ) );
		foreach ( var receiver in receivers )
			receiver.OnDamage( info );
	}
}
