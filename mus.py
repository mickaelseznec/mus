import random

COLORS = ["copas", "espadas", "bastos", "oros"]
VALUES = [1, 2, 3, 4, 5, 6, 7, 10, 11, 12]
CARDS = [(color, value) for color in COLORS for value in VALUES]

class Player():
    def __init__(self, player_id, player_name):
        self.id = player_id
        self.name = player_name
        self.cards = None

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

    def add_player(self, new_player):
        self.players.append(new_player)

    def remove_player(self, player):
        self.players.remove(player)

    def __len__(self):
        return len(self.players)

    def __contains__(self, player):
        return player in self.players


class Turn():
    TURNS = ["Truke", "Handiak", "Txikiak", "Pareak", "Jokoa"]
    def __init__(self):
        self.turn = self.TURNS[0]
        self.bet = 0
        self.proposal = 0


class Game():
    def __init__(self, game_id):
        self.game_id = game_id
        self.teams = (Team(), Team())
        self.players_per_team = 0
        self.current_team = 0
        self.turn = None
        self.is_started = False
        self.is_finished = False
        self.card_numbers = list(range(len(CARDS)))

    def __contains__(self, player):
        return any(player in team for team in self.teams)

    def other_team(self, team_number):
        return (team_number + 1) % 2

    def add_player(self, player, team_number):
        if player in self.teams[self.other_team(team_number)]:
            self.teams[self.other_team(team_number)].remove_player(player)
        if player not in self.teams[team_number]:
            self.teams[team_number].add_player(player)

    def remove_player(self, player):
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
        self.distribute_cards()
        self.turn = Turn()

    def distribute_cards(self):
        random.shuffle(self.card_numbers)
        for team in self.teams:
            for player in team.players:
                player.cards = (CARDS[self.card_numbers[0]], CARDS[self.card_numbers[1]])
                self.card_numbers = self.card_numbers[2:]

    def play(self, play):
        #do stuff
        self.current_team = self.other_team(self.current_team)
