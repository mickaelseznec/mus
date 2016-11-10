import random

class ForbiddenActionException(Exception):
    pass


class WrongPlayerException(ForbiddenActionException):
    pass


class TeamWonException(Exception):
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
        return sorted([c.value for c in self.hand]) > sorted([c.value for c in other.hand])


class PariakHand(Hand):
    def has_hand(self):
        values = [card.value for card in self.hand]
        counter = [values.count(value) for value in set(values)]
        if any(count >= 2 for count in counter):
            return True
        return False

    def group_pairs(self):
        values = [card.value for card in self.hand]
        return sorted(((values.count(value), value) for value in sorted(list(set(values)), reverse=True)), reverse=True)

    def has_double_pair(self):
        return all(pair[0] == 2 for pair in self.group_pairs()) or self.group_pairs()[0][0] == 4

    def has_triple(self):
        return any(pair[0] == 3 for pair in self.group_pairs())

    def has_double_only(self):
        return not self.has_double_pair() and any(pair[0] == 2 for pair in self.group_pairs())

    def bonus(self):
        if self.has_double_pair():
            return 3
        if self.has_triple():
            return 2
        if self.has_double_only():
            return 1
        return 0

    def __lt__(self, other):
        self_bonus, other_bonus = self.bonus(), other.bonus()
        if self_bonus != other_bonus:
            return self_bonus < other_bonus

        own_group, other_group = self.group_pairs(), other.group_pairs()
        return own_group < other_group


class JokuaHand(Hand):
    jokua_index = {(33 + i): i for i in range(8)}
    jokua_index.update({32: 8, 31: 9})

    def sum_cards(self):
        return sum(min(card.value, 10) for card in self.hand)

    def has_game(self):
        return self.sum_cards() > 30

    def bonus(self):
        card_sum = self.sum_cards()
        if card_sum > 31:
            return 2
        if card_sum == 31:
            return 3
        return 0

    def __lt__(self, other):
        if self.has_game():
            if not other.has_game():
                return False
            return JokuaHand.jokua_index[self.sum_cards()] < JokuaHand.jokua_index[other.sum_cards()]

        return self.sum_cards() < other.sum_cards()


class Packet:
    CARDS = [Card(i) for i in range(len(Card.COLORS) * len(Card.VALUES))]

    def __init__(self):
        self.used_cards = []
        self.unused_cards = []
        self.restore()

    def restore(self):
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
    def __init__(self, player_id, player_name):
        self.id = player_id
        self.name = player_name

        self.team = None
        self.index = None
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

    def __hash__(self):
        return hash(id(self))


class PlayerHolder:
    def __init__(self):
        self.teams = (Team(0), Team(1))
        self.echku = 0
        self.authorised_team = None
        self.authorised_player = None

    def has_finished(self):
        return any(team.score >= Game.score_max for team in self.teams)

    def winner_team(self):
        for i, team in enumerate(self.teams):
            if team.score >= Game.score_max:
                return i

    def add(self, player_id, player_name, team_number):
        if player_id in self:
            player = self[player_id]
            player.team.remove_player(player)
        self.get_team(team_number).add_player(Player(player_id, player_name))

    def remove(self, player_id):
        if player_id in self:
            player = self[player_id]
            player.team.remove_player(player)

    def get_all(self):
        return [player for team in self.teams for player in team.players]

    def get_all_echku_sorted(self):
        return sorted(self.get_all(), key=lambda player: player.index)

    def get_team(self, team_number):
        return self.teams[team_number]

    def authorise_echku_player(self):
        players = self.get_all_echku_sorted()
        self.authorised_player = players[0]
        for player in players:
            player.is_authorised = player == self.authorised_player

    def authorise_next_player(self):
        players = self.get_all_echku_sorted()
        self.authorised_player = players[(self.authorised_player.index + 1) % len(players)]
        for player in players:
            player.is_authorised = player == self.authorised_player

    def other_team(self, team):
        if team.number == 0:
            return self.teams[1]
        return self.teams[0]

    def authorise_team(self, team):
        self.authorised_team = team
        team.authorise(True)
        self.other_team(team).authorise(False)

    def authorise_echku_team(self):
        team = self.get_all_echku_sorted()[0].team
        team.authorise(True)
        self.other_team(team).authorise(False)

    def can_start(self):
        team_0_size = len(self.get_team(0))
        return team_0_size == len(self.get_team(1)) and (team_0_size == 1 or team_0_size == 2)

    def set_initial_echku(self):
        index = 0
        for i in range(len(self.teams[0])):
            for team in self.teams:
                team.players[i].index = index
                index = index + 1
        self.echku = self.get_all_echku_sorted()[0]

    def set_echku(self):
        players = self.get_all_echku_sorted()
        for player in players:
            player.index = (player.index + 1) % len(players)
        self.echku = self.get_all_echku_sorted()[0]

    def __iter__(self):
        return iter(self.get_all())

    def __contains__(self, player_id):
        return player_id in [player.id for player in self.get_all()]

    def __getitem__(self, player_id):
        for other in self.get_all():
            if player_id == other.id:
                return other
        raise IndexError

