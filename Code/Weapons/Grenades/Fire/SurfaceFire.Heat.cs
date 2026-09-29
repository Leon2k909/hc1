namespace Facepunch;

/// <summary>
/// The fire's heat, worked out on the host: burning ground and thermite burn the players, bots and zombies near them.
/// <para>
/// Each burning cell's flames radiate like a sheet of flame their own size (<see cref="FlameEmissivePower"/>), and walls
/// shade them. Anything inside the flames takes a flash fire's heat (<see cref="InFlameFlux"/>), and thermite radiates
/// from its burning point (<see cref="ThermiteGrenade.RadiantPower"/>). The body is taken at its legs, middle and head,
/// since ground fire reaches the legs first.
/// </para>
/// <para>
/// Damage follows Eisenberg's thermal dose, the exposure time times the heat flux to the 4/3. The dose that kills half the
/// people it reaches takes all 100 health (<see cref="LethalDose"/>), and heat skin can take indefinitely does nothing
/// (<see cref="HarmlessFlux"/>). So standing in 1.4 m grass flames kills in about 7 s, and a grass front hurts from a
/// couple of metres.
/// </para>
/// </summary>
public sealed partial class SurfaceFire
{
	private const float HeatInterval = 0.25f;

	/// <summary>
	/// kW/m² from the flames' surface. With it, a long grass front gives about 7 kW/m² four flame lengths away, Butler and
	/// Cohen's (1998) safety zone distance.
	/// </summary>
	public const float FlameEmissivePower = 60f;

	/// <summary> kW/m² inside the flames: the flash fire of ASTM F1930's burn manikin tests, radiant and convective. </summary>
	public const float InFlameFlux = 84f;

	/// <summary> kW/m² touching burning thermite: 2,000 C slag and flame. </summary>
	public const float ContactFlux = 300f;

	/// <summary> kW/m²: skin can take this indefinitely (API 521). </summary>
	public const float HarmlessFlux = 1.6f;

	/// <summary>
	/// (kW/m²)^(4/3)·s: Eisenberg's (1975) dose that kills half the people it reaches, which takes 100 health.
	/// </summary>
	public const float LethalDose = 2375f;

	/// <summary> Past 20 m even a big grass front's heat is under <see cref="HarmlessFlux"/>. </summary>
	private const float HeatRange = 800f;

	/// <summary> Heat from one direction worth checking for a wall in the way, in kW/m². </summary>
	private const float ShadeCheckFlux = 0.3f;

	private const int Sectors = 16;

	/// <summary> Where the body is taken (a share of its height) and how much of the skin each point stands for. </summary>
	private static readonly (float Height, float Share)[] BodyParts = { (0.18f, 0.35f), (0.55f, 0.45f), (0.9f, 0.2f) };

	/// <summary> A body the fire can burn: a player, a bot or a zombie, where its feet are and how tall it stands. </summary>
	public readonly struct FireTarget
	{
		public Component Body { get; init; }
		public Vector3 Feet { get; init; }
		public float Height { get; init; }
	}

	/// <summary> Heat from one direction around a body: per body point, and the fire that gives most of it. </summary>
	private struct Sector
	{
		public float Leg, Middle, Head;
		public Vector3 Centre;
		public float Weight;
		public FireSource Source;
		public Component Inflictor;
		public float Strongest;
	}

	private TimeSince _sinceHeat;
	private readonly List<FireTarget> _heatTargets = new();
	private readonly Sector[] _sectors = new Sector[Sectors + 1];
	private readonly Dictionary<Component, float> _heatDebt = new();
	private readonly Dictionary<Component, float> _heatLastBurnt = new();
	private readonly List<Component> _heatStale = new();

	/// <summary> The heat reaching one body: flux per body point, the fire that gave most of it, and where from. </summary>
	private struct Exposure
	{
		public float Leg, Middle, Head;
		public FireSource Source;
		public Component Inflictor;
		public Vector3 From;

		public float this[int part] => part switch { 0 => Leg, 1 => Middle, _ => Head };
	}

