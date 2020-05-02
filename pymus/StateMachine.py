import json

from abc import ABC, abstractmethod
from copy import deepcopy

from Cards import Hand, HaundiaHand, TipiaHand, PariakHand, JokuaHand, JSONCardEncoder
from Players import PlayerManager
from MusExceptions import *

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
        self.set_attending()
        self.reset_attributes()
        self.initialize_authorizations()

    @abstractmethod
    def available_actions(self):
        ...

    def initialize_authorizations(self):
        candidates = list(player for player in self.player_manager.get_all_players_echku_ordered()
                          if self.attendees[player.player_id])
        if len(candidates) != 0:
            self.current_player = candidates[0]
            self.player_manager.set_authorised_player(self.current_player)

    def authorise_next_player(self):
        candidates = list(player for player in self.player_manager.get_all_players_echku_ordered()
                          if self.attendees[player.player_id])

        current_index = candidates.index(self.current_player)
        self.current_player = candidates[(current_index + 1) % len(candidates)]
        self.player_manager.set_authorised_player(self.current_player)

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
        if team_id != 0 and team_id != 1:
            raise ForbiddenActionException("Invalid team team_id %d" % team_id)

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

        self.player_manager.set_authorised_team(first_players_team)

    def public_representation(self):
        return {"team_status": self.team_status}

    def handle_mus(self, player_id):
        player = self.player_manager.get_player_by_id(player_id)
        self.team_status[player.team_id] = "mus"

        if all(value == "mus" for value in self.team_status.values()):
            self.game.current_state = "Trading"

        self.player_manager.authorise_opposite_team(player.team_id)

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
            for player in self.player_manager.get_all_players_echku_ordered()
        }

    def is_player_authorised(self, player_id):
        return True

    def on_exit(self):
        for player in self.player_manager.get_all_players_echku_ordered():
            player.exchange_cards(self.player_status[player.player_id]["asks"], self.packet)

    def public_representation(self):
        public_status = deepcopy(self.player_status)
        for player_id in public_status.keys():
            public_status[player_id]["asks"] = len(public_status[player_id]["asks"])

        return {"player_status": public_status}

    def handle_change(self, player_id, indices):
        for index in indices:
            self._validate_card_index(index)

        self.player_status[player_id]["asks"] = set(indices)

    def handle_toggle(self, player_id, index):
        self._validate_card_index(index)

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
        if not 0 <= index <= 3:
                raise ForbiddenActionException("Invalid card_index %d" % index)


