using Facepunch;
using System.Text.Json;

var checks = 0;
void Check( bool condition, string description )
{
    if ( !condition ) throw new Exception( description );
    checks++;
}

var season = Rank.GetSeason();
var state = new Rank.RankState { Season = season };
Check( !Rank.IsPlaced && Rank.GetRankName() == "Unranked" && Rank.GetTierIndex() == -1, "New profiles must be Unranked" );
Check( Rank.MatchTag() == "[R:UNRANKED]", "Placements must have a separate queue" );
for ( var i = 0; i < 4; i++ )
{
    state = Rank.ApplyResult( state, $"placement-{i}", true, false, 0.5f, season );
    Check( !state.IsPlaced && state.ProgressUnits == 0, "A rank must stay hidden until the fifth match" );
}
var repeated = Rank.ApplyResult( state, "placement-3", true, false, 1f, season );
Check( repeated == state, "Duplicate completion must not count another placement" );
state = Rank.ApplyResult( state, "placement-4", true, false, 0.5f, season );
Check( state.IsPlaced && state.Placements == 5 && Rank.GetTierIndex( state.ProgressUnits ) > 0, "Five strong results must assign a rank above Bronze" );

Rank.RankState Place( bool won, float contribution )
{
    var result = new Rank.RankState { Season = season };
    for ( var i = 0; i < 5; i++ ) result = Rank.ApplyResult( result, $"{won}-{contribution}-{i}", won, false, contribution, season );
    return result;
}
Check( Place( false, 0 ).ProgressUnits < Place( true, 0 ).ProgressUnits, "Placement results must affect the assigned rank" );
Check( Place( true, 0 ).ProgressUnits < Place( true, 1 ).ProgressUnits, "Contribution must affect the assigned rank" );
Check( Rank.GetRankName( Place( false, 0 ).ProgressUnits ) == "Bronze III", "Lowest placement result must be Bronze III" );
Check( Rank.GetRankName( Place( true, 1 ).ProgressUnits ) == "Platinum I", "Placements must not grant the top ranks" );

var beforePromotion = state with { ProgressUnits = 2950, SeasonHighUnits = 2950 };
var promoted = Rank.ApplyResult( beforePromotion, "promotion", true, false, 0.5f, season );
Check( Rank.GetRankName( promoted.ProgressUnits ) == "Silver III" && promoted.ProgressUnits % 1000 == 75, "Promotion must carry excess progress into the next rank" );
var demoted = Rank.ApplyResult( promoted, "demotion", false, false, 0.5f, season );
Check( Rank.GetRankName( demoted.ProgressUnits ) == "Bronze I" && demoted.ProgressUnits % 1000 == 975, "A loss at the boundary must demote with the correct percentage" );
Check( demoted.SeasonHighUnits == promoted.ProgressUnits, "Demotion must preserve the season high" );
var draw = Rank.ApplyResult( demoted, "draw", false, true, 1f, season );
Check( draw.ProgressUnits == demoted.ProgressUnits, "Placed draws must not remove progress" );
var placementDraw = Rank.ApplyResult( new() { Season = season }, "placement-draw", false, true, 0.5f, season );
Check( placementDraw.Placements == 1 && Math.Abs( placementDraw.PlacementScore - 0.5f ) < 0.0001f, "Draw placements must count once and split the outcome credit" );
Check( Rank.ApplyResult( state with { ProgressUnits = 0 }, "floor", false, false, 0f, season ).ProgressUnits == 0, "Losses must stop at the bottom rank" );
Check( Rank.ApplyResult( state with { ProgressUnits = 14950 }, "master", true, false, 1f, season ).ProgressUnits == 15000, "Master must cap at 100%" );
var reset = Rank.ForSeason( state, season + 1 );
Check( !reset.IsPlaced && reset.Placements == 0 && reset.SeasonHighUnits == 0, "New seasons must require placements" );
Check( Rank.ApplyResult( state, state.LastMatchId, true, false, 1f, season + 1 ) == state, "A stale duplicate must not count toward a new season" );
Check( Rank.GetSeason( new DateTime( 2026, 12, 1 ) ) == 2, "Season rollover date" );

Game.Cookies.Set( "razed.rank.placements.v1", JsonSerializer.Serialize( promoted ) );
Check( Rank.IsPlaced && Rank.GetRankName() == "Silver III" && Math.Abs( Rank.GetDivisionProgress() - 0.075f ) < 0.0001f, "Saved state must restore the rank and percentage" );
Check( Rank.MatchTag() == "[R:SILVER]", "Placed matchmaking must follow the assigned tier" );
Rank.RecordResult( "persisted-result", false, false, 0.5f );
var saved = JsonSerializer.Deserialize<Rank.RankState>( Game.Cookies.Get<string>( "razed.rank.placements.v1", "" ) );
Check( saved.LastMatchId == "persisted-result" && saved.ProgressUnits == demoted.ProgressUnits, "The result and duplicate guard must persist together" );

Console.WriteLine( $"PASS: {checks} ranked placement, progression and persistence checks." );

// Only persistence is stubbed; the checks above compile and exercise the game's actual Rank.cs.
namespace Facepunch
{
    internal static class Game
    {
        internal static readonly CookieStore Cookies = new();
    }
    internal sealed class CookieStore
    {
        private readonly Dictionary<string, object> values = new();
        public T Get<T>( string key, T fallback ) => values.TryGetValue( key, out var value ) ? (T)value : fallback;
        public void Set<T>( string key, T value ) => values[key] = value;
    }
}
