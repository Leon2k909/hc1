using Facepunch;

var checks = 0;
void Check( bool condition, string label )
{
	checks++;
	if ( !condition ) throw new InvalidOperationException( $"FAIL: {label}" );
}

var a = Guid.Parse( "00000000-0000-0000-0000-000000000001" );
var b = Guid.Parse( "00000000-0000-0000-0000-000000000002" );
var c = Guid.Parse( "00000000-0000-0000-0000-000000000003" );
var outsider = Guid.Parse( "00000000-0000-0000-0000-000000000004" );

var votes = new SndReplayVotes();
Check( votes.Count == 0 && votes.EligibleCount == 0 && votes.Required == 1 && !votes.HasMajority, "unstarted vote stays closed" );
votes.Refresh( new[] { a } );
Check( !votes.TryVote( 0, a ) && votes.EligibleCount == 0, "refresh cannot open an unstarted vote" );

votes.Begin( 1, new[] { a, a, Guid.Empty } );
Check( votes.EligibleCount == 1 && votes.Required == 1, "duplicate roster entries and empty identities do not inflate the threshold" );
Check( !votes.TryVote( 1, Guid.Empty ) && !votes.TryVote( 1, outsider ) && votes.Count == 0, "invalid or ineligible connections cannot vote" );
Check( !votes.TryVote( 0, a ) && !votes.TryVote( 2, a ), "inactive replay IDs are rejected" );
Check( votes.TryVote( 1, a ) && votes.Count == 1 && votes.HasMajority, "one human can skip alone" );
Check( !votes.TryVote( 1, a ) && votes.Count == 1, "duplicate vote does not count twice" );

votes.Begin( 2, new[] { a, b } );
Check( votes.Required == 2 && votes.Count == 0 && !votes.HasMajority, "two humans require both votes and begin clears the old vote" );
Check( !votes.TryVote( 1, a ), "delayed previous-replay vote is rejected" );
Check( votes.TryVote( 2, a ) && !votes.HasMajority, "one of two is not a majority" );
Check( votes.TryVote( 2, b ) && votes.HasMajority, "two of two is a majority" );

votes.Begin( 3, new[] { a, b, c } );
Check( votes.Required == 2 && votes.TryVote( 3, a ) && !votes.HasMajority, "one of three is not a majority" );
Check( votes.TryVote( 3, b ) && votes.HasMajority, "two of three is a majority" );
votes.Refresh( new[] { a, c } );
Check( votes.Count == 1 && votes.Required == 2 && !votes.HasMajority, "departed voter's vote is removed" );
Check( !votes.TryVote( 3, b ), "departed connection cannot vote" );
votes.Refresh( new[] { a } );
Check( votes.Count == 1 && votes.Required == 1 && votes.HasMajority, "departed nonvoter reduces the majority threshold" );
votes.Refresh( new[] { a, b, c, outsider } );
Check( votes.Required == 3 && votes.Count == 1 && !votes.HasMajority, "late joiners count in the current electorate" );
Check( votes.TryVote( 3, b ) && !votes.HasMajority, "returning connection must cast a fresh vote" );
Check( votes.TryVote( 3, outsider ) && votes.HasMajority, "late joiner can complete the majority" );
votes.Refresh( Array.Empty<Guid>() );
Check( votes.Count == 0 && votes.EligibleCount == 0 && votes.Required == 1 && !votes.HasMajority, "empty electorate does not auto-pass" );

votes.Begin( 4, new[] { a } );
Check( !votes.TryVote( 3, a ) && votes.TryVote( 4, a ), "round reset accepts only its current generation" );
votes.Begin( 4, new[] { a } );
Check( votes.Count == 0 && votes.TryVote( 4, a ), "begin always resets even if a caller reuses its generation" );
votes.Begin( -1, new[] { a } );
Check( votes.EligibleCount == 0 && votes.Count == 0 && !votes.TryVote( -1, a ) && !votes.HasMajority, "negative replay ID clears and closes the vote" );
votes.Begin( 5, null! );
Check( votes.EligibleCount == 0 && !votes.HasMajority, "missing roster is empty" );
votes.Refresh( new[] { a } );
Check( votes.TryVote( 5, a ), "current replay can acquire a late roster" );
votes.Refresh( null! );
Check( votes.Count == 0 && votes.Required == 1 && !votes.HasMajority, "missing refreshed roster removes old votes" );

