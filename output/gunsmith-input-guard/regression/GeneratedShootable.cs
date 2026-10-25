namespace Facepunch;
public partial class Shootable
{
private void ClearBurst()
	{
		TimeSinceBurstFinished = 0;
		IsBurstFiring = false;
		BurstCount = 0;
	}
protected override void OnInputSuppressed()
	{
		if ( IsBurstFiring )
			ClearBurst();
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
}