# ABC for Haundia, Tipia, Pariak, Jokua
class BetState(GameState, ABC):
    def __init__(self, game):
        super().__init__(game)
        self.handle_map = {
            "paso": self.handle_paso,
            "gehiago": self.handle_gehiago,
            "iduki": self.handle_iduki,
            "tira": self.handle_tira,
            "hordago": self.handle_hordago,
            "kanta": self.handle_kanta,
            "imido": self.handle_imido,
            "confirm": self.handle_confirm,
        }

    def available_actions(self):
        if self.is_skipped():
            return ["confirm"]
        if self.under_hordago:
            return ["kanta", "tira"]

        actions = ["gehiago", "hordago"]
        if self.no_bid:
            actions += ["paso", "imido"]
        else:
            actions += ["tira", "iduki"]

        return actions

    def reset_attributes(self):
        self.player_status = {player.player_id: {"waiting_confirmation": True, "is_paso": False}
                              for player in self.player_manager.get_all_players_echku_ordered()}
        self._winner_team = None
        self.offer = 0
        self.bonus_points = {}
        self.was_engaged = False
        self.differed_bid = False
        self.no_bid = True
        self.under_hordago = False

        if self.is_skipped():
            self.bid = 0
            if any(attends for attends in self.attendees.values()):
                self.compute_winner_team()
        else:
            self.bid = 1

    def public_representation(self):
        representation =  {"Bid": self.bid, "Offer": self.offer, "BidDiffered": self.differed_bid,
                           "UnderHordago": self.under_hordago, "IsSkipped": self.is_skipped(),
                           "Winner": self.get_winner_team(),
                           "Bonus": self.get_bonus_representation()}

        bai_or_ez = self.player_has_it()
        if bai_or_ez :
            representation["PlayerHasIt"] = bai_or_ez

        return representation

    def get_bonus_representation(self):
        if self.bonus_points:
            return {player.public_id: bonus for player, bonus in self.bonus_points.items()}
        return None

    def player_has_it(self):
        return {}

    def is_player_authorised(self, player_id):
        if self.is_skipped():
            return self.player_status[player_id]["waiting_confirmation"]
        else:
            return super().is_player_authorised(player_id)

    def is_skipped(self):
        team_0_plays = any(self.attendees[player.player_id]
                           for player in self.player_manager.get_team_players(0))
        team_1_plays = any(self.attendees[player.player_id]
                           for player in self.player_manager.get_team_players(1))
        return (not team_0_plays) or (not team_1_plays)

    def distribute_bid_points(self):
        team_id = self.get_winner_team()
        self.player_manager.add_points(self.bid, team_id)

    def distribute_bonus_points(self):
        ...

    def compute_winner_team(self):
        players = self.player_manager.get_all_players_echku_ordered()

        cards_order_tuple = tuple(
            (self.get_hand_type()(player.get_cards()), -index) for (index, player) in enumerate(players)
        )

        winner = players[max(cards_order_tuple)[1]]

        self.set_winner_team(winner.team_id)

    def set_winner_team(self, team_id):
        self._winner_team = team_id

    def get_winner_team(self):
        return self._winner_team

    def compute_bonus_points(self):
        ...

    def distribute_bonus_points(self):
        winner_team = self.get_winner_team()
        for bonus in self.bonus_points.values():
            self.player_manager.add_points(bonus, winner_team)

    def handle_paso(self, player_id):
        self.player_status[player_id]["is_paso"] = True
        self.authorise_next_player()
        if self._everybody_is_paso():
            self.differed_bid = True
            self.game.current_state = self.get_next_state()

    def handle_gehiago(self, player_id, offer):
        player = self.player_manager.get_player_by_id(player_id)
        self.engaged = True

        if self.no_bid:
            offer -= 1
            self.no_bid = False

        if offer <= 0:
            raise ForbiddenActionException

        self.bid += self.offer
        self.offer = offer
        self.player_manager.authorise_opposite_team(player.team_id)

    def handle_imido(self, player_id):
        return self.handle_gehiago(player_id, 2)

    def handle_tira(self, player_id):
        self.offer = 0
        winner_team = PlayerManager.get_opposite_team_id(
            self.player_manager.get_player_by_id(player_id).team_id)

        self.set_winner_team(winner_team)
        self.distribute_bid_points()
        self.game.current_state = self.get_next_state()

    def handle_iduki(self, player_id):
        self.bid += self.offer
        self.offer = 0
        self.differed_bid = True
        self.game.current_state = self.get_next_state()

    def handle_kanta(self, player_id):
        self.game.current_state = "Finished"

    def handle_hordago(self, player_id):
        self.engaged = True
        self.under_hordago = True
        self.handle_gehiago(self, player_id, Gmae.score_max)

    def handle_confirm(self, player_id):
        if not self.player_status[player_id]["waiting_confirmation"]:
            raise ForbiddenActionException

        self.player_status[player_id]["waiting_confirmation"] = False

        if all(not player_status["waiting_confirmation"]
               for player_status in self.player_status.values()):
            self.game.current_state = self.get_next_state()

    def _everybody_is_paso(self):
        attendees = [player_id for (player_id, attends) in self.attendees.items() if attends]
        return all(self.player_status[attendee]["is_paso"] for attendee in attendees)

    @abstractmethod
    def get_next_state(self):
        ...

    @abstractmethod
    def get_hand_type(self):
        ...


class Haundia(BetState):
    def get_next_state(self):
        return "Tipia"

    def get_hand_type(self):
        return HaundiaHand