	/// <summary> Host: burn whoever the fire reaches. </summary>
	private void UpdateHeat()
	{
		if ( _sinceHeat < HeatInterval ) return;
		var dt = MathF.Min( _sinceHeat, 1f );
		_sinceHeat = 0;

		if ( !TryGetHeatBounds( out var mins, out var maxs ) )
		{
			_heatDebt.Clear();
			_heatLastBurnt.Clear();
			return;
		}

		FindBodies( Scene, new BBox( mins, maxs ), _heatTargets );
		var now = Time.Now;

		foreach ( var target in _heatTargets )
		{
			var exposure = Expose( target );
			var rate = DoseRate( exposure );
			if ( rate <= 0f ) continue;

			// Tiny amounts are saved up, so a body at the edge of the heat isn't sent a damage event every update.
			var hp = _heatDebt.GetValueOrDefault( target.Body ) + rate * dt / LethalDose * 100f;
			_heatLastBurnt[target.Body] = now;
			if ( hp < 1f )
			{
				_heatDebt[target.Body] = hp;
				continue;
			}

			_heatDebt[target.Body] = 0f;
			var inflictor = exposure.Inflictor.IsValid() ? exposure.Inflictor : this;
			BurnBody( target, hp, exposure.Source, inflictor, exposure.From );
		}

		// Forget bodies that have been out of the heat a while, so saved-up heat doesn't carry over to their next burn.
		foreach ( var (body, when) in _heatLastBurnt )
		{
			if ( !body.IsValid() || now - when > 3f ) _heatStale.Add( body );
		}

		foreach ( var body in _heatStale )
		{
			_heatDebt.Remove( body );
			_heatLastBurnt.Remove( body );
		}

		_heatStale.Clear();
	}

	/// <summary> The box around everything burning, if anything is. </summary>
	private bool TryGetHeatBounds( out Vector3 mins, out Vector3 maxs )
	{
		mins = new Vector3( float.MaxValue );
		maxs = new Vector3( float.MinValue );
		var any = false;

		foreach ( var burning in _burning )
		{
			mins = mins.ComponentMin( burning.Ground );
			maxs = maxs.ComponentMax( burning.Ground );
			any = true;
		}

		foreach ( var grenade in Scene.GetAllComponents<ThermiteGrenade>() )
		{
			if ( grenade.RadiantPower <= 0f ) continue;
			mins = mins.ComponentMin( grenade.WorldPosition );
			maxs = maxs.ComponentMax( grenade.WorldPosition );
			any = true;
		}

		mins -= new Vector3( HeatRange, HeatRange, 400f );
		maxs += new Vector3( HeatRange, HeatRange, 400f );
		return any;
	}

	/// <summary> The living players, bots and zombies standing in <paramref name="box"/>. </summary>
	public static void FindBodies( Scene scene, BBox box, List<FireTarget> into )
	{
		into.Clear();

		foreach ( var pawn in scene.GetAllComponents<PlayerPawn>() )
		{
			var health = pawn.HealthComponent;
			if ( !health.IsValid() || health.State != LifeState.Alive || !box.Contains( pawn.WorldPosition ) ) continue;
			var height = pawn.IsProne ? 18f : pawn.IsCrouching ? 46f : 72f;
			into.Add( new FireTarget { Body = pawn, Feet = pawn.WorldPosition, Height = height } );
		}

		foreach ( var bot in scene.GetAllComponents<LightweightCombatBot>() )
		{
			if ( !bot.IsAlive || !box.Contains( bot.WorldPosition ) ) continue;
			into.Add( new FireTarget { Body = bot, Feet = bot.WorldPosition, Height = bot.IsCrouching ? 46f : 72f } );
		}

		foreach ( var zombie in scene.GetAllComponents<ZombieAI>() )
		{
			if ( zombie.Health <= 0f || !box.Contains( zombie.WorldPosition ) ) continue;
			into.Add( new FireTarget { Body = zombie, Feet = zombie.WorldPosition, Height = 64f } );
		}
	}

	/// <summary> Dose per second, (kW/m²)^(4/3), over the whole body. </summary>
	private static float DoseRate( in Exposure exposure )
	{
		var rate = 0f;
		for ( var part = 0; part < BodyParts.Length; part++ )
		{
			var flux = exposure[part];
			if ( flux > HarmlessFlux ) rate += BodyParts[part].Share * MathF.Pow( flux, 4f / 3f );
		}

		return rate;
	}

