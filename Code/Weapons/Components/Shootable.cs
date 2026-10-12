using Sandbox.Events;
using Facepunch.Gunsmith;
using Tec.AI;

namespace Facepunch;

public record WeaponShotEvent( Equipment Equipment ) : IGameEvent;

public enum FireMode
{
	Semi,
	Automatic,
	Burst
}

[Icon( "track_changes" )]
[Title( "Bullet" ), Group( "Weapon Components" )]
public partial class Shootable : WeaponInputAction,
	IGameEventHandler<EquipmentHolsteredEvent>
{
	[Property, Group( "Bullet" ), EquipmentResourceProperty] public float BaseDamage { get; set; } = 25.0f;
	/// <summary> Cyclic rate in rounds per minute. Set to the real firearm's rate. </summary>
	[Property, Group( "Bullet" ), EquipmentResourceProperty] public float FireRate { get; set; } = 0.2f;
	/// <summary>
	/// Rate multiplier with a suppressor fitted. Back-pressure speeds up gas-operated and blowback actions: ~10% on a
	/// direct-impingement AR or an AK, ~5% on blowback and roller-delayed SMGs. 1 where the gun's gas can be set for the
	/// can (the SCAR-H's suppressed setting, the FAL's adjustable regulator) and on semi-only guns, whose rate is the
	/// trigger finger's. A fitted gas regulator part with a suppressed setting takes it away too (<see cref="SuppressorRateScale"/>).
	/// </summary>
	[Property, Group( "Bullet" )] public float SuppressorFireRateScale { get; set; } = 1f;
	[Property, Group( "Bullet" )] public float DryShootDelay { get; set; } = 0.15f;
	[Property, Group( "Bullet" )] public float BulletSize { get; set; } = 4.0f;
	[Property, Group( "Bullet" ), EquipmentResourceProperty] public int BulletCount { get; set; } = 1;

	[Property, Group( "Bullet Falloff" ), EquipmentResourceProperty] public Curve BaseDamageFalloff { get; set; } = new( new List<Curve.Frame>() { new( 0, 1 ), new( 1, 0 ) } );
	[Property, Group( "Bullet Falloff" ), EquipmentResourceProperty] public float MaxRange { get; set; } = 1024000;

	[Property, Group( "Bullet Spread" )] public float BulletSpread { get; set; } = 0;
	[Property, Group( "Bullet Spread" )] public float PlayerVelocityLimit { get; set; } = 300f;
	[Property, Group( "Bullet Spread" )] public float VelocitySpreadScale { get; set; } = 0.25f;
	[Property, Group( "Bullet Spread" )] public float InAirSpreadMultiplier { get; set; } = 2f;

	[Property, Group( "Penetration" )] public float PenetrationThickness { get; set; } = 32f;

	[Property, Group( "Effects" )] public GameObject MuzzleFlashPrefab { get; set; }
	[Property, Group( "Effects" )] public GameObject EjectionPrefab { get; set; }

	/// <summary>
	/// What sound should we play when we fire?
	/// </summary>
	[Property, Group( "Effects" )] public SoundEvent ShootSound { get; set; }

	[Property, Group( "Suppressed Effects" )] public GunsmithPart SuppressedAttachment { get; set; }
	[Property, Group( "Suppressed Effects" )] public GameObject SuppressedMuzzleFlashPrefab { get; set; }
	[Property, Group( "Suppressed Effects" )] public SoundEvent SuppressedShootSound { get; set; }
	[Property, Group( "Suppressed Effects" )] public float SuppressedBaseDamage { get; set; }

	/// <summary>
	/// What sound should we play when we dry fire?
	/// </summary>
	[Property, Group( "Effects" )] public SoundEvent DryFireSound { get; set; }

	/// <summary>
	/// The current weapon's ammo container.
	/// </summary>
	[Property, Category( "Ammo" ), Feature( "Ammo" )] public WeaponAmmo AmmoComponent { get; set; }

	/// <summary>
	/// Does this weapon require an ammo container to fire its bullets?
	/// </summary>
	[Property, Category( "Ammo" ), FeatureEnabled( "Ammo" )] public bool RequiresHasAmmo { get; set; } = false;

	/// <summary>
	/// How many ricochet hits until we stop traversing
	/// </summary>
	[Property, Group( "Ricochet" )] protected float RicochetMaxHits { get; set; } = 2f;

	/// <summary>
	/// Maximum angle in degrees for ricochet to be possible
	/// </summary>
	[Property, Group( "Ricochet" )] public float MaxRicochetAngle { get; set; } = 45f;

	/// <summary>
	/// Anything past 2048 units won't produce effects,
	/// This is squared.
	/// </summary>
	[Property, Group( "Effects" )] public float MaxEffectsPlayDistance { get; set; } = 4194304f;

	/// <summary>
	/// How far will we trace away from a gunshot wound, to make blood splatters?
	/// </summary>
	[Property, Group( "Effects" )] public float BloodEjectDistance { get; set; } = 512f;

	/// <summary>
	/// How quickly can we switch fire mode?
	/// </summary>
	[Property, Group( "Fire Modes" )] public float FireModeSwitchDelay { get; set; } = 0.3f;

	/// <summary>
	/// What fire modes do we support?
	/// </summary>
	[Property, Group( "Fire Modes" )]
	public List<FireMode> SupportedFireModes { get; set; } = new()
	{
		FireMode.Automatic
	};

	/// <summary>
	/// What's our current fire mode? (Or Default)
	/// </summary>
	[Property, Sync, Group( "Fire Modes" )] public FireMode CurrentFireMode { get; set; } = FireMode.Automatic;

	/// <summary>
	/// How many bullets describes a burst?
	/// </summary>
	[Property, Group( "Fire Modes" )] public int BurstAmount { get; set; } = 3;

	/// <summary>
	/// How long after we finish a burst until we can shoot again?
	/// </summary>
	[Property, Group( "Fire Modes" )] public float BurstEndDelay { get; set; } = 0.2f;

	/// <summary>
	/// The selector's positions: a fitted fire control group's (<see cref="Equipment.TriggerFireModes"/>, which only the
	/// owner has), else <see cref="SupportedFireModes"/>.
	/// </summary>
	public IReadOnlyList<FireMode> FireModes =>
		Equipment.IsValid() && Equipment.TriggerFireModes is { Count: > 0 } modes ? modes : SupportedFireModes;

	/// <summary>
	/// After the fire control group changes: a fire mode the new selector lacks becomes its counterpart (burst for
	/// automatic and back, as the M4's group and the M4A1's differ), else the selector's first.
	/// </summary>
	internal void KeepFireModeFitted()
	{
		var modes = FireModes;
		if ( modes.Count == 0 || modes.Contains( CurrentFireMode ) ) return;
		var counterpart = CurrentFireMode switch
		{
			FireMode.Automatic => FireMode.Burst,
			FireMode.Burst => FireMode.Automatic,
			_ => FireMode.Semi
		};
		CurrentFireMode = modes.Contains( counterpart ) ? counterpart : modes[0];
		ClearBurst();
		Equipment.ViewModel?.OnFireMode( CurrentFireMode );
	}

	[Sync] public TimeSince TimeSinceFireModeSwitch { get; set; }
	[Sync] public TimeSince TimeSinceBurstFinished { get; set; }
	[Sync] public bool IsBurstFiring { get; set; }

	/// <summary>
	/// Accessor for the aim ray.
	/// </summary>
	protected Ray WeaponRay
	{
		get
		{
			if ( Equipment.IsValid() && Equipment.HasTag( "aiming" ) )
			{
				var scope = Equipment.GetComponentsInChildren<CameraScope>( true ).FirstOrDefault();
				if ( scope.IsValid() && scope.RenderCamera.IsValid() )
				{
					return new Ray( scope.RenderCamera.WorldPosition, scope.RenderCamera.WorldRotation.Forward );
				}
			}
			return Equipment.Owner.AimRay;
		}
	}

	/// <summary>
	/// How long since we shot?
	/// </summary>
	public TimeSince TimeSinceShoot { get; private set; }

	/// <summary>
	/// When the next shot is due. Each shot is scheduled from when the previous one was due, not from the fixed-update
	/// tick that fired it, so the gun fires at exactly <see cref="FireRate"/> instead of being rounded up to a whole
	/// number of ticks (on the 50 Hz tick, 680 and 740 rpm both used to fire at 600).
	/// </summary>
	private float _nextShotTime;

	/// <summary>
	/// Fetches the desired model renderer that we'll focus effects on like trail effects, muzzle flashes, etc.
	/// </summary>
	protected WeaponModel Effector
	{
		get
		{
			if ( IsProxy || !Equipment.ViewModel.IsValid() )
				return Equipment.WorldModel;

			return Equipment.ViewModel;
		}
	}

	protected override void OnEnabled()
	{
		BindTag( "no_ammo", () => AmmoComponent.IsValid() && !AmmoComponent.HasAmmo );
	}

	private bool UseSuppressedEffects()
	{
		if ( Equipment.IsValid() && Equipment.ApplySavedAttachments && Equipment.Resource.IsValid()
			&& GunsmithLoadoutManager.TryGetAttachment( Equipment.Resource, GunsmithPartType.Muzzle, out var muzzle )
			&& muzzle.IsValid() && muzzle.IsSuppressor )
			return true;
		if ( Equipment.IsValid() && Equipment.ApplySavedAttachments && Equipment.Resource.IsValid()
			&& GunsmithLoadoutManager.TryGetAttachment( Equipment.Resource, GunsmithPartType.Barrel, out var barrel )
			&& barrel.IsValid() && (barrel.IsSuppressor || (barrel.Name?.Contains( "suppressor", StringComparison.OrdinalIgnoreCase ) ?? false)) )
			return true;

		return HasBuiltInSuppressor || (Equipment.IsValid() && Equipment.ApplySavedAttachments && SuppressedAttachment.IsValid()
		       && Equipment.Resource.IsValid()
		       && GunsmithLoadoutManager.HasAttachment( Equipment.Resource, SuppressedAttachment ));
	}

	private GameObject GetMuzzleFlashPrefab( bool suppressed )
	{
		// Never fall back to an unsuppressed flash when a suppressor has no flash asset.
		if ( suppressed )
			return HasBuiltInSuppressor ? MuzzleFlashPrefab : SuppressedMuzzleFlashPrefab;

		return MuzzleFlashPrefab;
	}

	private SoundEvent GetShootSound( bool suppressed )
	{
		if ( suppressed && SuppressedShootSound is not null )
			return SuppressedShootSound;

		return ShootSound;
	}

	/// <summary>
	/// Play any particle effects such as muzzle flashes.
	/// </summary>
	[Rpc.Broadcast]
	protected void DoShootEffects( bool suppressed, bool showFlash, float flashScale, float smokeScale, float soundVolume )
	{
		if ( Application.IsDedicatedServer || !Equipment.IsValid() )
			return;

		MatchRecorder.NoteShot( Equipment.Owner?.GameObject, suppressed );

		var effector = Effector;
		if ( !effector.IsValid() || !effector.ModelRenderer.IsValid() )
			return;

		if ( showFlash )
			CreateDischargeParticle( GetMuzzleFlashPrefab( suppressed ), effector.DischargeMuzzle, flashScale, "Muzzle flash" );

		if ( smokeScale > 0f )
			CreateDischargeParticle( MuzzleSmokePrefab, effector.DischargeMuzzle, smokeScale, "Muzzle smoke" );

		// One spent case per discharge, independent of flash/smoke chance and pellet count.
		effector.EjectCasing( EjectionPrefab, Equipment.Owner );

		// Falls off with distance as a real blast does, muffled through walls (GunshotAudio).
		var shootSound = GetShootSound( suppressed );
		var owner = Equipment.Owner;
		var forward = owner.IsValid() ? owner.EyeAngles.Forward : Equipment.WorldRotation.Forward;
		if ( GunshotAudio.Play( shootSound, Equipment.WorldPosition, forward, owner?.IsViewer ?? false, soundVolume ) is not null )
			Log.Trace( $"Shootable: ShootSound {shootSound.ResourceName}" );

		// Third person
		if ( Equipment.Owner.IsValid() && Equipment.Owner.BodyRenderer.IsValid() )
			Equipment.Owner.BodyRenderer.SetBool( "b_attack", true );

		// First person
		if ( Equipment.ViewModel.IsValid() )
			Equipment.ViewModel.ModelRenderer.SetBool( "b_attack", true );
	}

	private void CreateImpactEffects( in SceneTraceResult tr, Surface surface )
	{
		var hitObject = tr.GameObject;
		var pos = tr.EndPosition;
		var normal = tr.Normal;
		var impactPrefab = surface.GetBulletImpact();

		if ( impactPrefab.IsValid() )
		{
			var impact = impactPrefab.Clone();
			impact.WorldPosition = pos + normal;
			impact.WorldRotation = Rotation.LookAt( normal );
			if ( hitObject.IsValid() )                     // map clutter (trees) has no GameObject
				impact.SetParent( hitObject, true );

			// Shots run in fixed update, which interpolates the re-parent: for a frame the effect sits at
			// hitObject.PointToWorld( pos ) (thousands of units away) and its particles burst there.
			impact.Transform.ClearInterpolation();
		}

		// What the round strikes, by its material (Tools/world_sounds.py), heard once the round has got there and the
		// sound has come back.
		if ( WorldSounds.BulletImpact( tr, surface ) is { } sound )
			GunshotAudio.PlayDelayed( sound, pos, ImpactSoundDelay( pos ) );
	}

	/// <summary>
	/// Shoot the gun!
	/// </summary>
	public void Shoot()
	{
		// Held fire goes off on the first tick after the shot is due, so carry that lateness into the next shot and the
		// average rate is exact. A later shot (trigger released, or semi-auto) starts a fresh schedule, so clicking can
		// never beat the cyclic rate.
		var continuing = Time.Now - _nextShotTime < Time.Delta;
		_nextShotTime = (continuing ? _nextShotTime : Time.Now) + RPMToSeconds();
		TimeSinceShoot = 0;
		Equipment.RefreshAmmunitionLoadout();
		var suppressed = UseSuppressedEffects();

		// An unsuppressed shot briefly puts us on the enemy minimap, and bots hear it far off. A suppressed one, only close by.
		if ( Player.IsValid() )
		{
			if ( suppressed )
				Player.TimeSinceSuppressedShot = 0;
			else
				Player.TimeSinceUnsuppressedShot = 0;
		}

		if ( AmmoComponent.IsValid() )
			AmmoComponent.Ammo--;

		if ( CurrentFireMode == FireMode.Burst )
			IsBurstFiring = true;

		PlayDischargeEffects( suppressed );

		Player.GameObject.Dispatch( new WeaponShotEvent( Equipment ) );
		
		var hearingScale = GunsmithAttachmentEffects.For( Equipment ).HearingDistance;
		new Tec.AI.AudioStim( Player.Team.ToFaction(), Player.WorldPosition, 30000f * hearingScale,
			AudioStim.AudioStimType.Shoot, AudioStim.AudioStimDurationType.Finite, 1f );

		_flybys.Clear();
		for ( int i = 0; i < BulletCount; i++ )
		{
			int count = 0;
			var struck = new HashSet<GameObject>();

			foreach ( var trace in GetShootTrace() )
			{
				if ( !trace.Hit )
					continue;

				if ( trace.Distance == 0 )
					continue;

				// Where the round stops, for its crack: the last thing it meets that isn't glass.
				if ( _flybys.Count > 0 && trace.GameObject?.GetComponent<BreakableGlass>() is null )
					_flybys[^1] = new Flyby( trace.EndPosition, true );

				// The trace's box touches several of a body's hitboxes (both legs and the pelvis at once), but the bullet
				// hits that body once, where its line goes, or where the box touched it on a near miss.
				var tr = trace;
				if ( IsBody( tr ) )
				{
					if ( !struck.Add( tr.GameObject.Root ) )
						continue;

					tr = tr.ThroughBody( Scene );
				}

				CreateImpactEffects( tr, tr.GetImpactSurface() );

				// A window pane breaks as the round goes through (here, not a round trip later on the host), and a shot
				// through glass isn't a wallbang.
				if ( tr.GameObject?.GetComponent<BreakableGlass>() is { } glass )
				{
					glass.Break( tr.StartPosition );
					continue;
				}

				var damage = CalculateDamageFalloff( GetEffectiveDamage(), trace.Distance + _pathTravelled );
				damage = damage.CeilToInt();

				// Inflict damage on whatever we find.

				var damageFlags = DamageFlags.None;
				if ( count > 0 ) damageFlags |= DamageFlags.WallBang;
				if ( !Player.IsGrounded ) damageFlags |= DamageFlags.AirShot;

				using ( Rpc.FilterInclude( Connection.Host ) )
				{
					InflictDamage( tr.GameObject, damage, tr.EndPosition, tr.Direction, tr.GetHitboxTags(), damageFlags );
				}

				count++;
			}
		}

		SendFlybys();

		// If we have a recoil function, let it know.
		var recoil = Equipment.GetComponentInChildren<ShootRecoil>();
		if ( recoil.IsValid() )
			recoil.Shoot();

		// This shot's heat reaches the barrel after the bullet has left it.
		Equipment.GetComponentInChildren<BarrelHeat>()?.Shoot();
	}

	[Rpc.Broadcast]
	private void InflictDamage( GameObject target, float damage, Vector3 pos, Vector3 dir, HitboxTags hitbox, DamageFlags flags )
	{
		if ( target.IsValid() )
		{
			target.TakeDamage( new DamageInfo( Equipment.Owner, damage, Equipment, pos, dir * damage, hitbox, flags ) );
		}
	}

	private float CalculateDamageFalloff( float damage, float distance )
	{
		var distDelta = distance / (MaxRange * GunsmithAttachmentEffects.For( Equipment ).DamageFalloffDistance);
		var damageMultiplier = BaseDamageFalloff.Evaluate( distDelta );

		return damage * damageMultiplier;
	}

	protected void DryShoot()
	{
		TimeSinceShoot = 0f;
		DryShootEffects();
	}

	[Rpc.Broadcast]
	protected void DryShootEffects()
	{
		if ( DryFireSound is not null )
		{
			var snd = Sound.Play( DryFireSound, Equipment.WorldPosition );
			snd.SpacialBlend = (Equipment.Owner?.IsViewer ?? false) ? 0 : snd.SpacialBlend;
			Log.Trace( $"Shootable: ShootSound {DryFireSound.ResourceName}" );
		}

		// First person
		Equipment.ViewModel?.ModelRenderer.SetBool( "b_attack_dry", true );
	}

	/// <summary>
	/// Everything a bullet from <paramref name="start"/> to <paramref name="end"/> meets, nearest first. The bullet is a
	/// line: walls, floors and props stop it only where that line meets them. The whole trace used to be a box
	/// (<paramref name="radius"/> x 1.75, at least 14 units), which clipped a wall's edge up to 7 units off the line, so a
	/// shot aimed just past a corner you stood close to hit the corner. Bodies (players' and bots' hitboxes, zombies) are
	/// still found with that box, so a near miss hits them, but only where the box touches them in the open
	/// (<see cref="InTheOpen"/>).
	/// </summary>
	protected IEnumerable<SceneTraceResult> DoTraceBullet( Vector3 start, Vector3 end, float radius )
	{
		var world = BulletTrace( start, end )
			.RunAll()
			.Where( x => !IsBody( x ) );

		var bodies = BulletTrace( start, end )
			.UseHitboxes()
			.Size( MathF.Max( radius * 1.75f, 14.0f ) )
			.RunAll()
			.Where( x => IsBody( x ) && InTheOpen( x ) );

		return world.Concat( bodies ).OrderBy( x => x.Distance ).ToArray();
	}

	protected SceneTraceResult DoTraceBulletOne( Vector3 start, Vector3 end, float radius )
	{
		var first = DoTraceBullet( start, end, radius ).FirstOrDefault( x => x.Hit );
		if ( first.Hit ) return first;

		// A miss ends at the end, like a single trace's: the exit-point search below measures from it.
		return default( SceneTraceResult ) with
		{
			StartPosition = start, EndPosition = end, HitPosition = end, Direction = (end - start).Normal, Fraction = 1f
		};
	}

	private SceneTrace BulletTrace( Vector3 start, Vector3 end ) => Scene.Trace.Ray( start, end )
		.IgnoreGameObjectHierarchy( GameObject.Root )
		.WithoutTags( "trigger", "playerclip", "movement" );

	/// <summary> Whether a hit is on something a bullet wounds: a player's or bot's hitbox, or a zombie's capsule. </summary>
	private static bool IsBody( SceneTraceResult tr )
	{
		if ( tr.Hitbox is not null ) return true;
		if ( !tr.GameObject.IsValid() ) return false;

		return tr.GameObject.GetComponentInParent<HealthComponent>().IsValid()
			|| tr.GameObject.GetComponentInParent<ZombieAI>().IsValid();
	}

	/// <summary>
	/// Whether the bullet's line has a clear way to where the box touched a body (a box trace's HitPosition is the point
	/// of contact; its EndPosition is on the line). A body hidden behind a corner that the line only passes near isn't hit.
	/// </summary>
	private bool InTheOpen( SceneTraceResult tr )
	{
		var reach = BulletTrace( tr.EndPosition, tr.HitPosition ).Run();
		return !reach.Hit || reach.GameObject?.Root == tr.GameObject?.Root;
	}

	protected virtual Vector3 CalculateRicochetDirection( SceneTraceResult tr, ref float hits )
	{
		if ( tr.GameObject?.Tags.Has( "glass" ) ?? false )
		{
			// Allow us to do another hit
			hits--;
			return tr.Direction;
		}

		return Vector3.Reflect( tr.Direction, tr.Normal ).Normal;
	}

	/// <summary>
	/// Runs a trace with all the data we have supplied it, and returns the result
	/// </summary>
	/// <returns></returns>
	protected virtual IEnumerable<SceneTraceResult> GetShootTrace()
	{
		var start = WeaponRay.Position;
		var rot = Rotation.LookAt( WeaponRay.Forward );
		_flybyOrigin = start;

		var forward = rot.Forward;
		forward += (Vector3.Random + Vector3.Random + Vector3.Random + Vector3.Random) * (BulletSpread + Equipment.Owner.Spread) * 0.25f;
		if ( Equipment.GetComponentInChildren<BarrelHeat>() is { } heat )
			forward += heat.Deviation( rot );
		forward = forward.Normal;
		ApplyBallistics( ref start, ref forward, rot );

		var end = start + forward * (MaxRange - _pathTravelled);
		// Until it meets something, the round flies its full range.
		_flybys.Add( new Flyby( end, false ) );
		var original = DoTraceBullet( start, end, BulletSize ).ToArray();
		var firstHit = original.FirstOrDefault( trace => trace.Hit );
		PlayTracer( firstHit.Hit ? firstHit.EndPosition : end, start );

		return ResolvePenetration( Scene, original, PenetrationThickness );
	}

	/// <summary>
	/// Should we ricochet?
	/// </summary>
	/// <param name="tr"></param>
	/// <param name="angle"></param>
	/// <returns></returns>
	protected virtual bool ShouldBulletContinue( SceneTraceResult tr, float angle )
	{
		float maxAngle = MaxRicochetAngle;

		if ( angle > maxAngle )
			return false;

		return true;
	}

	// Weapon tuning is off (see WeaponTuningManager): damage and rate ignore saved tunings. Put back with tuning:
	// /// <summary>
	// /// Returns the weapon's resource name, used as the tuning key.
	// /// </summary>
	// private string TuningId => Equipment?.Resource?.ResourceName ?? string.Empty;

	/// <summary>
	/// Base damage scaled by the player's tuning preference (while tuning is on).
	/// </summary>
	private float GetEffectiveDamage()
	{
		// A suppressor changes the report, not the cartridge's damage.
		var baseDamage = BaseDamage;
		return baseDamage;
		// Put back with tuning:
		// if ( string.IsNullOrEmpty( TuningId ) ) return baseDamage;
		// var tune = WeaponTuningManager.GetTuning( TuningId );
		// return baseDamage * (1f + tune.Damage * 0.025f);
	}

	/// <summary>
	/// Effective RPM after fitted parts (gas system length, suppressor back-pressure) and, while tuning is on,
	/// fire-rate tuning. +10 tuning = +12% RPM.
	/// </summary>
	private float GetEffectiveFireRate()
	{
		// Zombies Hot Shot: a shorter delay between shots means a higher RPM.
		var perkScale = 1f / ZombiesPlayerState.FireDelayScale( Equipment?.Owner );

		var parts = GunsmithAttachmentEffects.For( Equipment );
		var partScale = parts.FireRate;
		// An integral suppressor is already part of the prefab's rate.
		if ( !HasBuiltInSuppressor && UseSuppressedEffects() )
			partScale *= SuppressorRateScale( parts );

		var rate = FireRate * partScale * perkScale;
		return rate;
		// Put back with tuning:
		// if ( string.IsNullOrEmpty( TuningId ) ) return rate;
		// var tune = WeaponTuningManager.GetTuning( TuningId );
		// return rate * (1f + tune.FireRate * 0.012f);
	}

	/// <summary> A suppressor's back-pressure on the rate, unless a fitted gas regulator is on its suppressed setting. </summary>
	public float SuppressorRateScale( GunsmithAttachmentEffects parts ) => parts.SuppressedGas ? 1f : SuppressorFireRateScale;

	protected float RPMToSeconds()
	{
		return 60 / GetEffectiveFireRate();
	}

	/// <summary>
	/// Can we shoot this gun right now?
	/// </summary>
	/// <returns></returns>
	public bool CanShoot()
	{
		// Do we still have a weapon?
		if ( !Equipment.IsValid() ) return false;
		if ( !Equipment.Owner.IsValid() ) return false;

		// Player
		if ( Equipment.Owner.IsFrozen )
			return false;

		// Weapon
		if ( Equipment.Tags.Has( "reloading" ) || Equipment.Tags.Has( "no_shooting" ) )
			return false;

		// Delay checks
		if ( Time.Now < _nextShotTime )
			return false;

		// Ammo checks
		if ( RequiresHasAmmo && (!AmmoComponent.IsValid() || !AmmoComponent.HasAmmo) )
			return false;

		return true;
	}

	[Sync] public int BurstCount { get; set; } = 0;

	private void ClearBurst()
	{
		TimeSinceBurstFinished = 0;
		IsBurstFiring = false;
		BurstCount = 0;
	}

	protected override void OnInputUpdate()
	{
		if ( Input.Pressed( "FireMode" ) )
		{
			CycleFireMode();
			return;
		}

		// A burst also ends when the magazine runs dry, or the fire mode switch would stay locked until the reload.
		if ( IsBurstFiring && (BurstCount >= BurstAmount - 1 || Tags.Has( "reloading" )
			|| (AmmoComponent.IsValid() && !AmmoComponent.HasAmmo)) )
		{
			ClearBurst();
		}

		if ( CurrentFireMode == FireMode.Burst && IsBurstFiring && CanShoot() )
		{
			BurstCount++;
			Shoot();
		}

		bool wantsToShoot = IsDown();

		// HACK
		// Semi fires a round per trigger pull, and burst a whole burst per pull, as on the M16A4: holding the trigger
		// doesn't fire another.
		if ( CurrentFireMode is FireMode.Semi or FireMode.Burst )
		{
			wantsToShoot = Input.Pressed( "attack1" );
		}

		if ( wantsToShoot )
		{
			if ( Equipment.HasTag( "lowered" ) )
			{
				Equipment.SetTag( "lowered", false );
				return;
			}

			if ( !CanShoot() )
			{
				// Dry fire
				if ( !AmmoComponent.HasAmmo )
				{
					if ( TimeSinceShoot < DryShootDelay )
						return;

					if ( Tags.Has( "reloading" ) )
						return;

					DryShoot();
				}
			}
			else
			{
				if ( IsBurstFiring ) return;
				if ( TimeSinceBurstFinished < BurstEndDelay ) return;

				Shoot();
			}
		}
	}

	protected int GetFireModeIndex( FireMode fireMode )
	{
		int i = 0;
		foreach ( var mode in FireModes )
		{
			if ( mode == fireMode ) return i;
			i++;
		}

		return 0;
	}

	public void CycleFireMode()
	{
		if ( TimeSinceFireModeSwitch < FireModeSwitchDelay ) return;
		if ( IsBurstFiring ) return;
		if ( IsDown() ) return;

		var curIndex = GetFireModeIndex( CurrentFireMode );
		var modes = FireModes;
		var length = modes.Count;
		var newIndex = (curIndex + 1 + length) % length;

		// We didn't change anything
		if ( newIndex == curIndex ) return;

		CurrentFireMode = modes[newIndex];

		Equipment.ViewModel?.OnFireMode( CurrentFireMode );

		// Toast.Instance?.Show( $"{CurrentFireMode}", ToastType.Generic, 1f );

		TimeSinceFireModeSwitch = 0;
	}

	void IGameEventHandler<EquipmentHolsteredEvent>.OnGameEvent( EquipmentHolsteredEvent eventArgs )
	{
		ClearBurst();
	}
}
