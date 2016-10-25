import random

class ForbiddenActionException(Exception):
    pass


class WrongPlayerException(ForbiddenActionException):
    pass


class Card:
    COLORS = ["Copas", "Espadas", "Bastos", "Oros"]
    VALUES = [1, 2, 3, 4, 5, 6, 7, 10, 11, 12]

    def __init__(self, index=None, value=None, color=None):
        if index is not None:
            self.value = Card.VALUES[int(index / len(Card.COLORS))]
            self.color = Card.COLORS[index % len(Card.COLORS)]
        else:
            if value not in Card.VALUES or color not in Card.COLORS:
                raise ForbiddenActionException
            self.value = value
            self.color = color

    @classmethod
    def has_hand(cls, cards):
        values = [card.value for card in cards]
        counter = [values.count(value) for value in set(values)]
        if any(count >= 2 for count in counter):
            return True
        return False

    @classmethod
    def has_game(cls, cards):
        return sum(min(card.value, 10) for card in cards) >= 30

    def index(self):
        return Card.COLORS.index(self.color) + len(Card.COLORS) * Card.VALUES.index(self.value)

    def __str__(self):
        return str(self.value) + ' - ' + self.color

    def __eq__(self, card):
        return self.index() == card.index()

    def __lt__(self, card):
        return self.index() < card.index()


class Hand:
    def __init__(self, cards):
        self.hand = cards


class HaundiaHand(Hand):
    def __lt__(self, other):
        return (sorted([c.value for c in self.hand], reverse=True)
                < sorted([c.value for c in other.hand], reverse=True))


class TipiaHand(Hand):
    def __lt__(self, other):
        return (sorted([c.value for c in self.hand]) > sorted([c.value for c in other.hand]))


class PariakHand(Hand):
    def group_pairs(self):
        values = [card.value for card in self.hand]
        return sorted(((values.count(value), value) for value in sorted(list(set(values)), reverse=True)), reverse=True)

    def has_double_pair(self):
        return all(pair[0] == 2 for pair in self.group_pairs()) or self.group_pairs()[0][0] == 4

    def has_triple(self):
        return any(pair[0] == 3 for pair in self.group_pairs())

    def has_double_only(self):
        return not self.has_double_pair() and any(pair[0] == 2 for pair in self.group_pairs())

    def __lt__(self, other):
        own_group, other_group = self.group_pairs(), other.group_pairs()

        if self.has_double_pair():
            if not other.has_double_pair():
                return False
            return max(own_group, other_group, key=lambda e: e[1]) == other_group
        if self.has_triple():
            return other.has_double_pair() or other.has_triple() and own_group < other_group
        if self.has_double_only():
            return other.has_double_pair() or other.has_triple() or other.has_double_only() and own_group < other_group
        return own_group < other_group


class JokuaHand(Hand):
    def __lt__(self, other):
        return True


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
            return [Card(index) for index in taken]
        else:
            taken = self.unused_cards
            self.new_packet()
            taken += self.unused_cards[0:-delta]
            self.unused_cards = self.unused_cards[-delta:]
            return [Card(index) for index in taken]

    def trade(self, card):
        self.used_cards.append(card.index())
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
        self.has_game = False
        self.has_hand = False

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

    def get_player_opposite_team(self, player_id):
        return self.teams[Team.other_team(self[player_id].team_number)]

    def authorised(self):
        return [player.id for player in self.players if player.is_authorised]

    def authorise_player(self, index=None):
        if index is None:
            self.authorised_player = self.echku
        else:
            self.authorised_player = index
        for i, player in enumerate(self.players):
            player.is_authorised = (i == self.authorised_player)

    def authorise_next_player(self):
        self.authorise_player((self.authorised_player + 1) % len(self.players))

    def authorise_team(self, team_number=None):
        if team_number is None:
            team_number = self.players[self.echku].team_number
        self.authorised_team = team_number
        for player in self.players:
            player.is_authorised = (player.team_number == team_number)

    def authorise_opposite_team(self, player_id):
        self.authorise_team(Team.other_team(self[player_id].team_number))

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

    def by_echku(self):
        return self.players[self.echku:] + self.players[:self.echku]

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
        self.actions = ["mus", "mintza"]

    def handle(self, action, player_id, *args):
        if action == "mus":
            self.players.get_player_team(player_id).said = "mus"
            if all(team.said == "mus" for team in self.players.teams):
                return "Trading"
            self.players.authorise_next_team()
            return "Speaking"
        elif action == "mintza":
            return "Haundia"

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