	private Exposure Expose( in FireTarget target )
	{
		Array.Clear( _sectors );
		var now = Time.Now;
		var middle = target.Feet + Vector3.Up * (BodyParts[1].Height * target.Height);

		var inFlame = new Exposure();
		var contact = new Exposure();

		foreach ( var burning in _burning )
		{
			var envelope = Envelope( burning, now );
			if ( envelope < 0.01f ) continue;

			var offset = burning.Ground - target.Feet;
			if ( offset.x * offset.x + offset.y * offset.y > HeatRange * HeatRange || MathF.Abs( offset.z ) > 400f ) continue;

			var flame = burning.Flame * envelope * FireFuels.Metre;
			var centre = burning.Ground + Vector3.Up * (flame * 0.5f);
			var area = CellSize / FireFuels.Metre * burning.Flame * envelope;
			var source = _cells.TryGetValue( burning.Key, out var cell ) ? cell.Source : null;

			// A body standing in the burning cell, or next to it, is in the heat whatever the walls.
			var near = offset.WithZ( 0 ).Length < CellSize * 1.5f;
			ref var sector = ref _sectors[near ? Sectors : SectorOf( centre - middle )];

			for ( var part = 0; part < BodyParts.Length; part++ )
			{
				var point = target.Feet + Vector3.Up * (BodyParts[part].Height * target.Height);
				var across = (point - burning.Ground).WithZ( 0 ).Length;
				if ( across < CellSize * 0.6f && point.z > burning.Ground.z - 8f && point.z < burning.Ground.z + flame )
				{
					SetPart( ref inFlame, part, InFlameFlux );
					inFlame.Source = source;
					inFlame.Inflictor = this;
					inFlame.From = burning.Ground;
					continue;
				}

				// A sheet of flame seen from a slant shows less of itself.
				var distance = MathF.Max( point.Distance( centre ) / FireFuels.Metre, 0.3f );
				var level = MathF.Min( 1f, across / FireFuels.Metre / distance + 0.2f );
				var view = MathF.Min( 1f, area * level / (MathF.PI * distance * distance) );
				AddPart( ref sector, part, FlameEmissivePower * view, centre, source, this );
			}
		}

		foreach ( var grenade in Scene.GetAllComponents<ThermiteGrenade>() )
		{
			var power = grenade.RadiantPower;
			if ( power <= 0f ) continue;

			var origin = grenade.WorldPosition;
			if ( origin.DistanceSquared( target.Feet ) > HeatRange * HeatRange ) continue;

			var hot = origin + Vector3.Up * 4f;
			var near = (origin - target.Feet).WithZ( 0 ).Length < ThermiteGrenade.ContactRadius * 2f;
			ref var sector = ref _sectors[near ? Sectors : SectorOf( hot - middle )];

			for ( var part = 0; part < BodyParts.Length; part++ )
			{
				var point = target.Feet + Vector3.Up * (BodyParts[part].Height * target.Height);
				var across = (point - origin).WithZ( 0 ).Length;
				if ( grenade.IsBurning && across < ThermiteGrenade.ContactRadius && point.z > origin.z - 8f
					&& point.z < origin.z + grenade.FlameHeight )
				{
					SetPart( ref contact, part, ContactFlux );
					contact.Source = grenade.Source;
					contact.Inflictor = grenade;
					contact.From = origin;
					continue;
				}

				var distance = MathF.Max( point.Distance( hot ) / FireFuels.Metre, 0.15f );
				AddPart( ref sector, part, power / (4f * MathF.PI * distance * distance), hot, grenade.Source, grenade );
			}
		}

		return Combine( middle, inFlame, contact );
	}

	private static int SectorOf( Vector3 direction ) =>
		(int)((MathF.Atan2( direction.y, direction.x ) + MathF.PI) / (2f * MathF.PI) * Sectors) % Sectors;

	private static void SetPart( ref Exposure exposure, int part, float flux )
	{
		switch ( part )
		{
			case 0: exposure.Leg = MathF.Max( exposure.Leg, flux ); break;
			case 1: exposure.Middle = MathF.Max( exposure.Middle, flux ); break;
			default: exposure.Head = MathF.Max( exposure.Head, flux ); break;
		}
	}

	private static void AddPart( ref Sector sector, int part, float flux, Vector3 from, FireSource source, Component inflictor )
	{
		if ( flux <= 0f ) return;

		switch ( part )
		{
			case 0: sector.Leg += flux; break;
			case 1: sector.Middle += flux; break;
			default: sector.Head += flux; break;
		}

		sector.Centre += from * flux;
		sector.Weight += flux;
		if ( flux > sector.Strongest )
		{
			sector.Strongest = flux;
			sector.Source = source;
			sector.Inflictor = inflictor;
		}
	}

