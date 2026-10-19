namespace Facepunch;

/// <summary>
/// One of the radar's icons (<see cref="Minimap"/>). The radar only rebuilds when the set of markers changes, so each icon
/// moves and turns itself every frame, and takes a new picture, tint or layer when its element's change.
/// </summary>
public sealed class MinimapIconMarker : Panel
{
	public Minimap Minimap { get; set; }
	public IMinimapIcon Icon { get; set; }

	private string _iconPath, _customStyle;
	private int _order;
	private bool _styled;
	private Minimap.Placement _placement;

	public override void Tick()
	{
		if ( Minimap is null || !Icon.IsValid() || !Minimap.Renderer.IsValid() )
			return;

		var path = Icon.IconPath;
		var custom = Icon is ICustomMinimapIcon customIcon ? customIcon.CustomStyle : null;
		var order = Icon.IconOrder;
		if ( !_styled || path != _iconPath || custom != _customStyle || order != _order )
		{
			_styled = true;
			_iconPath = path;
			_customStyle = custom;
			_order = order;

			// The style the radar's markup wrote, less the place and turn. A custom style still runs straight into the
			// z-index, as it did there.
			Style.Set( $"background-image: url( {path} ); {custom} z-index: {order};" );
		}

		var yaw = Icon is IDirectionalMinimapIcon { EnableDirectional: true } directional
			? directional.Direction.yaw
			: Minimap.FixedMode ? 0f : Minimap.ViewYaw;
		_placement.Apply( this, Minimap.MapPercent( Icon.WorldPosition ), Minimap.MapAngle( yaw ) );
	}
}

/// <summary> One of the radar's labels (<see cref="Minimap"/>), which moves itself every frame. Its text and colour are the radar's markup. </summary>
public sealed class MinimapLabelMarker : Panel
{
	public Minimap Minimap { get; set; }
	public IMinimapLabel Label { get; set; }

	private Minimap.Placement _placement;

	public override void Tick()
	{
		if ( Minimap is null || !Label.IsValid() || !Minimap.Renderer.IsValid() )
			return;

		_placement.Apply( this, Minimap.MapPercent( Label.WorldPosition ), null );
	}
}
