using Sandbox.Events;

namespace Facepunch.Gunsmith;

/// <summary>Uses the ordinary pawn, inventory and weapon components in a solo practice scene.</summary>
public sealed class FiringRangeSystem : SingletonComponent<FiringRangeSystem>
{
    public static FiringRangeSystem Current => Instance.IsValid() && Instance.Scene == Game.ActiveScene ? Instance : null;
    public static bool IsActive => Current.IsValid();
    public static bool IsMenuVisible => Current is { MenuOpen: true };

    public PlayerPawn Player { get; private set; }
    public bool MenuOpen { get; private set; }
    public bool MovingTargets { get; private set; }
    public int Shots { get; private set; }
    public int Hits { get; private set; }
    public int Knockdowns { get; private set; }
    public float LastDamage { get; private set; }
    public float LastDistance { get; private set; }
    public bool LastHeadshot { get; private set; }
    public TimeSince SinceHit { get; private set; } = 10;
    private TimeSince sinceReserveRefill = 1;

    protected override void OnUpdate()
    {
        if ( !Game.IsPlaying || Scene != Game.ActiveScene || !Networking.IsHost ) return;
        var client = Scene.GetAllComponents<Client>().FirstOrDefault( x => x.IsLocalPlayer );
        if ( !client.IsValid() ) return;

        if ( !Player.IsValid() || Player.HealthComponent.State != LifeState.Alive )
        {
            client.Team = Team.CounterTerrorist;
            client.Respawn( true );
            Player = client.PlayerPawn;
            if ( !Player.IsValid() ) return;
            Player.HealthComponent.IsGodMode = true;
            Player.Components.GetOrCreate<PlayerPerks>().LoadFromCookies();
            Player.Components.GetOrCreate<FiringRangeShotRecorder>();
            RefillLoadout();
        }

        Player.IsFrozen = MenuOpen;
        // Replenish only spare rounds, so magazine depletion, tactical reloads,
        // chambered rounds and attachment capacities behave exactly as in play.
        if ( sinceReserveRefill > .25f )
        {
            sinceReserveRefill = 0;
            foreach ( var weapon in Player.Inventory.Equipment )
                if ( weapon.GetComponentInChildren<WeaponAmmo>( true ) is { } ammo )
                    ammo.ReserveAmmo = ammo.GetMaxReserve();
        }
        if ( Player.WorldPosition.z < -128 ) Player.Teleport( Player.SpawnPosition, Player.SpawnRotation );
    }

    public void ToggleMenu()
    {
        MenuOpen = !MenuOpen;
        if ( Player.IsValid() ) Player.IsFrozen = MenuOpen;
    }

    public void Resume()
    {
        MenuOpen = false;
        if ( Player.IsValid() ) Player.IsFrozen = false;
    }

    public void ToggleMovingTargets() => MovingTargets = !MovingTargets;

    public void RefillLoadout()
    {
        if ( !Player.IsValid() || !Networking.IsHost ) return;
        var selected = ResourceLibrary.Get<EquipmentResource>( GunsmithRangeSession.WeaponPath ?? "" )
            ?? GunsmithLoadoutManager.GetPrimaryResource() ?? GunsmithLoadoutManager.GetSecondaryResource();
        var resources = GunsmithLoadoutManager.GetLoadoutResources().ToList();
        if ( selected.IsValid() && !resources.Contains( selected ) ) resources.Add( selected );
        foreach ( var resource in resources )
            if ( !Player.Inventory.Has( resource ) ) Player.Inventory.Give( resource, false );

        if ( !Player.CurrentEquipment.IsValid() )
        {
            var held = Player.Inventory.Equipment.FirstOrDefault( x => x.Resource == selected );
            if ( held.IsValid() ) Player.SetCurrentEquipment( held );
            else Player.Inventory.SwitchToBest();
        }
        Player.Inventory.RefillAmmo();
    }

    public void ResetTargets()
    {
        foreach ( var target in Scene.GetAllComponents<FiringRangeTarget>() ) target.ResetTarget();
        Shots = Hits = Knockdowns = 0;
        LastDamage = LastDistance = 0;
        LastHeadshot = false;
        SinceHit = 10;
    }

    public void RecordShot() => Shots++;

    public void RecordHit( float damage, float distance, bool headshot, bool down )
    {
        Hits++;
        if ( down ) Knockdowns++;
        LastDamage = damage;
        LastDistance = distance;
        LastHeadshot = headshot;
        SinceHit = 0;
    }
}

/// <summary>WeaponShotEvent is dispatched on the pawn, also for burst and automatic fire.</summary>
public sealed class FiringRangeShotRecorder : Component, IGameEventHandler<WeaponShotEvent>
{
    void IGameEventHandler<WeaponShotEvent>.OnGameEvent( WeaponShotEvent ev ) => FiringRangeSystem.Current?.RecordShot();
}
