// Targeted production ray tests; no scene rendering, play changes, or saved-scene edits.
var originalScene = Game.ActiveScene;
var editorScene = Editor.SceneEditorSession.Active?.Scene;
var checks = new System.Collections.Generic.List<object>();
var testScene = new Scene();
void Require(bool condition, string name, object detail = null)
{
    checks.Add(new { name, passed = condition, detail });
    if (!condition) throw new Exception("Laser verification failed: " + name + " " + Json.Serialize(detail));
}
try
{
    using (testScene.Push())
    {
        var wall = new GameObject(true, "Laser alignment target");
        var collider = wall.Components.Create<BoxCollider>();
        collider.Scale = new Vector3(4, 512, 512);
        var beam = new GameObject(true, "Laser alignment beam").Components.Create<Facepunch.Gunsmith.GunsmithLaserBeam>();
        float worstError = 0f, worstOriginalError = 0f;
        foreach (var distance in new[] { 64f, 512f, 4096f })
        foreach (var aimRotation in new[] { Rotation.Identity, Rotation.From(new Angles(-18f, 35f, 24f)) })
        foreach (var pose in new[] { Rotation.Identity, Rotation.From(new Angles(1.5f, -1f, 0f)), Rotation.From(new Angles(-2f, 1.2f, 15f)) })
        {
            cancellationToken.ThrowIfCancellationRequested();
            var origin = new Vector3(120f, -90f, 50f);
            var target = origin + aimRotation.Forward * distance;
            wall.WorldPosition = target + aimRotation.Forward * 2f;
            wall.WorldRotation = aimRotation;
            testScene.EditorTick(.016f, .016f);
            var emitter = origin + aimRotation * new Vector3(12f, -1.5f, -2.5f);
            var physicalForward = (aimRotation * pose).Forward;
            beam.TraceBeam(emitter, physicalForward, null);
            worstOriginalError = MathF.Max(worstOriginalError, beam.End.Distance(target));
            beam.TraceBeam(emitter, physicalForward, null, new Ray(origin, aimRotation.Forward));
            var error = beam.End.Distance(target);
            worstError = MathF.Max(worstError, error);
            Require(beam.HasHit && error < .03f, "Unobstructed aim convergence", new { distance, error });
        }
        Require(worstOriginalError > 1f, "Reproduced model-axis mismatch", new { worstOriginalError, worstError });
        wall.WorldRotation = Rotation.Identity;
        wall.WorldPosition = new Vector3(514f, 0f, 0f);
        testScene.EditorTick(.016f, .016f);
        var start = new Vector3(12f, -6f, -3f);
        var aim = new Ray(Vector3.Zero, Vector3.Forward);
        var cover = new GameObject(true, "Emitter-side cover");
        cover.WorldPosition = new Vector3(30f, -5.8f, -2.9f);
        cover.Components.Create<BoxCollider>().Scale = new Vector3(4f, 2f, 2f);
        testScene.EditorTick(.016f, .016f);
        beam.TraceBeam(start, Vector3.Forward, null, aim);
        Require(beam.HasHit && beam.End.x < 40f && MathF.Abs(beam.End.y) > 3f,
            "Emitter-side obstruction stops beam", new { endpoint = beam.End.ToString() });
        cover.DestroyImmediate();
        foreach (var tag in new[] { "trigger", "playerclip", "movement" })
        {
            var clip = new GameObject(true, "Non-visible clip " + tag);
            clip.WorldPosition = new Vector3(60f, 0f, 0f);
            clip.Tags.Add(tag);
            clip.Components.Create<BoxCollider>().Scale = new Vector3(4f, 80f, 80f);
            testScene.EditorTick(.016f, .016f);
            beam.TraceBeam(start, Vector3.Forward, null, aim);
            Require(beam.HasHit && beam.End.Distance(new Vector3(512f, 0f, 0f)) < .03f,
                "Ignore " + tag, new { endpoint = beam.End.ToString() });
            clip.DestroyImmediate();
        }
        var owner = new GameObject(true, "Ignored owner");
        var ownerChild = new GameObject(owner, true, "Owner collider");
        ownerChild.WorldPosition = new Vector3(40f, 0f, 0f);
        ownerChild.Components.Create<BoxCollider>().Scale = new Vector3(4f, 80f, 80f);
        testScene.EditorTick(.016f, .016f);
        beam.TraceBeam(start, Vector3.Forward, owner, aim);
        Require(beam.HasHit && beam.End.Distance(new Vector3(512f, 0f, 0f)) < .03f,
            "Ignore owner hierarchy");
        owner.DestroyImmediate();

        wall.WorldPosition = new Vector3(8f, 0f, 0f);
        testScene.EditorTick(.016f, .016f);
        beam.TraceBeam(start, Vector3.Forward, null, aim);
        Require(!beam.HasHit && (beam.End - start).Dot(Vector3.Forward) > 0f,
            "Target behind emitter does not reverse beam");
        wall.Enabled = false;
        testScene.EditorTick(.016f, .016f);
        beam.TraceBeam(start, Vector3.Forward, null, aim);
        Require(!beam.HasHit && MathF.Abs(beam.Start.Distance(beam.End) - beam.Range) < .03f,
            "No-hit beam retains emitter range", new { range = beam.Start.Distance(beam.End) });
        beam.TraceBeam(start, Vector3.Forward, null);
        Require(!beam.HasHit && beam.End.Distance(start + Vector3.Forward * beam.Range) < .03f,
            "Physical-direction fallback");
        var solid = new GameObject(true, "Solid around emitter");
        solid.WorldPosition = start;
        solid.Components.Create<BoxCollider>().Scale = new Vector3(2f, 2f, 2f);
        testScene.EditorTick(.016f, .016f);
        beam.TraceBeam(start, Vector3.Forward, null, aim);
        Require(!beam.IsVisible && !beam.HasHit, "Emitter inside solid hides beam");
        solid.DestroyImmediate();
        beam.TraceBeam(start, Vector3.Zero, null, aim);
        Require(!beam.IsVisible && !beam.HasHit, "Invalid physical direction hides beam");
        beam.TraceBeam(start, Vector3.Forward, null, aim);
        beam.Hide();
        Require(!beam.IsVisible && !beam.HasHit, "Hide clears beam and dot");
        beam.TraceBeam(start, Vector3.Forward, null, aim);
        beam.Enabled = false;
        Require(!beam.IsVisible && !beam.HasHit, "Disable releases beam and dot");
    }
}
finally { testScene.Destroy(); }
Require(Game.ActiveScene == originalScene && Editor.SceneEditorSession.Active?.Scene == editorScene,
    "Preserved active and edited scenes");
var report = new { passed = true, checks = checks.Count, results = checks };
System.IO.File.WriteAllText(@"D:\Documents\s&box projects\hc1\forked-shooter-main\output\laser-alignment-20261017\native-ray-results.json", Json.Serialize(report));
return report;
