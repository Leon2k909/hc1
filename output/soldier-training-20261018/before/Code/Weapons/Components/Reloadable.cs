using Sandbox.Events;

namespace Facepunch;

[Title( "Reload" ), Group( "Weapon Components" )]
public partial class Reloadable : WeaponInputAction,
	IGameEventHandler<EquipmentHolsteredEvent>
{
	/// <summary>
	/// How long does it take to reload?
	/// </summary>
	[Property] public float ReloadTime { get; set; } = 1.0f;

	/// <summary>
	/// How long does it take to reload while empty?
	/// </summary>
	[Property] public float EmptyReloadTime { get; set; } = 2.0f;

	[Property] public bool SingleReload { get; set; } = false;

	/// <summary>
	/// Shell-by-shell reloads: how long the gun takes to come back up after the last shell (the reload's closing
	/// animation). It can't fire until then.
	/// </summary>
	[Property] public float ReloadExitTime { get; set; } = 0f;

	/// <summary>
	/// This is really just the magazine for the weapon.
	/// </summary>
	[Property] public WeaponAmmo AmmoComponent { get; set; }

	private TimeUntil TimeUntilReload { get; set; }
	[Sync] public bool IsReloading { get; set; }

	/// <summary>A shell-by-shell reload's last shell is in and the gun is coming back up (<see cref="ReloadExitTime"/>).</summary>
	private bool _closing;

	protected override void OnEnabled()
	{
		BindTag( "reloading", () => IsReloading );
	}

	protected override void OnInput()
	{
		if ( CanReload() )
		{
			StartReload();
		}
	}

	protected override void OnUpdate()
	{
		if ( !Player.IsValid() )
			return;

		if ( !Player.IsLocallyControlled )
		{
			if ( Player.Client.IsBot )
			{
				if ( IsReloading && TimeUntilReload )
				{
					EndReload();
				}
				return;
			}
			return;
		}

		if ( SingleReload && IsReloading && Input.Pressed( "Attack1" ) )
		{
			_queueCancel = true;
		}

		if ( IsReloading && TimeUntilReload )
		{
			EndReload();
		}
	}

	void IGameEventHandler<EquipmentHolsteredEvent>.OnGameEvent( EquipmentHolsteredEvent eventArgs )
	{
		if ( !IsProxy && IsReloading )
		{
			// Conna: if we're no longer deployed cancel reloading.
			CancelReload();
		}
	}

	bool CanReload()
	{
		if ( Input.Down( "Use" ) ) return false; // Don't reload if we're using something.

		if ( IsReloading || !AmmoComponent.IsValid() ) return false;

		// Shell-by-shell reloads top the magazine up one at a time and stop at its size — they never
		// end on a chambered extra round, so targeting max + 1 here would let you start a pointless
		// extra reload while already full.
		var target = SingleReload
			? AmmoComponent.GetEffectiveMaxAmmo()
			: AmmoComponent.GetMaxAmmoWithChamber();

		return AmmoComponent.Ammo < target && HasSpareAmmo;
	}

	/// <summary>
	/// Bots never run dry — they don't know how to scavenge.
	/// </summary>
	bool HasInfiniteReserve => Equipment?.Owner?.Client?.IsBot ?? false;

	bool HasSpareAmmo => HasInfiniteReserve || AmmoComponent.ReserveAmmo > 0;

	/// <summary>
	/// Take up to <paramref name="wanted"/> rounds out of the spare ammo.
	/// </summary>
	int TakeFromReserve( int wanted )
	{
		if ( wanted <= 0 ) return 0;
		if ( HasInfiniteReserve ) return wanted;
		var take = Math.Min( wanted, AmmoComponent.ReserveAmmo );
		AmmoComponent.ReserveAmmo -= take;
		return take;
	}

	float GetReloadTime()
	{
		// A magazine with its own reload animations brings its own times.
		var magazine = Equipment?.ReloadMagazine;
		var time = !AmmoComponent.HasAmmo
			? magazine?.EmptyReloadTime > 0 ? magazine.EmptyReloadTime : EmptyReloadTime
			: magazine?.ReloadTime > 0 ? magazine.ReloadTime : ReloadTime;
		return time * DurationMultiplier * ZombiesPlayerState.ReloadScale( Equipment?.Owner );
	}

	public float DurationMultiplier
	{
		get
		{
			var multiplier = Equipment?.AttachmentReloadMultiplier ?? 1f;
			return multiplier;
			// Weapon tuning is off (see WeaponTuningManager). Put back with tuning:
			// var weaponId = Equipment?.Resource?.ResourceName ?? string.Empty;
			// if ( string.IsNullOrEmpty( weaponId ) ) return multiplier;
			// return multiplier * (1f - WeaponTuningManager.GetTuning( weaponId ).Reload * 0.015f);
		}
	}

	Dictionary<float, SoundEvent> GetReloadSounds()
	{
		var magazine = Equipment?.ReloadMagazine;
		if ( !AmmoComponent.HasAmmo ) return magazine?.EmptyReloadSounds is { Count: > 0 } empty ? empty : EmptyReloadSounds;
		return magazine?.ReloadSounds is { Count: > 0 } sounds ? sounds : TimedReloadSounds;
	}

	bool _queueCancel = false;

	[Rpc.Owner]
	public void StartReload()
	{
		_queueCancel = false;
		_closing = false;

		bool isContinuedReload = IsReloading;

		// Shell-by-shell reloads should release at most one residual wisp per sequence.
		if ( !IsProxy && !isContinuedReload )
			Equipment.GetComponentInChildren<Shootable>()?.PlayReloadSmoke();

		if ( !IsProxy )
		{
			IsReloading = true;
			TimeUntilReload = GetReloadTime();
		}

		if ( SingleReload )
		{
			// Tags will be better so we can just react to stimuli.
			Equipment.ViewModel?.ModelRenderer?.SetBool( "b_reloading", true );

			bool hasAmmo = AmmoComponent.HasAmmo;
			Equipment.ViewModel?.ModelRenderer.SetBool( !hasAmmo ? "b_reloading_first_shell" : "b_reloading_shell", true );
		}
		else
		{
			// Tags will be better so we can just react to stimuli.
			Equipment.ViewModel?.ModelRenderer?.SetBool( "b_reload", true );
		}


		foreach ( var kv in GetReloadSounds() )
		{
			// Play this sound after a certain time but only if we're reloading.
			PlayAsyncSound( kv.Key * DurationMultiplier, kv.Value, () => IsReloading );
		}

		Equipment.Owner?.BodyRenderer?.SetBool( "b_reload", true );
	}

	[Rpc.Owner]
	void CancelReload()
	{
		if ( !IsProxy )
		{
			IsReloading = false;
			_closing = false;
		}

		// Tags will be better so we can just react to stimuli.
		Equipment.ViewModel?.ModelRenderer?.SetBool( "b_reload", false );
		Equipment.Owner?.BodyRenderer?.SetBool( "b_reload", false );
		Equipment.ViewModel?.ModelRenderer?.SetBool( "b_reloading", false );
	}

	[Rpc.Owner]
	void EndReload()
	{
		if ( !IsProxy )
		{
			if ( _closing )
			{
				// Back up after the last shell.
				_closing = false;
				IsReloading = false;
			}
			else if ( SingleReload )
			{
				if ( AmmoComponent.Ammo < AmmoComponent.GetEffectiveMaxAmmo() )
					AmmoComponent.Ammo += TakeFromReserve( 1 );

				// Reload more!
				if ( !_queueCancel && AmmoComponent.Ammo < AmmoComponent.GetEffectiveMaxAmmo() && HasSpareAmmo )
					StartReload();
				else
				{
					Equipment.ViewModel?.ModelRenderer?.SetBool( "b_reloading", false );

					// The closing animation plays before the gun can fire.
					if ( ReloadExitTime > 0f )
					{
						_closing = true;
						TimeUntilReload = ReloadExitTime * DurationMultiplier * ZombiesPlayerState.ReloadScale( Equipment?.Owner );
					}
					else
					{
						IsReloading = false;
					}
				}
			}
			else
			{
				IsReloading = false;

				// Ammo still holds the pre-reload count here, so it tells us whether there was a round
				// left to keep in the chamber. Swapping a partially spent mag gives max + 1; reloading
				// from empty has nothing chambered, so just max.
				// Rounds only come out of the spare ammo, so a nearly-dry reserve gives a partial mag.
				var target = AmmoComponent.HasAmmo
					? AmmoComponent.GetMaxAmmoWithChamber()
					: AmmoComponent.GetEffectiveMaxAmmo();
				AmmoComponent.Ammo += TakeFromReserve( target - AmmoComponent.Ammo );
			}
		}

		// Tags will be better so we can just react to stimuli.
		Equipment.ViewModel?.ModelRenderer.SetBool( "b_reload", false );
	}

	[Property] public Dictionary<float, SoundEvent> TimedReloadSounds { get; set; } = new();
	[Property] public Dictionary<float, SoundEvent> EmptyReloadSounds { get; set; } = new();

	async void PlayAsyncSound( float delay, SoundEvent snd, Func<bool> playCondition = null )
	{
		await GameTask.DelaySeconds( delay );

		// Can we play this sound?
		if ( playCondition != null && !playCondition.Invoke() )
			return;

		if ( !GameObject.IsValid() )
			return;

		GameObject.PlaySound( snd );
	}
}
