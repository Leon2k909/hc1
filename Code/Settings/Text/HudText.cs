namespace Facepunch;

public static partial class GameText
{
	/// <summary> The combat HUD (vitals, ammo, weapons, radio, chat, minimap, markers, prompts), Battle Royale, Cash Grab and Zombies (round UI, workbench). </summary>
	private static TextTable HudText => new()
	{
		// Top of the HUD, vitals
		["UAV READY ({0})"] = ("Drone prêt ({0})", "Drohne bereit ({0})", "VANT listo ({0})", "VANT pronto ({0})"),
		["NEXT ZONE: {0}s"] = ("Prochaine zone : {0} s", "Nächste Zone: {0} s", "Siguiente zona: {0} s", "Próxima zona: {0} s"),
		["HELMET"] = ("Casque", "Helm", "Casco", "Capacete"),

		// Chat's system lines ({0} is the player's name, {1} a team's)
		["{0} is spectating"] = ("{0} passe en spectateur", "{0} schaut jetzt zu", "{0} pasa a espectador", "{0} agora está assistindo"),
		["{0} is joining the {1}"] = ("{0} rejoint l'{1}", "{0} tritt {1} bei", "{0} se une al {1}", "{0} está entrando na {1}"),
		["{0} has left the game"] = ("{0} a quitté la partie", "{0} hat das Spiel verlassen", "{0} ha abandonado la partida", "{0} saiu da partida"),

		// Voice chat's list of who's talking (Voices): a speaker on the other team, and who hears you on your own row
		["Enemy"] = ("Ennemi", "Feind", "Enemigo", "Inimigo"),
		["Everyone"] = ("Tout le monde", "Alle", "Todos", "Todos"),
		["Nearby"] = ("À proximité", "In der Nähe", "Cercanos", "Próximos"),

		// Radio menu and its lines in chat (Assets/radio_sounds/*.radio)
		["Remarks"] = ("Remarques", "Bemerkungen", "Comentarios", "Comentários"),
		["Good shot"] = ("Joli tir", "Guter Schuss", "Buen tiro", "Belo tiro"),
		["Friendly Fire"] = ("Tir allié", "Eigenbeschuss", "Fuego amigo", "Fogo amigo"),
		["Defusing the bomb"] = ("Je désamorce la bombe", "Entschärfe die Bombe", "Desactivando la bomba", "Desarmando a bomba"),
		["Planting bomb"] = ("Je pose la bombe", "Lege die Bombe", "Plantando la bomba", "Plantando a bomba"),

		// Bomb progress
		["Planting the bomb..."] = ("Pose de la bombe...", "Bombe wird gelegt...", "Plantando la bomba...", "Plantando a bomba..."),
		["Defusing the bomb..."] = ("Désamorçage de la bombe...", "Bombe wird entschärft...", "Desactivando la bomba...", "Desarmando a bomba..."),

		// Battle Royale
		["RETURN TO THE SAFE ZONE"] = ("Retournez dans la zone sûre", "Kehre in die sichere Zone zurück", "Vuelve a la zona segura", "Volte para a zona segura"),
		["SAFE ZONE MARKED"] = ("Zone sûre marquée", "Sichere Zone markiert", "Zona segura marcada", "Zona segura marcada"),
		["THE ZONE IS CLOSING"] = ("La zone se resserre", "Die Zone schrumpft", "La zona se está cerrando", "A zona está fechando"),
		["FINAL ZONE"] = ("Zone finale", "Letzte Zone", "Zona final", "Zona final"),
		["ELIMINATED"] = ("Éliminé", "Eliminiert", "Eliminado", "Eliminado"),
		// Placing ("2ND OF 50"): one line per English suffix. French says 1er but 21e, so it doesn't use an ordinal.
		["{0}ST OF {1}"] = ("Classement : {0}/{1}", "Platz {0} von {1}", "Puesto {0} de {1}", "{0}º de {1}"),
		["{0}ND OF {1}"] = ("Classement : {0}/{1}", "Platz {0} von {1}", "Puesto {0} de {1}", "{0}º de {1}"),
		["{0}RD OF {1}"] = ("Classement : {0}/{1}", "Platz {0} von {1}", "Puesto {0} de {1}", "{0}º de {1}"),
		["{0}TH OF {1}"] = ("Classement : {0}/{1}", "Platz {0} von {1}", "Puesto {0} de {1}", "{0}º de {1}"),
		["ALIVE"] = ("En vie", "Am Leben", "Vivos", "Vivos"),
		["MATCH OVER"] = ("Partie terminée", "Match vorbei", "Fin de la partida", "Fim da partida"),
		["DROPPING IN"] = ("Largage dans", "Absprung in", "Despliegue en", "Salto em"),
		["ZONE CLOSING"] = ("Fermeture de la zone", "Zone schrumpft", "Zona cerrándose", "Zona fechando"),
		["ZONE {0} CLOSES IN"] = ("Zone {0} : fermeture dans", "Zone {0} schrumpft in", "La zona {0} se cierra en", "Zona {0} fecha em"),

		// Cash Grab, the play area and the drone
		["EXTRACT"] = ("Extraction", "Extraktion", "Extracción", "Extração"),
		["Extraction Point"] = ("Point d'extraction", "Extraktionspunkt", "Punto de extracción", "Ponto de extração"),
		["Cash Point"] = ("Point d'argent", "Geldpunkt", "Punto de dinero", "Ponto de dinheiro"),
		["Cash"] = ("Argent", "Geld", "Dinero", "Dinheiro"),
		["Return to the AO"] = ("Retournez dans la zone de combat", "Kehre ins Kampfgebiet zurück", "Vuelve a la zona de combate", "Volte para a área de combate"),
		["Exit Drone"] = ("Quitter le drone", "Drohne verlassen", "Salir del dron", "Sair do drone"),
		["Return to Drone"] = ("Retourner au drone", "Zurück zur Drohne", "Volver al dron", "Voltar ao drone"),

		// Domination flags' and the hot zone's markers ("[A] - Neutral", "Hot Zone - CONTESTED")
		["Neutral"] = ("Neutre", "Neutral", "Neutral", "Neutro"),
		["CONTESTED"] = ("Contesté", "Umkämpft", "En disputa", "Em disputa"),
		["Capturing {0} ({1}% by {2})"] = (
			"Capture de {0} ({1} % par {2})",
			"{0} wird eingenommen ({1} % durch {2})",
			"Capturando {0} ({1} % por {2})",
			"Capturando {0} ({1}% por {2})" ),

		// Zombies: rounds, power-ups, going down
		["ROUND {0} IN {1}"] = ("Manche {0} dans {1}", "Runde {0} in {1}", "Ronda {0} en {1}", "Rodada {0} em {1}"),
		["{0} ZOMBIES LEFT"] = ("{0} zombies restants", "Noch {0} Zombies", "Quedan {0} zombis", "{0} zumbis restantes"),
		["One-Hit Kills"] = ("Mort en un coup", "Tödliche Treffer", "Muerte de un golpe", "Abate em um golpe"),
		["Point Boost"] = ("Bonus de points", "Punkte-Boost", "Bonificación de puntos", "Bônus de pontos"),
		["Resupply"] = ("Ravitaillement", "Nachschub", "Reabastecimiento", "Reabastecimento"),
		["Clean Sweep"] = ("Grand nettoyage", "Kahlschlag", "Limpieza total", "Limpeza geral"),
		["YOU ARE DOWN"] = ("Vous êtes à terre", "Du bist am Boden", "Estás derribado", "Você foi derrubado"),
		["Second Wind is getting you back up…"] = (
			"Second Wind vous remet sur pied…",
			"Second Wind bringt dich wieder auf die Beine…",
			"Second Wind te está levantando…",
			"Second Wind está te levantando…" ),
		["{0} is reviving you"] = ("{0} vous réanime", "{0} belebt dich wieder", "{0} te está reanimando", "{0} está te reanimando"),
		["Bleeding out in {0}s — wait for a teammate"] = (
			"Hémorragie : {0} s — attendez un coéquipier",
			"Du verblutest in {0} s — warte auf einen Teamkameraden",
			"Te desangras en {0} s — espera a un compañero",
			"Sangrando: {0} s — espere um aliado" ),
		["REVIVING {0}"] = ("Réanimation de {0}", "Wiederbelebung: {0}", "Reanimando a {0}", "Reanimando {0}"),
		["YOU DIED"] = ("Vous êtes mort", "Du bist gestorben", "Has muerto", "Você morreu"),
		["You'll respawn when the round ends"] = (
			"Vous réapparaîtrez à la fin de la manche",
			"Du erscheinst am Ende der Runde wieder",
			"Reaparecerás cuando termine la ronda",
			"Você vai renascer quando a rodada acabar" ),
		["SURVIVE AS LONG AS YOU CAN"] = ("Survivez le plus longtemps possible", "Überlebe so lange wie möglich", "Sobrevive todo lo que puedas", "Sobreviva o máximo que puder"),
		["GAME OVER"] = ("Fin de partie", "Spiel vorbei", "Fin del juego", "Fim de jogo"),
		["You survived {0} round"] = ("Vous avez survécu à {0} manche", "Du hast {0} Runde überlebt", "Has sobrevivido a {0} ronda", "Você sobreviveu a {0} rodada"),
		["You survived {0} rounds"] = ("Vous avez survécu à {0} manches", "Du hast {0} Runden überlebt", "Has sobrevivido a {0} rondas", "Você sobreviveu a {0} rodadas"),
		["Restarting in {0}…"] = ("Redémarrage dans {0}…", "Neustart in {0}…", "Reinicio en {0}…", "Reiniciando em {0}…"),
		// The opening's caption: {0} is the map's name, {1} the time.
		["{0} — OUTSKIRTS"] = ("{0} — Périphérie", "{0} — Stadtrand", "{0} — Afueras", "{0} — Periferia"),
		["DAY {0}  ·  {1}"] = ("Jour {0}  ·  {1}", "Tag {0}  ·  {1}", "Día {0}  ·  {1}", "Dia {0}  ·  {1}"),

		// Zombies: the use prompt, buy stations and perks ({0} is a gun, a perk or a player)
		["You already have {0}"] = ("Vous avez déjà {0}", "Du hast bereits {0}", "Ya tienes {0}", "Você já tem {0}"),
		["You already have this perk"] = ("Vous avez déjà cet atout", "Du hast dieses Extra bereits", "Ya tienes esta ventaja", "Você já tem esta vantagem"),
		["Ammo already full"] = ("Munitions déjà au maximum", "Munition bereits voll", "Munición ya al máximo", "Munição já no máximo"),
		["Hold to revive {0}"] = ("Maintenez pour réanimer {0}", "Halten, um {0} wiederzubeleben", "Mantén pulsado para reanimar a {0}", "Segure para reanimar {0}"),
		["Buy ammo for {0}"] = ("Acheter des munitions pour {0}", "Munition für {0} kaufen", "Comprar munición para {0}", "Comprar munição para {0}"),
		["Buy {0}"] = ("Acheter {0}", "{0} kaufen", "Comprar {0}", "Comprar {0}"),
		["Buy {0} — {1}"] = ("Acheter {0} — {1}", "{0} kaufen — {1}", "Comprar {0} — {1}", "Comprar {0} — {1}"),
		["Refill all ammo"] = ("Refaire le plein de munitions", "Alle Munition auffüllen", "Reponer toda la munición", "Repor toda a munição"),
		["Open the Workbench"] = ("Ouvrir l'établi", "Werkbank öffnen", "Abrir el banco de trabajo", "Abrir a bancada"),
		["Open the Weapon Crate"] = ("Ouvrir la caisse d'armes", "Waffenkiste öffnen", "Abrir la caja de armas", "Abrir a caixa de armas"),
		["Weapon Crate"] = ("Caisse d'armes", "Waffenkiste", "Caja de armas", "Caixa de armas"),
		["Ammo Box"] = ("Caisse de munitions", "Munitionskiste", "Caja de munición", "Caixa de munição"),
		["Workbench"] = ("Établi", "Werkbank", "Banco de trabajo", "Bancada"),
		["More health"] = ("Plus de santé", "Mehr Gesundheit", "Más salud", "Mais vida"),
		["Faster reloads"] = ("Rechargements plus rapides", "Schnelleres Nachladen", "Recargas más rápidas", "Recargas mais rápidas"),
		["Faster fire rate, double damage"] = (
			"Cadence de tir accrue, dégâts doublés",
			"Höhere Feuerrate, doppelter Schaden",
			"Más cadencia de fuego, daño doble",
			"Cadência de tiro maior, dano dobrado" ),
		["Faster revives, solo self-revive"] = (
			"Réanimations plus rapides, auto-réanimation en solo",
			"Schnellere Wiederbelebung, Selbstwiederbelebung im Solospiel",
			"Reanimaciones más rápidas, autorreanimación en solitario",
			"Reanimações mais rápidas, autorreanimação no solo" ),
		["Move faster"] = ("Déplacements plus rapides", "Schnellere Bewegung", "Movimiento más rápido", "Movimento mais rápido"),

		// Zombies workbench: attachments
		["Attachments are free. Armour, ammo and grenades cost points."] = (
			"Les accessoires sont gratuits. L'armure, les munitions et les grenades coûtent des points.",
			"Aufsätze sind kostenlos. Panzerung, Munition und Granaten kosten Punkte.",
			"Los accesorios son gratis. El blindaje, la munición y las granadas cuestan puntos.",
			"Os acessórios são grátis. Blindagem, munição e granadas custam pontos." ),
		["You're not carrying a gun that takes attachments."] = (
			"Vous ne portez aucune arme qui accepte des accessoires.",
			"Du trägst keine Waffe, an die Aufsätze passen.",
			"No llevas ningún arma que admita accesorios.",
			"Você não está com nenhuma arma que aceite acessórios." ),
		["No attachments fit the {0}."] = ("{0} : aucun accessoire compatible.", "{0}: keine passenden Aufsätze.", "{0}: no hay accesorios compatibles.", "{0}: nenhum acessório compatível."),
		["UNLOCKS AT WEAPON LV {0}"] = ("Débloqué au niveau d'arme {0}", "Freischaltung ab Waffenstufe {0}", "Se desbloquea al nivel de arma {0}", "Desbloqueia no nível de arma {0}"),
		["{0} OPTION"] = ("{0} option", "{0} Option", "{0} opción", "{0} opção"),
		["FREE · SAVED TO YOUR ACTIVE CLASS · MORE PARTS UNLOCK AS YOUR WEAPONS LEVEL UP"] = (
			"Gratuit · Enregistré dans votre classe active · D'autres pièces se débloquent quand vos armes montent de niveau",
			"Kostenlos · In deiner aktiven Klasse gespeichert · Weitere Teile schaltest du frei, wenn deine Waffen aufsteigen",
			"Gratis · Se guarda en tu clase activa · Se desbloquean más piezas al subir de nivel tus armas",
			"Grátis · Salvo na sua classe ativa · Mais peças são desbloqueadas conforme suas armas sobem de nível" ),

		// Zombies workbench: armour, ammo and grenades
		["Plates take the hits before your health does."] = (
			"Les plaques encaissent les coups avant votre santé.",
			"Platten fangen Treffer ab, bevor deine Gesundheit leidet.",
			"Las placas reciben los golpes antes que tu salud.",
			"As placas absorvem os golpes antes da sua vida." ),
		["+1 PLATE"] = ("+1 plaque", "+1 Platte", "+1 placa", "+1 placa"),
		["FILL VEST"] = ("Remplir le gilet", "Weste auffüllen", "Llenar el chaleco", "Encher o colete"),
		["{0} in the gun · {1} / {2} spare"] = ("{0} dans l'arme · {1} / {2} en réserve", "{0} in der Waffe · {1} / {2} Reserve", "{0} en el arma · {1} / {2} de reserva", "{0} na arma · {1} / {2} de reserva"),
		["REFILL"] = ("Remplir", "Auffüllen", "Reponer", "Repor"),
		["REFILL ALL"] = ("Tout remplir", "Alles auffüllen", "Reponer todo", "Repor tudo"),
		["Throw it into a crowd"] = ("Lancez-la dans la foule", "Wirf sie in die Menge", "Lánzala a la multitud", "Jogue-a na multidão"),
		["Out of stock"] = ("Rupture de stock", "Nicht vorrätig", "Agotado", "Esgotado"),
		["Lethal slot full"] = ("Emplacement létal plein", "Slot für Tödliches belegt", "Ranura letal llena", "Espaço letal cheio"),
		["BUY"] = ("Acheter", "Kaufen", "Comprar", "Comprar"),

		// Zombies workbench: the message after a pick or purchase
		["ARMOUR PLATE FITTED"] = ("Plaque de blindage installée", "Panzerplatte angebracht", "Placa de blindaje colocada", "Placa de blindagem colocada"),
		["VEST FILLED"] = ("Gilet rempli", "Weste aufgefüllt", "Chaleco lleno", "Colete cheio"),
		["AMMO REFILLED"] = ("Munitions réapprovisionnées", "Munition aufgefüllt", "Munición repuesta", "Munição reposta"),
		["ALL AMMO REFILLED"] = ("Toutes les munitions réapprovisionnées", "Alle Munition aufgefüllt", "Toda la munición repuesta", "Toda a munição reposta"),
		["HE GRENADE ADDED"] = ("Grenade HE ajoutée", "HE-Granate erhalten", "Granada HE añadida", "Granada HE adicionada"),
		["BOUGHT"] = ("Acheté", "Gekauft", "Comprado", "Comprado"),
		["{0}: STANDARD"] = ("{0} : standard", "{0}: Standard", "{0}: estándar", "{0}: padrão"),
		["{0} FITTED"] = ("Installé : {0}", "{0} angebracht", "Instalado: {0}", "Instalado: {0}"),
		["NOT ENOUGH POINTS · {0} NEEDED"] = ("Points insuffisants · {0} requis", "Nicht genug Punkte · {0} benötigt", "Puntos insuficientes · Necesitas {0}", "Pontos insuficientes · {0} necessários"),
	};
}
