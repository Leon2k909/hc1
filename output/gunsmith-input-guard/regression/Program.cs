using Facepunch;

int checks = 0;
void Check(bool condition, string message)
{
    if (!condition) throw new Exception(message);
    checks++;
}
foreach (var mode in Enum.GetValues<FireMode>())
{
    GameUtils.GunsmithOpen = false;
    var gun = new Shootable(mode);
    gun.Tick();
    GameUtils.GunsmithOpen = true;
    for (int i = 0; i < 5; i++) gun.Tick(true, i == 0);
    Check(gun.Shots == 0 && gun.Pressed == 0 && !gun.IsTakingInput, $"{mode}: gunsmith clicks reached weapon");
    GameUtils.GunsmithOpen = false;
    for (int i = 0; i < 5; i++) gun.Tick(true, i == 0);
    Check(gun.Shots == 0 && gun.Pressed == 0, $"{mode}: held close click fired");
    gun.Tick();
    for (int i = 0; i < 10; i++) gun.Tick(true, i == 0);
    Check(gun.Shots > 0, $"{mode}: fresh press no longer fires");

    GameUtils.GunsmithOpen = false;
    gun = new Shootable(mode);
    gun.Tick();
    GameUtils.GunsmithOpen = true;
    gun.Tick(); // UI has consumed the raw mouse input.
    GameUtils.GunsmithOpen = false;
    gun.Tick(true, true); // Same click becomes visible when the overlay closes.
    gun.Tick(true);
    Check(gun.Shots == 0, $"{mode}: UI-consumed click leaked on close");
}

GameUtils.GunsmithOpen = false;
var burst = new Shootable(FireMode.Burst);
burst.Tick();
burst.QueueBurst();
GameUtils.GunsmithOpen = true;
burst.Tick(true, true);
Check(!burst.IsBurstFiring && burst.BurstCount == 0 && burst.Shots == 0, "Queued burst continued in gunsmith");
GameUtils.GunsmithOpen = false;
for (int i = 0; i < 20; i++) burst.Tick();
Check(burst.Shots == 0, "Queued burst resumed after gunsmith closed");

var held = new Shootable(FireMode.Semi);
held.Deploy();
held.Tick(true, true);
Check(held.Shots == 0, "Deploy-held-input protection regressed");
held.Tick();
held.Tick(true, true);
Check(held.Shots == 1, "Deploy release did not restore firing");
GameUtils.GunsmithOpen = true;
held.Tick();
held.Tick();
Check(held.Released == 1 && !held.IsTakingInput, "Opening gunsmith did not release the existing action exactly once");

Console.WriteLine($"PASS: {checks} input regression checks (real weapon input handler and extracted production firing methods).");
