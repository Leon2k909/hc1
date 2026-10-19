using Facepunch;

static void Check(bool condition, string label)
{
    if (!condition) throw new Exception(label);
}

static bool Near(float a, float b) => MathF.Abs(a - b) < 0.0001f;

static int Hits(float damage) => (int)MathF.Ceiling(100f / damage);
Check(Hits(HardcoreTrauma.Damage(12, TraumaRegion.Chest, 100)) == 3, "Uzi unprotected chest survivor requires a third hit");
Check(Hits(HardcoreTrauma.Damage(12, TraumaRegion.Head, 100)) == 1, "Uzi unprotected head");
Check(Hits(HardcoreTrauma.Damage(12, TraumaRegion.Abdomen, 100)) == 3, "Abdomen less severe");
Check(Hits(HardcoreTrauma.Damage(12, TraumaRegion.Limb, 100)) == 5, "Limb less severe");
Check(HardcoreTrauma.Damage(1, TraumaRegion.Head, 100) < 100, "Weak pellet not automatic kill");
Check(HardcoreTrauma.Damage(0, TraumaRegion.Head, 100) == 0, "Zero energy");
Check(HardcoreTrauma.Damage(100, TraumaRegion.Limb, 100) == 50, "Single limb trauma bounded");
Check(HardcoreTrauma.Damage(100, TraumaRegion.Limb, 200) == 100, "Custom health limb cap");
Check(HardcoreTrauma.Damage(6, TraumaRegion.Chest, 100) < HardcoreTrauma.Damage(12, TraumaRegion.Chest, 100), "Range loss retained");
Check(HardcoreTrauma.Damage(12, TraumaRegion.Head, 200) == HardcoreTrauma.Damage(12, TraumaRegion.Head, 100), "Damage independent of max health");

// A body hit that doesn't kill outright leaves the victim alive, whatever the round: the kill chance decides.
Check(Near(HardcoreTrauma.Damage(26, TraumaRegion.Chest, 100), 90f), "7.62x39 chest survivable without the roll");
Check(Near(HardcoreTrauma.Damage(44, TraumaRegion.Abdomen, 100), 90f), "6.8x51 abdomen survivable without the roll");
Check(Near(HardcoreTrauma.Damage(20, TraumaRegion.Chest, 100), 90f), "M4 chest unchanged");
Check(HardcoreTrauma.Damage(26, TraumaRegion.Head, 100) >= 100, "Head still kills");

// The kill chance: the round's damage over 40, at most 95%, less in the gut, through armour and with more health.
Check(Near(HardcoreTrauma.KillChance(20, TraumaRegion.Chest, 100, 1), 20f/30f), "M4 chest two thirds of the time");
Check(Near(HardcoreTrauma.KillChance(12, TraumaRegion.Chest, 100, 1), 0.4f), "9 mm chest 40%");
Check(Near(HardcoreTrauma.KillChance(26, TraumaRegion.Chest, 100, 1), 26f/30f), "7.62x39 chest 87%");
Check(Near(HardcoreTrauma.KillChance(41, TraumaRegion.Chest, 100, 1), 0.95f), "FAL capped at 95%");
Check(Near(HardcoreTrauma.KillChance(20, TraumaRegion.Abdomen, 100, 1), 0.4f), "M4 gut 40%");
Check(Near(HardcoreTrauma.KillChance(20, TraumaRegion.Chest, 100, 0.25f), 1f/6f), "Armour stops most of it");
Check(Near(HardcoreTrauma.KillChance(20, TraumaRegion.Chest, 200, 1), 1f/3f), "Double health halves it");
Check(HardcoreTrauma.KillChance(20, TraumaRegion.Head, 100, 1) == 0f, "Head goes by damage");
Check(HardcoreTrauma.KillChance(20, TraumaRegion.Limb, 100, 1) == 0f, "Limbs never kill outright");
Check(HardcoreTrauma.KillChance(0, TraumaRegion.Chest, 100, 1) == 0f, "No energy, no chance");

// How many unarmoured chest hits an M4 takes to kill, over many lives: one about half the time, never more than two.
var random = new Random(1);
int one = 0, two = 0;
for (var life = 0; life < 100000; life++)
{
    var health = 100f;
    for (var hit = 1; ; hit++)
    {
        if (random.NextSingle() < HardcoreTrauma.KillChance(20, TraumaRegion.Chest, 100, 1)) health = 0f;
        else health -= HardcoreTrauma.Damage(20, TraumaRegion.Chest, 100);
        if (health > 0f) continue;
        if (hit == 1) one++; else if (hit == 2) two++;
        break;
    }
}
Check(MathF.Abs(one / 100000f - 2f/3f) < 0.01f && one + two == 100000, $"M4 chest hits to kill: {one} one, {two} two");
Console.WriteLine($"PASS: 25 regional trauma checks (M4 chest: {one / 1000f:F1}% one hit, {two / 1000f:F1}% two)");
