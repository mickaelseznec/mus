import json
import uuid

from abc import ABC, abstractmethod
from collections import UserList, deque
from copy import deepcopy
from itertools import chain

from cards import Card, Packet, Hand, HaundiaHand, TipiaHand, PariakHand, JokuaHand, JSONCardEncoder

class ForbiddenActionException(Exception):
    pass


class WrongPlayerException(ForbiddenActionException):
    pass


class TeamWonException(Exception):
    pass


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


class GameState(ABC):
    def __init__(self, game):
        self.game = game
        self.player_manager = game.player_manager
        self.current_player = None
        self.packet = game.packet
        self.attendees = {}
        self.player_status = {} # State-specific info about players
        self.team_status = {} # State-specific info about teams
        self.handle_map = {} # Function map for received commands
        self.history = []

    #Final
    def run(self, action, **kwargs):
        player_id = kwargs.get("player_id", None)

        if player_id is None and action != "add_player":
            raise ForbiddenActionException

        if action == "get_cards" and self.game.current_state != "Waiting Room":
            return json.dumps(self.player_manager.get_player_by_id(player_id).get_cards(),
                              cls=JSONCardEncoder)

        if action not in self.available_actions():
            raise ForbiddenActionException

        if not self.is_player_authorised(player_id):
            raise WrongPlayerException

        ret = self.handle_map[action](**kwargs)
        self.record(action, **kwargs)

        return ret

    #Final
    def on_entry(self):
        self.reset_attributes()
        self.set_attending()
        self.initialize_authorizations()

    @abstractmethod
    def available_actions(self):
        ...

    def initialize_authorizations(self):
        candidates = list(player for player in self.player_manager.get_all_players_echku_ordered()
                          if self.attendees[player.player_id])
        if len(candidates) != 0:
            self.current_player = candidates[0]
            self.player_manager.authorise_player(self.current_player)

    def authorise_next_player(self):
        candidates = list(player for player in self.player_manager.get_all_players_echku_ordered()
                          if self.attendees[player.player_id])

        current_index = candidates.index(self.current_player)
        self.current_player = candidates[(current_index + 1) % len(candidates)]
        self.player_manager.authorise_player(self.current_player)

    def reset_attributes(self):
        ...

    def set_attending(self):
        self.attendees = {player.player_id: True for
                          player in self.player_manager.get_all_players_echku_ordered()}

    def is_player_authorised(self, player_id):
        return (self.attendees[player_id] and
                self.player_manager.get_player_by_id(player_id).can_speak)

    def on_exit(self):
        ...

    @abstractmethod
    def public_representation(self):
        ...

    def record(self, action, **kwargs):
        self.history.append((action, kwargs))

    def reset_history(self):
        self.history = []


class WaitingRoom(GameState):
    def __init__(self, game):
        super().__init__(game)
        self.handle_map = {
            "add_player": self.handle_add_player,
            "remove_player": self.handle_remove_player,
            "start_game": self.handle_start_game,
        }

    def available_actions(self):
        actions = ["add_player", "remove_player"]

        if self.player_manager.well_configured:
            actions.append("start_game")

        return actions

    def on_exit(self):
        for player in self.player_manager.get_all_players_team_ordered():
            player.draw_new_hand(self.packet)
        self.player_manager.initialise_echku_order()

    def public_representation(self):
        ...

    def is_player_authorised(self, player_id):
        return True

    def handle_add_player(self, team_id, player_id=None):
        if team_id != 1 and team_id != 2:
            raise ForbiddenActionException("Invalid team team_id %d" % team_id)
        # 0-indexing FTW
        team_id -= 1

        return self.player_manager.add_player(player_id, team_id)

    def handle_remove_player(self, **kwargs):
        player_id = kwargs["player_id"]
        return self.player_manager.remove_player(player_id)

    def handle_start_game(self, **kwargs):
        self.game.current_state = "Speaking"


