using Sandbox.MovieMaker.Compiled;
using System.Collections.Generic;

namespace Facepunch;

/// <summary>
/// A frozen portion of the current match. Movie times and action times use the same absolute recording coordinates;
/// the bounded recorder can continue capturing or start a new round without changing this clip or its sidecars.
/// </summary>
public sealed record SndReplayClip( MovieClip Movie, List<TheaterReplays.Soldier> Soldiers,
	TheaterReplays.Actions Actions, string FollowTrack, float Start, float End )
{
	public float Duration => End - Start;
}
