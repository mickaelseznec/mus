import unittest
import mus

class TestInitialMus(unittest.TestCase):

    def setUp(self):
        self.game = mus.Game(0)
        self.christophe = mus.Player(1, "Christophe")
        self.gerard = mus.Player(2, "Gerard")
        self.thierry = mus.Player(3, "Thierry")
        self.michel = mus.Player(4, "Michel")

    def test_other_team(self):
        self.assertEqual(self.game.other_team(0), 1)
        self.assertEqual(self.game.other_team(1), 0)

    def test_add_player(self):
        self.game.add_player(self.christophe, 1)
        self.assertTrue(self.christophe in self.game)

    def test_add_multiple_player(self):
        self.game.add_player(self.christophe, 1)
        self.game.add_player(self.christophe, 1)
        self.assertEqual(len(self.game.teams[1]), 1)

    def test_remove_player(self):
        self.game.add_player(self.christophe, 1)
        self.game.remove_player(self.christophe)
        self.assertTrue(self.christophe not in self.game)

    def test_can_join_team(self):
        self.assertTrue(self.game.can_join_team(0))
        self.assertTrue(self.game.can_join_team(1))
        self.game.add_player(self.christophe, 0)
        self.game.add_player(self.gerard, 0)
        self.assertFalse(self.game.can_join_team(0))
        self.assertTrue(self.game.can_join_team(1))

    def test_can_start(self):
        self.assertFalse(self.game.can_start())
        self.game.add_player(self.christophe, 0)
        self.game.add_player(self.gerard, 1)
        self.assertTrue(self.game.can_start())
        self.game.add_player(self.thierry, 1)
        self.assertFalse(self.game.can_start())
        self.game.add_player(self.michel, 0)
        self.assertTrue(self.game.can_start())

    def test_is_started(self):
        self.assertFalse(self.game.is_started)
        self.game.add_player(self.christophe, 0)
        self.game.add_player(self.gerard, 1)
        self.game.start()
        self.assertTrue(self.game.is_started)

class TestTwoPlayerMus(unittest.TestCase):

    def setUp(self):
        self.game = mus.Game(0)
        self.christophe = mus.Player(1, "Christophe")
        self.gerard = mus.Player(2, "Gerard")
        self.game.add_player(self.christophe, 0)
        self.game.add_player(self.gerard, 1)
        self.game.start()

    def test_card_distribution(self):
        cards = [player.get_cards() for team in self.game.teams for player in team.players]
        # Check if not card is here twice
        self.assertEqual(len(cards), len(list(set(cards))))
        self.assertEqual(len(self.game.card_numbers), 36)

    def test_first_turn(self):
        self.assertEqual(self.game.turn.turn, "Truke")

    def test_order_play(self):
        self.assertEqual(self.game.current_team, 0)
        self.game.play("Mus")
        self.assertEqual(self.game.current_team, 1)
        self.game.play("Mus")
        self.assertEqual(self.game.current_team, 0)

if __name__ == '__main__':
    unittest.main()
