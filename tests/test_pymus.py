import json
import sys
sys.path.append("pymus")
import itertools as it
import unittest

from pprint import pprint

import PyMus as mus

from PyMus import Game, Card, Team, PlayerManager

class TestGame:
    def unwrap(self, game_answer):
        self.assertEqual(game_answer['status'], "OK")
        return game_answer["result"], game_answer["state"]

    def unwrap_fails(self, game_answer, status):
        self.assertEqual(game_answer['status'], status)

    def assertState(self, state):
        self.assertEqual(self.game.status()["current_state"], state)

    def register_four_player(self):
        player_1, _ = self.unwrap(self.game.do(("add_player", {"team_id": 0, "player_name": "Jean"})))
        player_2, _ = self.unwrap(self.game.do(("add_player", {"team_id": 1, "player_name": "Jacques"})))
        player_3, _ = self.unwrap(self.game.do(("add_player", {"team_id": 0, "player_name": "Julien"})))
        player_4, _ = self.unwrap(self.game.do(("add_player", {"team_id": 1, "player_name": "Jeremy"})))

        self.player_1, self.player_1_public = player_1
        self.player_2, self.player_2_public = player_2
        self.player_3, self.player_3_public = player_3
        self.player_4, self.player_4_public = player_4

        self.public_to_private = {player[1]: player[0]
                                  for player in (player_1, player_2, player_3, player_4)}

    def player_speaking(self):
        status = self.game.status()
        for player, info in status["players"].items():
            if info["can_speak"]:
                return self.public_to_private[player]
        return None

    def go_through_speaking(self):
        self.unwrap(self.game.do(("mintza", {"player_id": self.player_speaking()})))

    def go_through_betstate(self):
        status = self.game.status()
        if status[status["current_state"]].get("IsSkipped", False):
            for player in (self.player_1, self.player_2, self.player_3, self.player_4):
                self.unwrap(self.game.do(("confirm", {"player_id": player})))
        else:
            self.unwrap(self.game.do(("imido", {"player_id": self.player_speaking()})))
            self.unwrap(self.game.do(("iduki", {"player_id": self.player_speaking()})))

    def go_through_finished(self):
        for player in (self.player_1, self.player_2, self.player_3, self.player_4):
            self.unwrap(self.game.do(("confirm", {"player_id": player})))

    def set_hands(self, hands):
        for player, hand in zip((self.player_1, self.player_2, self.player_3, self.player_4), hands):
            self.game.player_manager.get_player_by_id(player).debug_card_setter(hand)


class TestWaitingRoom(unittest.TestCase, TestGame):
    def setUp(self):
        self.game = Game()

    def test_add_players(self):
        (player_1, _), _ = self.unwrap(self.game.do((
            "add_player", {"team_id": 0, "player_name": "Jean"})))
        (player_2, _), _ = self.unwrap(self.game.do((
            "add_player", {"team_id": 1, "player_name": "Jacques"})))

        (player_3, _), _ = self.unwrap(self.game.do((
            "add_player", {"team_id": 0, "player_name": "Julien"})))
        (player_4, _), _ = self.unwrap(self.game.do((
            "add_player", {"team_id": 1, "player_name": "Jeremy"})))

        self.unwrap_fails(self.game.do((
            "add_player", {"team_id": 1, "player_name": "Norbert"})), "Forbidden")

    def test_add_same_player(self):
        player_1, _ = self.unwrap(self.game.do(("add_player", {"team_id": 0, "player_name": "Jean"})))
        player_1_new, _ = self.unwrap(self.game.do((
            "add_player", {"team_id": 0, "player_id": player_1[0], "player_name": "Jean"})))

        self.assertEqual(player_1, player_1_new)

    def test_remove_player(self):
        player_1, _ = self.unwrap(self.game.do(("add_player", {"team_id": 0, "player_name": "Jean"})))

        _, state = self.unwrap(self.game.do(("remove_player", {"player_id": player_1[0]})))
        self.assertTrue(player_1[1] not in (player["player_id"] for player in state["players"]))

    def test_start_with_two_players(self):
        (player_1, _), _ = self.unwrap(self.game.do(("add_player",
                                                     {"team_id": 0, "player_name": "Jean"})))
        (player_2, _), _ = self.unwrap(self.game.do(("add_player",
                                                     {"team_id": 1, "player_name": "Jacques"})))

        self.unwrap(self.game.do(("start_game", {"player_id": player_1})))
        self.assertState("Speaking")

    def test_cannot_start_with_three_players(self):
        (player_1, _), _ = self.unwrap(self.game.do(("add_player",
                                                     {"team_id": 0, "player_name": "Jean"})))
        (player_2, _), _ = self.unwrap(self.game.do(("add_player",
                                                     {"team_id": 1, "player_name": "Jacques"})))
        (player_3, _), _ = self.unwrap(self.game.do(("add_player",
                                                     {"team_id": 0, "player_name": "Jean"})))

        self.unwrap_fails(self.game.do(("start_game", {"player_id": player_1})), "Forbidden")

        self.assertState("Waiting Room")

    def test_start_with_four_players(self):
        (player_1, _), _ = self.unwrap(self.game.do(("add_player",
                                                     {"team_id": 0, "player_name": "Jean"})))
        (player_2, _), _ = self.unwrap(self.game.do(("add_player",
                                                     {"team_id": 1, "player_name": "Jacques"})))
        (player_3, _), _ = self.unwrap(self.game.do(("add_player",
                                                     {"team_id": 0, "player_name": "Joël"})))
        (player_4, _), _ = self.unwrap(self.game.do(("add_player",
                                                     {"team_id": 1, "player_name": "Julien"})))

        self.unwrap(self.game.do(("start_game", {"player_id": player_1})))

        self.assertState("Speaking")