class Team:
    def __init__(self, number):
        self.number = number
        self.score = 0
        self.said = ""
        self.is_authorised = False
        self.players = []

    def add_score(self, score):
        self.score += score
        if self.score >= Game.score_max:
            raise TeamWonException

    def add_player(self, player):
        if player not in self.players:
            player.team = self
            self.players.append(player)

    def remove_player(self, player):
        if player in self.players:
            player.team = None
            self.players.remove(player)

    def authorise(self, yes_or_no):
        for player in self.players:
            player.is_authorised = yes_or_no

    def toggle_authorisation(self):
        for player in self.players:
            player.is_authorised = not player.is_authorised

    def __iter__(self):
        return iter(self.players)

    def __contains__(self, player):
        return player in self.players

    def __len__(self):
        return len(self.players)


class GameState:
    def __init__(self, players, packet):
        self.players = players
        self.packet = packet
        self.actions = []

    def actions_authorised(self):
        return self.actions

    def players_authorised(self):
        return [p.id for p in self.players.get_all() if p.is_authorised]

    def is_player_authorised(self, player_id):
        return player_id in self.players_authorised()

    def authorise_next_player(self):
        self.players.authorise_next_player()

    def authorise_opposite_team(self, player_id):
        self.players.authorise_team(self.players.other_team(self.players[player_id].team))

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
        self.players.set_initial_echku()


