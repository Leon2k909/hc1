namespace Facepunch.UI;

public partial class MarkerSystem : Panel
{
	private const float RefreshInterval = 0.1f;
	private readonly List<IMarkerObject> _deleteList = new();
	private TimeSince _timeSinceRefresh;
	private ViewModelMask _gunMask;
	private Texture _maskImage;
	private bool _scopeWasActive;

	public Dictionary<IMarkerObject, Marker> ActiveMarkers { get; set; } = new();

	/// <summary>Draw inside ScopeOverlay's clipped lens, using its camera and no viewmodel mask.</summary>
	public bool ScopeView { get; set; }

	public CameraComponent ProjectionCamera => ScopeView ? OpticZoom.LensCamera
		: Client.Viewer?.PlayerPawn?.CameraController?.Camera ?? Scene?.Camera;

	void Refresh()
	{
		if ( Scene is null ) return;

		// A lowered or unmagnified optic doesn't need a second scan of the scene's markers.
		if ( ScopeView && (!ProjectionCamera.IsValid() || OpticZoom.LensTexture is null || OpticZoom.LensVisibility <= 0f) )
		{
			foreach ( var marker in ActiveMarkers.Values ) marker.Delete();
			ActiveMarkers.Clear();
			return;
		}

		_deleteList.Clear();
		_deleteList.AddRange( ActiveMarkers.Keys );

		foreach ( var markerObject in Scene.GetAllComponents<IMarkerObject>() )
		{
			if ( UpdateMarker( markerObject ) )
			{
				_deleteList.Remove( markerObject );
			}
		}

		foreach ( var marker in _deleteList )
		{
			ActiveMarkers[marker].Delete();
			ActiveMarkers.Remove( marker );
		}
	}

	public Marker CreateMarker( IMarkerObject marker )
	{
		var inst = new Marker()
		{
			Object = marker,
		};
		AddChild( inst );
		return inst;
	}

	public bool UpdateMarker( IMarkerObject marker )
	{
		if ( !marker.GameObject.IsValid() )
			return false;

		if ( !marker.ShouldShow() )
			return false;

		var camera = ProjectionCamera;
		if ( !camera.IsValid() )
			return false;

		if ( ScopeView && (OpticZoom.LensTexture is null || OpticZoom.LensVisibility <= 0f) )
			return false;

		if ( marker.MarkerMaxDistance != 0f && camera.WorldPosition.DistanceSquared( marker.MarkerPosition ) > marker.MarkerMaxDistance * marker.MarkerMaxDistance )
			return false;

		if ( !ActiveMarkers.TryGetValue( marker, out var instance ) )
		{
			instance = CreateMarker( marker );
			if ( instance.IsValid() )
			{
				ActiveMarkers[marker] = instance;
			}
		}

		instance.Reposition();

		return true;
	}

	/// <summary>
	/// The first-person gun draws over the markers: they're masked out wherever it covers the view.
	/// </summary>
	void UpdateGunMask()
	{
		// The scope picture has no gun in it. The enclosing lens clips its markers to the glass.
		if ( ScopeView )
		{
			_gunMask?.Update( null );
			if ( _maskImage is not null )
			{
				_maskImage = null;
				Style.MaskImage = null;
			}
			return;
		}

		// Made here, not in an initialiser: a hotload leaves a new field on an existing panel null.
		_gunMask ??= new ViewModelMask();

		// Only while there are markers to hide, since the mask draws the viewmodel a second time.
		_gunMask.Update( ActiveMarkers.Count > 0 ? Scene : null );

		var texture = _gunMask.Texture;
		if ( texture == _maskImage )
			return;

		_maskImage = texture;
		Style.MaskImage = texture;

		if ( texture is null )
			return;

		Style.MaskMode = MaskMode.Luminance;
		Style.MaskSizeX = Length.Percent( 100 );
		Style.MaskSizeY = Length.Percent( 100 );
		Style.MaskRepeat = BackgroundRepeat.Clamp;
	}

	public override void OnDeleted()
	{
		base.OnDeleted();

		_gunMask?.Dispose();
	}

	public override void Tick()
	{
		var scopeActive = ScopeView && ProjectionCamera.IsValid() && OpticZoom.LensTexture is not null && OpticZoom.LensVisibility > 0f;
		if ( scopeActive != _scopeWasActive )
		{
			_scopeWasActive = scopeActive;
			_timeSinceRefresh = RefreshInterval;
		}

		UpdateGunMask();

		foreach ( var pair in ActiveMarkers )
		{
			if ( pair.Value.IsValid() )
			{
				pair.Value.Reposition();
			}
		}

		if ( _timeSinceRefresh < RefreshInterval )
			return;

		_timeSinceRefresh = 0f;
		Refresh();
	}
}
