using System.Data.SqlTypes;
using Sandbox.Events;
using Sandbox;
using Facepunch;

namespace Tec;

public class Interactable : Component, IUse
{
	[RequireComponent]
	public Collider Collider { get; set; }

	[Property]
	public bool CanInteract { get; protected set; } = true;

	[Property]
	private GrabAction GrabAction { get; set; } = GrabAction.None;
	
	[Property]
	public Action OnInteract { get; set; }
	
	public GrabAction GetGrabAction()
	{
		return GrabAction;
	}

	public UseResult CanUse( PlayerPawn player )
	{
		return CanInteract;
	}

	public void OnUse( PlayerPawn player )
	{
		OnInteract?.Invoke();
	}
}
