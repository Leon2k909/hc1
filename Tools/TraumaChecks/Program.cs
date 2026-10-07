using Facepunch;

static void Check(bool condition, string label)
{
    if (!condition) throw new Exception(label);
}

static int Hits(float damage) => (int)MathF.Ceiling(100f / damage);
Check(Hits(HardcoreTrauma.Damage(12, TraumaRegion.Chest, 100)) == 2, "Uzi unprotected chest");
Check(Hits(HardcoreTrauma.Damage(12, TraumaRegion.Head, 100)) == 1, "Uzi unprotected head");
Check(Hits(HardcoreTrauma.Damage(12, TraumaRegion.Abdomen, 100)) == 3, "Abdomen less severe");
Check(Hits(HardcoreTrauma.Damage(12, TraumaRegion.Limb, 100)) == 5, "Limb less severe");
Check(HardcoreTrauma.Damage(1, TraumaRegion.Head, 100) < 100, "Weak pellet not automatic kill");
Check(HardcoreTrauma.Damage(0, TraumaRegion.Head, 100) == 0, "Zero energy");
Check(HardcoreTrauma.Damage(100, TraumaRegion.Limb, 100) == 50, "Single limb trauma bounded");
Check(HardcoreTrauma.Damage(100, TraumaRegion.Limb, 200) == 100, "Custom health limb cap");
Check(HardcoreTrauma.Damage(6, TraumaRegion.Chest, 100) < HardcoreTrauma.Damage(12, TraumaRegion.Chest, 100), "Range loss retained");
Check(HardcoreTrauma.Damage(12, TraumaRegion.Head, 200) == HardcoreTrauma.Damage(12, TraumaRegion.Head, 100), "Damage independent of max health");
Console.WriteLine("PASS: 10 regional trauma checks");
