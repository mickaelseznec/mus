import uuid

from collections import UserList, deque
from itertools import chain

from MusExceptions import *

class Player:
    def __init__(self, player_id, public_id):
        self.public_id = public_id
        self.player_id = player_id
        self.team_reference = None
        self.can_speak = False
        self._cards = []

    @property
    def team_id(self):
        if self.team_reference:
            return self.team_reference.team_id
        return None

    def draw_new_hand(self, packet):
        self._cards = sorted(packet.draw() for _ in range(4))

    def exchange_cards(self, index_set, packet):
        for index in index_set:
            self._cards[index] = packet.exchange(self._cards[index])
        self._cards = sorted(self._cards)

    def get_cards(self):
        return self._cards

    def __repr__(self):
        return "Player(public_id={}, team_id={})".format(self.public_id, self.team_id)


class Team(UserList):
    def __init__(self, team_id):
        self.team_id = team_id
        self.data = []

        self.begin_score = 0
        self.score = 0

    def add_score(self, score):
        self.score += score
        if self.score >= Game.score_max:
            self.score = Game.score_max
            raise TeamWonException


class PlayerManager:
    def __init__(self):
        self.teams = (Team(0), Team(1))
        self.echku_order = deque()
        self._id_counter = 0

    @staticmethod
    def get_opposite_team_id(team_id):
        return (team_id + 1) % 2

    @property
    def well_configured(self):
        return (len(self.teams[0]) == len(self.teams[1]) and
                (len(self.teams[0]) == 1 or len(self.teams[0]) == 2))

    def get_all_players_team_ordered(self):
        return tuple(chain(*self.teams))

    def get_all_players_echku_ordered(self):
        return tuple(self.echku_order)

    def get_player_by_id(self, player_id):
        for player in self.get_all_players_team_ordered():
            if player_id == player.player_id:
                return player
        else:
            return None

    def add_player(self, player_id, team_id):
        player = self.get_player_by_id(player_id)

        if player and player.team_id == team_id:
            return player.player_id, player.public_id

        if len(self.teams[team_id]) >= 2:
            raise ForbiddenActionException("Team %d already full" % team_id)

        if player is None:
            player = self._create_new_player()
        else:
            self._detach_player(player)
        self._attach_player(player, team_id)

        return player.player_id, player.public_id

    def remove_player(self, player_id):
        player = self.get_player_by_id(player_id)
        if not player:
            return

        self._detach_player(player)

    def initialise_echku_order(self):
        for player_1, player_2 in zip(*self.teams):
            self.echku_order.append(player_1)
            self.echku_order.append(player_2)

    def step_echku_order(self):
        self.echku_order.rotate()

    def has_finished(self):
        return any(team.score >= Game.score_max for team in self.teams)

    def winner_team(self):
        for i, team in enumerate(self.teams):
            if team.score >= Game.score_max:
                return i

    def authorise_player(self, speaking_player):
        for player in self.get_all_players_echku_ordered():
            player.can_speak = player == speaking_player

    def set_team_authorisation(self, team_id):
        for player in self.get_all_players_team_ordered():
            player.can_speak = (player.team_id == team_id)

    def authorise_next_team(self, team_id):
        next_team_id = PlayerManager.get_opposite_team_id(team_id)
        self.set_team_authorisation(next_team_id)

    def _create_new_player(self):
        player_id = uuid.uuid4().hex
        public_id = self._id_counter
        self._id_counter += 1

        return Player(player_id, public_id)

    def _detach_player(self, player):
        player_team = player.team_reference

        player.team_reference = None
        player_team.remove(player)

    def _attach_player(self, player, team_id):
        self.teams[team_id].append(player)
        player.team_reference = self.teams[team_id]



