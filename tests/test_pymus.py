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
        player_1, _ = self.unwrap(self.game.do(("add_player", {"team_id": 0})))
        player_2, _ = self.unwrap(self.game.do(("add_player", {"team_id": 1})))
        player_3, _ = self.unwrap(self.game.do(("add_player", {"team_id": 0})))
        player_4, _ = self.unwrap(self.game.do(("add_player", {"team_id": 1})))

        self.player_1, self.player_1_public = player_1
        self.player_2, self.player_2_public = player_2
        self.player_3, self.player_3_public = player_3
        self.player_4, self.player_4_public = player_4

        self.public_to_private = {player[1]: player[0]
                                  for player in (player_1, player_2, player_3, player_4)}

    def player_speaking(self):
        status = self.game.status()
        for player in status["players"]:
            if player["can_speak"]:
                return self.public_to_private[player["player_id"]]
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
        (player_1, _), _ = self.unwrap(self.game.do(("add_player", {"team_id": 0})))
        (player_2, _), _ = self.unwrap(self.game.do(("add_player", {"team_id": 1})))

        (player_3, _), _ = self.unwrap(self.game.do(("add_player", {"team_id": 0})))
        (player_4, _), _ = self.unwrap(self.game.do(("add_player", {"team_id": 1})))

        self.unwrap_fails(self.game.do(("add_player", {"team_id": 1})), "Forbidden")

    def test_add_same_player(self):
        player_1, _ = self.unwrap(self.game.do(("add_player", {"team_id": 0})))
        player_1_new, _ = self.unwrap(self.game.do((
            "add_player", {"team_id": 0, "player_id": player_1[0]})))

        self.assertEqual(player_1, player_1_new)

    def test_remove_player(self):
        player_1, _ = self.unwrap(self.game.do(("add_player", {"team_id": 0})))

        _, state = self.unwrap(self.game.do(("remove_player", {"player_id": player_1[0]})))
        self.assertTrue(player_1[1] not in (player["player_id"] for player in state["players"]))

    def test_start_with_two_players(self):
        (player_1, _), _ = self.unwrap(self.game.do(("add_player", {"team_id": 0})))
        (player_2, _), _ = self.unwrap(self.game.do(("add_player", {"team_id": 1})))

        self.unwrap(self.game.do(("start_game", {"player_id": player_1})))
        self.assertState("Speaking")

    def test_cannot_start_with_three_players(self):
        (player_1, _), _ = self.unwrap(self.game.do(("add_player", {"team_id": 0})))
        (player_2, _), _ = self.unwrap(self.game.do(("add_player", {"team_id": 1})))
        (player_3, _), _ = self.unwrap(self.game.do(("add_player", {"team_id": 0})))

        self.unwrap_fails(self.game.do(("start_game", {"player_id": player_1})), "Forbidden")

        self.assertState("Waiting Room")

    def test_start_with_four_players(self):
        (player_1, _), _ = self.unwrap(self.game.do(("add_player", {"team_id": 0})))
        (player_2, _), _ = self.unwrap(self.game.do(("add_player", {"team_id": 1})))
        (player_3, _), _ = self.unwrap(self.game.do(("add_player", {"team_id": 0})))
        (player_4, _), _ = self.unwrap(self.game.do(("add_player", {"team_id": 1})))

        self.unwrap(self.game.do(("start_game", {"player_id": player_1})))

        self.assertState("Speaking")


