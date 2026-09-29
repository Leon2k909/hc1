namespace Facepunch;

public static partial class GameText
{
	private static TextTable OperatorsText => new()
	{
		["OPERATORS"] = ("OPÉRATEURS", "OPERATOR", "OPERADORES", "OPERADORES"),
		["OUTFITS"] = ("TENUES", "AUSRÜSTUNGEN", "ATUENDOS", "TRAJES"),
		["Inspect the outfits used in game."] = ("Examinez les tenues utilisées en jeu.", "Sieh dir die Ausrüstungen im Spiel an.", "Examina los atuendos que se usan en el juego.", "Veja os trajes usados no jogo."),
		["Military Operator"] = ("Opérateur militaire", "Militärischer Operator", "Operador militar", "Operador militar"),
		["Field Operator"] = ("Opérateur de terrain", "Feldoperator", "Operador de campo", "Operador de campo"),
		["FIELD KIT"] = ("ÉQUIPEMENT", "FELDAUSRÜSTUNG", "EQUIPO", "EQUIPAMENTO"),
		["Camouflage fatigues, tactical vest, combat helmet, headset and boots."] = ("Treillis camouflé, gilet tactique, casque de combat, casque radio et bottes.", "Tarnuniform, taktische Weste, Gefechtshelm, Headset und Stiefel.", "Uniforme de camuflaje, chaleco táctico, casco de combate, auriculares y botas.", "Uniforme camuflado, colete tático, capacete de combate, headset e botas."),
		["Camouflage fatigues, olive tactical vest, combat helmet, gloves and boots."] = ("Treillis camouflé, gilet tactique olive, casque de combat, gants et bottes.", "Tarnuniform, olivgrüne taktische Weste, Gefechtshelm, Handschuhe und Stiefel.", "Uniforme de camuflaje, chaleco táctico verde oliva, casco de combate, guantes y botas.", "Uniforme camuflado, colete tático verde-oliva, capacete de combate, luvas e botas."),
		["Outfits are assigned by team."] = ("Les tenues sont attribuées selon l'équipe.", "Die Ausrüstung wird vom Team bestimmt.", "Los atuendos se asignan según el equipo.", "Os trajes são definidos pela equipe."),
		["3D PREVIEW"] = ("APERÇU 3D", "3D-VORSCHAU", "VISTA PREVIA 3D", "PRÉVIA 3D"),
		["Outfit preview unavailable."] = ("Aperçu de la tenue indisponible.", "Ausrüstungsvorschau nicht verfügbar.", "Vista previa del atuendo no disponible.", "Prévia do traje indisponível."),
		["Drag to rotate · Scroll to zoom"] = ("Glisser pour tourner · Molette pour zoomer", "Ziehen zum Drehen · Scrollen zum Zoomen", "Arrastra para girar · Rueda para acercar", "Arraste para girar · Role para ampliar"),
		["Rotate left"] = ("Tourner à gauche", "Nach links drehen", "Girar a la izquierda", "Girar à esquerda"),
		["Rotate right"] = ("Tourner à droite", "Nach rechts drehen", "Girar a la derecha", "Girar à direita"),
		["Zoom out"] = ("Dézoomer", "Verkleinern", "Alejar", "Reduzir zoom"),
		["Zoom in"] = ("Zoomer", "Vergrößern", "Acercar", "Ampliar zoom"),
		["Reset view"] = ("Réinitialiser la vue", "Ansicht zurücksetzen", "Restablecer vista", "Redefinir visualização")
	};
}
