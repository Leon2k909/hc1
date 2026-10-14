namespace Facepunch.Gunsmith;

/// <summary>Reusable steel silhouette with real weapon impact damage and a timed reset.</summary>
public sealed class FiringRangeTarget : Component, Component.IDamageable
{
    [Property] public float DistanceMetres { get; set; } = 10;
    [Property] public float MaxHealth { get; set; } = 100;
    [Property] public float Travel { get; set; } = 70;
    public float Health { get; private set; } = 100;
    public bool IsDown { get; private set; }
    private Vector3 origin;
    private TimeSince sinceDown;
    private TimeSince sinceImpact = 10;
    private ModelRenderer renderer;
    private ModelCollider collider;

    protected override void OnStart()
    {
        origin = WorldPosition;
        renderer = Components.Get<ModelRenderer>();
        collider = Components.Get<ModelCollider>();
        Health = MaxHealth;
    }

    protected override void OnUpdate()
    {
        if ( IsDown && sinceDown > 1.5f ) ResetTarget();
        var range = FiringRangeSystem.Current;
        if ( range.IsValid() && !range.MenuOpen && !IsDown )
            WorldPosition = origin + Vector3.Left * (range.MovingTargets ? MathF.Sin( Time.Now * 1.1f + DistanceMetres ) * Travel : 0);
        if ( renderer.IsValid() && !IsDown )
            renderer.Tint = sinceImpact < .12f ? new Color( 1f, .65f, .22f ) : Color.White;
    }

    public void OnDamage( in Sandbox.DamageInfo info )
    {
        var range = FiringRangeSystem.Current;
        if ( !range.IsValid() || IsDown || range.MenuOpen || info.Damage <= 0 ) return;
        var attacker = info.Attacker?.GetComponent<PlayerPawn>() ?? info.Attacker?.GetComponentInParent<PlayerPawn>();
        if ( !attacker.IsValid() || attacker != range.Player ) return;

        // Report the actual projectile's impact damage (including ammunition and
        // range falloff), without match-only armor or hardcore injury rules.
        var headshot = WorldTransform.PointToLocal( info.Position ).z >= 59;
        Health = MathF.Max( 0, Health - info.Damage );
        sinceImpact = 0;
        var down = Health <= 0;
        range.RecordHit( info.Damage, (info.Position - attacker.EyePosition).Length / 39.37007874f, headshot, down );
        attacker.GetComponent<Crosshair>()?.ShowHit( down, headshot );
        if ( down )
        {
            IsDown = true;
            sinceDown = 0;
            if ( renderer.IsValid() ) renderer.Enabled = false;
            if ( collider.IsValid() ) collider.Enabled = false;
        }
    }

    public void ResetTarget()
    {
        Health = MaxHealth;
        IsDown = false;
        sinceImpact = 10;
        WorldPosition = origin;
        if ( renderer.IsValid() ) { renderer.Enabled = true; renderer.Tint = Color.White; }
        if ( collider.IsValid() ) collider.Enabled = true;
    }
}