class TestSpeaking(unittest.TestCase, TestGame):

    def setUp(self):
        self.game = Game()
        self.register_four_player()
        self.unwrap(self.game.do(("start_game", {"player_id": self.player_1})))
        self.assertState("Speaking")

    def test_who_can_speak(self):
        player_can_speak = {player["player_id"]: player["can_speak"] for
                         player in self.game.status()["players"]}

        self.assertTrue(player_can_speak[self.player_1_public])
        self.assertTrue(player_can_speak[self.player_3_public])
        self.assertFalse(player_can_speak[self.player_2_public])
        self.assertFalse(player_can_speak[self.player_4_public])

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
            old_player_cards[player] = json.loads(self.unwrap(self.game.do((
                "get_cards", {"player_id": player})))[0])

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
            new_player_cards[player] = json.loads(self.unwrap(self.game.do((
                "get_cards", {"player_id": player})))[0])

        self.assertTrue(all([old_card not in new_player_cards[self.player_1]
             for old_card in old_player_cards[self.player_1]]))

        self.assertTrue(all([old_card not in new_player_cards[self.player_2]
             for old_card in [old_player_cards[self.player_2][i] for i in (0, 1)]]))
        self.assertTrue(all([old_card in new_player_cards[self.player_2]
             for old_card in [old_player_cards[self.player_2][i] for i in (2, 3)]]))

        self.assertTrue(all([old_card not in new_player_cards[self.player_3]
             for old_card in [old_player_cards[self.player_3][i] for i in (0, )]]))
        self.assertTrue(all([old_card in new_player_cards[self.player_3]
             for old_card in [old_player_cards[self.player_3][i] for i in (1, 2, 3)]]))

        self.assertTrue(all([old_card not in new_player_cards[self.player_4]
             for old_card in [old_player_cards[self.player_4][i] for i in (0, )]]))
        self.assertTrue(all([old_card in new_player_cards[self.player_4]
             for old_card in [old_player_cards[self.player_4][i] for i in (1, 2, 3)]]))

class TestHandia(unittest.TestCase, TestGame):
    def setUp(self):
        self.game = Game()
        self.register_four_player()
        self.unwrap(self.game.do(("start_game", {"player_id": self.player_1})))

    def advance_to_haundia(self):
        self.go_through_speaking()

    def advance_to_finished(self):
        self.go_through_betstate()
        self.go_through_betstate()
        self.go_through_betstate()

    def test_all_paso(self):
        self.advance_to_haundia()

        status = self.game.status()

        self.assertEqual(status['Haundia']['Bid'], 1)
        self.assertEqual(status['Haundia']['Offer'], 0)

        self.unwrap(self.game.do(("paso", {"player_id": self.player_1})))
        self.unwrap(self.game.do(("paso", {"player_id": self.player_2})))
        self.unwrap(self.game.do(("paso", {"player_id": self.player_3})))
        _, status = self.unwrap(self.game.do(("paso", {"player_id": self.player_4})))

        self.assertEqual(status['Haundia']['Bid'], 1)
        self.assertEqual(status['Haundia']['BidDiffered'], True)

        self.advance_to_finished()

        status = self.game.status()

    def test_paso_bet_iduki(self):
        self.advance_to_haundia()

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

        self.advance_to_finished()
        status = self.game.status()


class TestTipia(unittest.TestCase, TestGame):
    def setUp(self):
        self.game = Game()

        self.register_four_player()
        self.unwrap(self.game.do(("start_game", {"player_id": self.player_1})))
        self.go_through_speaking()
        self.go_through_betstate()

    def test_paso_imido_iduki(self):
        self.unwrap(self.game.do(("imido", {"player_id": self.player_1})))
        _, state = self.unwrap(self.game.do(("iduki", {"player_id": self.player_2})))

        self.assertEqual(state["current_state"], "Pariak")