class Speaking(GameState):
    def __init__(self, game):
        super().__init__(game)
        self.handle_map = {
            "mus": self.handle_mus,
            "mintza": self.handle_mintza,
        }

    def available_actions(self):
        return ["mus", "mintza"]

    def reset_attributes(self):
        self.team_status = {0: "", 1: ""}

    def initialize_authorizations(self):
        first_players_team = self.player_manager.get_all_players_echku_ordered()[0].team_id
        opposite_team = PlayerManager.get_opposite_team_id(first_players_team)

        self.player_manager.set_team_authorisation(first_players_team)

    def public_representation(self):
        return {"team_status": self.team_status}

    def handle_mus(self, player_id):
        player = self.player_manager.get_player_by_id(player_id)
        self.team_status[player.team_id] = "mus"

        if all(value == "mus" for value in self.team_status.values()):
            self.game.current_state = "Trading"

        self.player_manager.authorise_next_team(player.team_id)

    def handle_mintza(self, player_id):
        self.game.current_state = "Haundia"


class Trading(GameState):
    def __init__(self, game):
        super().__init__(game)
        self.handle_map = {
            "change": self.handle_change,
            "toggle": self.handle_toggle,
            "confirm": self.handle_confirm
        }

    def available_actions(self):
        return ["change", "toggle", "confirm"]

    def reset_attributes(self):
        self.player_status = {
            player.player_id: {"waiting_confirmation": True,
                               "asks": set()}
            for player in self.player_manager.get_all_players_team_ordered()
        }

    def is_player_authorised(self, player_id):
        return True

    def on_exit(self):
        for player in self.player_manager.get_all_players_team_ordered():
            player.exchange_cards(self.player_status[player.player_id]["asks"], self.packet)

    def public_representation(self):
        public_status = deepcopy(self.player_status)
        for player_id in public_status.keys():
            public_status[player_id]["asks"] = len(public_status[player_id]["asks"])

        return {"player_status": public_status}

    def handle_change(self, player_id, indices):
        for index in indices:
            self._validate_card_index(index)

        # 0-indexing FTW
        zero_indexed_indices = (index - 1 for index in indices)
        self.player_status[player_id]["asks"] = set(zero_indexed_indices)

    def handle_toggle(self, player_id, index):
        self._validate_card_index(index)

        # 0-indexing FTW
        index = index - 1

        if index not in self.player_status[player_id]["asks"]:
            self.player_status[player_id]["asks"].add(index)
        else:
            self.player_status[player_id]["asks"].remove(index)

    def handle_confirm(self, player_id):
        if len(self.player_status[player_id]["asks"]) == 0:
            raise ForbiddenActionException

        self.player_status[player_id]["waiting_confirmation"] = False

        if all(not player["waiting_confirmation"] for player in self.player_status.values()):
            self.game.current_state = "Speaking"

    def _validate_card_index(self, index):
        if not 1<= index <= 4:
                raise ForbiddenActionException("Invalid card_index %d" % index)


