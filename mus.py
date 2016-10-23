import random

class Card():
    COLORS = ["copas", "espadas", "bastos", "oros"]
    VALUES = [1, 2, 3, 4, 5, 6, 7, 10, 11, 12]

    def __init__(self, index):
        self.value = Card.VALUES[int(index / len(Card.COLORS))]
        self.color = Card.COLORS[index % len(Card.COLORS)]

    def index(self):
        return Card.COLORS.index(self.color) + len(Card.COLORS) * Card.VALUES.index(self.value)

    def __str__(self):
        return str(self.value) + '-' + self.color

class Packet():
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
            #import ipdb; ipdb.set_trace()
            taken = self.unused_cards
            self.new_packet()
            taken.append(self.unused_cards[0:-delta])
            self.unused_cards = self.unused_cards[-delta:]
            return taken

    def trade(self, card):
        self.used_cards.append(card)
        return self.take(1)


class Player():
    def __init__(self, player_id, player_name):
        self.id = player_id
        self.name = player_name
        self.cards = None
        self.asks = []

    def get_cards(self):
        return self.cards

    def __str__(self):
        return self.name

    def __eq__(self, other):
        return self.id == other.id


class Team():
    def __init__(self):
        self.players = []
        self.score = 0
        self.said = ""

    @classmethod
    def other_team(cls, team_number):
        return (team_number + 1) % 2

    def add_player(self, new_player):
        self.players.append(new_player)

    def remove_player(self, player):
        self.players.remove(player)

    def get(self, player):
        return self.players[self.players.index(player)]

    def __len__(self):
        return len(self.players)

    def __contains__(self, player):
        return player in self.players


class Turn():
    TURNS = ["Truke", "Handiak", "Txikiak", "Pareak", "Jokoa"]
    SUBTURNS = ["Speak", "Cards"]
    def __init__(self, teams):
        self.current = self.TURNS[0]
        self.sub_current = self.SUBTURNS[0]
        self.packet = Packet()
        self.teams = teams
        self.current_team = 0
        self.bet = 0
        self.proposal = 0
        self.distribute_cards()

    def next(self):
        self.current_team = Team.other_team(self.current_team)
        self.current = Turn.TURNS[Turn.TURNS.index(self.current) + 1]

    def distribute_cards(self):
        for team in self.teams:
            for player in team.players:
                player.cards = self.packet.take(4)

    def next_sub(self):
        if self.sub_current == "Speak":
            for team in self.teams:
                for player in team.players:
                    player.ready = False
                    player.asks = set()
            self.sub_current = Turn.SUBTURNS[1]
        elif self.sub_current == "Cards":
            for team in self.teams:
                team.said = ""
                for player in team.players:
                    for i in list(player.asks):
                        player.cards[i] = self.packet.trade(player.cards[i])[0]
            self.sub_current = Turn.SUBTURNS[0]
            self.current_team = 0


class Game():
    def __init__(self, game_id):
        self.game_id = game_id
        self.teams = (Team(), Team())
        self.players_per_team = 0
        self.turn = None
        self.is_started = False
        self.is_finished = False

    def __contains__(self, player):
        return any(player in team for team in self.teams)

    def add_player(self, player, team_number):
        assert not self.is_started
        if player in self.teams[Team.other_team(team_number)]:
            self.teams[Team.other_team(team_number)].remove_player(player)
        if player not in self.teams[team_number]:
            self.teams[team_number].add_player(player)

    def remove_player(self, player):
        assert not self.is_started
        for team in self.teams:
            if player in team:
                team.remove_player(player)

    def can_start(self):
        return len(self.teams[0]) == len(self.teams[1]) and (
            len(self.teams[0]) == 1 or len(self.teams[0]) == 2)

    def can_join_team(self, team_number):
        return len(self.teams[team_number]) < 2

    def start(self):
        self.is_started = True
        self.players_per_team = len(self.teams[0])
        self.begin_set()

    def begin_set(self):
        self.turn = Turn(self.teams)

    def get_player(self, player):
        for team in self.teams:
            if player in team:
                return team.get(player)

    def play(self, play, player):
        if self.turn.current == Turn.TURNS[0]:
            if self.turn.sub_current == Turn.SUBTURNS[0]:
                assert player in self.teams[self.turn.current_team]
                assert play == "Mus" or play == "Minsa"
                self.teams[self.turn.current_team].said = play
                if play == "Minsa":
                    self.turn.next()
                elif all(team.said == "Mus" for team in self.teams):
                    self.turn.next_sub()
                else:
                    self.turn.current_team = Team.other_team(self.turn.current_team)
            elif self.turn.sub_current == Turn.SUBTURNS[1]:
                assert play == "Ready" or int(play) >= 0 and int(play) <= 3
                own_player = self.get_player(player)
                if play == "Ready":
                    own_player.ready = True
                else:
                    own_player.asks.add(int(play))
                if all(player.ready for team in self.teams for player in team.players):
                    self.turn.next_sub()
