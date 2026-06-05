using Sandbox;
using System.Linq;

namespace Facepunch;

public sealed class ZombieAI : Component, Component.ITriggerListener, Component.IDamageable
{
    [Property] public float WalkSpeed { get; set; } = 85f;
    [Property] public float RunSpeed { get; set; } = 130f;
    [Property] public float AttackRange { get; set; } = 60f;
    [Property] public float AttackDamage { get; set; } = 25f;
    [Property] public float AttackCooldown { get; set; } = 1.5f;
    [Property] public float MaxHealth { get; set; } = 100f;

    public float Health { get; private set; }

    [RequireComponent] private NavMeshAgent Agent { get; set; }
    [RequireComponent] private SkinnedModelRenderer Renderer { get; set; }

    private TimeSince _lastAttack;
    private PlayerPawn _target;
    private bool _isDead = false;

    // Default sequence the zombie plays while shambling/idling.
    private const string MoveSeq = "walk";
    private const string IdleSeq = "idle";
    private const string AttackSeq = "attack"; // confirmed on trinit.zombiebasic
    private const string DeathSeq = "die";

    // How long an attack swing locks the move-anim out, so the attack sequence can play through.
    private const float AttackAnimHold = 0.6f;
    private TimeSince _timeSinceAttackAnim = 999f;

    private TimeSince _timeSinceStuck;
    private Rigidbody _rb;
    private CapsuleCollider _collider;

    protected override void OnStart()
    {
        Health = MaxHealth;
        Agent.MaxSpeed = WalkSpeed;
        Agent.UpdateRotation = false;

        if ( Renderer.IsValid() )
            Renderer.UseAnimGraph = false;

        _collider = Components.Get<CapsuleCollider>();
        _rb = Components.Create<Rigidbody>();
        _rb.MotionEnabled = false;

        PlaySequence( IdleSeq, looping: true );
    }

    protected override void OnUpdate()
    {
        if ( _isDead || !Networking.IsHost ) return;

        if ( Renderer.IsValid() && !Renderer.UseAnimGraph )
        {
            Renderer.Sequence.Time += Time.Delta;
        }

        FindTarget();

        // If we are leaping/falling, let physics handle it until we hit the ground
        if ( _rb.IsValid() && _rb.MotionEnabled )
        {
            // Keep them upright so they don't tumble and land on their side
            Transform.Rotation = Rotation.From( 0, Transform.Rotation.Angles().yaw, 0 );
            _rb.AngularVelocity = Vector3.Zero;

            // Tracing below our feet to check for ground hit
            var tr = Scene.Trace.Ray( Transform.Position, Transform.Position + Vector3.Down * 60f )
                .IgnoreGameObjectHierarchy( GameObject )
                .Run();

            if ( tr.Hit && _rb.Velocity.z > -10f && _timeSinceStuck > 0.5f )
            {
                _rb.MotionEnabled = false;
                if ( Agent.IsValid() ) Agent.Enabled = true;
            }
            return;
        }

        if ( _target.IsValid() )
        {
            var dirToTarget = (_target.Transform.Position - Transform.Position).WithZ(0).Normal;
            if ( dirToTarget.LengthSquared > 0.1f )
            {
                var targetRot = Rotation.LookAt( dirToTarget, Vector3.Up );
                Transform.Rotation = Rotation.Lerp( Transform.Rotation, targetRot, Time.Delta * 10f );
            }

            if ( Agent.IsValid() && Agent.Enabled )
            {
                // Offset the move target slightly away from nearby zombies so they
                // don't pile onto the exact same point. Pure math — never blocks the agent.
                Agent.MoveTo( _target.Transform.Position + GetSeparationOffset() );
            }

            UpdateAnimation();

            float dist = Vector3.DistanceBetween( Transform.Position, _target.Transform.Position );
            if ( dist <= AttackRange && _lastAttack > AttackCooldown )
            {
                Attack();
            }

            // Leap logic: if we are stuck but far from the target
            if ( Agent.IsValid() && Agent.Enabled && Agent.Velocity.Length < 10f && dist > AttackRange * 1.5f )
            {
                if ( _timeSinceStuck > 1.5f )
                {
                    Agent.Enabled = false;
                    _rb.MotionEnabled = true;
                    // Jump forward and slightly up towards the target
                    var dir = (_target.Transform.Position - Transform.Position).WithZ(0).Normal;
                    _rb.Velocity = dir * 150f + Vector3.Up * 150f;
                    _timeSinceStuck = 0;
                    PlaySequence( MoveSeq, looping: false );
                }
            }
            else
            {
                _timeSinceStuck = 0;
            }
        }
        else
        {
            if ( Agent.IsValid() && Agent.Enabled )
                Agent.Stop();
            UpdateAnimation();
        }
    }

    private void PlaySequence( string name, bool looping )
    {
        if ( !Renderer.IsValid() ) return;
        if ( Renderer.Sequence.Name == name ) return;

        Renderer.Sequence.Name = name;
        Renderer.Sequence.Looping = looping;
    }

    // How far apart zombies try to stay, and how strongly they push.
    private const float SeparationRadius = 50f;
    private const float SeparationStrength = 40f;

