#!/usr/bin/env python3
"""
A text adventure that the whole class plays at once, over nc.

    python3 netcat-game.py [port] [--log]   # default port 12345
    nc <address> 12345                      # on each student's machine

The commands are the server's protocol. `aide` lists the general ones
(directions, regarder, dire, qui, quitter); the actions that solve the game are
only hinted at by the room descriptions, everything else gets « Commande
inconnue. ».

Solution: give a name, `sud`, `caresser chien`, `prendre clé` (the key on its
collar), `nord`, `nord`, `ouvrir cadenas`, `ouvrir frigo`. Every action names
its object: a bare `caresser`, `prendre` or `ouvrir` only gets « Caresser
quoi ? », « Prendre quoi ? », « Ouvrir quoi ? ». Players in the same room see
each other come and go, and `dire <message>` talks to them: the server relays
every message, the clients never connect to each other. Each player who reaches
the paradis is announced to everyone with their position, then the server
closes their connection.

The server console is meant to be projected. It shows one panel per player, in
a grid laid out for a class of about twelve (4 × 3): the commands they type
(red when unknown, cyan when they talk),
the room they are in and the machine they play from. With --log, or when the
output isn't a terminal, it prints a plain log instead: every connection and
every command received. Ctrl+C stops the server.
"""

import collections
import curses
import locale
import math
import socket
import sys
import threading
import unicodedata

ROOMS = {
    "salon": {
        "description": (
            "Vous êtes dans le salon. Il y a une porte au nord et une porte au sud.\n"
            "Un perroquet répète en boucle : « dire bonjour ! dire bonjour ! »"
        ),
        "exits": {"nord": "cuisine", "sud": "jardin"},
    },
    "cuisine": {
        "description": (
            "Vous êtes dans la cuisine. Il y a un frigo, fermé par un cadenas, "
            "et une porte au sud."
        ),
        "description_unlocked": (
            "Vous êtes dans la cuisine. Il y a un frigo, dont le cadenas pend, ouvert, "
            "et une porte au sud."
        ),
        "exits": {"sud": "salon"},
    },
    "jardin": {
        "description": (
            "Vous êtes dans le jardin. Un chien vous regarde en remuant la queue. "
            "Il y a une porte au nord."
        ),
        "exits": {"nord": "salon"},
    },
}

PARADISE = "Vous êtes au paradis. Cocas et tacos infinis !"

HELP = """Commandes :
  nord (n), sud (s)    se déplacer
  regarder             décrire la pièce à nouveau
  dire <message>       parler aux joueurs de la même pièce
  qui                  lister les joueurs connectés
  aide                 afficher cette aide
  quitter              se déconnecter
D'autres actions existent : les descriptions des pièces les suggèrent."""

SHORTCUTS = {"n": "nord", "s": "sud"}

UNKNOWN ="Commande inconnue. (« aide » pour la liste des commandes)"

# The grid: 4 × 3 panels for the usual class of twelve, more when needed.
GRID_COLUMNS = 4
GRID_ROWS = 3
EVENT_LINES = 3  # connections and arrivals, under the grid
HISTORY = 50  # commands kept per player


def normalize(text):
    """Lowercase and without accents, so that « clé » and « cle » both match."""
    decomposed = unicodedata.normalize("NFD", text.lower())
    return "".join(c for c in decomposed if unicodedata.category(c) != "Mn")


def local_address():
    """The address of the interface that leads to the network, for the students.

    Connecting a UDP socket sends nothing: it only makes the system pick the
    interface it would route through.
    """
    probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        probe.connect(("192.0.2.1", 9))  # TEST-NET-1, never actually reached
        return probe.getsockname()[0]
    except OSError:
        return None  # no network: only this machine can connect
    finally:
        probe.close()


def grid_shape(count):
    """Columns and rows: 4 × 3 up to twelve players, then as square as fits."""
    columns = max(GRID_COLUMNS, math.ceil(math.sqrt(count * GRID_COLUMNS / GRID_ROWS)))
    rows = max(GRID_ROWS, math.ceil(count / columns))
    return columns, rows


def put(window, y, x, text, attributes=0):
    """Writes what fits; curses raises on the last cell of a window."""
    _, width = window.getmaxyx()
    if x >= width or y < 0 or x < 0:
        return
    try:
        window.addnstr(y, x, text, width - x, attributes)
    except curses.error:
        pass


