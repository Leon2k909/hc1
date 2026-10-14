var flags = System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Public | System.Reflection.BindingFlags.Instance;
var type = typeof(Facepunch.Weather).GetNestedType("RainCycle", System.Reflection.BindingFlags.NonPublic);
var method = type.GetMethod("Next", flags);
var cycle = Activator.CreateInstance(type, true);
var random = new System.Random(8712);
var wet = 0;
var maxClear = 0;
var clear = 0;
for (var block = 0; block < 1000; block++)
{
    var blockWet = 0;
    for (var i = 0; i < 4; i++)
    {
        if ((bool)method.Invoke(cycle, new object[] {random})) { wet++; blockWet++; clear = 0; }
        else { clear++; maxClear = Math.Max(maxClear, clear); }
    }
    if (blockWet != 1) throw new Exception("Rain share drifted from one in four");
}
if (maxClear > 6) throw new Exception("Unbounded clear streak");
var delayed = 0;
var present = 0;
var maxCoverStep = 0f;
var moving = 0;
for (var seed = 0; seed < 256; seed++)
{
    var start = Facepunch.Weather.Schedule.RainStart(seed);
    if (start < 0) present++; else delayed++;
    foreach (var kind in new[] {Facepunch.WeatherKind.Drizzle, Facepunch.WeatherKind.Steady})
    {
        if (Facepunch.Weather.Schedule.RateAt(kind, seed, start - 1) != 0) throw new Exception("Rain started before its front");
        if (Facepunch.Weather.Schedule.RateAt(kind, seed, Math.Max(0, start) + 150) <= 0) throw new Exception("Wet match has no rain");
        if (Facepunch.Weather.Schedule.RateAt(kind, seed, 1200) != 0) throw new Exception("Front did not clear");
        if (Facepunch.Weather.Schedule.OvercastAt(kind, seed, 1200) != 0) throw new Exception("Sky did not clear");
    }
    var min = 1f;
    var max = 0f;
    for (var t = 0; t <= 1200; t++)
    {
        var cover = Facepunch.Weather.Schedule.CloudCoverAt(seed, t);
        if (!float.IsFinite(cover) || cover < .15f || cover > .75f) throw new Exception("Invalid cloud cover");
        maxCoverStep = MathF.Max(maxCoverStep, MathF.Abs(cover - Facepunch.Weather.Schedule.CloudCoverAt(seed, t - 1)));
        min = MathF.Min(min, cover); max = MathF.Max(max, cover);
        if (Facepunch.Weather.Schedule.RateAt(Facepunch.WeatherKind.Clear, seed, t) != 0) throw new Exception("Clear match rained");
    }
    if (max - min > .05f) moving++;
}
if (maxCoverStep > .0031f || moving < 240 || delayed < 80 || present < 80) throw new Exception("Weather variation is missing or too abrupt");
return new { Passed = true, Matches = 4000, WetMatches = wet, MaximumClearStreak = maxClear, Seeds = 256, PresentFronts = present, DelayedFronts = delayed, MovingCloudProfiles = moving, MaximumCloudChangePerSecond = maxCoverStep };
