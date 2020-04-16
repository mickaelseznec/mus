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

        player_id = self.player_manager.add(None, 0)

        self.assertEqual(len(self.player_manager.teams[0]), 1)
        self.assertEqual(player_id, 0)

    def test_many_players(self):
        self.assertEqual(len(self.player_manager.teams[0]), 0)
        self.assertEqual(len(self.player_manager.teams[1]), 0)

        player_id_1 = self.player_manager.add(None, 0)
        player_id_2 = self.player_manager.add(None, 0)
        player_id_3 = self.player_manager.add(None, 1)
        player_id_4 = self.player_manager.add(None, 1)

        self.assertEqual(len(self.player_manager.teams[0]), 2)
        self.assertEqual(len(self.player_manager.teams[1]), 2)

        player_id_list = (player_id_1, player_id_2, player_id_3, player_id_4)
        self.assertEqual(len(player_id_list), len(set(player_id_list)))

    def test_cannot_exceed_two_per_team(self):
        player_id_1 = self.player_manager.add(None, 0)
        player_id_2 = self.player_manager.add(None, 0)

        self.assertRaises(mus.ForbiddenActionException,
                          self.player_manager.add, None, 0)

        player_id_3 = self.player_manager.add(None, 1)
        player_id_4 = self.player_manager.add(None, 1)

        self.player_manager.add(player_id_1, 0)

        self.assertRaises(mus.ForbiddenActionException,
                          self.player_manager.add, player_id_1, 1)

    def test_change_teams(self):
        player_id_1 = self.player_manager.add(None, 0)
        player_id_2 = self.player_manager.add(None, 0)

        self.assertEqual(len(self.player_manager.teams[0]), 2)

        player_id_1_save = player_id_1
        player_id_1 = self.player_manager.add(player_id_1, 1)

        self.assertEqual(player_id_1_save, player_id_1)

        self.assertEqual(len(self.player_manager.teams[0]), 1)
        self.assertEqual(len(self.player_manager.teams[1]), 1)


# class TestInitialMus(unittest.TestCase):

#     def setUp(self):
#         self.game = Game(0)
#         self.christophe = (1, "Christophe")
#         self.gerard = (2, "Gerard")
#         self.thierry = (3, "Thierry")
#         self.michel = (4, "Michel")

#     def test_other_team(self):
#         team_0 = self.game.players.get_team(0)
#         team_1 = self.game.players.get_team(1)
#         self.assertEqual(team_0, self.game.players.other_team(team_1))
#         self.assertEqual(team_1, self.game.players.other_team(team_0))

#     def test_add_player(self):
#         self.game.do("add_player", *self.christophe, "1")
#         self.assertTrue(self.christophe[0] in self.game.players)

#     def test_add_multiple_player(self):
#         self.game.do("add_player", *self.christophe, "1")
#         self.game.do("add_player", *self.christophe, "1")
#         self.assertEqual(len(self.game.players.get_team(1)), 1)

#     def test_remove_player(self):
#         self.game.do("add_player", *self.christophe, "1")
#         self.game.do("remove_player", self.christophe[0])
#         self.assertTrue(self.christophe not in self.game.players)

#     def test_change_team(self):
#         self.game.do("add_player", *self.christophe, "1")
#         self.game.do("add_player", *self.christophe, "0")
#         self.assertTrue(self.game.players[self.christophe[0]].team.number == 0)

#     def test_can_join_team(self):
#         self.assertTrue(self.game.can_join_team(0))
#         self.assertTrue(self.game.can_join_team(1))
#         self.game.do("add_player", *self.christophe, "0")
#         self.game.do("add_player", *self.gerard, "0")
#         self.assertFalse(self.game.can_join_team(0))
#         self.assertTrue(self.game.can_join_team(1))

#     def test_can_start(self):
#         self.assertFalse("start" in self.game.state.actions_authorised())
#         self.game.do("add_player", *self.christophe, "0")
#         self.game.do("add_player", *self.gerard, "1")
#         self.assertTrue("start" in self.game.state.actions_authorised())
#         self.game.do("add_player", *self.thierry, "1")
#         self.assertFalse("start" in self.game.state.actions_authorised())
#         self.game.do("add_player", *self.michel, "0")
#         self.assertTrue("start" in self.game.state.actions_authorised())

#     def test_is_started(self):
#         self.assertEqual(self.game.current, "waiting_room")
#         self.game.do("add_player", *self.christophe, "0")
#         self.game.do("add_player", *self.gerard, "1")
#         self.game.do("start", self.gerard[0])
#         self.assertNotEqual(self.game.current, "waiting_room")

# class TestTwoPlayerSpeakTrade(unittest.TestCase):

#     def setUp(self):
#         self.game = Game(0)
#         self.christophe = 1
#         self.gerard = 2
#         self.game.do("add_player", 1, "Christophe", "0")
#         self.game.do("add_player", 2, "Gerard", "1")
#         self.game.do("start", self.christophe)

#     def test_first_turn(self):
#         self.assertEqual(self.game.current, "Speaking")

#     def test_play_mus(self):
#         self.assertTrue(self.christophe in self.game.state.players_authorised())
#         self.assertRaises(mus.ForbiddenActionException, self.game.do, "mus", self.gerard)
#         self.assertTrue(self.christophe in self.game.state.players_authorised())
#         self.game.do("mus", self.christophe)
#         self.assertTrue(self.gerard in self.game.state.players_authorised())
#         self.game.do("mus", self.gerard)

#         old_gerard_cards = self.game.players[self.gerard].get_cards().copy()
#         old_christophe_cards = self.game.players[self.christophe].get_cards().copy()
#         self.game.do("change", self.christophe, "2")
#         self.game.do("change", self.christophe, "3")
#         self.game.do("confirm", self.christophe)

#         self.assertRaises(mus.ForbiddenActionException,
#                           self.game.do, "confirm", self.gerard)
#         self.game.do("change", self.gerard, "1")
#         self.game.do("confirm", self.gerard)

#         new_gerard_cards = self.game.players[self.gerard].get_cards().copy()
#         new_christophe_cards = self.game.players[self.christophe].get_cards().copy()

#         self.assertTrue(old_christophe_cards[0] in new_christophe_cards)
#         self.assertTrue(old_christophe_cards[1] not in new_christophe_cards)
#         self.assertTrue(old_christophe_cards[2] not in new_christophe_cards)
#         self.assertTrue(old_christophe_cards[3] in new_christophe_cards)

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
