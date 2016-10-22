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
        self.assertEqual(mus.Team.other_team(0), 1)
        self.assertEqual(mus.Team.other_team(1), 0)

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
        cards = [card for card_set in cards for card in card_set]
        # Check if not card is here twice
        self.assertEqual(len(cards), len(set(cards)))
        self.assertEqual(len(self.game.turn.packet.unused_cards), 32)

    def test_first_turn(self):
        self.assertEqual(self.game.turn.current, "Truke")

    def test_play_mus(self):
        self.assertEqual(self.game.turn.current_team, 0)
        self.assertRaises(AssertionError, self.game.play, "Mus", self.gerard)
        self.assertEqual(self.game.turn.current_team, 0)
        self.game.play("Mus", self.christophe)
        self.assertEqual(self.game.turn.current_team, 1)
        self.game.play("Mus", self.gerard)

        gerard_cards = self.gerard.get_cards().copy()
        christophe_cards = self.christophe.get_cards().copy()
        self.game.play("2", self.christophe)
        self.game.play("3", self.christophe)
        self.game.play("Ready", self.christophe)
        self.game.play("Ready", self.gerard)

        self.assertEqual(gerard_cards, self.gerard.get_cards())

        self.assertEqual(christophe_cards[0], self.christophe.get_cards()[0])
        self.assertEqual(christophe_cards[1], self.christophe.get_cards()[1])
        self.assertNotEqual(christophe_cards[2], self.christophe.get_cards()[2])
        self.assertNotEqual(christophe_cards[3], self.christophe.get_cards()[3])

    def test_empy_card_packet(self):
        for i in range(50):
            self.game.play("Mus", self.christophe)
            self.game.play("Mus", self.gerard)
            self.game.play("0", self.christophe)
            self.game.play("1", self.christophe)
            self.game.play("2", self.christophe)
            self.game.play("3", self.christophe)
            self.game.play("0", self.gerard)
            self.game.play("1", self.gerard)
            self.game.play("2", self.gerard)

            gerard_cards = self.gerard.get_cards().copy()
            christophe_cards = self.christophe.get_cards().copy()
            self.game.play("Ready", self.christophe)
            self.game.play("Ready", self.gerard)

            for j in range(4):
                self.assertNotEqual(christophe_cards[j], self.christophe.get_cards()[j])
            for j in range(3):
                self.assertNotEqual(gerard_cards[j], self.gerard.get_cards()[j])
            self.assertEqual(gerard_cards[3], self.gerard.get_cards()[3])


if __name__ == '__main__':
    unittest.main()
