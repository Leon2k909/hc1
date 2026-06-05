using Sandbox;
using Sandbox.MovieMaker;

namespace Facepunch;

public class TheaterController : Component
{
    [Property] public MoviePlayer Player { get; set; }

    [Property] public GameObject FreeCamObject { get; set; }

    public bool IsFreecam { get; set; } = true;
    public float Duration { get; set; }
    public float CurrentTime { get; set; }

    protected override void OnStart()
    {
        // Load the movie path from Game.Cookies that we set in TheaterPage
        string path = Game.Cookies.Get<string>( "theater_replay_path", "" );
        
        if ( !string.IsNullOrEmpty(path) && Player.IsValid() )
        {
            var clip = FileSystem.Data.ReadJson<Sandbox.MovieMaker.Compiled.MovieClip>( path );
            if ( clip != null )
            {
                Duration = (float)clip.Duration.TotalSeconds;
                Player.Play(clip);
            }
        }
    }

    protected override void OnUpdate()
    {
        CurrentTime += Time.Delta;

        // Simple Freecam controls
        if ( IsFreecam && FreeCamObject.IsValid() )
        {
            var cam = FreeCamObject.GetComponent<CameraComponent>();
            if ( cam.IsValid() )
            {
                // Basic fly movement
                var vel = Vector3.Zero;
                if ( Input.Down( "forward" ) ) vel += FreeCamObject.Transform.Rotation.Forward;
                if ( Input.Down( "backward" ) ) vel -= FreeCamObject.Transform.Rotation.Forward;
                if ( Input.Down( "left" ) ) vel -= FreeCamObject.Transform.Rotation.Right;
                if ( Input.Down( "right" ) ) vel += FreeCamObject.Transform.Rotation.Right;

                FreeCamObject.Transform.Position += vel * Time.Delta * 500f * (Input.Down("run") ? 2f : 1f);

                // Mouse look
                var angles = FreeCamObject.Transform.Rotation.Angles();
                angles += new Angles( Input.AnalogLook.pitch, Input.AnalogLook.yaw, 0 );
                FreeCamObject.Transform.Rotation = angles.ToRotation();
            }
        }
    }
}