class Player:
    def __init__(self, connection, address):
        self.connection = connection
        self.address = address
        self.machine = None  # filled in by log_connection, if the lookup succeeds
        self.name = None
        self.room = "salon"
        self.dog_is_friendly = False
        self.has_key = False
        self.padlock_is_open = False
        self.connected = True
        self.position = None  # rank of arrival in the paradis
        self.history = collections.deque(maxlen=HISTORY)  # [kind, command], for the grid
        self.send_lock = threading.Lock()

    def origin(self):
        """The machine's name when known, its IP address otherwise."""
        return self.machine or self.address[0]

    def mark(self, kind):
        """Colors the last command in the grid: "unknown" or "say"."""
        if self.history:
            self.history[-1][0] = kind

    def send(self, text):
        # Other players' threads send to this one too (arrivals, messages).
        with self.send_lock:
            try:
                self.connection.sendall((text + "\n").encode())
            except OSError:
                pass


class GameServer:
    def __init__(self, host, port, grid):
        self.host = host
        self.port = port
        self.grid = grid
        self.players = []
        self.winners = []
        self.lock = threading.Lock()
        # What the console shows, behind its own lock so that drawing never
        # waits on the game.
        self.journal_lock = threading.Lock()
        self.panels = {}  # normalized name -> its latest player, in order of arrival
        self.events = collections.deque(maxlen=EVENT_LINES)
        self.how_to_connect = ""
        self.styles = collections.defaultdict(int)

    def start(self):
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((self.host, self.port))
        server.listen()

        if self.host == "0.0.0.0":
            listening = f"Serveur à l'écoute sur toutes les interfaces (0.0.0.0), port {self.port}."
            address = local_address()
            if address:
                self.how_to_connect = f"Pour se connecter : nc {address} {self.port}"
            else:
                self.how_to_connect = (
                    f"Pas de réseau : seul nc 127.0.0.1 {self.port}, depuis cette machine, fonctionne."
                )
        else:
            listening = f"Serveur à l'écoute sur {self.host}, port {self.port}."
            self.how_to_connect = f"Pour se connecter : nc {self.host} {self.port}"

        if self.grid:
            threading.Thread(target=self.accept, args=(server,), daemon=True).start()
            curses.wrapper(self.show_grid)
        else:
            print(listening)
            print(self.how_to_connect)
            print("En attente de connexions...")
            self.accept(server)

    def accept(self, server):
        while True:
            connection, address = server.accept()
            player = Player(connection, address)
            threading.Thread(target=self.handle_client, args=(player,), daemon=True).start()
            threading.Thread(target=self.log_connection, args=(player,), daemon=True).start()

    def log_connection(self, player):
        # A reverse DNS lookup can take seconds: it gets its own thread so that
        # neither accept() nor the player's welcome waits for it.
        try:
            player.machine = socket.gethostbyaddr(player.address[0])[0]
        except OSError:
            pass
        self.log(f"Connexion depuis {player.origin()}")

    # -- What the console shows

    def log(self, text):
        """An event outside the players' commands: connections, arrivals."""
        with self.journal_lock:
            self.events.append(text)
        if not self.grid:
            print(text)

    def record(self, player, command):
        with self.journal_lock:
            player.history.append(["command", command])
        if not self.grid:
            print(f"[{player.name}] {command}")

    def show_grid(self, screen):
        try:
            curses.curs_set(0)
        except curses.error:
            pass
        if curses.has_colors():
            curses.use_default_colors()
            for pair, color in enumerate((curses.COLOR_RED, curses.COLOR_GREEN, curses.COLOR_CYAN), 1):
                curses.init_pair(pair, color, -1)
            self.styles.update(
                unknown=curses.color_pair(1),
                say=curses.color_pair(3),
                paradise=curses.color_pair(2) | curses.A_BOLD,
            )
        self.styles.update(gone=curses.A_DIM, title=curses.A_BOLD, header=curses.A_REVERSE)
        screen.timeout(250)  # redraw four times a second, and on a resize
        while True:
            self.draw(screen)
            screen.getch()

    def draw(self, screen):
        with self.journal_lock:
            panels = [
                (p.name, p.origin(), p.room, p.has_key, p.connected, p.position, list(p.history))
                for p in self.panels.values()
            ]
            events = list(self.events)
        connected = sum(1 for panel in panels if panel[4])
        arrived = sum(1 for panel in panels if panel[5])

        screen.erase()
        height, width = screen.getmaxyx()

        status = f"{connected} connecté{'s' if connected > 1 else ''} · {arrived} au paradis · Ctrl+C pour arrêter "
        put(screen, 0, 0, " " * width, self.styles["header"])
        put(screen, 0, 1, self.how_to_connect, self.styles["header"] | curses.A_BOLD)
        put(screen, 0, max(len(self.how_to_connect) + 3, width - len(status)), status, self.styles["header"])

        grid_height = height - 1 - EVENT_LINES
        if not panels:
            put(screen, 1 + grid_height // 2, max(0, (width - 26) // 2), "En attente des joueurs...")
        else:
            columns, rows = grid_shape(len(panels))
            cell_width, cell_height = width // columns, grid_height // rows
            for index, panel in enumerate(panels):
                row, column = divmod(index, columns)
                self.draw_panel(screen, 1 + row * cell_height, column * cell_width, cell_height, cell_width, panel)

        for index, event in enumerate(events):
            put(screen, height - EVENT_LINES + index, 1, event, self.styles["gone"])
        screen.refresh()

    def draw_panel(self, screen, y, x, height, width, panel):
        name, origin, room, has_key, connected, position, history = panel
        if height < 3 or width < 12:
            return
        try:
            window = screen.derwin(height, width, y, x)
        except curses.error:
            return

        if position:
            frame, place = self.styles["paradise"], f" paradis #{position} "
        elif not connected:
            frame, place = self.styles["gone"], " parti "
        else:
            frame, place = 0, f" {room}{' · clé' if has_key else ''} "
        window.attron(frame)
        window.box()
        window.attroff(frame)
        put(window, 0, width - len(place) - 1, place, frame)
        put(window, 0, 1, f" {name} "[: max(0, width - len(place) - 3)], frame | self.styles["title"])
        put(window, height - 1, 2, f" {origin} "[: width - 4], self.styles["gone"])

        for line, (kind, command) in enumerate(history[-(height - 2):], 1):
            style = self.styles[kind] if connected or position else self.styles["gone"]
            put(window, line, 1, command[: width - 2], style)

    # -- Messages to several players

    def others_in(self, room, player):
        with self.lock:
            return [p for p in self.players if p.room == room and p is not player]

    def tell_room(self, room, player, text):
        for other in self.others_in(room, player):
            other.send(text)

    def tell_everyone(self, text):
        with self.lock:
            players = list(self.players)
        for p in players:
            p.send(text)

    # -- One thread per client

    def handle_client(self, player):
        lines = player.connection.makefile("r", encoding="utf-8", errors="replace")
        try:
            if self.ask_name(player, lines):
                self.play(player, lines)
        except OSError:
            pass
        finally:
            player.connected = False
            with self.lock:
                if player in self.players:
                    self.players.remove(player)
            if player.name and player.room != "paradis":
                self.tell_room(player.room, player, f"{player.name} disparaît.")
            self.log(f"Déconnexion de {player.name or player.origin()}")
            player.connection.close()

    def ask_name(self, player, lines):
        player.send("Bienvenue dans le jeu d'aventure !")
        while True:
            player.send("Quel est votre nom ?")
            line = lines.readline()
            if not line:
                return False
            name = line.strip()[:20]
            if not name:
                continue
            with self.lock:
                taken = any(normalize(p.name) == normalize(name) for p in self.players)
                if not taken:
                    player.name = name
                    self.players.append(player)
            if taken:
                player.send("Ce nom est déjà pris.")
            else:
                break

        with self.journal_lock:
            # Someone who comes back under the same name gets their panel back.
            self.panels[normalize(player.name)] = player
        self.log(f"{player.origin()} s'appelle {player.name}")
        self.tell_room(player.room, player, f"{player.name} arrive dans le salon.")
        player.send(f"Bonjour {player.name} ! (« aide » pour la liste des commandes)")
        self.describe(player)
        return True

    def play(self, player, lines):
        for line in lines:
            line = line.strip()
            if not line:
                continue
            self.record(player, line)

            verb, _, rest = line.partition(" ")
            verb = normalize(verb)
            verb = SHORTCUTS.get(verb, verb)

            if verb in ("aide", "help", "?"):
                player.send(HELP)
            elif verb == "quitter":
                player.send("Au revoir !")
                return
            elif verb in ("regarder", "regarde"):
                self.describe(player)
            elif verb == "qui":
                with self.lock:
                    names = ", ".join(p.name for p in self.players)
                player.send(f"Joueurs connectés : {names}")
            elif verb in ("dire", "dis"):
                player.mark("say")
                self.say(player, rest.strip())
            elif verb in ROOMS[player.room]["exits"]:
                self.move(player, verb)
            elif verb.startswith("caress"):
                self.pet(player, normalize(rest))
            elif verb.startswith("pren"):
                self.take(player, normalize(rest))
            elif verb.startswith("ouvr"):
                if self.open(player, normalize(rest)):
                    return
            else:
                player.mark("unknown")
                player.send(UNKNOWN)

    # -- Actions

    def describe(self, player):
        room = ROOMS[player.room]
        if player.padlock_is_open and "description_unlocked" in room:
            player.send(room["description_unlocked"])
        else:
            player.send(room["description"])
        others = self.others_in(player.room, player)
        if others:
            player.send("Dans la pièce avec vous : " +", ".join(p.name for p in others) + ".")

    def move(self, player, direction):
        destination = ROOMS[player.room]["exits"][direction]
        self.tell_room(player.room, player, f"{player.name} part vers le {direction}.")
        player.room = destination
        self.tell_room(player.room, player, f"{player.name} arrive.")
        self.describe(player)

    def say(self, player, message):
        if not message:
            player.send("Dire quoi ? Par exemple : dire bonjour")
            return
        self.tell_room(player.room, player, f"{player.name} dit : {message}")
        player.send(f"Vous dites : {message}")
        if player.room == "salon":
            # Proof that the message went somewhere, even with nobody else in the
            # room. Only the speaker hears it, so a full salon isn't flooded.
            player.send(f"Le perroquet répète : {message.rstrip(' .!?')} !")

    def pet(self, player, target):
        if player.room != "jardin":
            player.send("Il n'y a rien à caresser ici.")
        elif "chien" not in target:
            player.send("Caresser quoi ?")
        elif player.has_key:
            player.send("WOOF! Le chien vous lèche la main.")
        else:
            player.dog_is_friendly = True
            player.send("WOOF! Le chien se roule par terre. Une petite clé brille à son collier.")
            self.tell_room(player.room, player, f"{player.name} caresse le chien.")

    def take(self, player, target):
        if player.room != "jardin" or player.has_key:
            player.send("Il n'y a rien à prendre ici.")
        elif "cle" not in target:  # normalized: « clé », « cle », « clef »
            player.send("Prendre quoi ?")
        elif not player.dog_is_friendly:
            player.send("Le chien grogne. Il ne vous connaît pas encore.")
        else:
            player.has_key = True
            player.send("Vous prenez la petite clé. Le chien remue la queue.")

    def open(self, player, target):
        """Returns True when the player has reached the paradis."""
        if player.room != "cuisine":
            player.send("Il n'y a rien à ouvrir ici.")
        elif "cadenas" in target:
            self.open_padlock(player)
        elif "frigo" in target:
            return self.open_fridge(player)
        else:
            player.send("Ouvrir quoi ?")
        return False

    def open_padlock(self, player):
        if player.padlock_is_open:
            player.send("Le cadenas est déjà ouvert.")
        elif not player.has_key:
            player.send("Le cadenas tient bon. Il faudrait une clé.")
            self.tell_room(player.room, player, f"{player.name} tire sur le cadenas du frigo.")
        else:
            player.padlock_is_open = True
            player.send("La clé tourne dans le cadenas. Le cadenas s'ouvre.")

    def open_fridge(self, player):
        if not player.padlock_is_open:
            player.send("Le frigo ne s'ouvre pas : le cadenas est fermé.")
            return False

        with self.lock:
            self.winners.append(player.name)
            position = len(self.winners)
        player.position = position
        self.tell_room(player.room, player, f"{player.name} ouvre le frigo... et disparaît dedans !")
        player.room = "paradis"
        player.send("Le frigo s'ouvre sur une lumière aveuglante...")
        player.send(PARADISE)
        self.tell_everyone(f"*** {player.name} a trouvé le paradis, en position {position} ! ***")
        self.log(f"*** {player.name} : position {position}")
        return True


if __name__ == "__main__":
    arguments = [a for a in sys.argv[1:] if not a.startswith("--")]
    port = int(arguments[0]) if arguments else 12345
    grid = "--log" not in sys.argv and sys.stdout.isatty()
    locale.setlocale(locale.LC_ALL, "")  # so that curses writes the accents
    server = GameServer("0.0.0.0", port, grid)
    try:
        server.start()
    except KeyboardInterrupt:
        pass
    # The grid is gone with curses: the ranking stays in the terminal.
    if server.winners:
        print("Paradis : " + ", ".join(f"{i}. {name}" for i, name in enumerate(server.winners, 1)))