class TestPariak(unittest.TestCase, TestGame):
    def setUp(self):
        self.game = Game()

        self.register_four_player()
        self.unwrap(self.game.do(("start_game", {"player_id": self.player_1})))
        self.go_through_speaking()
        self.go_through_betstate()
        self.go_through_betstate()

    def test_paso_imido_iduki(self):
        ...


    # def test_imido_bi_hiru_iduki(self):
    #     self.game.do("imido", self.christophe)
    #     self.game.do("gehiago", self.gerard, "2")
    #     self.game.do("gehiago", self.christophe, "3")
    #     self.game.do("iduki", self.gerard)
    #     self.assertTrue(self.game.states[self.own_name].deffered)
    #     self.assertEqual(self.game.states[self.own_name].bet, 7)
    #     self.assertEqual(self.game.current, self.next_name)

    # def test_paso_imido_tira(self):
    #     self.game.do("paso", self.christophe)
    #     self.game.do("imido", self.gerard)
    #     self.game.do("tira", self.christophe)
    #     self.assertFalse(self.game.states[self.own_name].deffered)
    #     self.assertEqual(self.game.states[self.own_name].bet, 1)
    #     self.assertEqual(self.game.players[self.gerard].team.score, 1)
    #     self.assertEqual(self.game.current, self.next_name)

    # def test_imdido_lau_tira(self):
    #     self.game.do("imido", self.christophe)
    #     self.game.do("gehiago", self.gerard, "4")
    #     self.game.do("tira", self.christophe)
    #     self.assertEqual(self.game.states[self.own_name].bet, 2)
    #     self.assertEqual(self.game.players[self.gerard].team.score, 2)
    #     self.assertEqual(self.game.current, self.next_name)


# class TestTwoPlayerTipia(TestTwoPlayerHandiak):
#     own_name = "Tipia"
#     next_name = "Pariak"
#     def setUp(self):
#         super().setUp()
#         self.game.do("paso", self.christophe)
#         self.game.do("paso", self.gerard)


# class TestFourPlayerPariak(unittest.TestCase):
#     def setUp(self):
#         self.game = Game(0)
#         self.paired_cards = sorted([Card(value=1, color='Oros'),
#                                     Card(value=5, color='Oros'),
#                                     Card(value=5, color='Bastos'),
#                                     Card(value=12, color='Copas')])
#         self.unpaired_cards = sorted([Card(value=2, color='Oros'),
#                                       Card(value=6, color='Oros'),
#                                       Card(value=7, color='Bastos'),
#                                       Card(value=11, color='Copas')])
#         self.christophe = 1
#         self.gerard = 2
#         self.michel = 3
#         self.robert = 4
#         self.game.do("add_player", 1, "Christophe", "0")
#         self.game.do("add_player", 2, "Gerard", "0")
#         self.game.do("add_player", 3, "Michel", "1")
#         self.game.do("add_player", 4, "Robert", "1")
#         self.game.do("start", self.christophe)

#         self.game.players[self.christophe].cards = self.unpaired_cards
#         self.game.players[self.michel].cards = self.paired_cards
#         self.game.players[self.gerard].cards = self.paired_cards
#         self.game.players[self.robert].cards = self.unpaired_cards

#         self.game.do("mintza", self.christophe)

#         self.game.do("imido", self.christophe)
#         self.game.do("tira", self.michel)

#         self.game.do("imido", self.christophe)
#         self.game.do("tira", self.michel)

#     def test_everyone_is_pacho(self):

#         self.assertEqual("Pariak", self.game.current)
#         self.game.do("paso", self.michel)
#         self.game.do("paso", self.gerard)
#         self.assertEqual("Jokua", self.game.current)

# class TestTwoPlayerPariak(unittest.TestCase):
#     def setUp(self):
#         self.game = Game(0)
#         self.paired_cards = sorted([Card(value=1, color='Oros'),
#                                     Card(value=5, color='Oros'),
#                                     Card(value=5, color='Bastos'),
#                                     Card(value=12, color='Copas')])
#         self.unpaired_cards = sorted([Card(value=2, color='Oros'),
#                                       Card(value=6, color='Oros'),
#                                       Card(value=7, color='Bastos'),
#                                       Card(value=11, color='Copas')])
#         self.christophe = 1
#         self.gerard = 2
#         self.game.do("add_player", 1, "Christophe", "0")
#         self.game.do("add_player", 2, "Gerard", "1")
#         self.game.do("start", self.christophe)
#         self.game.do("mintza", self.christophe)
#         self.game.do("paso", self.christophe)
#         self.game.do("paso", self.gerard)
#         self.game.do("paso", self.christophe)