class BetState(GameState):
    own_state = ""
    next_state = ""
    has_bonus = False
    HandType = Hand

    def __init__(self, game):
        super().__init__(game)
        self.handle_map = {
            "paso": self.handle_paso,
            "gehiago": self.handle_gehiago,
            "idoki": self.handle_idoki,
            "tira": self.handle_tira,
            "hordago": self.handle_hordago,
            "kanta": self.handle_kanta,
        }

    def available_actions(self):
        if self.under_hordago:
            return ["kanta", "tira"]

        actions = ["gehiago", "hordago"]
        if not self.engaged:
            actions += ["paso", "imido"]
        else:
            actions += ["tira", "idoki"]

        return actions

    def reset_attributes(self):
        self.player_status = {player.player_id: {"is_paso": False}
                              for player in self.player_manager.get_all_players_echku_ordered()}
        self.winner = None
        self.bid = 1
        self.bid_accepted = True
        self.engaged = False
        self.under_hordago = False
        self.proposal = 0
        self.bonus = 0

    def public_representation(self):
        ...

    def compute_winner(self):
        if not self.bid_accepted:
            return
        echku_order = self.player_manager.get_all_echku_sorted()
        for i in range(len(echku_order)):
            for j in range(i, len(echku_order)):
                hand_1 = self.HandType(echku_order[i].cards)
                hand_2 = self.HandType(echku_order[j].cards)
                if hand_1 < hand_2:
                    echku_order[i], echku_order[j] = echku_order[j], echku_order[i]
        self.winner = echku_order[0].team

    def compute_bonus(self):
        if self.has_bonus and self.engaged:
            for player in self.player_manager:
                if player.team == self.winner:
                    self.bonus += self.HandType(player.cards).bonus()

    def everybody_is_paso(self):
        attendees = [player_id for (player_id, attends) in self.attendees.items() if attends]
        return all(self.player_status[attendee]["is_paso"] for attendee in attendees)

    def handle_paso(self, player_id):
        self.player_status[player_id]["is_paso"] = True
        self.authorise_next_player()
        if self.everybody_is_paso():
            self.bid_accepted = True
            self.game.current_state = self.next_state

    def handle_gehiago(self, player_id, proposal):
        if not self.engaged:
            proposal -= 1
            self.engaged = True

        if proposal <= 0:
            raise ForbiddenActionException

        self.bid += self.proposal
        self.proposal = proposal
        self.authorise_opposite_team(player_id)

    def handle_tira(self, player_id):
        self.bid_accepted = False
        self.winner = PlayerManager.get_opposite_team_id(self.player_manager[player_id].team_id)
        try:
            self.player_manager.other_team(self.player_manager[player_id].team).add_score(self.bid)
        except TeamWonException:
            self.game.current_state = "Finished"
        else:
            self.game.current_state = self.next_state

    def handle_idoki(self, player_id):
        self.bid += self.proposal
        self.game.current_state = self.next_state

    def handle_kanta(self, player_id):
        self.game.current_state = "Finished"

    def handle_hordago(self, player_id):
        self.under_hordago = True
        self.handle_gehiago(self, player_id, Gmae.score_max)


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

    def __init__(self, game):
        super().__init__(game)
        self.no_bet = False
        self.no_winner = False

    def is_player_authorised(self, player_id):
        if self.no_bet:
            return True
        return self.player_manager[player_id].has_hand and super().is_player_authorised(player_id)

    def possible_actions(self):
        if self.no_bet:
            return ['ok']
        return super().possible_actions()

    def authorise_next_player(self):
        self.player_manager.authorise_next_player()
        while not self.player_manager.authorised_player.has_hand:
            self.player_manager.authorise_next_player()

    def handle(self, action, player_id, *args):
        if action == 'ok':
            if not self.player_manager[player_id].waiting_confirmation:
                raise ForbiddenActionException
            self.player_manager[player_id].waiting_confirmation = False

            if all(not player.waiting_confirmation for player in self.player_manager):
                return self.next_state
            else:
                return self.own_state

        return super().handle(action, player_id, *args)

    def compute_winner(self):
        if not self.no_winner:
            super().compute_winner()

    def on_entry(self):
        super().on_entry()
        self.no_bet = False
        self.no_winner = False
        self.bid = 1
        for player in self.player_manager:
            player.has_hand = PariakHand(player.cards).is_special
        if all(not player.has_hand for player in self.player_manager):
            self.no_winner = True
            self.no_bet = True
            self.bid_accepted = False
            self.bid = 0

        elif not (any(player.has_hand for player in self.player_manager.get_team(0)) and
                  any(player.has_hand for player in self.player_manager.get_team(1))):
            self.compute_winner()
            self.no_bet = True
            self.bid = 0
            self.bid_accepted = False
            self.engaged = True
        else:
            while not self.player_manager.authorised_player.has_hand:
                self.player_manager.authorise_next_player()
            self.first_player = self.player_manager.authorised_player

        if self.no_bet:
            for player in self.player_manager:
                player.waiting_confirmation = True


class Jokua(BetState):
    own_state = "Jokua"
    next_state = "Finished"
    HandType = JokuaHand
    has_bonus = True

    def __init__(self, game):
        super().__init__(game)
        self.no_bet = False
        self.false_game = False

    def is_player_authorised(self, player_id):
        if self.no_bet:
            return True
        if not self.false_game:
            return self.player_manager[player_id].has_game and super().is_player_authorised(player_id)
        return super().is_player_authorised(player_id)

    def possible_actions(self):
        if self.no_bet:
            return ['ok']
        return super().possible_actions()

    def handle(self, action, player_id, *args):
        if action == 'ok':
            if not self.player_manager[player_id].waiting_confirmation:
                raise ForbiddenActionException
            self.player_manager[player_id].waiting_confirmation = False

            if all(not player.waiting_confirmation for player in self.player_manager):
                return self.next_state
            else:
                return self.own_state
        return super().handle(action, player_id, *args)

    def on_entry(self):
        super().on_entry()
        self.no_bet = False
        self.false_game = False
        for player in self.player_manager:
            player.has_game = JokuaHand(player.cards).is_special
        if any(player.has_game for player in self.player_manager):
            if not (any(player.has_game for player in self.player_manager.get_team(0)) and
                    any(player.has_game for player in self.player_manager.get_team(1))):
                self.compute_winner()
                self.no_bet = True
                self.bid = 0
                self.engaged = True
                self.bid_accepted = False
            else:
                while not self.player_manager.authorised_player.has_game:
                    self.player_manager.authorise_next_player()
                self.first_player = self.player_manager.authorised_player
        else:
            self.false_game = True

        if self.no_bet:
            for player in self.player_manager:
                player.waiting_confirmation = True

    def compute_bonus(self):
        if self.false_game and self.engaged:
            self.bonus = 1
        else:
            super().compute_bonus()

