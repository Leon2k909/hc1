using Sandbox;
using System;

namespace Facepunch;

public sealed class ZombiesRoundSystem : Component
{
    [Property, Sync] public int CurrentRound { get; private set; } = 0;
    [Property, Sync] public int ZombiesRemainingInRound { get; private set; } = 0;
    [Property, Sync] public int ZombiesAlive { get; private set; } = 0;
    [Property, Sync] public float TimeBetweenRounds { get; set; } = 10f;
    [Property, Sync] public bool IsIntermission { get; private set; } = true;

    [Property] public GameObject ZombiePrefab { get; set; }

    private TimeSince _timeSinceRoundEnd;
    private TimeSince _lastSpawnTime;

    protected override void OnStart()
    {
        if ( !Networking.IsHost ) return;
        StartNextRound();
    }

    protected override void OnUpdate()
    {
        if ( !Networking.IsHost ) return;

        if ( IsIntermission )
        {
            if ( _timeSinceRoundEnd > TimeBetweenRounds )
            {
                StartNextRound();
            }
        }
        else
        {
            // Spawn logic
            if ( ZombiesRemainingInRound > 0 && ZombiesAlive < GetMaxZombiesAllowed() )
            {
                if ( _lastSpawnTime > GetSpawnRate() )
                {
                    SpawnZombie();
                }
            }

            // Check for round end
            if ( ZombiesRemainingInRound == 0 && ZombiesAlive == 0 )
            {
                EndRound();
            }
        }
    }

    private void StartNextRound()
    {
        CurrentRound++;
        IsIntermission = false;
        
        // Basic scaling math for total zombies
        ZombiesRemainingInRound = (int)(24 * Math.Pow( 1.15, CurrentRound - 1 ));
        
        Sound.Play( "ui.round_start" );
        Log.Info( $"Starting Round {CurrentRound} with {ZombiesRemainingInRound} zombies." );
    }

    private void EndRound()
    {
        IsIntermission = true;
        _timeSinceRoundEnd = 0;
        Sound.Play( "ui.round_end" );
        Log.Info( $"Round {CurrentRound} ended." );
    }

    private void SpawnZombie()
    {
        _lastSpawnTime = 0;

        var spawnPoints = Scene.GetAllComponents<SpawnPoint>();
        var point = spawnPoints.OrderBy( x => Guid.NewGuid() ).FirstOrDefault();

        if ( point != null )
        {
            GameObject zombie = null;

            if ( ZombiePrefab.IsValid() )
            {
                zombie = ZombiePrefab.Clone( point.Transform.Position );
            }
            else
            {
                // Dynamically construct the zombie
                zombie = new GameObject( true, "Zombie" );
                zombie.WorldPosition = point.WorldPosition;
                zombie.Tags.Add( "enemy" );

                // Half-size trinit zombie for Flatgrass
                zombie.LocalScale = new Vector3( 0.5f, 0.5f, 0.5f );

                var renderer = zombie.Components.Create<SkinnedModelRenderer>();
                renderer.Model = Model.Load( "zombie_block/zombie_basic.vmdl" );
                // Drive raw sequences (attack/walk/etc.) — the trinit model has no anim graph.
                renderer.UseAnimGraph = false;

                // NavMeshAgent dimensions for full size
                var nav = zombie.Components.Create<NavMeshAgent>();
                nav.Height = 72f;
                nav.Radius = 16f;

                var collider = zombie.Components.Create<CapsuleCollider>();
                collider.Radius = 16f;
                collider.Start = new Vector3( 0, 0, 16f );
                collider.End = new Vector3( 0, 0, 72f );

                var modelCollider = zombie.Components.Create<ModelCollider>();
                modelCollider.Model = renderer.Model;

                var ai = zombie.Components.Create<ZombieAI>();
            }

            zombie.NetworkSpawn( null );
            
            // Scale zombie health based on round
            if ( zombie.Components.TryGet<ZombieAI>( out var zombieAi ) )
            {
                zombieAi.MaxHealth = 100 + (CurrentRound * 20); // Scale up each round
            }

            ZombiesRemainingInRound--;
            ZombiesAlive++;
        }
    }

    public void OnZombieKilled()
    {
        if ( !Networking.IsHost ) return;
        ZombiesAlive--;
    }

    private int GetMaxZombiesAllowed()
    {
        // Limit max concurrent zombies based on round/player count
        return Math.Min( 24, 10 + (CurrentRound * 2) );
    }

    private float GetSpawnRate()
    {
        // Faster spawns in higher rounds
        return Math.Max( 0.5f, 2.0f - (CurrentRound * 0.1f) );
    }
}