class TestSpeaking(unittest.TestCase, TestGame):

    def setUp(self):
        self.game = Game()
        self.register_four_player()
        self.unwrap(self.game.do(("start_game", {"player_id": self.player_1})))
        self.assertState("Speaking")

    def test_who_can_speak(self):
        player_info = self.game.status()["players"]

        self.assertTrue(player_info[self.player_1_public]["can_speak"])
        self.assertTrue(player_info[self.player_3_public]["can_speak"])
        self.assertFalse(player_info[self.player_2_public]["can_speak"])
        self.assertFalse(player_info[self.player_4_public]["can_speak"])

        self.unwrap_fails(self.game.do(("mus", {"player_id": self.player_2})), "WrongPlayer")
        self.unwrap(self.game.do(("mus", {"player_id": self.player_1})))
        self.unwrap_fails(self.game.do(("mus", {"player_id": self.player_3})), "WrongPlayer")
        self.unwrap(self.game.do(("mus", {"player_id": self.player_4})))

        self.assertState("Trading")

    def test_trade(self):
        self.unwrap(self.game.do(("mus", {"player_id": self.player_1})))
        self.unwrap(self.game.do(("mus", {"player_id": self.player_2})))
        self.assertState("Trading")


class TestTrading(unittest.TestCase, TestGame):

    def setUp(self):
        self.game = Game()

        self.register_four_player()
        self.unwrap(self.game.do(("start_game", {"player_id": self.player_1})))
        self.unwrap(self.game.do(("mus", {"player_id": self.player_1})))
        self.unwrap(self.game.do(("mus", {"player_id": self.player_2})))
        self.assertState("Trading")

    def test_card_indices(self):
        self.unwrap_fails(self.game.do(("change", {"player_id": self.player_1,
                                                   "indices": [-1]})),
                          "Forbidden")

        self.unwrap_fails(self.game.do(("change", {"player_id": self.player_1,
                                                   "indices": [4]})),
                          "Forbidden")

        self.unwrap(self.game.do(("change", {"player_id": self.player_1, "indices": [0]})))
        self.unwrap(self.game.do(("change", {"player_id": self.player_1, "indices": [1]})))
        self.unwrap(self.game.do(("change", {"player_id": self.player_1, "indices": [2, 3]})))

    def test_toggle(self):
        _, state = self.unwrap(self.game.do(("toggle", {"player_id": self.player_3, "index": 0})))
        self.assertEqual(state["Trading"]["player_status"][self.player_3]["asks"], 1)

        _, state = self.unwrap(self.game.do(("toggle", {"player_id": self.player_3, "index": 1})))
        self.assertEqual(state["Trading"]["player_status"][self.player_3]["asks"], 2)

        _, state = self.unwrap(self.game.do(("toggle", {"player_id": self.player_3, "index": 1})))
        self.assertEqual(state["Trading"]["player_status"][self.player_3]["asks"], 1)

        _, state = self.unwrap(self.game.do(("toggle", {"player_id": self.player_3, "index": 2})))
        self.assertEqual(state["Trading"]["player_status"][self.player_3]["asks"], 2)

    def test_change(self):
        old_player_cards = {}
        for player in (self.player_1, self.player_2, self.player_3, self.player_4):
            raw_cards = self.unwrap(self.game.do(("get_cards", {"player_id": player})))[0]
            old_player_cards[player] = [Card(*card) for card in raw_cards]
        self.unwrap(self.game.do(("change", {"player_id": self.player_1, "indices": [0, 1, 2, 3]})))

        self.unwrap(self.game.do(("change", {"player_id": self.player_1, "indices": [0, 1, 2, 3]})))
        self.unwrap(self.game.do(("confirm", {"player_id": self.player_1})))
        self.unwrap(self.game.do(("change", {"player_id": self.player_2, "indices": [0, 1]})))
        self.unwrap(self.game.do(("confirm", {"player_id": self.player_2})))

        self.unwrap(self.game.do(("change", {"player_id": self.player_3, "indices": [0]})))
        self.unwrap(self.game.do(("confirm", {"player_id": self.player_3})))
        self.unwrap(self.game.do(("change", {"player_id": self.player_4, "indices": [0]})))
        self.unwrap(self.game.do(("confirm", {"player_id": self.player_4})))

        new_player_1_hand, _ = self.unwrap(self.game.do(("get_cards", {"player_id": self.player_1})))
        new_player_2_hand, _ = self.unwrap(self.game.do(("get_cards", {"player_id": self.player_2})))
        new_player_3_hand, _ = self.unwrap(self.game.do(("get_cards", {"player_id": self.player_3})))
        new_player_4_hand, _ = self.unwrap(self.game.do(("get_cards", {"player_id": self.player_4})))

        new_player_cards = {}
        for player in (self.player_1, self.player_2, self.player_3, self.player_4):
            raw_cards = self.unwrap(self.game.do(("get_cards", {"player_id": player})))[0]
            new_player_cards[player] = [Card(*card) for card in raw_cards]

        self.assertTrue(all([all(not old_card.is_same(new_card)
                                 for new_card in new_player_cards[self.player_1])
                             for old_card in old_player_cards[self.player_1]]))


        self.assertTrue(all([all(not old_card.is_same(new_card)
                                 for new_card in new_player_cards[self.player_2])
                             for old_card in old_player_cards[self.player_2][:2]]))
        self.assertTrue(all([any(old_card.is_same(new_card)
                                 for new_card in new_player_cards[self.player_2])
                             for old_card in old_player_cards[self.player_2][2:]]))


        self.assertTrue(all([all(not old_card.is_same(new_card)
                                 for new_card in new_player_cards[self.player_3])
                             for old_card in old_player_cards[self.player_3][:1]]))
        self.assertTrue(all([any(old_card.is_same(new_card)
                                 for new_card in new_player_cards[self.player_3])
                             for old_card in old_player_cards[self.player_3][1:]]))


        self.assertTrue(all([all(not old_card.is_same(new_card)
                                 for new_card in new_player_cards[self.player_4])
                             for old_card in old_player_cards[self.player_4][:1]]))
        self.assertTrue(all([any(old_card.is_same(new_card)
                                 for new_card in new_player_cards[self.player_4])
                             for old_card in old_player_cards[self.player_4][1:]]))