class Finished(GameState):
    own_state = "Finished"
    next_state = "Speaking"

    def __init__(self, game):
        super().__init__(game)
        self.actions = ["ok"]

    def available_actions(self):
        ...

    def public_representation(self):
        ...


    def is_player_authorised(self, player_id):
        return True

    def on_entry(self):
        self.reset_history()
        if not self.player_manager.has_finished():
            try:
                for state in Game.bet_states:
                    if self.game.states[state].winner is not None:
                        if self.game.states[state].bid_accepted:
                            self.player_manager.teams[self.game.states[state].winner.team_id].add_score(self.game.states[state].bid)
                        self.player_manager.teams[self.game.states[state].winner.team_id].add_score(self.game.states[state].bonus)
            except TeamWonException:
                self.game.finished = True

            for player in self.player_manager:
                player.waiting_confirmation = True

    def handle(self, action, player_id, *args):
        if not self.player_manager[player_id].waiting_confirmation:
            raise ForbiddenActionException

        self.player_manager[player_id].waiting_confirmation = False

        if all(not player.waiting_confirmation for player in self.player_manager):
            return self.next_state
        else:
            return self.own_state

    def on_exit(self):
        self.packet.restore()
        for player in self.player_manager:
            player.cards = sorted(self.packet.draw() for _ in range(4))
        self.player_manager.get_all_echku_sorted()
        if self.player_manager.has_finished():
            for team in self.player_manager.teams:
                team.score = 0
        self.player_manager.set_echku()
        self.reset_history()


class Game:
    score_max = 40
    bet_states = ["Haundia", "Tipia", "Pariak", "Jokua"]

    def __init__(self):
        self.player_manager = PlayerManager()
        self.packet = Packet()
        self.visited_states = set()
        self._current_state = "Waiting Room"

        self.states = {
            "Waiting Room": WaitingRoom(self),
            "Speaking": Speaking(self),
            "Trading": Trading(self),
            "Haundia": Haundia(self),
            "Tipia": Tipia(self),
            "Pariak": Pariak(self),
            "Jokua": Jokua(self),
            "Finished": Finished(self),
        }

        self.states[self.current_state].on_entry()

    @property
    def current_state(self):
        return self._current_state

    @current_state.setter
    def current_state(self, value):
        self.visited_states.add(value)
        self._current_state = value

    def record_scores(self):
        pass

    def status(self):
        data = {
            "players": [],
            "teams": [],
            "current_state": self.current_state,
        }

        for player in self.player_manager.get_all_players_team_ordered():
            data["players"].append({
                "player_id": player.public_id,
                "team_id" : player.team_id + 1,
                "can_speak": player.can_speak,
            })

        for team in self.player_manager.teams:
            data["teams"].append({
                "team_id": team.team_id + 1,
                "players": [player.public_id for player in team]
            })

        for state in self.visited_states:
            data[state] = self.states[state].public_representation()

        data["echku_order"] = [player.public_id
                               for player in self.player_manager.get_all_players_echku_ordered()]

        return data

    def do(self, message):
        action = message[0]
        kwargs = message[1]

        old_state = self.current_state

        try:
            answer = self.states[self.current_state].run(action, **kwargs)
        except WrongPlayerException:
            return {"status": "WrongPlayer"}
        except ForbiddenActionException:
            return {"status": "Forbidden"}
        else:
            if old_state != self.current_state:
                self.states[old_state].on_exit()
                self.states[self.current_state].on_entry()

            return {"status": "OK", "result": answer, "state": self.status()}
