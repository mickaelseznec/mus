import random

class ForbiddenActionException(Exception):
    pass


class WrongPlayerException(ForbiddenActionException):
    pass


class Card:
    COLORS = ["Copas", "Espadas", "Bastos", "Oros"]
    VALUES = [1, 2, 3, 4, 5, 6, 7, 10, 11, 12]

    def __init__(self, index):
        self.value = Card.VALUES[int(index / len(Card.COLORS))]
        self.color = Card.COLORS[index % len(Card.COLORS)]

    def index(self):
        return Card.COLORS.index(self.color) + len(Card.COLORS) * Card.VALUES.index(self.value)

    def __str__(self):
        return str(self.value) + '-' + self.color

class Packet:
    CARDS = [Card(i) for i in range(len(Card.COLORS) * len(Card.VALUES))]

    def __init__(self):
        self.unused_cards = []
        self.used_cards = list(range(len(Packet.CARDS)))
        self.new_packet()

    def new_packet(self):
        self.unused_cards = self.used_cards
        random.shuffle(self.unused_cards)
        self.used_cards = []

    def take(self, n):
        delta = len(self.unused_cards) - n
        if delta > 0:
            taken = self.unused_cards[0: n]
            self.unused_cards = self.unused_cards[n:]
            return taken
        else:
            taken = self.unused_cards
            self.new_packet()
            taken.append(self.unused_cards[0:-delta])
            self.unused_cards = self.unused_cards[-delta:]
            return taken

    def trade(self, card):
        self.used_cards.append(card)
        return self.take(1)


class Player:
    def __init__(self, player_id, player_name, team_number):
        self.id = player_id
        self.name = player_name
        self.team_number = team_number
        self.is_authorised = False
        self.said = ""
        self.cards = []
        self.asks = set()

    def get_cards(self):
        return self.cards

    def __str__(self):
        return self.name

    def __eq__(self, other):
        return self.id == other.id


class PlayerHolder:
    def __init__(self):
        self.teams = (Team(), Team())
        self.players = []
        self.echku = 0
        self.authorised_team = 0
        self.authorised_player = 0

    def add(self, player_id, player_name, team_number):
        if player_id in self:
            self[player_id].team_number = team_number
        else:
            self.players.append(Player(player_id, player_name, team_number))

    def remove(self, player_id):
        for i, player in enumerate(self.players):
            if player.id == player_id:
                self.players.pop(i)

    def get_player_team(self, player_id):
        return self.teams[self[player_id].team_number]

    def authorised(self):
        return [player.id for player in self.players if player.is_authorised]

    def authorise_player(self, player_id=None):
        if player_id is None:
            player_id = self.player[self.echku].id
        self.authorised_player = player_id
        for player in self.players:
            player.is_authorised (player.id == player_id)

    def authorise_next_player(self):
        self.authorise_player((self.authorised_player + 1) % len(self.players))

    def authorise_team(self, team_number=None):
        if team_number is None:
            team_number = self.players[self.echku].team_number
        self.authorised_team = team_number
        for player in self.players:
            player.is_authorised = (player.team_number == team_number)

    def authorise_next_team(self):
        self.authorise_team(Team.other_team(self.authorised_team))

    def by_team(self, team_number):
        return [player for player in self.players if player.team_number == team_number]

    def can_start(self):
        return len(self.by_team(0)) == len(self.by_team(1)) and (
            len(self.by_team(0)) == 1 or len(self.by_team(0)) == 2)

    def sort(self):
        if len(self.players) == 2:
            return
        for i in range(len(self.players) - 1):
            if self.players[i].team_number == self.players[i + 1].team_number:
                self.players[i], self.players[i + 1] = self.players[i + 1], self.players[i]

    def set_echku(self, n=None):
        if n is not None:
            self.echku = n
        else:
            self.echku = (self.echku + 1) % len(self.players)


    def __iter__(self):
        return iter(self.players)

    def __contains__(self, player_id):
        return player_id in [player.id for player in self.players]

    def __getitem__(self, player_id):
        for player in self.players:
            if player.id == player_id:
                return player
        raise IndexError