class TestHandia(unittest.TestCase, TestGame):
    def setUp(self):
        self.game = Game()
        self.register_four_player()
        self.unwrap(self.game.do(("start_game", {"player_id": self.player_1})))

    def advance_to_test_state(self):
        self.go_through_speaking()

    def advance_to_finished(self):
        self.go_through_betstate()
        self.go_through_betstate()
        self.go_through_betstate()

    def test_all_paso(self):
        self.set_hands([
            [Card(1, 'Oros'), Card(1, 'Bastos'), Card(10, 'Oros'), Card(11, 'Bastos')],
            [Card(1, 'Oros'), Card(1, 'Bastos'), Card(10, 'Oros'), Card(12, 'Bastos')],
            [Card(1, 'Oros'), Card(1, 'Bastos'), Card(10, 'Oros'), Card(11, 'Bastos')],
            [Card(1, 'Oros'), Card(1, 'Bastos'), Card(10, 'Oros'), Card(11, 'Bastos')]
        ])

        self.advance_to_test_state()

        status = self.game.status()

        self.assertEqual(status['Haundia']['Bid'], 1)
        self.assertEqual(status['Haundia']['Offer'], 0)

        self.unwrap(self.game.do(("paso", {"player_id": self.player_1})))
        self.unwrap(self.game.do(("paso", {"player_id": self.player_2})))
        self.unwrap(self.game.do(("paso", {"player_id": self.player_3})))
        _, status = self.unwrap(self.game.do(("paso", {"player_id": self.player_4})))

        self.assertEqual(status['Haundia']['Bid'], 1)
        self.assertEqual(status['Haundia']['BidDiffered'], True)
        self.assertEqual(status['Haundia']['Winner'], None)

        self.advance_to_finished()

        status = self.game.status()
        self.assertEqual(status['Haundia']['Winner'], 1)

    def test_paso_bet_iduki(self):
        self.set_hands([
            [Card(1, 'Oros'), Card(1, 'Bastos'), Card(10, 'Oros'), Card(12, 'Bastos')],
            [Card(1, 'Oros'), Card(1, 'Bastos'), Card(10, 'Oros'), Card(12, 'Bastos')],
            [Card(1, 'Oros'), Card(1, 'Bastos'), Card(10, 'Oros'), Card(11, 'Bastos')],
            [Card(1, 'Oros'), Card(1, 'Bastos'), Card(10, 'Oros'), Card(11, 'Bastos')]
        ])

        self.advance_to_test_state()

        self.unwrap(self.game.do(("paso", {"player_id": self.player_1})))
        self.unwrap(self.game.do(("paso", {"player_id": self.player_2})))
        _, status = self.unwrap(self.game.do(("imido", {"player_id": self.player_3})))

        self.assertEqual(status['Haundia']['Bid'], 1)
        self.assertEqual(status['Haundia']['Offer'], 1)

        _, status = self.unwrap(self.game.do(("gehiago", {"player_id": self.player_4,
                                                         "offer": 2})))

        self.assertEqual(status['Haundia']['Bid'], 2)
        self.assertEqual(status['Haundia']['Offer'], 2)

        _, status = self.unwrap(self.game.do(("gehiago", {"player_id": self.player_1,
                                              "offer": 3})))

        self.assertEqual(status['Haundia']['Bid'], 4)
        self.assertEqual(status['Haundia']['Offer'], 3)

        _, status = self.unwrap(self.game.do(("iduki", {"player_id": self.player_2})))

        self.assertEqual(status['Haundia']['Bid'], 7)
        self.assertEqual(status['Haundia']['Offer'], 0)
        self.assertEqual(status['Haundia']['BidDiffered'], True)
        self.assertEqual(status['Haundia']['Winner'], None)

        self.advance_to_finished()

        status = self.game.status()
        self.assertEqual(status['Haundia']['Winner'], 0)

    def test_bet_tira(self):
        self.advance_to_test_state()

        self.unwrap(self.game.do(("imido", {"player_id": self.player_1})))
        self.unwrap(self.game.do(("gehiago", {"player_id": self.player_2,
                                              "offer": 2})))
        self.unwrap(self.game.do(("gehiago", {"player_id": self.player_3,
                                              "offer": 3})))
        _, status = self.unwrap(self.game.do(("tira", {"player_id": self.player_2})))

        self.assertEqual(status['Haundia']['Bid'], 4)
        self.assertEqual(status['Haundia']['Offer'], 0)
        self.assertEqual(status['Haundia']['BidDiffered'], False)
        self.assertEqual(status['Haundia']['Winner'], 0)


