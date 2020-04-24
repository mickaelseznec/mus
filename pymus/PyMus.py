import json
import uuid

from abc import ABC, abstractmethod
from collections import UserList, deque
from copy import deepcopy
from itertools import chain

from Cards import Card, Packet, Hand, HaundiaHand, TipiaHand, PariakHand, JokuaHand, JSONCardEncoder
from StateMachine import WaitingRoom, Speaking, Trading, Haundia, Tipia, Pariak, Jokua, Finished
from Players import Team, PlayerManager
from MusExceptions import *

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
