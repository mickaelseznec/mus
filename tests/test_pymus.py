import sys
sys.path.append("pymus")

import itertools as it
import unittest

import mus
from mus import Game, Card, Team, PlayerManager

class TestPlayerManager(unittest.TestCase):
    def setUp(self):
        self.player_manager = PlayerManager()

    def test_add_one_player(self):
        self.assertEqual(len(self.player_manager.teams[0]), 0)

        player_id = self.player_manager.add_player(None, 0)

        self.assertEqual(len(self.player_manager.teams[0]), 1)
        self.assertEqual(player_id, 0)

    def test_delete_player(self):
        player_id = self.player_manager.add_player(None, 0)
        self.assertEqual(len(self.player_manager.teams[0]), 1)

        self.player_manager.remove_player(player_id)
        self.assertEqual(len(self.player_manager.teams[0]), 0)

    def test_many_players(self):
        self.assertEqual(len(self.player_manager.teams[0]), 0)
        self.assertEqual(len(self.player_manager.teams[1]), 0)

        player_id_1 = self.player_manager.add_player(None, 0)
        player_id_2 = self.player_manager.add_player(None, 0)
        player_id_3 = self.player_manager.add_player(None, 1)
        player_id_4 = self.player_manager.add_player(None, 1)

        self.assertEqual(len(self.player_manager.teams[0]), 2)
        self.assertEqual(len(self.player_manager.teams[1]), 2)

        player_id_list = (player_id_1, player_id_2, player_id_3, player_id_4)
        self.assertEqual(len(player_id_list), len(set(player_id_list)))

    def test_cannot_exceed_two_per_team(self):
        player_id_1 = self.player_manager.add_player(None, 0)
        player_id_2 = self.player_manager.add_player(None, 0)

        self.assertRaises(mus.ForbiddenActionException,
                          self.player_manager.add_player, None, 0)

        player_id_3 = self.player_manager.add_player(None, 1)
        player_id_4 = self.player_manager.add_player(None, 1)

        self.player_manager.add_player(player_id_1, 0)

        self.assertRaises(mus.ForbiddenActionException,
                          self.player_manager.add_player, player_id_1, 1)

    def test_change_teams(self):
        player_id_1 = self.player_manager.add_player(None, 0)
        player_id_2 = self.player_manager.add_player(None, 0)

        self.assertEqual(len(self.player_manager.teams[0]), 2)

        player_id_1_save = player_id_1
        player_id_1 = self.player_manager.add_player(player_id_1, 1)

        self.assertEqual(player_id_1_save, player_id_1)

        self.assertEqual(len(self.player_manager.teams[0]), 1)
        self.assertEqual(len(self.player_manager.teams[1]), 1)


class TestWaitingRoom(unittest.TestCase):
    def setUp(self):
        self.game = Game()

    def test_add_players(self):
        player_1 = self.game.do(("add_player", {"team_id": 1}))["result"]
        player_2 = self.game.do(("add_player", {"team_id": 2}))["result"]

        player_3 = self.game.do(("add_player", {"team_id": 1}))["result"]
        player_4 = self.game.do(("add_player", {"team_id": 2}))["result"]

        res = self.game.do(("add_player", {"team_id": 2}))
        self.assertEqual(res["status"], "Forbidden")

    def test_add_same_player(self):
        player_1 = self.game.do(("add_player", {"team_id": 1}))["result"]
        player_1_new = self.game.do(("add_player", {"team_id": 1, "player_id": player_1}))["result"]

        self.assertEqual(player_1, player_1_new)

    def test_remove_player(self):
        player_1 = self.game.do(("add_player", {"team_id": 1}))["result"]
        self.game.do(("remove_player", {"player_id": player_1}))["result"]

        status = self.game.status()
        self.assertTrue(player_1 not in (player["player_id"] for player in status["players"]))

    def test_start_with_two_players(self):
        player_1 = self.game.do(("add_player", {"team_id": 1}))["result"]
        player_2 = self.game.do(("add_player", {"team_id": 2}))["result"]

        self.game.do(("start_game", {}))

        status = self.game.status()
        self.assertEqual(status["current_state"], "Speaking")

    def test_cannot_start_with_three_players(self):
        player_1 = self.game.do(("add_player", {"team_id": 1}))["result"]
        player_2 = self.game.do(("add_player", {"team_id": 2}))["result"]
        player_3 = self.game.do(("add_player", {"team_id": 1}))["result"]

        res = self.game.do(("start_game", {}))
        self.assertEqual(res["status"], "Forbidden")

        status = self.game.status()
        self.assertEqual(status["current_state"], "Waiting Room")

    def test_start_with_four_players(self):
        player_1 = self.game.do(("add_player", {"team_id": 1}))["result"]
        player_2 = self.game.do(("add_player", {"team_id": 2}))["result"]
        player_3 = self.game.do(("add_player", {"team_id": 1}))["result"]
        player_4 = self.game.do(("add_player", {"team_id": 2}))["result"]

        self.game.do(("start_game", {}))

        status = self.game.status()
        self.assertEqual(status["current_state"], "Speaking")