class TestTipia(unittest.TestCase, TestGame):
    def setUp(self):
        self.game = Game()

        self.register_four_player()
        self.unwrap(self.game.do(("start_game", {"player_id": self.player_1})))

    def advance_to_test_state(self):
        self.go_through_speaking()
        self.go_through_betstate()

    def advance_to_finished(self):
        self.go_through_betstate()
        self.go_through_betstate()

    def test_all_paso(self):
        self.set_hands([
            [Card(5, 'Oros'), Card(7, 'Bastos'), Card(10, 'Oros'), Card(11, 'Bastos')],
            [Card(3, 'Oros'), Card(4, 'Bastos'), Card(10, 'Oros'), Card(12, 'Bastos')],
            [Card(2, 'Oros'), Card(4, 'Bastos'), Card(10, 'Oros'), Card(11, 'Bastos')],
            [Card(1, 'Oros'), Card(2, 'Bastos'), Card(10, 'Oros'), Card(11, 'Bastos')]
        ])
        self.advance_to_test_state()

        status = self.game.status()

        self.assertEqual(status['Tipia']['Bid'], 1)
        self.assertEqual(status['Tipia']['Offer'], 0)

        self.unwrap(self.game.do(("paso", {"player_id": self.player_1})))
        self.unwrap(self.game.do(("paso", {"player_id": self.player_2})))
        self.unwrap(self.game.do(("paso", {"player_id": self.player_3})))
        _, status = self.unwrap(self.game.do(("paso", {"player_id": self.player_4})))

        self.assertEqual(status['Tipia']['Bid'], 1)
        self.assertEqual(status['Tipia']['BidDiffered'], True)
        self.assertEqual(status['Tipia']['Winner'], None)

        self.advance_to_finished()

        status = self.game.status()
        self.assertEqual(status['Tipia']['Winner'], 1)

    def test_paso_bet_iduki(self):
        self.set_hands([
            [Card(1, 'Oros'), Card(1, 'Bastos'), Card(10, 'Oros'), Card(12, 'Bastos')],
            [Card(1, 'Oros'), Card(1, 'Bastos'), Card(10, 'Oros'), Card(12, 'Bastos')],
            [Card(1, 'Oros'), Card(1, 'Bastos'), Card(10, 'Oros'), Card(11, 'Bastos')],
            [Card(1, 'Oros'), Card(1, 'Bastos'), Card(10, 'Oros'), Card(11, 'Bastos')]
        ])
        self.advance_to_test_state()

        self.unwrap(self.game.do(("paso", {"player_id": self.player_1})))
        self.unwrap(self.game.do(("paso", {"player_id": self.player_2})))
        _, status = self.unwrap(self.game.do(("imido", {"player_id": self.player_3})))

        self.assertEqual(status['Tipia']['Bid'], 1)
        self.assertEqual(status['Tipia']['Offer'], 1)

        _, status = self.unwrap(self.game.do(("gehiago", {"player_id": self.player_4,
                                                         "offer": 2})))

        self.assertEqual(status['Tipia']['Bid'], 2)
        self.assertEqual(status['Tipia']['Offer'], 2)

        _, status = self.unwrap(self.game.do(("gehiago", {"player_id": self.player_1,
                                              "offer": 3})))

        self.assertEqual(status['Tipia']['Bid'], 4)
        self.assertEqual(status['Tipia']['Offer'], 3)

        _, status = self.unwrap(self.game.do(("iduki", {"player_id": self.player_2})))

        self.assertEqual(status['Tipia']['Bid'], 7)
        self.assertEqual(status['Tipia']['Offer'], 0)
        self.assertEqual(status['Tipia']['BidDiffered'], True)
        self.assertEqual(status['Tipia']['Winner'], None)

        self.advance_to_finished()

        status = self.game.status()
        self.assertEqual(status['Tipia']['Winner'], 0)

    def test_bet_tira(self):
        self.advance_to_test_state()

        self.unwrap(self.game.do(("imido", {"player_id": self.player_1})))
        self.unwrap(self.game.do(("gehiago", {"player_id": self.player_2,
                                              "offer": 2})))
        self.unwrap(self.game.do(("gehiago", {"player_id": self.player_3,
                                              "offer": 3})))
        _, status = self.unwrap(self.game.do(("tira", {"player_id": self.player_2})))

        self.assertEqual(status['Tipia']['Bid'], 4)
        self.assertEqual(status['Tipia']['Offer'], 0)
        self.assertEqual(status['Tipia']['BidDiffered'], False)
        self.assertEqual(status['Tipia']['Winner'], 0)


