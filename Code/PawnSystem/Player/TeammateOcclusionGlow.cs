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

	private static Material GlowMaterial => _material ??= Material.FromShader( "shaders/hc1_teammate_occlusion.shader" );

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

	// When a teammate's glow was last set up. The first-person gun only needs its shield while one is.
	private static float _lastApplied = float.NegativeInfinity;

	internal static void Apply( HighlightOutline outline, Color color )
	{
		_lastApplied = RealTime.Now;
		outline.Material = GlowMaterial;
		outline.Width = OutlineWidth;
		outline.Color = Color.Transparent;
		outline.InsideColor = Color.Transparent;
		outline.ObscuredColor = color.WithAlpha( EdgeOpacity );
		outline.InsideObscuredColor = color.WithAlpha( FillOpacity );
	}

	/// <summary>
	/// The first-person gun and arms are drawn in the overlay layer, whose depth the glow reads as cover, so a teammate
	/// behind your own gun lit up over it. An invisible outline on the viewer's gun puts it in the glow's own depth
	/// buffer, in front of the teammate, so nothing is drawn there. Its geometry is the whole model, so a red dot's
	/// window blocks the glow too.
	/// </summary>
	internal static void UpdateShield( ViewModel viewModel, ref HighlightOutline shield )
	{
		var show = RealTime.Now - _lastApplied < 0.25f
			&& viewModel == Client.Viewer?.PlayerPawn?.CurrentEquipment?.ViewModel;

		if ( !show )
		{
			if ( shield.IsValid() )
				shield.Enabled = false;
			return;
		}

		if ( !shield.IsValid() )
		{
			shield = viewModel.Components.Create<HighlightOutline>();
			shield.Flags |= ComponentFlags.NotSaved | ComponentFlags.NotNetworked;
			shield.OverrideTargets = true;
			shield.Targets = new();
		}

		shield.Material = GlowMaterial;
		shield.Width = 0f;
		shield.Color = Color.Transparent;
		shield.ObscuredColor = Color.Transparent;
		shield.InsideColor = Color.Transparent;
		shield.InsideObscuredColor = Color.Transparent;

		// What the camera draws of the gun: as ViewModelMask picks it.
		var excluded = (ITagSet)(Game.ActiveScene?.Camera?.RenderExcludeTags);
		shield.Targets.Clear();
		foreach ( var renderer in viewModel.GameObject.Components.GetAll<ModelRenderer>( FindMode.EnabledInSelfAndDescendants ) )
		{
			if ( renderer.RenderType == ModelRenderer.ShadowRenderType.ShadowsOnly ) continue;
			if ( !renderer.SceneObject.IsValid() || !renderer.SceneObject.RenderingEnabled ) continue;
			if ( excluded is not null && renderer.GameObject.Tags.HasAny( excluded ) ) continue;
			shield.Targets.Add( renderer );
		}

		shield.Enabled = shield.Targets.Count > 0;
	}
}