class Speaking(GameState):
    def __init__(self, players, packet):
        super().__init__(players, packet)
        self.actions = ["mus", "mintza"]

    def handle(self, action, player_id, *args):
        if action == "mus":
            self.players[player_id].team.said = "mus"
            if all(team.said == "mus" for team in self.players.teams):
                return "Trading"
            self.authorise_opposite_team(player_id)
            return "Speaking"
        elif action == "mintza":
            return "Haundia"

    def prepare(self):
        self.players.authorise_echku_team()

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
    has_bonus = False
    HandType = Hand

    def __init__(self, players, packet):
        super().__init__(players, packet)
        self.actions = ["paso", "imido", "tira", "gehiago", "hordago", "kanta", "idoki", "ok"]
        self.bet = 0
        self.bonus = 0
        self.deffered = True
        self.engaged = False
        self.hor_daged = False
        self.proposal = 0
        self.winner = None

    def compute_winner(self):
        if not self.deffered:
            return
        echku_order = self.players.get_all_echku_sorted()
        for i in range(len(echku_order)):
            for j in range(i, len(echku_order)):
                hand_1 = self.HandType(echku_order[i].cards)
                hand_2 = self.HandType(echku_order[j].cards)
                if hand_1 < hand_2:
                    echku_order[i], echku_order[j] = echku_order[j], echku_order[i]
        self.winner = echku_order[0].team

    def compute_bonus(self):
        if self.has_bonus and self.engaged:
            for player in self.players:
                if player.team_number == self.winner:
                    self.bonus += self.HandType(player.cards).bonus()

    def actions_authorised(self):
        actions = []
        if self.hor_daged:
            actions += "kanta", "tira"
        else:
            actions += "gehiago", "hordago"
            if not self.engaged:
                actions += "paso", "imido"
            else:
                actions += "tira", "idoki"
        return actions

    def prepare(self):
        self.players.authorise_echku_player()
        self.winner = None
        self.bet = 1
        self.deffered = True
        self.engaged = False
        self.hor_daged = False
        self.proposal = 0
        self.bonus = 0

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
            self.engaged = True
            self.authorise_opposite_team(player_id)
            return self.own_state
        elif action == "hordago":
            self.hor_daged = True
            bet = Game.score_max - self.players.teams[self.players[player_id].team_number].score
            return self.handle("gehiago", player_id, str(bet))
        elif action == "tira":
            self.deffered = False
            self.winner = self.players.other_team(self.players[player_id].team)
            try:
                self.players.other_team(self.players[player_id].team).add_score(self.bet)
            except TeamWonException:
                return "Finished"
            return self.next_state
        elif action == "idoki":
            self.bet += self.proposal
            return self.next_state
        elif action == "kanta":
            self.bet += self.proposal
            return "Finished"

    def clean_up(self):
        self.compute_winner()
        self.compute_bonus()


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
    has_bonus = True

    def __init__(self, players, packet):
        super().__init__(players, packet)
        self.no_bet = False
        self.no_winner = False

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
        while not self.players.authorised_player.has_hand:
            self.players.authorise_next_player()

    def handle(self, action, player_id, *args):
        if action == 'ok':
            return self.next_state
        return super().handle(action, player_id, *args)

    def compute_winner(self):
        if not self.no_winner:
            super().compute_winner()

    def prepare(self):
        super().prepare()
        self.no_bet = False
        self.no_winner = False
        self.bet = 1
        for player in self.players:
            player.has_hand = PariakHand(player.cards).has_hand()
        if all(not player.has_hand for player in self.players):
            self.no_winner = True
            self.no_bet = True
            self.deffered = False
            self.bet = 0
            return
        if not (any(player.has_hand for player in self.players.get_team(0)) and
                any(player.has_hand for player in self.players.get_team(1))):
            self.compute_winner()
            self.no_bet = True
            self.bet = 0
            self.deffered = False
            self.engaged = True


class Jokua(BetState):
    own_state = "Jokua"
    next_state = "Finished"
    HandType = JokuaHand
    has_bonus = True

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
            player.has_game = JokuaHand(player.cards).has_game()
        if any(player.has_game for player in self.players):
            if not (any(player.has_game for player in self.players.get_team(0)) and
                    any(player.has_game for player in self.players.get_team(1))):
                self.compute_winner()
                self.no_bet = True
                self.bet = 0
                self.engaged = True
                self.deffered = False
        else:
            self.false_game = True

    def compute_bonus(self):
        if self.false_game and self.engaged:
            self.bonus = 1
        else:
            super().compute_bonus()

class Finished(GameState):
    def __init__(self, players, packet, game):
        super().__init__(players, packet)
        self.actions = ["ok"]
        self.game = game

    def is_player_authorised(self, player_id):
        return True

    def prepare(self):
        if not self.players.has_finished():
            try:
                for state in Game.bet_states:
                    if self.game.states[state].winner is not None:
                        if self.game.states[state].deffered:
                            self.players.teams[self.game.states[state].winner].add_score(self.game.states[state].bet)
                        self.players.teams[self.game.states[state].winner].add_score(self.game.states[state].bonus)
            except TeamWonException:
                self.game.finished = True

    def handle(self, action, player_id, *args):
        return "Speaking"

    def clean_up(self):
        self.packet.restore()
        for player in self.players:
            player.cards = sorted(self.packet.take(4))
        self.players.sort()
        if self.players.has_finished():
            for team in self.players.teams:
                team.score = 0
            self.players.set_echku(0)
        else:
            self.players.set_echku()


class Game:
    score_max = 40
    bet_states = ["Haundia", "Tipia", "Pariak", "Jokua"]

    def __init__(self, game_id):
        self.finished = False
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
        return len(self.players.get_team(team_number)) < 2

    def action(self, action, player_id, *args):
        #print("Received action '" + action +"' from", player_id, "with args:", *args)
        next_state = self.states[self.current].run(action, player_id, *args)
        if next_state != self.current:
            self.states[self.current].clean_up()
            self.current = next_state
            self.states[self.current].prepare()
