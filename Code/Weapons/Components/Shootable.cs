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
	/// Rate multiplier with a suppressor fitted. Back-pressure speeds up gas-operated actions: a lot on a direct-impingement
	/// AR, less on roller-delayed or long-stroke guns, and not at all on guns with a suppressed gas setting (SCAR) or
	/// trigger-limited semi-autos.
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

		var effector = Effector;
		if ( !effector.IsValid() || !effector.ModelRenderer.IsValid() )
			return;

		if ( showFlash )
			CreateDischargeParticle( GetMuzzleFlashPrefab( suppressed ), effector.DischargeMuzzle, flashScale, "Muzzle flash" );

		if ( smokeScale > 0f )
			CreateDischargeParticle( MuzzleSmokePrefab, effector.DischargeMuzzle, smokeScale, "Muzzle smoke" );

		// One spent case per discharge, independent of flash/smoke chance and pellet count.
		effector.EjectCasing( EjectionPrefab, Equipment.Owner );

		var shootSound = GetShootSound( suppressed );
		if ( shootSound is not null )
		{
			if ( Sound.Play( shootSound, Equipment.WorldPosition ) is { } snd )
			{
				snd.SpacialBlend = (Equipment.Owner?.IsViewer ?? false) ? 0 : snd.SpacialBlend;
				snd.Volume *= soundVolume;
				Log.Trace( $"Shootable: ShootSound {shootSound.ResourceName}" );
			}
		}

		// Third person
		if ( Equipment.Owner.IsValid() && Equipment.Owner.BodyRenderer.IsValid() )
			Equipment.Owner.BodyRenderer.Set( "b_attack", true );

		// First person
		if ( Equipment.ViewModel.IsValid() )
			Equipment.ViewModel.ModelRenderer.Set( "b_attack", true );
	}

	private void CreateImpactEffects( GameObject hitObject, Surface surface, Vector3 pos, Vector3 normal )
	{
		var impactPrefab = surface.GetBulletImpact();

		if ( impactPrefab.IsValid() )
		{
			var impact = impactPrefab.Clone();
			impact.WorldPosition = pos + normal;
			impact.WorldRotation = Rotation.LookAt( normal );
			impact.SetParent( hitObject, true );

			// Shots run in fixed update, which interpolates the re-parent: for a frame the effect sits at
			// hitObject.PointToWorld( pos ) (thousands of units away) and its particles burst there.
			impact.Transform.ClearInterpolation();
		}

		if ( surface.SoundCollection.Bullet.IsValid() )
		{
			Sound.Play( surface.SoundCollection.Bullet, pos );
		}
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

		// CoD-style minimap reveal: an unsuppressed shot briefly puts us on the enemy minimap.
		if ( !suppressed && Player.IsValid() )
			Player.TimeSinceUnsuppressedShot = 0;

		if ( AmmoComponent.IsValid() )
			AmmoComponent.Ammo--;

		if ( CurrentFireMode == FireMode.Burst )
			IsBurstFiring = true;

		PlayDischargeEffects( suppressed );

		Player.GameObject.Dispatch( new WeaponShotEvent( Equipment ) );
		
		var hearingScale = GunsmithAttachmentEffects.For( Equipment ).HearingDistance;
		new Tec.AI.AudioStim( Player.Team.ToFaction(), Player.WorldPosition, 30000f * hearingScale,
			AudioStim.AudioStimType.Shoot, AudioStim.AudioStimDurationType.Finite, 1f );

		for ( int i = 0; i < BulletCount; i++ )
		{
			int count = 0;

			foreach ( var tr in GetShootTrace() )
			{
				if ( !tr.Hit )
					continue;

				if ( tr.Distance == 0 )
					continue;

				CreateImpactEffects( tr.GameObject, tr.Surface, tr.EndPosition, tr.Normal );

				var damage = CalculateDamageFalloff( GetEffectiveDamage(), tr.Distance );
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

		// If we have a recoil function, let it know.
		var recoil = Equipment.GetComponentInChildren<ShootRecoil>();
		if ( recoil.IsValid() )
			recoil.Shoot();
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
		Equipment.ViewModel?.ModelRenderer.Set( "b_attack_dry", true );
	}

	protected IEnumerable<SceneTraceResult> DoTraceBullet( Vector3 start, Vector3 end, float radius )
	{
		var finalRadius = MathF.Max( radius * 1.75f, 14.0f );
		return Scene.Trace.Ray( start, end )
			.UseHitboxes()
			.IgnoreGameObjectHierarchy( GameObject.Root )
			.WithoutTags( "trigger", "playerclip", "movement" )
			.Size( finalRadius )
			.RunAll();
	}

	protected SceneTraceResult DoTraceBulletOne( Vector3 start, Vector3 end, float radius )
	{
		var finalRadius = MathF.Max( radius * 1.75f, 14.0f );
		return Scene.Trace.Ray( start, end )
			.UseHitboxes()
			.IgnoreGameObjectHierarchy( GameObject.Root )
			.WithoutTags( "trigger", "playerclip", "movement" )
			.Size( finalRadius )
			.Run();
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
		var hits = new List<SceneTraceResult>();

		var start = WeaponRay.Position;
		var rot = Rotation.LookAt( WeaponRay.Forward );

		var forward = rot.Forward;
		forward += (Vector3.Random + Vector3.Random + Vector3.Random + Vector3.Random) * (BulletSpread + Equipment.Owner.Spread) * 0.25f;
		forward = forward.Normal;

		var end = WeaponRay.Position + forward * MaxRange;
		var original = DoTraceBullet( start, end, BulletSize ).ToArray();
		var firstHit = original.FirstOrDefault( trace => trace.Hit );
		PlayTracer( firstHit.Hit ? firstHit.EndPosition : end, start );

		if ( original.Count() < 1 ) return original;

		// Run through and fix the start positions for the traces
		// By using the last end position as the start

		int depth = 0;
		Vector3 startPos = original.ElementAt( 0 ).StartPosition;
		List<SceneTraceResult> fixedPath = new();
		for ( int i = 0; i < original.Count(); i++ )
		{
			var el = original.ElementAt( i );

			fixedPath.Add( el with { StartPosition = startPos } );
			startPos = el.EndPosition;
		}

		var entries = new List<(SceneTraceResult Trace, float Thickness)>();

		// Then, trace backwards from the end so we can get exit points and thickness
		for ( int i = fixedPath.Count - 1; i >= 0; i-- )
		{
			var el = fixedPath.ElementAt( i );

			// Do a trace back, from the end position to the start, this'll give us the LAST entry's exit point.
			var backTrace = DoTraceBulletOne( el.EndPosition, el.StartPosition, BulletSize );
			var impact = backTrace.EndPosition;

			// From that, we can calculate the surface thickness
			float thickness = (el.StartPosition - impact).Length;

			// Return the element starting at the exit point, it's more useful that way.
			el = el with { StartPosition = impact };
			entries.Insert( 0, (el, thickness) );
		}

		depth = 0;
		float accThickness = 0;
		foreach ( var el in entries )
		{
			accThickness += el.Thickness;
			if ( accThickness >= PenetrationThickness )
				break;

			hits.Add( el.Trace );
			// DrawLineSegment( el.Trace.StartPosition, el.Trace.EndPosition, depth, fixedPath.Count() );
			depth++;
		}

		return hits;
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

	/// <summary>
	/// Returns the weapon's resource name, used as the tuning key.
	/// </summary>
	private string TuningId => Equipment?.Resource?.ResourceName ?? string.Empty;

	/// <summary>
	/// Base damage scaled by the player's tuning preference.
	/// </summary>
	private float GetEffectiveDamage()
	{
		// A suppressor changes the report, not the cartridge's damage.
		var baseDamage = BaseDamage;
		if ( string.IsNullOrEmpty( TuningId ) ) return baseDamage;
		var tune = WeaponTuningManager.GetTuning( TuningId );
		return baseDamage * (1f + tune.Damage * 0.025f);
	}

	/// <summary>
	/// Effective RPM after fitted parts (gas system length, suppressor back-pressure) and fire-rate tuning. +10 tuning = +12% RPM.
	/// </summary>
	private float GetEffectiveFireRate()
	{
		// Zombies Double Tap: a shorter delay between shots means a higher RPM.
		var perkScale = 1f / ZombiesPlayerState.FireDelayScale( Equipment?.Owner );

		var partScale = GunsmithAttachmentEffects.For( Equipment ).FireRate;
		// An integral suppressor is already part of the prefab's rate.
		if ( !HasBuiltInSuppressor && UseSuppressedEffects() )
			partScale *= SuppressorFireRateScale;

		var rate = FireRate * partScale * perkScale;
		if ( string.IsNullOrEmpty( TuningId ) ) return rate;
		var tune = WeaponTuningManager.GetTuning( TuningId );
		return rate * (1f + tune.FireRate * 0.012f);
	}

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

		if ( IsBurstFiring && BurstCount >= BurstAmount - 1 || (Tags.Has( "reloading" ) && IsBurstFiring) )
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
		if ( CurrentFireMode == FireMode.Semi )
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
		foreach ( var mode in SupportedFireModes )
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
		var length = SupportedFireModes.Count;
		var newIndex = (curIndex + 1 + length) % length;

		// We didn't change anything
		if ( newIndex == curIndex ) return;

		CurrentFireMode = SupportedFireModes[newIndex];

		Equipment.ViewModel?.OnFireMode( CurrentFireMode );

		// Toast.Instance?.Show( $"{CurrentFireMode}", ToastType.Generic, 1f );

		TimeSinceFireModeSwitch = 0;
	}

	void IGameEventHandler<EquipmentHolsteredEvent>.OnGameEvent( EquipmentHolsteredEvent eventArgs )
	{
		ClearBurst();
	}
}