class Tipia(BetState):
    def get_next_state(self):
        return "Pariak"

    def get_hand_type(self):
        return TipiaHand


class Pariak(BetState):
    def set_attending(self):
        self.attendees = {player.player_id: PariakHand(player.get_cards()).is_special for
                          player in self.player_manager.get_all_players_echku_ordered()}

    def player_has_it(self):
        return {player.public_id: PariakHand(player.get_cards()).is_special for
                          player in self.player_manager.get_all_players_echku_ordered()}

    def compute_bonus_points(self):
        if self.is_skipped() or not self.no_bid:
            winner_team = self.get_winner_team()
            self.bonus_points = {player: PariakHand(player.get_cards()).bonus
                                 for player in self.player_manager.get_team_players(winner_team)}

    def get_next_state(self):
        return "Jokua"

    def get_hand_type(self):
        return PariakHand


class Jokua(BetState):
    def set_attending(self):
        if self._is_real_game():
            self.attendees = {player.player_id: JokuaHand(player.get_cards()).is_special
                              for player in self.player_manager.get_all_players_echku_ordered()}
        else:
            self.attendees = {player.player_id: True
                              for player in self.player_manager.get_all_players_echku_ordered()}

    def compute_bonus_points(self):
        if self.is_skipped() or not self.no_bid:
            winner_team = self.get_winner_team()
            if self._is_real_game():
                self.bonus_points = {player: JokuaHand(player.get_cards()).bonus
                                    for player in self.player_manager.get_team_players(winner_team)}
            else:
                team_representant = self.player_manager.get_team_players(winner_team)[0]
                self.bonus_points = {team_representant: 1}

    def player_has_it(self):
        return {player.public_id: JokuaHand(player.get_cards()).is_special
                for player in self.player_manager.get_all_players_echku_ordered()}

    def get_next_state(self):
        return "Finished"

    def get_hand_type(self):
        return JokuaHand

    def _is_real_game(self):
        return any(JokuaHand(player.get_cards()).is_special
                   for player in self.player_manager.get_all_players_echku_ordered())


class Finished(GameState):
    def __init__(self, game):
        super().__init__(game)
        self.handle_map = {
            "confirm": self.handle_confirm,
        }

    def available_actions(self):
        return ["confirm"]

    def public_representation(self):
        return {"RevealCards":
                {player.public_id: [json.dumps(card, cls=JSONCardEncoder) for card in player.get_cards()]
                 for player in self.player_manager.get_all_players_echku_ordered()}}

    def on_exit(self):
        self.game.reset_packet()

        if self.player_manager.is_finished():
            self.game.turn_number = 1
        else:
            self.game.turn_number += 1

        for player in self.player_manager.get_all_players_echku_ordered():
            player.draw_new_hand(self.packet)

        self.player_manager.step_echku_order()

        if self.player_manager.is_finished():
            self.player_manager.reset_scores()

    def is_player_authorised(self, player_id):
        return True

    def reset_attributes(self):
        self.player_status = {player.player_id: {"waiting_confirmation": True}
                              for player in self.player_manager.get_all_players_echku_ordered()}

    def on_entry(self):
        super().on_entry()

        if self.player_manager.is_finished():
            return

        try:
            for state in self.game.bet_states:
                if self.game.states[state].differed_bid:
                    self.game.states[state].compute_winner_team()
                    self.game.states[state].distribute_bid_points()

                self.game.states[state].compute_bonus_points()
                self.game.states[state].distribute_bonus_points()

        except TeamWonException:
            ...

    def handle_confirm(self, player_id):
        if not self.player_status[player_id]["waiting_confirmation"]:
            raise ForbiddenActionException

        self.player_status[player_id]["waiting_confirmation"] = False

        if all(not player_status["waiting_confirmation"]
               for player_status in self.player_status.values()):
            self.game.current_state = self.get_next_state()

    def get_next_state(self):
        self.game.clean_visited_states()
        return "Speaking"