class TestPariak(unittest.TestCase, TestGame):
    def setUp(self):
        self.game = Game()

        self.register_four_player()
        self.unwrap(self.game.do(("start_game", {"player_id": self.player_1})))

    def advance_to_test_state(self):
        self.go_through_speaking()
        self.go_through_betstate()
        self.go_through_betstate()

    def advance_to_finished(self):
        self.go_through_betstate()

    def test_no_pairs(self):
        self.set_hands([
            [Card(2, 'Oros'), Card(3, 'Bastos'), Card(10, 'Oros'), Card(12, 'Bastos')],
            [Card(1, 'Oros'), Card(4, 'Bastos'), Card(10, 'Oros'), Card(12, 'Bastos')],
            [Card(1, 'Oros'), Card(5, 'Bastos'), Card(10, 'Oros'), Card(11, 'Bastos')],
            [Card(1, 'Oros'), Card(6, 'Bastos'), Card(10, 'Oros'), Card(11, 'Bastos')]
        ])
        self.advance_to_test_state()

        status = self.game.status()

        self.assertEqual(status['Pariak']['IsSkipped'], True)
        self.assertEqual(status['Pariak']['Bid'], 0)
        self.assertEqual(status['Pariak']['Winner'], None)

        self.unwrap(self.game.do(("confirm", {"player_id": self.player_1})))
        self.unwrap(self.game.do(("confirm", {"player_id": self.player_2})))
        self.unwrap(self.game.do(("confirm", {"player_id": self.player_3})))
        self.unwrap(self.game.do(("confirm", {"player_id": self.player_4})))

        self.assertState("Jokua")
        self.go_through_betstate()

        status = self.game.status()

        self.assertEqual(status['Pariak']['IsSkipped'], True)
        self.assertEqual(status['Pariak']['Bid'], 0)
        self.assertEqual(status['Pariak']['Winner'], None)

    def test_pairs_in_one_team(self):
        self.set_hands([
            [Card(2, 'Oros'), Card(12, 'Bastos'), Card(12, 'Oros'), Card(12, 'Bastos')],
            [Card(1, 'Oros'), Card(4, 'Bastos'), Card(10, 'Oros'), Card(12, 'Bastos')],
            [Card(1, 'Oros'), Card(1, 'Bastos'), Card(2, 'Oros'), Card(2, 'Bastos')],
            [Card(1, 'Oros'), Card(6, 'Bastos'), Card(10, 'Oros'), Card(11, 'Bastos')]
        ])
        self.advance_to_test_state()

        status = self.game.status()

        self.assertEqual(status['Pariak']['IsSkipped'], True)
        self.assertEqual(status['Pariak']['Bid'], 0)
        self.assertEqual(status['Pariak']['Winner'], 0)
        self.assertEqual(status['Pariak']['Bonus'], None)

        self.go_through_betstate()

        self.go_through_finished()

        status = self.game.status()
        self.assertEqual(status['Pariak']['Bonus'], {self.player_1_public: 2, self.player_3_public: 3})

    def test_all_paso_no_bonus(self):
        self.set_hands([
            [Card(2, 'Oros'), Card(12, 'Bastos'), Card(12, 'Oros'), Card(12, 'Bastos')],
            [Card(1, 'Oros'), Card(4, 'Bastos'), Card(10, 'Oros'), Card(12, 'Bastos')],
            [Card(1, 'Oros'), Card(6, 'Bastos'), Card(10, 'Oros'), Card(11, 'Bastos')],
            [Card(1, 'Oros'), Card(1, 'Bastos'), Card(2, 'Oros'), Card(2, 'Bastos')],
        ])
        self.advance_to_test_state()

        status = self.game.status()

        self.assertEqual(status['Pariak']['IsSkipped'], False)
        self.assertEqual(status['Pariak']['Bid'], 1)
        self.assertEqual(status['Pariak']['Winner'], None)
        self.assertEqual(status['Pariak']['Bonus'], None)

        self.unwrap(self.game.do(("paso", {"player_id": self.player_1})))
        self.unwrap(self.game.do(("paso", {"player_id": self.player_4})))

        self.go_through_finished()

        status = self.game.status()

        self.assertEqual(status['Pariak']['Winner'], 1)
        self.assertEqual(status['Pariak']['Bonus'], None)

    def test_3_players_in_game_paso(self):
        self.set_hands([
            [Card(2, 'Oros'), Card(3, 'Bastos'), Card(4, 'Oros'), Card(5, 'Bastos')],
            [Card(1, 'Oros'), Card(4, 'Bastos'), Card(12, 'Oros'), Card(12, 'Bastos')],
            [Card(1, 'Oros'), Card(6, 'Bastos'), Card(11, 'Oros'), Card(11, 'Bastos')],
            [Card(1, 'Oros'), Card(1, 'Bastos'), Card(2, 'Oros'), Card(2, 'Bastos')],
        ])
        self.advance_to_test_state()

        status = self.game.status()

        self.assertEqual(status['Pariak']['IsSkipped'], False)
        self.assertEqual(status['Pariak']['Bid'], 1)
        self.assertEqual(status['Pariak']['Winner'], None)
        self.assertEqual(status['Pariak']['Bonus'], None)

        self.unwrap(self.game.do(("paso", {"player_id": self.player_2})))
        self.unwrap(self.game.do(("paso", {"player_id": self.player_3})))
        self.unwrap(self.game.do(("paso", {"player_id": self.player_4})))

        self.assertState("Jokua")

    def test_3_players_in_game_bet(self):
        self.set_hands([
            [Card(2, 'Oros'), Card(3, 'Bastos'), Card(4, 'Oros'), Card(5, 'Bastos')],
            [Card(1, 'Oros'), Card(4, 'Bastos'), Card(12, 'Oros'), Card(12, 'Bastos')],
            [Card(1, 'Oros'), Card(6, 'Bastos'), Card(11, 'Oros'), Card(11, 'Bastos')],
            [Card(1, 'Oros'), Card(1, 'Bastos'), Card(2, 'Oros'), Card(2, 'Bastos')],
        ])
        self.advance_to_test_state()

        status = self.game.status()

        self.assertEqual(status['Pariak']['IsSkipped'], False)
        self.assertEqual(status['Pariak']['Bid'], 1)
        self.assertEqual(status['Pariak']['Winner'], None)
        self.assertEqual(status['Pariak']['Bonus'], None)

        self.unwrap(self.game.do(("imido", {"player_id": self.player_2})))
        self.unwrap(self.game.do(("gehiago", {"player_id": self.player_3,
                                              "offer": 2})))

        status = self.game.status()

        for player, info in status["players"].items():
            can_speak = (player == self.player_2_public or player == self.player_4_public)
            self.assertEqual(info["can_speak"], can_speak)