class TestInitialSpeakingTrading(unittest.TestCase):

    def setUp(self):
        self.game = Game()

        self.player_1 = self.game.do(("add_player", {"team_id": 1}))["result"]
        self.player_2 = self.game.do(("add_player", {"team_id": 2}))["result"]
        self.player_3 = self.game.do(("add_player", {"team_id": 1}))["result"]
        self.player_4 = self.game.do(("add_player", {"team_id": 2}))["result"]
        self.game.do(("start_game", {}))

    def test_in_right_state(self):
        status = self.game.status()
        self.assertEqual(status["current_state"], "Speaking")

    def test_who_can_speak(self):
        player_can_speak = {player["player_id"]: player["can_speak"] for
                         player in self.game.status()["players"]}

        self.assertTrue(player_can_speak[self.player_1])
        self.assertTrue(player_can_speak[self.player_3])
        self.assertFalse(player_can_speak[self.player_2])
        self.assertFalse(player_can_speak[self.player_4])

        res = self.game.do(("mus", {"player_id": self.player_2}))
        self.assertEqual(res["status"], "WrongPlayer")

        res = self.game.do(("mus", {"player_id": self.player_1}))
        self.assertEqual(res["status"], "OK")

        res = self.game.do(("mus", {"player_id": self.player_3}))
        self.assertEqual(res["status"], "WrongPlayer")

        res = self.game.do(("mus", {"player_id": self.player_4}))
        self.assertEqual(res["status"], "OK")

        status = self.game.status()
        self.assertEqual(status["current_state"], "Trading")

# class TestTwoPlayerHandiak(unittest.TestCase):
#     own_name = "Haundia"
#     next_name = "Tipia"

#     def setUp(self):
#         self.game = Game(0)
#         self.christophe = 1
#         self.gerard = 2
#         self.game.do("add_player", 1, "Christophe", "0")
#         self.game.do("add_player", 2, "Gerard", "1")
#         self.game.do("start", self.christophe)
#         self.game.do("mintza", self.christophe)

#     def test_init_handiak(self):
#         self.assertEqual(self.game.current, self.own_name)
#         self.assertEqual(self.game.players.echku, self.game.players[self.christophe])

#     def test_paso_paso(self):
#         self.game.do("paso", self.christophe)
#         self.game.do("paso", self.gerard)
#         self.assertEqual(self.game.current, self.next_name)

#     def test_paso_imido_idoki(self):
#         self.game.do("paso", self.christophe)
#         self.game.do("imido", self.gerard)
#         self.game.do("idoki", self.christophe)
#         self.assertTrue(self.game.states[self.own_name].deffered)
#         self.assertEqual(self.game.states[self.own_name].bet, 2)
#         self.assertEqual(self.game.current, self.next_name)

#     def test_imido_bi_hiru_idoki(self):
#         self.game.do("imido", self.christophe)
#         self.game.do("gehiago", self.gerard, "2")
#         self.game.do("gehiago", self.christophe, "3")
#         self.game.do("idoki", self.gerard)
#         self.assertTrue(self.game.states[self.own_name].deffered)
#         self.assertEqual(self.game.states[self.own_name].bet, 7)
#         self.assertEqual(self.game.current, self.next_name)

#     def test_paso_imido_tira(self):
#         self.game.do("paso", self.christophe)
#         self.game.do("imido", self.gerard)
#         self.game.do("tira", self.christophe)
#         self.assertFalse(self.game.states[self.own_name].deffered)
#         self.assertEqual(self.game.states[self.own_name].bet, 1)
#         self.assertEqual(self.game.players[self.gerard].team.score, 1)
#         self.assertEqual(self.game.current, self.next_name)

#     def test_imdido_lau_tira(self):
#         self.game.do("imido", self.christophe)
#         self.game.do("gehiago", self.gerard, "4")
#         self.game.do("tira", self.christophe)
#         self.assertEqual(self.game.states[self.own_name].bet, 2)
#         self.assertEqual(self.game.players[self.gerard].team.score, 2)
#         self.assertEqual(self.game.current, self.next_name)


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
