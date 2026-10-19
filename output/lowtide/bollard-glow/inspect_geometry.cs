var baseDir = @"C:\sbox-projects\hc1\forked-shooter-main\assets\models\maps\lowtide";
var results = new System.Collections.Generic.List<object>();
foreach (var side in new[] {"east","west"})
{
    var obj = System.IO.Path.Combine(baseDir, $"lowtide_dress_{side}.obj");
    var marker = "# Lowtide street bollards: sealed smooth caps, pavement contact";
    var found = false;
    var after = new System.Collections.Generic.List<string>();
    var bandSections = 0;
    var newBand = 0;
    using (var reader = new System.IO.StreamReader(obj))
    {
        string line;
        while ((line = reader.ReadLine()) != null)
        {
            if (line == marker) found = true;
            if (found)
            {
                if (line == "usemtl rw_white_paint") bandSections++;
                if (line == "usemtl lt_bollard_diffuser") newBand++;
                if (line.StartsWith("usemtl ")) after.Add(line);
            }
        }
    }
    results.Add(new {Side=side, RepairMarker=found, BandSections=bandSections, NewBandSections=newBand, TailMaterials=after.TakeLast(20).ToArray()});
}
return results;