#     def test_bai_ez(self):
#         self.game.players[self.christophe].cards = self.paired_cards
#         self.game.players[self.gerard].cards = self.unpaired_cards
#         self.game.do("paso", self.gerard)
#         self.assertEqual("Pariak", self.game.current)
#         self.assertTrue("ok" in self.game.states[self.game.current].actions_authorised())

#     def test_ez_ez(self):
#         self.game.players[self.christophe].cards = self.unpaired_cards
#         self.game.players[self.gerard].cards = self.unpaired_cards
#         self.game.do("paso", self.gerard)
#         self.assertEqual("Pariak", self.game.current)
#         self.assertTrue("ok" in self.game.states[self.game.current].actions_authorised())

#     def test_bai_bai(self):
#         self.game.players[self.christophe].cards = self.paired_cards
#         self.game.players[self.gerard].cards = self.paired_cards
#         self.game.do("paso", self.gerard)
#         self.assertEqual("Pariak", self.game.current)
#         self.assertTrue("ok" not in self.game.states[self.game.current].actions_authorised())
#         self.game.do("paso", self.christophe)
#         self.game.do("paso", self.gerard)


class TestJokua(unittest.TestCase, TestGame):
    def setUp(self):
        self.game = Game()

        self.register_four_player()
        self.unwrap(self.game.do(("start_game", {"player_id": self.player_1})))
        self.go_through_speaking()
        self.go_through_betstate()
        self.go_through_betstate()
        self.go_through_betstate()

    def test_paso_imido_iduki(self):
        self.go_through_betstate()
        ...


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
        ...

# class TestTwoPlayerJokua(unittest.TestCase):
#     def setUp(self):
#         self.game = Game(0)
#         self.game_cards = sorted([Card(value=4, color='Oros'),
#                                   Card(value=7, color='Oros'),
#                                   Card(value=10, color='Bastos'),
#                                   Card(value=12, color='Copas')])
#         self.nogame_cards = sorted([Card(value=2, color='Oros'),
#                                     Card(value=6, color='Oros'),
#                                     Card(value=7, color='Bastos'),
#                                     Card(value=11, color='Copas')])
#         self.christophe = 1
#         self.gerard = 2
#         self.game.do("add_player", 1, "Christophe", "0")
#         self.game.do("add_player", 2, "Gerard", "1")
#         self.game.do("start", self.christophe)
#         self.game.do("mintza", self.christophe)
#         self.game.do("paso", self.christophe)
#         self.game.do("paso", self.gerard)
#         # Tipia
#         self.game.do("paso", self.christophe)

#     def test_bai_ez(self):
#         self.game.players[self.christophe].cards = self.game_cards
#         self.game.players[self.gerard].cards = self.nogame_cards
#         self.game.do("paso", self.gerard)
#         self.game.do("ok", self.gerard)
#         self.game.do("ok", self.christophe)
#         self.assertEqual("Jokua", self.game.current)
#         self.assertTrue("ok" in self.game.states[self.game.current].actions_authorised())

#     def test_ez_ez(self):
#         self.game.players[self.christophe].cards = self.nogame_cards
#         self.game.players[self.gerard].cards = self.nogame_cards
#         self.game.do("paso", self.gerard)
#         self.game.do("ok", self.gerard)
#         self.game.do("ok", self.christophe)
#         self.assertEqual("Jokua", self.game.current)
#         self.assertTrue("ok" not in self.game.states[self.game.current].actions_authorised())
#         self.assertTrue(self.game.states[self.game.current].false_game)

#     def test_bai_bai(self):
#         self.game.players[self.christophe].cards = self.game_cards
#         self.game.players[self.gerard].cards = self.game_cards
#         self.game.do("paso", self.gerard)
#         self.game.do("ok", self.gerard)
#         self.assertEqual("Pariak", self.game.current)
#         self.game.do("ok", self.christophe)
#         self.assertEqual("Jokua", self.game.current)
#         self.assertTrue("ok" not in self.game.states[self.game.current].actions_authorised())
#         self.assertFalse(self.game.states[self.game.current].false_game)


if __name__ == '__main__':
    unittest.main()
