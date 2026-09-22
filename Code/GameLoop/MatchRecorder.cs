using Sandbox;
using Sandbox.MovieMaker;
using System;

namespace Facepunch;

public class MatchRecorder : Component
{
    private MovieRecorder _recorder;
    private bool _isRecording;

    [ConVar( "hc1_match_recorder_enabled" )]
    public static bool MatchRecorderEnabled { get; set; } = false;

    [Property] public bool AutoRecord { get; set; } = true;

    protected override void OnStart()
    {
        if ( !MatchRecorderEnabled )
        {
            Log.Info( "MatchRecorder disabled by hc1_match_recorder_enabled=0." );
            return;
        }

        if ( AutoRecord && Networking.IsHost )
        {
            StartRecording();
        }
    }

    public void StartRecording()
    {
        if ( !MatchRecorderEnabled ) return;
        if ( _isRecording ) return;

        _recorder = new MovieRecorder( Scene );
        _recorder.Start();
        _isRecording = true;
        Log.Info( "MatchRecorder started recording." );
    }

    public void StopRecording()
    {
        if ( !_isRecording || _recorder == null ) return;

        _recorder.Stop();
        _isRecording = false;
        
        var clip = _recorder.ToClip();
        
        // Ensure directory exists
        FileSystem.Data.CreateDirectory( "replays" );
        
        var mapName = Game.ActiveScene?.Title ?? "UnknownMap";
        if ( string.IsNullOrWhiteSpace( mapName ) || mapName == "minimal" )
        {
            mapName = "Match";
        }
        
        string filename = $"replays/{mapName}_{DateTime.Now:yyyyMMdd_HHmmss}.movie";
        
        FileSystem.Data.WriteJson( filename, clip );
        
        Log.Info( $"MatchRecorder saved replay to: {filename}" );
    }

    protected override void OnDestroy()
    {
        if ( _isRecording )
        {
            StopRecording();
        }
    }
}
