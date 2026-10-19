var victim = Game.ActiveScene.GetAllComponents<Facepunch.HealthComponent>()
    .FirstOrDefault( h => h.IsValid() && h.MaxHealth == 100f );
if ( victim is null ) return "No 100 HP health component found";
var method = typeof( Facepunch.HealthComponent ).GetMethod( "HardcoreBullet",
    System.Reflection.BindingFlags.Instance | System.Reflection.BindingFlags.NonPublic );
if ( method is null ) return "HardcoreBullet method missing";
int one = 0;
float hpAfter = 0f;
for ( int i = 0; i < 250; i++ )
{
    var hit = new Facepunch.DamageInfo( null, 20f, Hitbox: Facepunch.HitboxTags.Chest );
    var args = new object[] { hit, 20f, false };
    var result = (Facepunch.DamageInfo)method.Invoke( victim, args );
    if ( (bool)args[2] ) one++;
    hpAfter = victim.MaxHealth - result.Damage;
}
return new { Checks = 250, OneShotRolls = one, Chance = one / 250f, SampleSurvivorHealth = hpAfter,
    ActualHealthUntouched = victim.Health };
