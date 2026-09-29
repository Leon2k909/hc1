namespace Facepunch;

public static partial class GameText
{
	/// <summary> The main menu's header, hub, mode rail, sidebar, playlists, quick play filter, party and bug report panels. </summary>
	private static TextTable MenuText => new()
	{
		// Header (MainMenuRoot), breadcrumb bar (MenuTopbar) and dialogs
		["More"] = ("Plus", "Mehr", "Más", "Mais"),
		["Notifications"] = ("Notifications", "Benachrichtigungen", "Notificaciones", "Notificações"),
		["No notifications"] = ("Aucune notification", "Keine Benachrichtigungen", "No hay notificaciones", "Nenhuma notificação"),
		["LV {0}"] = ("Niv. {0}", "Stufe {0}", "Nv. {0}", "Nv. {0}"),
		["Are you sure you want to quit?"] = (
			"Voulez-vous vraiment quitter ?",
			"Willst du das Spiel wirklich beenden?",
			"¿Seguro que quieres salir?",
			"Tem certeza de que quer sair?" ),
		// The quit prompt (QuitPrompt) and the pause menu: s&box won't let a game close it, so outside a standalone
		// build the only way out is back to s&box.
		["Quit to s&box"] = ("Quitter vers s&box", "Zurück zu s&box", "Salir a s&box", "Sair para o s&box"),
		["Menu"] = ("Menu", "Menü", "Menú", "Menu"),
		["Home"] = ("Accueil", "Startseite", "Inicio", "Início"),

		// Hub: the mode rail (HubModeRail)
		["Story Experience"] = ("Mode histoire", "Story-Erlebnis", "Modo historia", "Modo história"),
		["Compete Online"] = ("Rivalisez en ligne", "Tritt online an", "Compite en línea", "Compita online"),
		["Last One Standing"] = ("Dernier survivant", "Nur einer überlebt", "El último en pie", "Último sobrevivente"),
		["Fight the Undead"] = ("Affrontez les zombies", "Bekämpfe die Untoten", "Lucha contra zombis", "Enfrente os zumbis"),

		// Hub: Multiplayer, the Quick Play filter and the playlists
		["Featured"] = ("À la une", "Empfohlen", "Destacado", "Destaque"),
		["Skill. Strategy. All out war."] = (
			"Talent. Stratégie. Guerre totale.",
			"Können. Strategie. Krieg mit allen Mitteln.",
			"Habilidad. Estrategia. Guerra total.",
			"Habilidade. Estratégia. Guerra total." ),
		["All"] = ("Tous", "Alle", "Todos", "Todos"),
		["Popular Playlists"] = ("Playlists populaires", "Beliebte Playlists", "Listas de juego populares", "Playlists populares"),
		["View All Playlists"] = ("Voir toutes les playlists", "Alle Playlists anzeigen", "Ver todas las listas de juego", "Ver todas as playlists"),
		["All Playlists"] = ("Toutes les playlists", "Alle Playlists", "Todas las listas de juego", "Todas as playlists"),
		["{0} Map"] = ("{0} carte", "{0} Karte", "{0} mapa", "{0} mapa"),
		["{0} Maps"] = ("{0} cartes", "{0} Karten", "{0} mapas", "{0} mapas"),

		// Playlist card subtitles (PopularPlaylists.Subtitles). One line on a narrow card, so they stay short.
		["5V5 | Instant Respawns"] = ("5v5 | Réapparition immédiate", "5v5 | Sofortiger Respawn", "5v5 | Reaparición inmediata", "5v5 | Renascimento imediato"),
		["1V1 | Instant Respawns"] = ("1v1 | Réapparition immédiate", "1v1 | Sofortiger Respawn", "1v1 | Reaparición inmediata", "1v1 | Renascimento imediato"),
		["2V2 | Instant Respawns"] = ("2v2 | Réapparition immédiate", "2v2 | Sofortiger Respawn", "2v2 | Reaparición inmediata", "2v2 | Renascimento imediato"),
		["5V5 | Capture and Hold"] = ("5v5 | Capturer et tenir", "5v5 | Erobern und halten", "5v5 | Capturar y mantener", "5v5 | Capturar e manter"),
		["5V5 | Rotating Zone"] = ("5v5 | Zone mobile", "5v5 | Wechselnde Zone", "5v5 | Zona rotativa", "5v5 | Zona rotativa"),
		["5V5 | No Respawns"] = ("5v5 | Sans réapparition", "5v5 | Kein Respawn", "5v5 | Sin reapariciones", "5v5 | Sem renascimento"),
		["5V5 | After-Plant Rounds"] = ("5v5 | Bombe déjà posée", "5v5 | Bombe schon gelegt", "5v5 | Bomba ya plantada", "5v5 | Bomba já plantada"),
		["5V5 | Capture the Cash"] = ("5v5 | Capturer l'argent", "5v5 | Geld erobern", "5v5 | Capturar el dinero", "5v5 | Capturar o dinheiro"),
		["Free For All | Weapon Tiers"] = ("Mêlée générale | Paliers", "Jeder gegen jeden | Stufen", "Todos contra todos | Niveles", "Todos contra todos | Níveis"),

		// Hub: Battle Royale
		["Solos · {0}"] = ("Solo · {0}", "Solo · {0}", "Individual · {0}", "Solo · {0}"),
		["Drop in. Outrun the zone. Be the last one standing."] = (
			"Sautez. Semez la zone. Soyez le dernier survivant.",
			"Spring ab. Häng die Zone ab. Bleib als Letzter stehen.",
			"Lánzate. Escapa de la zona. Sé el último en pie.",
			"Salte. Fuja da zona. Seja o último sobrevivente." ),
		["{0} Bots"] = ("{0} bots", "{0} Bots", "{0} bots", "{0} bots"),
		["Field Size"] = ("Participants", "Teilnehmerzahl", "Participantes", "Participantes"),
		["Quick Match"] = ("Partie rapide", "Schnelles Match", "Partida rápida", "Partida rápida"),
		["Standard"] = ("Standard", "Standard", "Estándar", "Padrão"),
		["Crowded"] = ("Bondé", "Gut gefüllt", "Concurrido", "Lotado"),
		["Full Lobby"] = ("Lobby complet", "Volle Lobby", "Sala llena", "Lobby cheio"),
		["Wide Open"] = ("Grands espaces", "Weites Gelände", "Campo abierto", "Campo aberto"),
		["Mountain Valley"] = ("Vallée de montagne", "Bergtal", "Valle de montaña", "Vale montanhoso"),

		// Hub: Zombies
		["Co-op"] = ("Coop", "Koop", "Cooperativo", "Cooperativo"),
		["Fight together. Stay human."] = (
			"Combattez ensemble. Restez humains.",
			"Kämpfe im Team. Bleib menschlich.",
			"Lucha en equipo. Sigue siendo humano.",
			"Lute em equipe. Permaneça humano." ),
		["Zombies Maps"] = ("Cartes Zombies", "Zombies-Karten", "Mapas de Zombis", "Mapas de Zumbis"),
		["Co-op Survival"] = ("Survie en coop", "Koop-Überleben", "Supervivencia cooperativa", "Sobrevivência cooperativa"),
		["No Zombies maps available."] = (
			"Aucune carte Zombies disponible.",
			"Keine Zombies-Karten verfügbar.",
			"No hay mapas de Zombis disponibles.",
			"Nenhum mapa de Zumbis disponível." ),
		["Co-op · Zombies"] = ("Coop · Zombies", "Koop · Zombies", "Cooperativo · Zombis", "Cooperativo · Zumbis"),
		["Select Map"] = ("Choisir une carte", "Karte wählen", "Seleccionar mapa", "Selecionar mapa"),

		// Hub: the sidebar (HubSidebar, DailyChallenges). The challenge titles share one narrow line.
		["Daily Challenges"] = ("Défis quotidiens", "Tagesaufgaben", "Desafíos diarios", "Desafios diários"),
		["{0}M"] = ("{0} min", "{0} Min.", "{0} min", "{0} min"),
		["Get {0} Operator Kills"] = ("Éliminez {0} opérateurs", "Schalte {0} Operator aus", "Elimina a {0} operadores", "Abata {0} operadores"),
		["Get {0} Headshots"] = ("Réalisez {0} tirs à la tête", "Erziele {0} Kopfschüsse", "Haz {0} tiros a la cabeza", "Dê {0} tiros na cabeça"),
		["Win a Match"] = ("Gagnez une partie", "Gewinne ein Match", "Gana una partida", "Vença uma partida"),
		["Win {0} Matches"] = ("Gagnez {0} parties", "Gewinne {0} Matches", "Gana {0} partidas", "Vença {0} partidas"),
		["Finish a Match"] = ("Terminez une partie", "Beende ein Match", "Termina una partida", "Termine uma partida"),
		["Finish {0} Matches"] = ("Terminez {0} parties", "Beende {0} Matches", "Termina {0} partidas", "Termine {0} partidas"),
		["Your Squad"] = ("Votre escouade", "Dein Trupp", "Tu escuadrón", "Seu esquadrão"),
		["Leave"] = ("Quitter", "Verlassen", "Salir", "Sair"),

		// Party (PartyPanel)
		["Invite Players"] = ("Inviter des joueurs", "Spieler einladen", "Invitar jugadores", "Convidar jogadores"),
		["No other players online"] = ("Aucun autre joueur en ligne", "Keine anderen Spieler online", "No hay otros jugadores en línea", "Nenhum outro jogador online"),
		["Invite"] = ("Inviter", "Einladen", "Invitar", "Convidar"),
		["Party Invite"] = ("Invitation de groupe", "Gruppeneinladung", "Invitación de grupo", "Convite de grupo"),
		["{0} wants to party up"] = (
			"{0} vous invite dans son groupe",
			"{0} möchte mit dir eine Gruppe bilden",
			"{0} quiere formar grupo contigo",
			"{0} quer formar um grupo com você" ),
		["Accept"] = ("Accepter", "Annehmen", "Aceptar", "Aceitar"),
		["Decline"] = ("Refuser", "Ablehnen", "Rechazar", "Recusar"),
		["Party Leader"] = ("Chef de groupe", "Gruppenleiter", "Líder del grupo", "Líder do grupo"),
		["In Party"] = ("Dans un groupe", "In einer Gruppe", "En un grupo", "Em um grupo"),
		["Not in party"] = ("Pas dans un groupe", "In keiner Gruppe", "Sin grupo", "Sem grupo"),
		["{0} · Leader"] = ("{0} · Chef", "{0} · Leiter", "{0} · Líder", "{0} · Líder"),
		["Invite to Party"] = ("Inviter dans le groupe", "In die Gruppe einladen", "Invitar al grupo", "Convidar para o grupo"),
		["Leave Party"] = ("Quitter le groupe", "Gruppe verlassen", "Salir del grupo", "Sair do grupo"),
		["Unknown Player"] = ("Joueur inconnu", "Unbekannter Spieler", "Jugador desconocido", "Jogador desconhecido"),

		// Squad privacy: the cog on the hub's squad card (SquadPrivacy). The option names say "squad" in other languages, so
		// they agree with it; English shows OPEN / INVITE ONLY / PRIVATE.
		["Squad privacy"] = ("Accès à l'escouade", "Zugang zum Trupp", "Acceso al escuadrón", "Acesso ao esquadrão"),
		["Open squad"] = ("Escouade ouverte", "Offener Trupp", "Escuadrón abierto", "Esquadrão aberto"),
		["Private squad"] = ("Escouade privée", "Privater Trupp", "Escuadrón privado", "Esquadrão privado"),
		["Anyone can find and join your squad"] = (
			"Tout le monde peut trouver et rejoindre votre escouade",
			"Jeder kann deinen Trupp finden und ihm beitreten",
			"Cualquiera puede encontrar tu escuadrón y unirse",
			"Qualquer um pode encontrar e entrar no seu esquadrão" ),
		["Only players you invite can join"] = (
			"Seuls les joueurs que vous invitez peuvent rejoindre",
			"Nur Spieler, die du einlädst, können beitreten",
			"Solo pueden unirse los jugadores que invites",
			"Só os jogadores que você convidar podem entrar" ),
		["Nobody can join your squad"] = (
			"Personne ne peut rejoindre votre escouade",
			"Niemand kann deinem Trupp beitreten",
			"Nadie puede unirse a tu escuadrón",
			"Ninguém pode entrar no seu esquadrão" ),
		["Only the squad leader can change this."] = (
			"Seul le chef d'escouade peut modifier ce réglage.",
			"Nur der Truppführer kann das ändern.",
			"Solo el líder del escuadrón puede cambiarlo.",
			"Só o líder do esquadrão pode mudar isso." ),
		["Applies to your next squad"] = ("S'appliquera à votre prochaine escouade", "Gilt für deinen nächsten Trupp", "Se aplicará a tu próximo escuadrón", "Vale para o seu próximo esquadrão"),
		["Your squad is private"] = ("Votre escouade est privée", "Dein Trupp ist privat", "Tu escuadrón es privado", "Seu esquadrão é privado"),

		// The hub's friends card (RecentFriends): the Steam friends you've played with, and their status
		["Recent"] = ("Récents", "Zuletzt", "Recientes", "Recentes"),
		["All friends"] = ("Tous les amis", "Alle Freunde", "Todos los amigos", "Todos os amigos"),
		["In game"] = ("En jeu", "Im Spiel", "En partida", "Em jogo"),
		["Online"] = ("En ligne", "Online", "En línea", "Online"),
		["Away"] = ("Absent", "Abwesend", "Ausente", "Ausente"),
		["Offline"] = ("Hors ligne", "Offline", "Desconectado", "Offline"),
		["Steam friends you play with show up here."] = (
			"Vos amis Steam avec qui vous jouez apparaîtront ici.",
			"Steam-Freunde, mit denen du spielst, erscheinen hier.",
			"Aquí aparecerán los amigos de Steam con los que juegues.",
			"Seus amigos da Steam com quem você joga aparecem aqui." ),

		// Bug report (BugReportPanel). The categories are saved in English and shown translated.
		["Title"] = ("Titre", "Titel", "Título", "Título"),
		["Short description..."] = ("Brève description...", "Kurzbeschreibung...", "Descripción breve...", "Descrição curta..."),
		["Category"] = ("Catégorie", "Kategorie", "Categoría", "Categoria"),
		["Description"] = ("Description", "Beschreibung", "Descripción", "Descrição"),
		["Detailed description..."] = ("Description détaillée...", "Ausführliche Beschreibung...", "Descripción detallada...", "Descrição detalhada..."),
		["Submit"] = ("Envoyer", "Absenden", "Enviar", "Enviar"),
		["Crash"] = ("Plantage", "Absturz", "Bloqueo", "Travamento"),
		["User interface"] = ("Interface", "Oberfläche", "Interfaz", "Interface"),
		["Gameplay"] = ("Gameplay", "Gameplay", "Jugabilidad", "Jogabilidade"),
		["Network"] = ("Réseau", "Netzwerk", "Red", "Rede"),
	};
}