class TestJokua(unittest.TestCase, TestGame):
    def setUp(self):
        self.game = Game()

        self.register_four_player()
        self.unwrap(self.game.do(("start_game", {"player_id": self.player_1})))

    def advance_to_test_state(self):
        self.go_through_speaking()
        self.go_through_betstate()
        self.go_through_betstate()
        self.go_through_betstate()

    def advance_to_finished(self):
        ...

    def test_puntua(self):
        self.set_hands([
            [Card(2, 'Oros'), Card(3, 'Bastos'), Card(10, 'Oros'), Card(12, 'Bastos')],
            [Card(1, 'Oros'), Card(4, 'Bastos'), Card(10, 'Oros'), Card(12, 'Bastos')],
            [Card(1, 'Oros'), Card(5, 'Bastos'), Card(10, 'Oros'), Card(11, 'Bastos')],
            [Card(1, 'Oros'), Card(6, 'Bastos'), Card(10, 'Oros'), Card(11, 'Bastos')]
        ])
        self.advance_to_test_state()

        status = self.game.status()
        self.assertEqual(status['Jokua']['IsSkipped'], False)
        self.assertEqual(status['Jokua']['Bid'], 1)
        map(self.assertFalse, status['Jokua']['PlayerHasIt'].keys())

        self.unwrap(self.game.do(("imido", {"player_id": self.player_1})))
        self.unwrap(self.game.do(("iduki", {"player_id": self.player_2})))

        status = self.game.status()
        self.assertEqual(status['Jokua']['IsSkipped'], False)
        self.assertEqual(next(iter(status['Jokua']['Bonus'].values())), 1)

    def test_jokua_with_bonus(self):
        self.set_hands([
            [Card(2, 'Oros'), Card(3, 'Bastos'), Card(10, 'Oros'), Card(12, 'Bastos')],
            [Card(4, 'Oros'), Card(10, 'Bastos'), Card(10, 'Oros'), Card(12, 'Bastos')],
            [Card(1, 'Oros'), Card(10, 'Bastos'), Card(10, 'Oros'), Card(11, 'Bastos')],
            [Card(7, 'Oros'), Card(7, 'Bastos'), Card(11, 'Oros'), Card(11, 'Bastos')]
        ])
        self.advance_to_test_state()

        status = self.game.status()
        self.assertEqual(status['Jokua']['IsSkipped'], False)
        self.assertEqual(status['Jokua']['Bid'], 1)

        self.unwrap(self.game.do(("imido", {"player_id": self.player_2})))
        self.unwrap(self.game.do(("tira", {"player_id": self.player_3})))

        status = self.game.status()
        self.assertEqual(status['Jokua']['Bonus'], {self.player_2_public: 2,
                                                    self.player_4_public: 2})


