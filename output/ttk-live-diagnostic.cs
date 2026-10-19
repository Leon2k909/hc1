var scene = Game.ActiveScene;
var mode = Facepunch.GameMode.Instance;
return new
{
    Scene = scene?.Name,
    Mode = mode?.Ident,
    Facepunch.GameMode.IsHardcore,
    ModeHardcore = mode?.Hardcore,
    StandardHealth = mode?.UsesStandardHealth,
    ModeArmor = mode?.ArmorEnabled,
    ModeHelmets = mode?.HelmetsEnabled,
    Samples = System.Linq.Enumerable.Range( 0, 10 ).Select( _ => Game.Random.Float() ).ToArray(),
    ChanceM4 = Facepunch.HardcoreTrauma.KillChance( 20, Facepunch.TraumaRegion.Chest, 100, 1 ),
    Living = scene?.GetAllComponents<Facepunch.HealthComponent>().Where( h => h.IsValid() && h.Health > 0 )
        .Take( 16 ).Select( h => new { Owner = h.GameObject.Name, Hp = h.Health, MaxHp = h.MaxHealth, State = h.State.ToString() } ).ToArray(),
    Weapons = scene?.GetAllComponents<Facepunch.Shootable>().Where( w => w.IsValid() )
        .Take( 18 ).Select( w => new { Owner = w.GameObject.Name, Damage = w.BaseDamage, Range = w.MaxRange } ).ToArray()
};