	/// <summary>
	/// Adds up the heat from every direction a wall doesn't shade, then the flames and thermite the body is touching.
	/// </summary>
	private Exposure Combine( Vector3 middle, in Exposure inFlame, in Exposure contact )
	{
		var total = new Exposure();
		var centre = Vector3.Zero;
		var weight = 0f;
		var strongest = 0f;

		for ( var i = 0; i <= Sectors; i++ )
		{
			ref var sector = ref _sectors[i];
			if ( sector.Weight <= 0f ) continue;

			var from = sector.Centre / sector.Weight;
			if ( i < Sectors && sector.Weight / 3f > ShadeCheckFlux && IsShaded( middle, from ) ) continue;

			total.Leg += sector.Leg;
			total.Middle += sector.Middle;
			total.Head += sector.Head;
			centre += sector.Centre;
			weight += sector.Weight;

			if ( sector.Weight > strongest )
			{
				strongest = sector.Weight;
				total.Source = sector.Source;
				total.Inflictor = sector.Inflictor;
			}
		}

		total.From = weight > 0f ? centre / weight : middle;

		// Radiant heat can't be more than the flames it comes from.
		total.Leg = MathF.Min( total.Leg, InFlameFlux );
		total.Middle = MathF.Min( total.Middle, InFlameFlux );
		total.Head = MathF.Min( total.Head, InFlameFlux );

		Touch( ref total, inFlame );
		Touch( ref total, contact );
		return total;
	}

	private static void Touch( ref Exposure total, in Exposure touching )
	{
		if ( touching.Leg + touching.Middle + touching.Head <= 0f ) return;

		total.Leg = MathF.Max( total.Leg, touching.Leg );
		total.Middle = MathF.Max( total.Middle, touching.Middle );
		total.Head = MathF.Max( total.Head, touching.Head );
		total.Source = touching.Source;
		total.Inflictor = touching.Inflictor;
		total.From = touching.From;
	}

	private bool IsShaded( Vector3 from, Vector3 to )
	{
		var tr = Trace( from, to );
		return tr.Hit && tr.Distance < from.Distance( to ) - 24f;
	}

	/// <summary>
	/// Host: <paramref name="hp"/> of burns to a body, from <paramref name="from"/>. The kill goes to whoever lit the fire.
	/// </summary>
	public static void BurnBody( in FireTarget target, float hp, FireSource source, Component inflictor, Vector3 from )
	{
		var attacker = source?.Attacker;

		switch ( target.Body )
		{
			case PlayerPawn pawn when pawn.HealthComponent.IsValid():
				pawn.HealthComponent.TakeDamage( new DamageInfo( attacker, hp, inflictor, from, Flags: DamageFlags.Burn ) );
				break;

			case LightweightCombatBot bot when bot.HealthComponent.IsValid():
				bot.HealthComponent.TakeDamage( new DamageInfo( attacker, hp, inflictor, from, Flags: DamageFlags.Burn ) );
				break;

			case ZombieAI zombie:
				zombie.OnDamage( new Sandbox.DamageInfo( hp, attacker?.GameObject, inflictor?.GameObject )
				{
					Position = target.Feet + Vector3.Up * 30f,
					Origin = from,
					Tags = new TagSet( new[] { "burn" } ),
				} );
				break;
		}
	}

	/// <summary>
	/// Host: the heat at a point in kW/m² (radiant, not shaded by walls, which is enough for bots to stay out of it) and
	/// where most of it comes from.
	/// </summary>
	public static float HeatAt( Scene scene, Vector3 point, out Vector3 from )
	{
		from = point;
		var fire = Get( scene );
		var now = Time.Now;
		var flux = 0f;
		var centre = Vector3.Zero;

		if ( fire.IsValid() )
		{
			foreach ( var burning in fire._burning )
			{
				var envelope = Envelope( burning, now );
				if ( envelope < 0.01f ) continue;

				var offset = burning.Ground - point;
				if ( offset.x * offset.x + offset.y * offset.y > HeatRange * HeatRange || MathF.Abs( offset.z ) > 400f ) continue;

				var flame = burning.Flame * envelope * FireFuels.Metre;
				var hot = burning.Ground + Vector3.Up * (flame * 0.5f);
				var across = offset.WithZ( 0 ).Length;
				var q = across < CellSize * 0.6f && point.z < burning.Ground.z + flame
					? InFlameFlux
					: FlameEmissivePower * MathF.Min( 1f, CellSize / FireFuels.Metre * burning.Flame * envelope
						/ (MathF.PI * MathF.Pow( MathF.Max( point.Distance( hot ) / FireFuels.Metre, 0.3f ), 2f )) );

				flux += q;
				centre += hot * q;
			}
		}

		foreach ( var grenade in scene.GetAllComponents<ThermiteGrenade>() )
		{
			var power = grenade.RadiantPower;
			if ( power <= 0f ) continue;

			var distance = MathF.Max( point.Distance( grenade.WorldPosition ) / FireFuels.Metre, 0.15f );
			var q = distance * FireFuels.Metre < ThermiteGrenade.ContactRadius && grenade.IsBurning
				? ContactFlux
				: power / (4f * MathF.PI * distance * distance);

			flux += q;
			centre += grenade.WorldPosition * q;
		}

		if ( flux > 0f ) from = centre / flux;
		return flux;
	}
}
