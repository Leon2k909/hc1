namespace Facepunch;

/// <summary>
/// Quiet friendly identification. The engine depth-tests each highlighted pixel:
/// visible skin/clothing stays untouched, including limbs peeking around cover.
/// </summary>
internal static class TeammateOcclusionGlow
{
	private static Material _material;
	internal const float EdgeOpacity = 0.18f;
	internal const float FillOpacity = 0.07f;
	internal const float OutlineWidth = 0.03f;

	internal static bool IsTeammate( Team team )
	{
		if ( team == Team.Unassigned || GameUtils.IsFreeForAllMode )
			return false;

		var viewer = Client.Viewer;
		if ( !viewer.IsValid() || !viewer.PlayerPawn.IsValid() )
			return false;

		var pawn = viewer.PlayerPawn;
		return pawn.Team == team && pawn.HealthComponent.IsValid()
			&& pawn.HealthComponent.State == LifeState.Alive;
	}

	internal static void Apply( HighlightOutline outline, Color color )
	{
		outline.Material = _material ??= Material.FromShader( "shaders/hc1_teammate_occlusion.shader" );
		outline.Width = OutlineWidth;
		outline.Color = Color.Transparent;
		outline.InsideColor = Color.Transparent;
		outline.ObscuredColor = color.WithAlpha( EdgeOpacity );
		outline.InsideObscuredColor = color.WithAlpha( FillOpacity );
	}
}