class BetState(GameState):
    own_state = ""
    next_state = ""

    def __init__(self, players, packet):
        super().__init__(players, packet)
        self.actions = ["paso", "imido", "tira", "gehiago", "hor_dago", "kanta", "idoki", "ok"]
        self.bet = 0
        self.deffered = True
        self.engaged = False
        self.hor_daged = False
        self.proposal = 0
        self.winner = None

    def compute_winner(self):
        echku_order = self.players.by_echku()
        for i in range(len(echku_order)):
            for j in range(i, len(echku_order)):
                hand_1 = self.HandType(echku_order[i].cards)
                hand_2 = self.HandType(echku_order[j].cards)
                if hand_1 < hand_2:
                    echku_order[i], echku_order[j] = echku_order[j], echku_order[i]
        return echku_order[0].team_number

    def actions_authorised(self):
        actions = []
        if self.hor_daged:
            actions += "kanta", "tira"
        else:
            actions += "gehiago", "hor_dago"
            if not self.engaged:
                actions += "paso", "imido"
            else:
                actions += "tira", "idoki"
        return actions

    def prepare(self):
        self.players.authorise_player()
        self.bet = 1
        self.deffered = True
        self.engaged = False
        self.hor_daged = False
        self.proposal = 0

    def authorise_next_player(self):
        self.players.authorise_next_player()

    def authorise_opposite_team(self, player_id):
        self.players.authorise_opposite_team(player_id)

    def everybody_is_mus(self):
        return self.players.authorised_player == self.players.echku

    def handle(self, action, player_id, *args):
        if action == "paso":
            self.authorise_next_player()
            if self.everybody_is_mus():
                self.deffered = True
                return self.next_state
            return self.own_state
        elif action == "imido":
            self.proposal = 1
            self.engaged = True
            self.authorise_opposite_team(player_id)
            return self.own_state
        elif action == "gehiago":
            proposal = int(args[0])
            if proposal <= 0 or not self.engaged and proposal == 1:
                raise ForbiddenActionException
            if not self.engaged:
                proposal -= 1
            self.bet += self.proposal
            self.proposal = proposal
            if not self.engaged:
                self.engaged = True
            self.authorise_opposite_team(player_id)
            return self.own_state
        elif action == "hor_dago":
            self.hor_daged = True
            self.deffered = False
            self.authorise_opposite_team(player_id)
            return self.own_state
        elif action == "tira":
            self.deffered = False
            self.players.get_player_opposite_team(player_id).score += self.bet
            if self.players.get_player_opposite_team(player_id).score >= Game.score_max:
                return "Finished"
            return self.next_state
        elif action == "idoki":
            self.bet += self.proposal
            return self.next_state
        elif action == "kanta":
            self.deffered = False
            return "Finished"

    def clean_up(self):
        self.winner = self.compute_winner()


class Haundia(BetState):
    own_state = "Haundia"
    next_state = "Tipia"
    HandType = HaundiaHand


class Tipia(BetState):
    own_state = "Tipia"
    next_state = "Pariak"
    HandType = TipiaHand


class Pariak(BetState):
    own_state = "Pariak"
    next_state = "Jokua"
    HandType = PariakHand

    def __init__(self, players, packet):
        super().__init__(players, packet)
        self.no_bet = False

    def is_player_authorised(self, player_id):
        if self.no_bet:
            return True
        return self.players[player_id].has_hand and super().is_player_authorised(player_id)

    def actions_authorised(self):
        if self.no_bet:
            return ['ok']
        return super().actions_authorised()

    def authorise_next_player(self):
        self.players.authorise_next_player()
        while not self.players.players[self.players.authorised_player].has_hand:
            self.players.authorise_next_player()

    def handle(self, action, player_id, *args):
        if action == 'ok':
            return self.next_state
        return super().handle(action, player_id, *args)

    def prepare(self):
        super().prepare()
        self.no_bet = False
        self.bet = 1
        for player in self.players:
            player.has_hand = Card.has_hand(player.cards)
        if not (any(player.has_hand for player in self.players.by_team(0)) and
            any(player.has_hand for player in self.players.by_team(1))):
            self.no_bet = True
            self.bet = 0
            self.deffered = False


class Jokua(BetState):
    own_state = "Jokua"
    next_state = "Finished"

    def __init__(self, players, packet):
        super().__init__(players, packet)
        self.no_bet = False
        self.false_game = False

    def is_player_authorised(self, player_id):
        if self.no_bet:
            return True
        if not self.false_game:
            return self.players[player_id].has_game and super().is_player_authorised(player_id)
        return super().is_player_authorised(player_id)

    def actions_authorised(self):
        if self.no_bet:
            return ['ok']
        return super().actions_authorised()

    def handle(self, action, player_id, *args):
        if action == 'ok':
            return self.next_state
        return super().handle(action, player_id, *args)

    def prepare(self):
        super().prepare()
        self.no_bet = False
        self.false_game = False
        for player in self.players:
            player.has_game = Card.has_game(player.cards)
        if any(player.has_game for player in self.players):
            if not (any(player.has_game for player in self.players.by_team(0)) and
                    any(player.has_game for player in self.players.by_team(1))):
                self.no_bet = True
                self.bet = 0
                self.deffered = False
        else:
            self.false_game = True


class Finished(GameState):
    def __init__(self, players, packet, game):
        super().__init__(players, packet)
        self.actions = ["ok", "new_game"]
        self.game = game

    def prepare(self):
        for state in Game.bet_states:
            self.game.states[state].add_points()

    def handle(self, action, player_id, *args):
        return "Speaking"


class Game:
    score_max = 40
    bet_states = ["Haundia", "Tipia", "Pariak", "Jokua"]

    def __init__(self, game_id):
        self.game_id = game_id
        self.players = PlayerHolder()
        self.packet = Packet()
        self.states = {
            "Waiting": Waiting(self.players, self.packet),
            "Speaking": Speaking(self.players, self.packet),
            "Trading": Trading(self.players, self.packet),
            "Haundia": Haundia(self.players, self.packet),
            "Tipia": Tipia(self.players, self.packet),
            "Pariak": Pariak(self.players, self.packet),
            "Jokua": Jokua(self.players, self.packet),
            "Finished": Finished(self.players, self.packet, self),
        }
        self.current = "Waiting"

    @property
    def state(self):
        return self.states[self.current]

    def can_join_team(self, team_number):
        return len(self.players.by_team(team_number)) < 2

    def action(self, action, player_id, *args):
        #print("Received action '" + action +"' from", player_id, "with args:", *args)
        next_state = self.states[self.current].run(action, player_id, *args)
        if next_state != self.current:
            self.states[self.current].clean_up()
            self.current = next_state
            self.states[self.current].prepare()
