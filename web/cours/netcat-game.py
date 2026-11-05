#!/usr/bin/env python3
"""
A text adventure that the whole class plays at once, over nc.

    python3 netcat-game.py [port]      # default 12345
    nc <address> 12345                 # on each student's machine

The commands are the server's protocol. `aide` lists the general ones
(directions, regarder, dire, qui, quitter); the actions that solve the game are
only hinted at by the room descriptions, everything else gets « Commande
inconnue. ».

Solution: give a name, `sud`, `caresser` (the dog), `prendre` (the key on its
collar), `nord`, `nord`, `ouvrir` (the fridge). Players in the same room see
each other come and go, and `dire <message>` talks to them: the server relays
every message, the clients never connect to each other. Each player who reaches
the paradis is announced to everyone with their position, then the server
closes their connection.

The server console logs every connection and every command received, and can
be projected.
"""

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
  nord, sud            se déplacer
  regarder             décrire la pièce à nouveau
  dire <message>       parler aux joueurs de la même pièce
  qui                  lister les joueurs connectés
  aide                 afficher cette aide
  quitter              se déconnecter
D'autres actions existent : les descriptions des pièces les suggèrent."""

UNKNOWN = "Commande inconnue. (« aide » pour la liste des commandes)"


def normalize(text):
    """Lowercase and without accents, so that « clé » and « cle » both match."""
    decomposed = unicodedata.normalize("NFD", text.lower())
    return "".join(c for c in decomposed if unicodedata.category(c) != "Mn")


class Player:
    def __init__(self, connection, address):
        self.connection = connection
        self.address = address
        self.name = None
        self.room = "salon"
        self.dog_is_friendly = False
        self.has_key = False
        self.send_lock = threading.Lock()

    def send(self, text):
        # Other players' threads send to this one too (arrivals, messages).
        with self.send_lock:
            try:
                self.connection.sendall((text + "\n").encode())
            except OSError:
                pass


class GameServer:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.players = []
        self.winners = []
        self.lock = threading.Lock()

    def start(self):
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((self.host, self.port))
        server.listen()
        print(f"Serveur en attente de connexions sur le port {self.port}...")

        while True:
            connection, address = server.accept()
            print(f"Connexion depuis {address[0]}")
            player = Player(connection, address)
            threading.Thread(target=self.handle_client, args=(player,), daemon=True).start()

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
            with self.lock:
                if player in self.players:
                    self.players.remove(player)
            if player.name and player.room != "paradis":
                self.tell_room(player.room, player, f"{player.name} disparaît.")
            print(f"Déconnexion de {player.name or player.address[0]}")
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

        print(f"{player.address[0]} s'appelle {player.name}")
        self.tell_room(player.room, player, f"{player.name} arrive dans le salon.")
        player.send(f"Bonjour {player.name} ! (« aide » pour la liste des commandes)")
        self.describe(player)
        return True

    def play(self, player, lines):
        for line in lines:
            line = line.strip()
            if not line:
                continue
            print(f"[{player.name}] {line}")

            verb, _, rest = line.partition(" ")
            verb = normalize(verb)

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
                self.say(player, rest.strip())
            elif verb in ROOMS[player.room]["exits"]:
                self.move(player, verb)
            elif verb.startswith("caress"):
                self.pet(player)
            elif verb.startswith("pren"):
                self.take(player)
            elif verb.startswith("ouvr"):
                if self.open_fridge(player):
                    return
            else:
                player.send(UNKNOWN)

    # -- Actions

    def describe(self, player):
        player.send(ROOMS[player.room]["description"])
        others = self.others_in(player.room, player)
        if others:
            player.send("Ici : " + ", ".join(p.name for p in others) + ".")

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

    def pet(self, player):
        if player.room != "jardin":
            player.send("Il n'y a rien à caresser ici.")
        elif player.has_key:
            player.send("WOOF! Le chien vous lèche la main.")
        else:
            player.dog_is_friendly = True
            player.send("WOOF! Le chien se roule par terre. Une petite clé brille à son collier.")
            self.tell_room(player.room, player, f"{player.name} caresse le chien.")

    def take(self, player):
        if player.room != "jardin" or player.has_key:
            player.send("Il n'y a rien à prendre ici.")
        elif not player.dog_is_friendly:
            player.send("Le chien grogne. Il ne vous connaît pas encore.")
        else:
            player.has_key = True
            player.send("Vous prenez la petite clé. Le chien remue la queue.")

    def open_fridge(self, player):
        if player.room != "cuisine":
            player.send("Il n'y a rien à ouvrir ici.")
            return False
        if not player.has_key:
            player.send("Le cadenas tient bon. Il faudrait une clé.")
            self.tell_room(player.room, player, f"{player.name} tire sur le cadenas du frigo.")
            return False

        with self.lock:
            self.winners.append(player.name)
            position = len(self.winners)
        self.tell_room(player.room, player, f"{player.name} ouvre le frigo... et disparaît dedans !")
        player.room = "paradis"
        player.send("La clé tourne dans le cadenas. Le frigo s'ouvre sur une lumière aveuglante...")
        player.send(PARADISE)
        self.tell_everyone(f"*** {player.name} a trouvé le paradis, en position {position} ! ***")
        print(f"*** {player.name} : position {position}")
        return True


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 12345
    GameServer("0.0.0.0", port).start()
