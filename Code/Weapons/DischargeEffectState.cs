namespace Facepunch;

/// <summary>Owner-side cosmetic choices shared by both weapon systems.</summary>
internal sealed class DischargeEffectState
{
	// Keep cosmetic randomness separate from bullet spread and recoil.
	private readonly Random _random = new();
	private TimeSince _timeSinceDischarge = 999f;
	private TimeSince _timeSinceSmoke = 999f;
	private float _heat;

	private float RemainingHeat => MathF.Max( 0f, _heat - (float)_timeSinceDischarge * 0.12f );
	private float RandomRange( float min, float max ) => min + (float)_random.NextDouble() * (max - min);

	public (bool Flash, float FlashScale, float SmokeScale) Shoot( float flashChance, float flashScale, float smokeScale, bool suppressed )
	{
		_heat = MathF.Min( 1f, RemainingHeat + 0.16f );
		_timeSinceDischarge = 0f;

		bool flash = RandomRange( 0f, 1f ) < flashChance.Clamp( 0f, 1f );
		flashScale *= RandomRange( 0.8f, 1.15f );

		// Smoke can appear without a flash, but cannot accumulate on every automatic shot.
		var smokeChance = 0.12f + _heat * 0.25f + (suppressed ? 0.1f : 0f);
		if ( smokeScale > 0f && _timeSinceSmoke >= 0.3f && RandomRange( 0f, 1f ) < smokeChance )
		{
			smokeScale *= RandomRange( 0.55f, 0.8f ) * (0.75f + _heat * 0.35f);
			_timeSinceSmoke = 0f;
		}
		else
		{
			smokeScale = 0f;
		}

		return (flash, flashScale, smokeScale);
	}

	public float ReloadSmoke( float scale )
	{
		var heat = RemainingHeat;
		if ( scale <= 0f || _timeSinceDischarge > 4f || heat < 0.12f || _timeSinceSmoke < 0.3f
			|| RandomRange( 0f, 1f ) >= 0.2f + heat * 0.5f )
			return 0f;

		_timeSinceSmoke = 0f;
		return scale * RandomRange( 0.55f, 0.85f ) * (0.7f + heat * 0.4f);
	}
}
