import unittest
import mus

class TestInitialMus(unittest.TestCase):

    def setUp(self):
        self.game = mus.Game(0)
        self.christophe = (1, "Christophe")
        self.gerard = (2, "Gerard")
        self.thierry = (3, "Thierry")
        self.michel = (4, "Michel")

    def test_other_team(self):
        self.assertEqual(mus.Team.other_team(0), 1)
        self.assertEqual(mus.Team.other_team(1), 0)

    def test_add_player(self):
        self.game.action("add_player", *self.christophe, "1")
        self.assertTrue(self.christophe[0] in self.game.players)

    def test_add_multiple_player(self):
        self.game.action("add_player", *self.christophe, "1")
        self.game.action("add_player", *self.christophe, "1")
        self.assertEqual(len(self.game.players.by_team(1)), 1)

    def test_remove_player(self):
        self.game.action("add_player", *self.christophe, "1")
        self.game.action("remove_player", self.christophe[0])
        self.assertTrue(self.christophe not in self.game.players)

    def test_change_team(self):
        self.game.action("add_player", *self.christophe, "1")
        self.game.action("add_player", *self.christophe, "0")
        self.assertTrue(self.christophe[0] in [p.id for p in self.game.players.by_team(0)])
        self.assertFalse(self.christophe[0] in [p.id for p in self.game.players.by_team(1)])

    def test_can_join_team(self):
        self.assertTrue(self.game.can_join_team(0))
        self.assertTrue(self.game.can_join_team(1))
        self.game.action("add_player", *self.christophe, "0")
        self.game.action("add_player", *self.gerard, "0")
        self.assertFalse(self.game.can_join_team(0))
        self.assertTrue(self.game.can_join_team(1))

    def test_can_start(self):
        self.assertFalse("start" in self.game.state.actions_authorised())
        self.game.action("add_player", *self.christophe, "0")
        self.game.action("add_player", *self.gerard, "1")
        self.assertTrue("start" in self.game.state.actions_authorised())
        self.game.action("add_player", *self.thierry, "1")
        self.assertFalse("start" in self.game.state.actions_authorised())
        self.game.action("add_player", *self.michel, "0")
        self.assertTrue("start" in self.game.state.actions_authorised())

    def test_is_started(self):
        self.assertEqual(self.game.current, "Waiting")
        self.game.action("add_player", *self.christophe, "0")
        self.game.action("add_player", *self.gerard, "1")
        self.game.action("start", self.gerard[0])
        self.assertNotEqual(self.game.current, "Waiting")

class TestTwoPlayerSpeakTrade(unittest.TestCase):

    def setUp(self):
        self.game = mus.Game(0)
        self.christophe = 1
        self.gerard = 2
        self.game.action("add_player", 1, "Christophe", "0")
        self.game.action("add_player", 2, "Gerard", "1")
        self.game.action("start", self.christophe)

    def test_card_distribution(self):
        cards = [player.get_cards() for player in self.game.players]
        cards = [card for card_set in cards for card in card_set]
        # Check if not card is here twice
        self.assertEqual(len(cards), len(set(cards)))
        self.assertEqual(len(self.game.packet.unused_cards), 32)

    def test_first_turn(self):
        self.assertEqual(self.game.current, "Speaking")

    def test_play_mus(self):
        self.assertTrue(self.christophe in self.game.state.players_authorised())
        self.assertRaises(mus.ForbiddenActionException, self.game.action, "mus", self.gerard)
        self.assertTrue(self.christophe in self.game.state.players_authorised())
        self.game.action("mus", self.christophe)
        self.assertTrue(self.gerard in self.game.state.players_authorised())
        self.game.action("mus", self.gerard)

        old_gerard_cards = self.game.players[self.gerard].get_cards().copy()
        old_christophe_cards = self.game.players[self.christophe].get_cards().copy()
        self.game.action("change", self.christophe, "2")
        self.game.action("change", self.christophe, "3")
        self.game.action("confirm", self.christophe)
        self.game.action("confirm", self.gerard)

        new_gerard_cards = self.game.players[self.gerard].get_cards().copy()
        new_christophe_cards = self.game.players[self.christophe].get_cards().copy()

        self.assertEqual(old_gerard_cards, new_gerard_cards)

        self.assertTrue(old_christophe_cards[0] in new_christophe_cards)
        self.assertTrue(old_christophe_cards[1] in new_christophe_cards)
        self.assertFalse(old_christophe_cards[2] in new_christophe_cards)
        self.assertFalse(old_christophe_cards[3] in new_christophe_cards)

    def test_empy_card_packet(self):
        for _ in range(50):
            self.game.action("mus", self.christophe)
            self.game.action("mus", self.gerard)
            self.game.action("change", self.christophe, "0")
            self.game.action("change", self.christophe, "1")
            self.game.action("change", self.christophe, "2")
            self.game.action("change", self.christophe, "3")
            self.game.action("change", self.gerard, "0")
            self.game.action("change", self.gerard, "1")
            self.game.action("change", self.gerard, "2")

            old_gerard_cards = self.game.players[self.gerard].get_cards().copy()
            old_christophe_cards = self.game.players[self.christophe].get_cards().copy()
            overflow = len(self.game.packet.unused_cards) < 7
            self.game.action("confirm", self.christophe)
            self.game.action("confirm", self.gerard)
            new_gerard_cards = self.game.players[self.gerard].get_cards().copy()
            new_christophe_cards = self.game.players[self.christophe].get_cards().copy()

            # Don't check if cards are not in hand again in case of overflow, you could draw the same
            if not overflow:
                for j in range(4):
                    self.assertFalse(old_christophe_cards[j] in new_christophe_cards)
                for j in range(3):
                    self.assertFalse(old_gerard_cards[j] in new_gerard_cards)
            self.assertTrue(old_gerard_cards[3] in new_gerard_cards)


if __name__ == '__main__':
    unittest.main()
