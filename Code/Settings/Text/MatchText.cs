namespace Facepunch;

public static partial class GameText
{
	/// <summary> A match's flow: class select, scoreboard, round state, kill feed, medals, toasts, deaths, spectating, end of match and the map vote. </summary>
	private static TextTable MatchText => new()
	{
		// The team win banner (Toast): {0} is the team's name, and the words after it are the coloured accent.
		["{0} Wins!"] = ("L'{0} gagne !", "{0} gewinnt!", "¡El {0} gana!", "A {0} vence!"),

		// Toasts from the game modes (ShowToast in prefabs/game_modes, RoundLimit, EarlyWinCondition, spawning)
		["Preparing to start..."] = ("Préparation du lancement...", "Start wird vorbereitet...", "Preparando el inicio...", "Preparando o início..."),
		["Scores are Tied!"] = ("Scores à égalité !", "Punktgleichstand!", "¡Empate en el marcador!", "Placar empatado!"),
		["Preparing to swap teams"] = ("Changement de camp imminent", "Seitenwechsel wird vorbereitet", "Preparando el cambio de bando", "Preparando a troca de lados"),
		["Final round"] = ("Dernière manche", "Letzte Runde", "Última ronda", "Última rodada"),
		["Final round of the first half"] = (
			"Dernière manche de la première mi-temps",
			"Letzte Runde der ersten Halbzeit",
			"Última ronda de la primera mitad",
			"Última rodada do primeiro tempo" ),
		["Match Point"] = ("Balle de match", "Matchball", "Punto de partido", "Ponto decisivo"),
		["Respawning..."] = ("Réapparition...", "Respawn...", "Reapareciendo...", "Renascendo..."),
		["Spawn Protected"] = ("Protection d'apparition active", "Spawnschutz aktiv", "Protección de aparición activa", "Proteção de renascimento ativa"),
		["The game is over - returning to menu"] = (
			"La partie est terminée - retour au menu",
			"Das Spiel ist vorbei - zurück zum Menü",
			"La partida ha terminado - volviendo al menú",
			"A partida acabou - voltando ao menu" ),
		["Last One Standing Wins"] = ("Le dernier survivant l'emporte", "Wer als Letzter steht, gewinnt", "Gana el último en pie", "O último sobrevivente vence"),
		["Gun Game starting..."] = ("Le Jeu d'armes commence...", "Waffenspiel startet...", "El Juego de armas va a empezar...", "O Jogo de Armas vai começar..."),
		["Prepare for cash point"] = ("Préparez-vous pour le point d'argent", "Mach dich bereit für den Geldpunkt", "Prepárate para el punto de dinero", "Prepare-se para o ponto de dinheiro"),
		["The cash point is open"] = ("Le point d'argent est ouvert", "Der Geldpunkt ist offen", "El punto de dinero está abierto", "O ponto de dinheiro está aberto"),
		["The cash was grabbed"] = ("L'argent a été récupéré", "Das Geld wurde geschnappt", "Se han llevado el dinero", "O dinheiro foi pego"),
		["The Cash Was Extracted"] = ("L'argent a été extrait", "Das Geld wurde extrahiert", "Se ha extraído el dinero", "O dinheiro foi extraído"),

		// Toasts from Domination, Hot Zone and Gun Game: {0} and {1} are a team's name, a flag's letter, a player or a weapon
		["{0} Neutralized!"] = ("Drapeau {0} neutralisé !", "Flagge {0} neutralisiert!", "¡Bandera {0} neutralizada!", "Bandeira {0} neutralizada!"),
		["{0} Captured {1}!"] = ("L'{0} a capturé le drapeau {1} !", "{0} hat Flagge {1} erobert!", "¡El {0} ha capturado la bandera {1}!", "A {0} capturou a bandeira {1}!"),
		["Zone secured by {0}!"] = (
			"Zone sécurisée par l'{0} !",
			"Zone von {0} gesichert!",
			"¡Zona asegurada por el {0}!",
			"Zona capturada pela {0}!" ),
		["The zone has moved!"] = (
			"La zone s'est déplacée !",
			"Die Zone hat sich verlagert!",
			"¡La zona se ha movido!",
			"A zona mudou de lugar!" ),
		["{0} → {1} (Tier {2}/{3})"] = ("{0} → {1} (palier {2}/{3})", "{0} → {1} (Stufe {2}/{3})", "{0} → {1} (nivel {2}/{3})", "{0} → {1} (nível {2}/{3})"),
		["{0} was demoted to {1}"] = ("Rétrogradation de {0} : {1}", "{0} wurde auf {1} zurückgestuft", "{0} ha retrocedido a {1}", "{0} voltou para {1}"),
		["🏆 {0} won Gun Game!"] = (
			"🏆 {0} remporte le Jeu d'armes !",
			"🏆 {0} hat das Waffenspiel gewonnen!",
			"🏆 ¡{0} ha ganado el Juego de armas!",
			"🏆 {0} venceu o Jogo de Armas!" ),

		// Toasts: why something can't be used (IUse.CanUse; the Zombies ones are in HudText) and a class picked mid-life
		["Can't pick this up"] = ("Impossible de ramasser cet objet", "Kann nicht aufgehoben werden", "No puedes recoger esto", "Não é possível pegar isto"),
		["{0} will be equipped on your next spawn"] = (
			"La classe {0} sera équipée à votre prochaine apparition",
			"Klasse {0} wird bei deinem nächsten Respawn ausgerüstet",
			"La clase {0} se equipará en tu próxima reaparición",
			"A classe {0} será equipada no seu próximo renascimento" ),

		// The match's status (ShowStatusText in the game modes), after the mode's name on the scoreboard. "Paused", "Match
		// Over", "Game Over", "Extract" and "Dropping In" are in PageText and HudText.
		["Waiting"] = ("En attente", "Warten", "Esperando", "Aguardando"),
		["Starting"] = ("Démarrage", "Startet", "Empezando", "Iniciando"),
		["Prepare"] = ("Préparez-vous", "Mach dich bereit", "Prepárate", "Prepare-se"),
		["In Progress"] = ("En cours", "Läuft", "En curso", "Em andamento"),
		["Round Over"] = ("Fin de la manche", "Runde vorbei", "Fin de la ronda", "Fim da rodada"),
		["Half Time"] = ("Mi-temps", "Halbzeit", "Descanso", "Intervalo"),
		["Plant the Bomb"] = ("Posez la bombe", "Platziere die Bombe", "Planta la bomba", "Plante a bomba"),
		["Defend"] = ("Défendez", "Verteidige", "Defiende", "Defenda"),
		["Get the cash"] = ("Récupérez l'argent", "Hol dir das Geld", "Consigue el dinero", "Pegue o dinheiro"),
		["Open in.."] = ("Ouverture dans..", "Öffnet in..", "Se abre en..", "Abre em.."),
		["Incoming.."] = ("En approche..", "Im Anflug..", "En camino..", "A caminho.."),
		["Failure.."] = ("Échec..", "Gescheitert..", "Fracaso..", "Falha.."),

		// Class select (ClassSelect). "CHOOSE CLASS", the weapon slots, "Perk {0}" and the perks are in SettingsText,
		// GunsmithText and PageText.
		["EDIT CLASS"] = ("Modifier la classe", "Klasse bearbeiten", "Editar clase", "Editar classe"),
		["Equip class"] = ("Équiper la classe", "Klasse ausrüsten", "Equipar clase", "Equipar classe"),
		["No secondary weapon"] = ("Aucune arme secondaire", "Keine Sekundärwaffe", "Sin arma secundaria", "Sem arma secundária"),
		["Use the mode's default"] = (
			"Utiliser l'équipement par défaut du mode",
			"Standardausrüstung des Modus verwenden",
			"Usar el equipo predeterminado del modo",
			"Usar o equipamento padrão do modo" ),
		["Pick a weapon, piece of equipment or perk on the right to change it."] = (
			"Choisissez à droite ce que vous voulez modifier : une arme, un équipement ou un atout.",
			"Wähle rechts, was du ändern willst: eine Waffe, Ausrüstung oder ein Extra.",
			"Elige a la derecha lo que quieras cambiar: un arma, un equipo o una ventaja.",
			"Escolha à direita o que quer mudar: uma arma, um equipamento ou uma vantagem." ),
		["Attachments and camos are changed in the gunsmith."] = (
			"Les accessoires et les camouflages se modifient dans l'Armurier.",
			"Aufsätze und Tarnungen änderst du im Büchsenmacher.",
			"Los accesorios y camuflajes se cambian en el Armero.",
			"Acessórios e camuflagens são alterados no Armeiro." ),

		// Scoreboard (Scoreboard, ScoreboardRow); Balance and Ratio are columns (ScoreAttribute)
		["Round {0} of {1}"] = ("Manche {0} sur {1}", "Runde {0} von {1}", "Ronda {0} de {1}", "Rodada {0} de {1}"),
		["Voice Channel:"] = ("Canal vocal :", "Sprachkanal:", "Canal de voz:", "Canal de voz:"),
		["Auto"] = ("Auto", "Auto", "Auto", "Auto"),
		["Lobby"] = ("Salon", "Lobby", "Sala", "Sala"),
		["Prox Chat"] = ("Proximité", "Umgebung", "Proximidad", "Proximidade"),
		["Add Bot"] = ("Ajouter un bot", "Bot hinzufügen", "Añadir bot", "Adicionar bot"),
		["Kick bot"] = ("Expulser le bot", "Bot entfernen", "Expulsar bot", "Expulsar bot"),
		["AI"] = ("IA", "KI", "IA", "IA"),
		["Balance"] = ("Argent", "Geld", "Dinero", "Dinheiro"),
		["Ratio"] = ("Ratio", "Quote", "Ratio", "Razão"),

		// The score feed (PlayerScore.AddScore reasons; zombie kills through ZombiesPlayerEconomy.AddPoints) and medals (MedalFeed)
		["Killed a player"] = ("Joueur éliminé", "Spieler ausgeschaltet", "Jugador abatido", "Jogador abatido"),
		["Killed a zombie"] = ("Zombie éliminé", "Zombie ausgeschaltet", "Zombi abatido", "Zumbi abatido"),
		["Planted the bomb"] = ("Bombe posée", "Bombe gelegt", "Bomba plantada", "Bomba plantada"),
		["Defused the bomb"] = ("Bombe désamorcée", "Bombe entschärft", "Bomba desactivada", "Bomba desarmada"),
		["Team defused the bomb"] = ("Votre équipe a désamorcé la bombe", "Dein Team hat die Bombe entschärft", "Tu equipo ha desactivado la bomba", "Sua equipe desarmou a bomba"),
		["Bomb exploded"] = ("La bombe a explosé", "Bombe explodiert", "La bomba ha explotado", "A bomba explodiu"),
		["UAV Deployed"] = ("Drone déployé", "Drohne gestartet", "VANT desplegado", "VANT acionado"),
		["DOUBLE KILL"] = ("Double élimination", "Doppelabschuss", "Baja doble", "Abate duplo"),
		["TRIPLE KILL"] = ("Triple élimination", "Dreifachabschuss", "Baja triple", "Abate triplo"),
		["FURY KILL"] = ("Élimination furieuse", "Wutabschuss", "Baja furiosa", "Abate furioso"),
		["FRENZY KILL"] = ("Élimination frénétique", "Rasereiabschuss", "Baja frenética", "Abate frenético"),
		["RAPID ELIMINATIONS"] = ("Éliminations rapides", "Schnelle Abschüsse", "Bajas rápidas", "Abates rápidos"),
		["MERCILESS"] = ("Impitoyable", "Gnadenlos", "Despiadado", "Impiedoso"),
		["RUTHLESS"] = ("Sans pitié", "Rücksichtslos", "Implacable", "Implacável"),
		["KILL STREAK"] = ("Série d'éliminations", "Abschussserie", "Racha de bajas", "Sequência de abates"),
		["HEADSHOT"] = ("Tir à la tête", "Kopfschuss", "Disparo a la cabeza", "Tiro na cabeça"),
		["PRECISION KILL"] = ("Élimination de précision", "Präzisionsabschuss", "Baja de precisión", "Abate de precisão"),
		["ONE SHOT, ONE KILL"] = ("Un tir, une élimination", "Ein Schuss, ein Abschuss", "Un disparo, una baja", "Um tiro, um abate"),
		["SINGLE SHOT ELIMINATION"] = ("Élimination en un tir", "Abschuss mit einem Schuss", "Baja de un solo disparo", "Abate com um único tiro"),

		// The kill feed, death screen (Deathcam), spectating and deploying
		["killed"] = ("a tué", "tötete", "mató a", "matou"),
		["KILLED BY"] = ("Tué par", "Getötet von", "Te ha matado", "Morto por"),
		["Zombie"] = ("Zombie", "Zombie", "Zombi", "Zumbi"),
		["Unknown"] = ("Inconnu", "Unbekannt", "Desconocido", "Desconhecido"),
		["Press {0} or {1} to start spectating"] = (
			"Appuyez sur {0} ou {1} pour passer en spectateur",
			"Drücke {0} oder {1}, um zuzuschauen",
			"Pulsa {0} o {1} para pasar a modo espectador",
			"Pressione {0} ou {1} para espectar" ),
		["DAMAGE TAKEN"] = ("Dégâts subis", "Erlittener Schaden", "Daño recibido", "Dano sofrido"),
		["INFLICTED DAMAGE"] = ("Dégâts infligés", "Verursachter Schaden", "Daño infligido", "Dano causado"),
		["{0} damage in {1} hits"] = ("{0} dégâts en {1} coups", "{0} Schaden mit {1} Treffern", "{0} de daño en {1} impactos", "{0} de dano em {1} acertos"),
		["SPECTATING"] = ("Spectateur", "Zuschauen", "Espectador", "Espectando"),
		["Deploying in {0}"] = ("Déploiement dans {0}", "Einsatz in {0}", "Despliegue en {0}", "Entrando em campo em {0}"),
		["Press {0} to deploy"] = ("Appuyez sur {0} pour vous déployer", "Drücke {0} für den Einsatz", "Pulsa {0} para desplegarte", "Pressione {0} para entrar em campo"),

		// End of match (EndOfMatchScreen): "{0} PLACE" is given the English ordinal ("2ND") as {0} and the number as {1}
		["{0} PLACE"] = ("{1}e place", "{1}. Platz", "{1}.º puesto", "{1}º lugar"),
		["WIN BONUS INCLUDED"] = ("Bonus de victoire inclus", "Siegbonus enthalten", "Bonificación por victoria incluida", "Bônus de vitória incluído"),
		["LEVEL UP!"] = ("Niveau supérieur !", "Stufenaufstieg!", "¡Subes de nivel!", "Subiu de nível!"),
		["RANKED RESULT"] = ("Résultat classé", "Gewertetes Ergebnis", "Resultado competitivo", "Resultado ranqueado"),
		["PLACEMENT COMPLETE"] = ("Placement terminé", "Platzierung abgeschlossen", "Posicionamiento completado", "Posicionamento concluído"),
		["{0:0.#}% THROUGH RANK"] = ("Rang accompli à {0:0.#} %", "{0:0.#} % des Rangs geschafft", "{0:0.#} % del rango completado", "{0:0.#}% do ranque concluído"),
		["{0} / {1} PLACEMENT MATCHES"] = ("{0} / {1} matchs de placement", "{0} / {1} Platzierungsspiele", "{0} / {1} partidas de posicionamiento", "{0} / {1} partidas de posicionamento"),
		["RETURNING TO RANKED"] = ("Retour au mode classé", "Zurück zu Gewertet", "Volviendo a competitivo", "Voltando para a ranqueada"),

		// The map vote (MapVoteOverlay, MapVoteCard)
		["Map vote"] = ("Vote de carte", "Kartenabstimmung", "Votación de mapa", "Votação de mapa"),
		["Something went wrong"] = ("Une erreur s'est produite", "Etwas ist schiefgelaufen", "Algo ha salido mal", "Algo deu errado"),
		["Next map"] = ("Carte suivante", "Nächste Karte", "Próximo mapa", "Próximo mapa"),
		["Vote for the next map"] = ("Votez pour la prochaine carte", "Stimme für die nächste Karte ab", "Vota el próximo mapa", "Vote no próximo mapa"),
		["Leave game"] = ("Quitter la partie", "Spiel verlassen", "Abandonar partida", "Sair da partida"),
		["Voting has closed"] = ("Le vote est clos", "Die Abstimmung ist beendet", "La votación ha terminado", "A votação foi encerrada"),
		["Click another map to change your vote, or yours again to take it back"] = (
			"Cliquez sur une autre carte pour changer de vote, ou à nouveau sur la vôtre pour le retirer",
			"Klicke auf eine andere Karte, um deine Stimme zu ändern, oder noch einmal auf deine, um sie zurückzuziehen",
			"Haz clic en otro mapa para cambiar tu voto, o de nuevo en el tuyo para retirarlo",
			"Clique em outro mapa para mudar seu voto, ou de novo no seu para retirá-lo" ),
		["Click a map to vote for it"] = ("Cliquez sur une carte pour voter", "Klicke auf eine Karte, um abzustimmen", "Haz clic en un mapa para votarlo", "Clique em um mapa para votar nele"),
		["Leading"] = ("En tête", "Führt", "En cabeza", "Na liderança"),
		["Your vote"] = ("Votre vote", "Deine Stimme", "Tu voto", "Seu voto"),
		["No votes"] = ("Aucun vote", "Keine Stimmen", "Sin votos", "Nenhum voto"),
		["1 vote"] = ("1 vote", "1 Stimme", "1 voto", "1 voto"),
		["{0} votes"] = ("{0} votes", "{0} Stimmen", "{0} votos", "{0} votos"),
		["Play a different mode"] = (
			"Jouer à un autre mode",
			"Einen anderen Modus spielen",
			"Jugar a otro modo",
			"Jogar outro modo" ),
		["Leaves this lobby and starts a new match in that mode"] = (
			"Quitte ce salon et lance une nouvelle partie dans ce mode",
			"Verlässt diese Lobby und startet ein neues Match in diesem Modus",
			"Sale de esta sala e inicia una nueva partida en ese modo",
			"Sai desta sala e inicia uma nova partida nesse modo" ),
		["You're the host, so leaving closes this lobby for everyone"] = (
			"Vous êtes l'hôte : si vous partez, ce salon fermera pour tout le monde",
			"Du bist der Host: Wenn du gehst, wird diese Lobby für alle geschlossen",
			"Eres el anfitrión: si te vas, esta sala se cerrará para todos",
			"Você é o anfitrião: se sair, esta sala será fechada para todos" ),
		["Starting {0}…"] = ("Lancement : {0}…", "{0} wird gestartet…", "Iniciando {0}…", "Iniciando {0}…"),
		["Couldn't leave this lobby. Try again."] = (
			"Impossible de quitter ce salon. Veuillez réessayer.",
			"Diese Lobby konnte nicht verlassen werden. Versuche es erneut.",
			"No se ha podido salir de esta sala. Inténtalo de nuevo.",
			"Não foi possível sair desta sala. Tente novamente." ),
	};
}
