using Sandbox.Audio;

namespace Facepunch;

/// <summary>
/// The kill-confirm sound: a short thwack when the player you're viewing kills an enemy, with a bright ping on top for a
/// headshot (sounds/ui/kill, made by Tools/kill_sounds.py). Kills in quick succession climb in pitch, a tone, a third,
/// then a fifth, in step with the double, triple and fury kill medals. It's a UI sound, so the UI volume sets it.
/// </summary>
public static class KillSounds
{
	private const string KillSound = "sounds/ui/kill/kill_confirm.sound";
	private const string HeadshotSound = "sounds/ui/kill/kill_confirm_headshot.sound";

	/// <summary> How soon the next kill has to come to climb a step: the medals' rapid-kill window (MedalFeed). </summary>
	private const float StreakWindow = 3f;

	/// <summary> Semitones for the first, second, third and later kills in quick succession. </summary>
	private static readonly float[] Steps = { 0f, 2f, 4f, 7f };

	private static RealTimeSince _sinceLastKill = StreakWindow;
	private static int _streak;

	/// <summary>
	/// Every machine gets every <see cref="KillEvent"/>, so this only plays for an enemy player or bot killed by the player
	/// being viewed, not a teammate or themselves. Their own death starts the climb again.
	/// </summary>
	public static void OnKill( KillEvent eventArgs )
	{
		var info = eventArgs.DamageInfo;
		var viewer = Client.Viewer.IsValid() ? Client.Viewer.Pawn as PlayerPawn : null;
		if ( !viewer.IsValid() )
			return;

		var victim = GameUtils.GetPlayerFromComponent( info.Victim );
		if ( victim == viewer )
		{
			_streak = 0;
			return;
		}

		if ( GameUtils.GetPlayerFromComponent( info.Attacker ) != viewer )
			return;

		if ( !victim.IsValid() && !GameUtils.GetLightweightBotFromComponent( info.Victim ).IsValid() )
			return;

		var team = GameUtils.GetTeamFromComponent( info.Attacker );
		if ( team != Team.Unassigned && team == GameUtils.GetTeamFromComponent( info.Victim ) )
			return;

		_streak = _sinceLastKill <= StreakWindow ? _streak + 1 : 1;
		_sinceLastKill = 0;

		Play( info.Hitbox.HasFlag( HitboxTags.Head ), _streak );
	}

	/// <summary>
	/// A zombie killed by the player being viewed (<see cref="ZombieAI"/>: zombies raise no KillEvent). It doesn't climb:
	/// Zombies has no multikill medals, and in a wave nearly every kill would be at the top.
	/// </summary>
	public static void OnZombieKill( bool headshot ) => Play( headshot, 1 );

	private static void Play( bool headshot, int streak )
	{
		var sound = Sound.Play( headshot ? HeadshotSound : KillSound );
		if ( !sound.IsValid() )
			return;

		sound.TargetMixer = Mixer.FindMixerByName( "UI" );
		sound.Pitch = MathF.Pow( 2f, Steps[Math.Clamp( streak - 1, 0, Steps.Length - 1 )] / 12f );
	}
}