class Team:
    def __init__(self):
        self.score = 0
        self.said = ""

    @classmethod
    def other_team(cls, team_number):
        return (team_number + 1) % 2


class GameState:
    def __init__(self, players, packet):
        self.players = players
        self.packet = packet
        self.actions = []

    def actions_authorised(self):
        return self.actions

    def players_authorised(self):
        return self.players.authorised()

    def is_player_authorised(self, player_id):
        return player_id in self.players_authorised()

    def handle(self, action, player_id, *args):
        raise NotImplementedError

    def run(self, action, player_id, *args):
        if action not in self.actions_authorised():
            raise ForbiddenActionException
        if not self.is_player_authorised(player_id):
            raise WrongPlayerException
        return self.handle(action, player_id, *args)

    def prepare(self):
        pass

    def clean_up(self):
        pass


class Waiting(GameState):
    def __init__(self, players, packet):
        super().__init__(players, packet)
        self.actions = ["add_player", "remove_player", "start"]

    def actions_authorised(self):
        actions = ["add_player", "remove_player"]
        if self.players.can_start():
            actions.append("start")
        return actions

    def is_player_authorised(self, player_id):
        return True

    def handle(self, action, player_id, *args):
        if action == "add_player":
            if (len(args) != 2 and
                    not 0 <= int(args[1]) <= 1):
                raise ForbiddenActionException
            self.players.add(player_id, args[0], int(args[1]))
            return "Waiting"
        elif action == "remove_player":
            self.players.remove(player_id)
            return "Waiting"
        elif action == "start":
            if not self.players.can_start:
                raise ForbiddenActionException
            return "Speaking"

    def clean_up(self):
        for player in self.players:
            player.cards = sorted(self.packet.take(4))
        self.players.sort()
        self.players.set_echku(0)


class Speaking(GameState):
    def __init__(self, players, packet):
        super().__init__(players, packet)
        self.actions = ["mus", "minsa"]

    def handle(self, action, player_id, *args):
        if action == "mus":
            self.players.get_player_team(player_id).said = "mus"
            if all(team.said == "mus" for team in self.players.teams):
                return "Trading"
            self.players.authorise_next_team()
            return "Speaking"
        elif action == "minsa":
            return "Handiak"

    def prepare(self):
        self.players.authorise_team()

    def clean_up(self):
        for team in self.players.teams:
            team.said = ""


class Trading(GameState):
    def __init__(self, players, packet):
        super().__init__(players, packet)
        self.actions = ["change", "confirm"]

    def is_player_authorised(self, player_id):
        return True

    def handle(self, action, player_id, *args):
        if action == "confirm":
            self.players[player_id].said = "confirm"
            if all(player.said == "confirm" for player in self.players):
                for player in self.players:
                    for i in list(player.asks):
                        player.cards[i] = self.packet.trade(player.cards[i])[0]
                return "Speaking"
            return "Trading"
        else:
            if len(args) != 1 or not 0 <= int(args[0]) <= 3:
                raise ForbiddenActionException
            self.players[player_id].asks.add(int(args[0]))
            return "Trading"

    def prepare(self):
        for player in self.players:
            player.said = ""
            player.asks = set()

    def clean_up(self):
        for player in self.players:
            player.cards.sort()


class Game:
    def __init__(self, game_id):
        self.game_id = game_id
        self.players = PlayerHolder()
        self.packet = Packet()
        self.states = {
            "Waiting": Waiting(self.players, self.packet),
            "Speaking": Speaking(self.players, self.packet),
            "Trading": Trading(self.players, self.packet),
        }
        self.current = "Waiting"

    @property
    def state(self):
        return self.states[self.current]

    def can_join_team(self, team_number):
        return len(self.players.by_team(team_number)) < 2

    def action(self, action, player_id, *args):
        print("Received action '" + action +"' from ", player_id, "with args: ", *args)
        next_state = self.states[self.current].run(action, player_id, *args)
        if next_state != self.current:
            self.states[self.current].clean_up()
            self.current = next_state
            self.states[self.current].prepare()