class TestNextTurn(unittest.TestCase, TestGame):
    def setUp(self):
        self.game = Game()

        self.register_four_player()
        self.unwrap(self.game.do(("start_game", {"player_id": self.player_1})))
        self.go_through_speaking()
        self.go_through_betstate()
        self.go_through_betstate()
        self.go_through_betstate()
        self.go_through_betstate()

    def test_paso_imido_iduki(self):
        self.go_through_finished()

        self.assertState("Speaking")
        status = self.game.status()

        self.assertTrue("Haundia" not in status)
        self.assertTrue("Tipia" not in status)
        self.assertTrue("Pariak" not in status)
        self.assertTrue("Jokua" not in status)
        self.assertTrue("Finished" not in status)

        self.assertEqual(status["echku_order"], ['Jacques', 'Julien', 'Jeremy', 'Jean'])


class TestFinishing(unittest.TestCase, TestGame):
    def setUp(self):
        self.game = Game()

        self.register_four_player()
        self.unwrap(self.game.do(("start_game", {"player_id": self.player_1})))

    def test_finish_right_order_tira(self):
        self.set_hands([
            [Card(2, 'Oros'), Card(3, 'Bastos'), Card(10, 'Oros'), Card(12, 'Bastos')],
            [Card(4, 'Oros'), Card(10, 'Bastos'), Card(11, 'Oros'), Card(12, 'Bastos')],
            [Card(1, 'Oros'), Card(10, 'Bastos'), Card(10, 'Oros'), Card(11, 'Bastos')],
            [Card(7, 'Oros'), Card(7, 'Bastos'), Card(11, 'Oros'), Card(11, 'Bastos')]
        ])

        self.game.player_manager.teams[0].score = 39
        self.game.player_manager.teams[1].score = 38

        self.go_through_speaking()

        self.unwrap(self.game.do(("imido", {"player_id": self.player_1})))
        self.unwrap(self.game.do(("iduki", {"player_id": self.player_2})))

        self.unwrap(self.game.do(("imido", {"player_id": self.player_1})))
        self.unwrap(self.game.do(("tira", {"player_id": self.player_2})))

        status = self.game.status()

        self.assertState("Finished")
        self.assertEqual(status["game_over"], True)
        self.assertEqual(status["winner"], 0)

    def test_finish_right_order_iduki(self):
        self.set_hands([
            [Card(2, 'Oros'), Card(3, 'Bastos'), Card(10, 'Oros'), Card(12, 'Bastos')],
            [Card(1, 'Oros'), Card(10, 'Bastos'), Card(10, 'Oros'), Card(11, 'Bastos')],
            [Card(4, 'Oros'), Card(10, 'Bastos'), Card(11, 'Oros'), Card(12, 'Bastos')],
            [Card(7, 'Oros'), Card(7, 'Bastos'), Card(11, 'Oros'), Card(11, 'Bastos')]
        ])

        self.game.player_manager.teams[0].score = 39
        self.game.player_manager.teams[1].score = 38

        self.go_through_speaking()

        self.unwrap(self.game.do(("paso", {"player_id": self.player_1})))
        self.unwrap(self.game.do(("imido", {"player_id": self.player_2})))
        self.unwrap(self.game.do(("tira", {"player_id": self.player_1})))

        self.unwrap(self.game.do(("imido", {"player_id": self.player_1})))
        self.unwrap(self.game.do(("iduki", {"player_id": self.player_2})))

        self.go_through_betstate()
        self.go_through_betstate()

        status = self.game.status()

        self.assertState("Finished")

        self.assertEqual(status["game_over"], True)
        self.assertEqual(status["winner"], 1)

    def test_finish_and_restart(self):
        self.set_hands([
            [Card(2, 'Oros'), Card(3, 'Bastos'), Card(10, 'Oros'), Card(12, 'Bastos')],
            [Card(1, 'Oros'), Card(10, 'Bastos'), Card(10, 'Oros'), Card(11, 'Bastos')],
            [Card(4, 'Oros'), Card(10, 'Bastos'), Card(11, 'Oros'), Card(12, 'Bastos')],
            [Card(7, 'Oros'), Card(7, 'Bastos'), Card(11, 'Oros'), Card(11, 'Bastos')]
        ])

        self.game.player_manager.teams[0].score = 39
        self.game.player_manager.teams[1].score = 38

        self.go_through_speaking()

        self.unwrap(self.game.do(("paso", {"player_id": self.player_1})))
        self.unwrap(self.game.do(("imido", {"player_id": self.player_2})))
        self.unwrap(self.game.do(("tira", {"player_id": self.player_1})))

        self.unwrap(self.game.do(("imido", {"player_id": self.player_1})))
        self.unwrap(self.game.do(("iduki", {"player_id": self.player_2})))

        self.go_through_betstate()
        self.go_through_betstate()

        status = self.game.status()

        self.assertState("Finished")
        self.assertEqual(status["game_over"], True)
        self.assertEqual(status["winner"], 1)

        self.go_through_finished()
        self.assertState("Speaking")


if __name__ == '__main__':
    unittest.main()