    /// <summary>
    /// Returns a small world-space offset that points away from nearby zombies,
    /// so they spread out instead of stacking on the same target point.
    /// </summary>
    private Vector3 GetSeparationOffset()
    {
        var push = Vector3.Zero;
        var myPos = Transform.Position;

        foreach ( var other in Scene.GetAllComponents<ZombieAI>() )
        {
            if ( other == this || !other.IsValid() || other._isDead ) continue;

            var away = (myPos - other.Transform.Position).WithZ( 0 );
            var d = away.Length;
            if ( d > 0.1f && d < SeparationRadius )
            {
                // Closer zombies push harder.
                push += away.Normal * (1f - d / SeparationRadius);
            }
        }

        return push * SeparationStrength;
    }

    private void FindTarget()
    {
        // Simple targeting: closest living player
        _target = Scene.GetAllComponents<PlayerPawn>()
            .Where( p => p.IsValid() && p.HealthComponent.State == LifeState.Alive )
            .OrderBy( p => Vector3.DistanceBetween( Transform.Position, p.Transform.Position ) )
            .FirstOrDefault();
    }

    private void Attack()
    {
        _lastAttack = 0;
        _timeSinceAttackAnim = 0;
        PlaySequence( AttackSeq, looping: false );

        // Deal damage
        var damageInfo = new Facepunch.DamageInfo( this, AttackDamage, this );
        _target.HealthComponent.TakeDamage( damageInfo );

        Sound.Play( "zombie.attack", Transform.Position );
    }

    private void UpdateAnimation()
    {
        // Let the attack swing play through before switching back to walk/idle.
        if ( _timeSinceAttackAnim < AttackAnimHold )
            return;

        var moving = Agent.IsValid() && Agent.Velocity.Length > 10f;
        PlaySequence( moving ? MoveSeq : IdleSeq, looping: true );
    }

    private void SpawnBlood( Vector3 pos, int count = 1 )
    {
        var prefabFile = ResourceLibrary.Get<PrefabFile>( "prefabs/impact_fx/impact_blood_mist.prefab" );
        if ( prefabFile is null ) return;

        var prefab = SceneUtility.GetPrefabScene( prefabFile );
        if ( !prefab.IsValid() ) return;

        for ( int i = 0; i < count; i++ )
        {
            var blood = prefab.Clone();
            var jitter = count > 1 ? Vector3.Random * 12f : Vector3.Zero;
            blood.WorldPosition = (pos == default ? WorldPosition + Vector3.Up * 30f : pos) + jitter;
            blood.DestroyAsync( 2f );
        }
    }

    public void OnDamage( in Sandbox.DamageInfo info )
    {
        if ( _isDead ) return;

        // Spawn blood particle at the hit location
        SpawnBlood( info.Position );

        Health -= info.Damage;
        
        // Grant points to the attacker if it's a player
        if ( info.Attacker.IsValid() && info.Attacker.Components.TryGet<PlayerPawn>( out var player ) )
        {
            if ( player.Components.TryGet<ZombiesPlayerEconomy>( out var eco ) )
            {
                eco.AddPoints( 10 );
            }
        }

        if ( Health <= 0 )
        {
            Die( info.Attacker );
        }
        else
        {
            // Flinch — trinit model has no flinch sequence; just play the pain sound.
            Sound.Play( "zombie.pain", Transform.Position );
        }
    }

    private void Die( GameObject attacker )
    {
        _isDead = true;

        // Big blood burst on death
        SpawnBlood( WorldPosition + Vector3.Up * 35f, count: 8 );

        if ( Agent.IsValid() )
        {
            Agent.Stop();
            Agent.Enabled = false;
        }

        // The block zombie model has no ragdoll skeleton, so topple the whole
        // body with the rigidbody for a "dies and falls over" effect.
        if ( _rb.IsValid() )
        {
            _rb.MotionEnabled = true;
            _rb.Enabled = true;

            var dir = attacker.IsValid()
                ? (WorldPosition - attacker.WorldPosition).WithZ( 0 ).Normal
                : Vector3.Backward;

            _rb.Velocity = dir * 120f + Vector3.Up * 100f;
            _rb.AngularVelocity = Vector3.Random * 8f; // tumble
        }

        Sound.Play( "zombie.die", Transform.Position );

        // Grant kill points
        if ( attacker.IsValid() && attacker.Components.TryGet<PlayerPawn>( out var player ) )
        {
            if ( player.Components.TryGet<ZombiesPlayerEconomy>( out var eco ) )
            {
                eco.AddPoints( 90 ); // 100 total for kill
            }
        }

        // Notify Round System
        if ( GameMode.Instance.IsValid() && GameMode.Instance.Components.TryGet<ZombiesRoundSystem>( out var roundSystem ) )
        {
            roundSystem.OnZombieKilled();
        }

        // Destroy after a delay so ragdoll can settle
        GameObject.DestroyAsync( 10f );
    }

    public void OnTriggerEnter( Collider other ) {}
    public void OnTriggerExit( Collider other ) {}
}
