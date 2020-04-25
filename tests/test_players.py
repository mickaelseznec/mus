import sys
sys.path.append("pymus")

import unittest

from MusExceptions import *
from Players import PlayerManager

class TestPlayerManager(unittest.TestCase):
    def setUp(self):
        self.player_manager = PlayerManager()

    def test_add_one_player(self):
        self.assertEqual(len(self.player_manager.teams[0]), 0)

        player_id = self.player_manager.add_player(None, 0)

        self.assertEqual(len(self.player_manager.teams[0]), 1)

    def test_delete_player(self):
        player_id = self.player_manager.add_player(None, 0)
        self.assertEqual(len(self.player_manager.teams[0]), 1)

        self.player_manager.remove_player(player_id[0])
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

        self.assertRaises(ForbiddenActionException,
                          self.player_manager.add_player, None, 0)

        player_id_3 = self.player_manager.add_player(None, 1)
        player_id_4 = self.player_manager.add_player(None, 1)

        self.player_manager.add_player(player_id_1[0], 0)

        self.assertRaises(ForbiddenActionException,
                          self.player_manager.add_player, player_id_1[0], 1)

    def test_change_teams(self):
        player_id_1 = self.player_manager.add_player(None, 0)
        player_id_2 = self.player_manager.add_player(None, 0)

        self.assertEqual(len(self.player_manager.teams[0]), 2)

        player_id_1_save = player_id_1
        player_id_1 = self.player_manager.add_player(player_id_1[0], 1)

        self.assertEqual(player_id_1_save, player_id_1)

        self.assertEqual(len(self.player_manager.teams[0]), 1)
        self.assertEqual(len(self.player_manager.teams[1]), 1)


if __name__ == '__main__':
    unittest.main()
