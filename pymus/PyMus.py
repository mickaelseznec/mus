import json
import uuid

from abc import ABC, abstractmethod
from collections import UserList, deque
from copy import deepcopy
from itertools import chain

from Cards import Card, Packet, Hand, HaundiaHand, TipiaHand, PariakHand, JokuaHand
from StateMachine import WaitingRoom, Speaking, Trading, Haundia, Tipia, Pariak, Jokua, Finished
from Players import Team, PlayerManager
from MusExceptions import *

class Game:
    max_score = 40
    bet_states = ["Haundia", "Tipia", "Pariak", "Jokua"]

    def __init__(self):
        self.player_manager = PlayerManager(Game.max_score)
        self.packet = Packet()
        self.visited_states = set()
        self._current_state = "Waiting Room"
        self.turn_number = 1
        self.finished = False
        self.winner = None

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

    def reset_packet(self):
        self.packet = Packet()

    @property
    def current_state(self):
        return self._current_state

    @current_state.setter
    def current_state(self, value):
        self.visited_states.add(value)
        self._current_state = value

    def prepare_next_turn(self):
        self.visited_states = set()

        if self.finished:
            self.finished = False
            self.turn_number = 1
            self.winner = None
            self.player_manager.reset_team_scores()
        else:
            self.turn_number += 1

    def set_game_finished(self):
        self.finished = True
        self.winner = self.player_manager.get_winner()

    def record_scores(self):
        pass

    def status(self):
        data = {
            "players": {},
            "teams": [],
            "number_of_player": len(self.player_manager.get_all_players_team_ordered()),
            "current_state": self.current_state,
            "turn_number": self.turn_number,
            "game_over": self.finished,
            "winner": self.winner,
        }

        for player in self.player_manager.get_all_players_team_ordered():
            data["players"][player.player_name] = {
                "team_id" : player.team_id,
                "can_speak": self.states[self.current_state].is_player_authorised(player.player_id),
            }

        data["teams"] = [{
            "players": [player.player_name for player in team],
            "score": team.score,
            "games": team.games,
        } for team in self.player_manager.teams]

        for state in self.visited_states:
            data[state] = self.states[state].public_representation()

        data["echku_order"] = [player.player_name
                               for player in self.player_manager.get_all_players_echku_ordered()]

        return data

    def do(self, message):
        action = message[0]
        kwargs = message[1]

        old_state = self.current_state

        answer = None

        try:
            answer = self.states[self.current_state].run(action, **kwargs)
        except WrongPlayerException:
            return {"status": "WrongPlayer"}
        except ForbiddenActionException:
            return {"status": "Forbidden"}
        except TeamWonException:
            self.current_state = "Finished"
            self.set_game_finished()

        if old_state != self.current_state:
            self.states[old_state].on_exit()
            self.states[self.current_state].on_entry()

        return {"status": "OK", "result": answer, "state": self.status()}