var scoring = new SndReplayScoring();
Check( SndReplayScoring.WindowSeconds == 6f, "highlight window is six seconds" );
Check( scoring.Record( a, 0, false, 0 ) == new SndReplayScore( 1000, 1, 0 ), "ordinary enemy kill" );
Check( scoring.Record( a, 3, true, 393.7f ) == new SndReplayScore( 2110, 2, 1 ), "headshot in a multikill adds headshot and metre points" );
Check( scoring.Record( a, 6, false, 39.37f ) == new SndReplayScore( 3110, 3, 1 ), "kill exactly six seconds old remains in the window" );
Check( scoring.Record( b, 6, false, 0 ) == new SndReplayScore( 1000, 1, 0 ), "attackers have independent streaks" );
Check( scoring.Record( a, 6.001, false, 0 ) == new SndReplayScore( 3110, 3, 1 ), "kill older than six seconds expires" );
Check( scoring.Record( a, 12.002, false, 0 ) == new SndReplayScore( 1000, 1, 0 ), "expired headshots and distances cannot carry to a new streak" );

scoring.Reset();
var farShot = scoring.Record( a, 100, false, float.MaxValue );
var headshot = scoring.Record( b, 100, true, 0 );
Check( farShot == new SndReplayScore( 1099, 1, 0 ), "extreme finite distance is capped without integer overflow" );
Check( headshot.Value > farShot.Value, "a headshot outranks the longest body-shot tiebreaker" );
Check( scoring.Record( c, 100, false, 19.685f ).Value == 1000, "fractional metre does not become a full distance point" );
Check( scoring.Record( a, 101, false, 3937f ) == new SndReplayScore( 2099, 2, 0 ), "distance tiebreaker uses the longest shot and does not accumulate" );

scoring.Reset();
Check( scoring.Record( a, 10, false, 0 ) == new SndReplayScore( 1000, 1, 0 ), "reset permits a fresh earlier timeline" );
Check( scoring.Record( a, 8, true, 0 ) == new SndReplayScore( 2100, 2, 1 ), "out-of-order kill within the current window is counted" );
Check( scoring.Record( a, 4, false, 0 ) == new SndReplayScore( 3100, 3, 1 ), "out-of-order kill on the boundary is counted" );
Check( scoring.Record( a, 3.999, true, 3937f ) == new SndReplayScore( 3100, 3, 1 ), "late kill outside the window cannot resurrect an expired event" );
Check( scoring.Record( a, 16.001, false, 0 ) == new SndReplayScore( 1000, 1, 0 ), "all out-of-order history expires against the newest time" );
Check( scoring.Record( a, 16.001, true, 0 ) == new SndReplayScore( 2100, 2, 1 ), "simultaneous valid kills remain distinct" );

scoring.Reset();
foreach ( var time in new[] { double.NaN, double.PositiveInfinity, double.NegativeInfinity } )
	Check( scoring.Record( a, time, true, 3937f ) == default, $"nonfinite time {time} is ignored" );
Check( scoring.Record( Guid.Empty, 99, true, 3937f ) == default, "empty attacker identity is ignored" );
Check( scoring.Record( a, 1, false, 0 ) == new SndReplayScore( 1000, 1, 0 ), "invalid events do not advance or populate scoring history" );

foreach ( var distance in new[] { float.NaN, float.PositiveInfinity, float.NegativeInfinity, -1f } )
{
	scoring.Reset();
	Check( scoring.Record( a, 1, true, distance ) == new SndReplayScore( 1100, 1, 1 ), $"invalid distance {distance} contributes no tiebreaker" );
}

scoring.Reset();
scoring.Record( a, double.MinValue, false, 0 );
Check( scoring.Record( a, double.MaxValue, true, 0 ) == new SndReplayScore( 1100, 1, 1 ), "extreme finite time range safely expires old history" );

Console.WriteLine( $"PASS: {checks} S&D replay policy checks (authenticated vote identities, majority changes, replay generations, rolling multikills, headshot priority, invalid and out-of-order inputs)." );
