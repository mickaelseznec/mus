import unittest
import mus

from mus import Game, Card, Team

class TestInitialMus(unittest.TestCase):

    def setUp(self):
        self.game = Game(0)
        self.christophe = (1, "Christophe")
        self.gerard = (2, "Gerard")
        self.thierry = (3, "Thierry")
        self.michel = (4, "Michel")

    def test_other_team(self):
        team_0 = self.game.players.get_team(0)
        team_1 = self.game.players.get_team(1)
        self.assertEqual(team_0, self.game.players.other_team(team_1))
        self.assertEqual(team_1, self.game.players.other_team(team_0))

    def test_add_player(self):
        self.game.action("add_player", *self.christophe, "1")
        self.assertTrue(self.christophe[0] in self.game.players)

    def test_add_multiple_player(self):
        self.game.action("add_player", *self.christophe, "1")
        self.game.action("add_player", *self.christophe, "1")
        self.assertEqual(len(self.game.players.get_team(1)), 1)

    def test_remove_player(self):
        self.game.action("add_player", *self.christophe, "1")
        self.game.action("remove_player", self.christophe[0])
        self.assertTrue(self.christophe not in self.game.players)

    def test_change_team(self):
        self.game.action("add_player", *self.christophe, "1")
        self.game.action("add_player", *self.christophe, "0")
        self.assertTrue(self.game.players[self.christophe[0]].team.number == 0)

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
        self.game = Game(0)
        self.christophe = 1
        self.gerard = 2
        self.game.action("add_player", 1, "Christophe", "0")
        self.game.action("add_player", 2, "Gerard", "1")
        self.game.action("start", self.christophe)

    def test_card_distribution(self):
        cards = [player.get_cards() for player in self.game.players]
        card_indexes = [card.index() for card_set in cards for card in card_set]
        # Check if not card is here twice
        self.assertEqual(len(card_indexes), len(set(card_indexes)))
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

    def test_empty_card_packet(self):
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

class TestTwoPlayerHandiak(unittest.TestCase):
    own_name = "Haundia"
    next_name = "Tipia"

    def setUp(self):
        self.game = Game(0)
        self.christophe = 1
        self.gerard = 2
        self.game.action("add_player", 1, "Christophe", "0")
        self.game.action("add_player", 2, "Gerard", "1")
        self.game.action("start", self.christophe)
        self.game.action("mintza", self.christophe)

    def test_init_handiak(self):
        self.assertEqual(self.game.current, self.own_name)
        self.assertEqual(self.game.players.echku, self.game.players[self.christophe])

    def test_paso_paso(self):
        self.game.action("paso", self.christophe)
        self.game.action("paso", self.gerard)
        self.assertEqual(self.game.current, self.next_name)

    def test_paso_imido_idoki(self):
        self.game.action("paso", self.christophe)
        self.game.action("imido", self.gerard)
        self.game.action("idoki", self.christophe)
        self.assertTrue(self.game.states[self.own_name].deffered)
        self.assertEqual(self.game.states[self.own_name].bet, 2)
        self.assertEqual(self.game.current, self.next_name)

    def test_imido_bi_hiru_idoki(self):
        self.game.action("imido", self.christophe)
        self.game.action("gehiago", self.gerard, "2")
        self.game.action("gehiago", self.christophe, "3")
        self.game.action("idoki", self.gerard)
        self.assertTrue(self.game.states[self.own_name].deffered)
        self.assertEqual(self.game.states[self.own_name].bet, 7)
        self.assertEqual(self.game.current, self.next_name)

    def test_paso_imido_tira(self):
        self.game.action("paso", self.christophe)
        self.game.action("imido", self.gerard)
        self.game.action("tira", self.christophe)
        self.assertFalse(self.game.states[self.own_name].deffered)
        self.assertEqual(self.game.states[self.own_name].bet, 1)
        self.assertEqual(self.game.players[self.gerard].team.score, 1)
        self.assertEqual(self.game.current, self.next_name)

    def test_imdido_lau_tira(self):
        self.game.action("imido", self.christophe)
        self.game.action("gehiago", self.gerard, "4")
        self.game.action("tira", self.christophe)
        self.assertEqual(self.game.states[self.own_name].bet, 2)
        self.assertEqual(self.game.players[self.gerard].team.score, 2)
        self.assertEqual(self.game.current, self.next_name)


class TestTwoPlayerTipia(TestTwoPlayerHandiak):
    own_name = "Tipia"
    next_name = "Pariak"
    def setUp(self):
        super().setUp()
        self.game.action("paso", self.christophe)
        self.game.action("paso", self.gerard)


class TestTwoPlayerPariak(unittest.TestCase):
    def setUp(self):
        self.game = Game(0)
        self.paired_cards = sorted([Card(value=1, color='Oros'),
                                    Card(value=5, color='Oros'),
                                    Card(value=5, color='Bastos'),
                                    Card(value=12, color='Copas')])
        self.unpaired_cards = sorted([Card(value=2, color='Oros'),
                                      Card(value=6, color='Oros'),
                                      Card(value=7, color='Bastos'),
                                      Card(value=11, color='Copas')])
        self.christophe = 1
        self.gerard = 2
        self.game.action("add_player", 1, "Christophe", "0")
        self.game.action("add_player", 2, "Gerard", "1")
        self.game.action("start", self.christophe)
        self.game.action("mintza", self.christophe)
        self.game.action("paso", self.christophe)
        self.game.action("paso", self.gerard)
        self.game.action("paso", self.christophe)

    def test_bai_ez(self):
        self.game.players[self.christophe].cards = self.paired_cards
        self.game.players[self.gerard].cards = self.unpaired_cards
        self.game.action("paso", self.gerard)
        self.assertEqual("Pariak", self.game.current)
        self.assertTrue("ok" in self.game.states[self.game.current].actions_authorised())

    def test_ez_ez(self):
        self.game.players[self.christophe].cards = self.unpaired_cards
        self.game.players[self.gerard].cards = self.unpaired_cards
        self.game.action("paso", self.gerard)
        self.assertEqual("Pariak", self.game.current)
        self.assertTrue("ok" in self.game.states[self.game.current].actions_authorised())

    def test_bai_bai(self):
        self.game.players[self.christophe].cards = self.paired_cards
        self.game.players[self.gerard].cards = self.paired_cards
        self.game.action("paso", self.gerard)
        self.assertEqual("Pariak", self.game.current)
        self.assertTrue("ok" not in self.game.states[self.game.current].actions_authorised())
        self.game.action("paso", self.christophe)
        self.game.action("paso", self.gerard)


class TestTwoPlayerJokua(unittest.TestCase):
    def setUp(self):
        self.game = Game(0)
        self.game_cards = sorted([Card(value=4, color='Oros'),
                                  Card(value=7, color='Oros'),
                                  Card(value=10, color='Bastos'),
                                  Card(value=12, color='Copas')])
        self.nogame_cards = sorted([Card(value=2, color='Oros'),
                                    Card(value=6, color='Oros'),
                                    Card(value=7, color='Bastos'),
                                    Card(value=11, color='Copas')])
        self.christophe = 1
        self.gerard = 2
        self.game.action("add_player", 1, "Christophe", "0")
        self.game.action("add_player", 2, "Gerard", "1")
        self.game.action("start", self.christophe)
        self.game.action("mintza", self.christophe)
        self.game.action("paso", self.christophe)
        self.game.action("paso", self.gerard)
        # Tipia
        self.game.action("paso", self.christophe)

    def test_bai_ez(self):
        self.game.players[self.christophe].cards = self.game_cards
        self.game.players[self.gerard].cards = self.nogame_cards
        self.game.action("paso", self.gerard)
        self.game.action("ok", self.gerard)
        self.assertEqual("Jokua", self.game.current)
        self.assertTrue("ok" in self.game.states[self.game.current].actions_authorised())

    def test_ez_ez(self):
        self.game.players[self.christophe].cards = self.nogame_cards
        self.game.players[self.gerard].cards = self.nogame_cards
        self.game.action("paso", self.gerard)
        self.game.action("ok", self.gerard)
        self.assertEqual("Jokua", self.game.current)
        self.assertTrue("ok" not in self.game.states[self.game.current].actions_authorised())
        self.assertTrue(self.game.states[self.game.current].false_game)

    def test_bai_bai(self):
        self.game.players[self.christophe].cards = self.game_cards
        self.game.players[self.gerard].cards = self.game_cards
        self.game.action("paso", self.gerard)
        self.game.action("ok", self.gerard)
        self.assertEqual("Jokua", self.game.current)
        self.assertTrue("ok" not in self.game.states[self.game.current].actions_authorised())
        self.assertFalse(self.game.states[self.game.current].false_game)


class TestCardComparisons(unittest.TestCase):
    game_state = ""
    def setUp(self):
        self.game = Game(0)
        self.christophe = 1
        self.gerard = 2
        self.game.action("add_player", 1, "Christophe", "0")
        self.game.action("add_player", 2, "Gerard", "1")
        self.game.action("start", "Gerard")
        self.state = self.game.states[self.game_state]
        self.compute_winner = self.state.compute_winner


class TestHaundiaComparisons(TestCardComparisons):
    game_state = "Haundia"

    def test_haundia_11v12(self):
        self.game.players[self.christophe].cards = sorted([Card(value=4, color='Oros'),
                                                           Card(value=7, color='Oros'),
                                                           Card(value=10, color='Bastos'),
                                                           Card(value=12, color='Copas')])
        self.game.players[self.gerard].cards = sorted([Card(value=2, color='Oros'),
                                                       Card(value=6, color='Oros'),
                                                       Card(value=10, color='Bastos'),
                                                       Card(value=11, color='Copas')])
        self.compute_winner()
        self.assertEqual(self.state.winner.number, 0)

    def test_haundia_both_12(self):
        self.game.players[self.christophe].cards = sorted([Card(value=4, color='Oros'),
                                                           Card(value=7, color='Oros'),
                                                           Card(value=10, color='Bastos'),
                                                           Card(value=12, color='Copas')])
        self.game.players[self.gerard].cards = sorted([Card(value=2, color='Oros'),
                                                       Card(value=6, color='Oros'),
                                                       Card(value=11, color='Bastos'),
                                                       Card(value=12, color='Copas')])
        self.compute_winner()
        self.assertEqual(self.state.winner.number, 1)

    def test_haundia_same_cards(self):
        self.game.players[self.christophe].cards = sorted([Card(value=4, color='Oros'),
                                                           Card(value=7, color='Oros'),
                                                           Card(value=10, color='Bastos'),
                                                           Card(value=12, color='Copas')])
        self.game.players[self.gerard].cards = sorted([Card(value=4, color='Oros'),
                                                       Card(value=7, color='Oros'),
                                                       Card(value=10, color='Bastos'),
                                                       Card(value=12, color='Copas')])
        self.compute_winner()
        self.assertEqual(self.state.winner.number, 0)


class TestTipaComparisons(TestCardComparisons):
    game_state = "Tipia"

    def test_tipia_2v4(self):
        self.game.players[self.christophe].cards = sorted([Card(value=4, color='Oros'),
                                                           Card(value=7, color='Oros'),
                                                           Card(value=10, color='Bastos'),
                                                           Card(value=12, color='Copas')])
        self.game.players[self.gerard].cards = sorted([Card(value=2, color='Oros'),
                                                       Card(value=6, color='Oros'),
                                                       Card(value=10, color='Bastos'),
                                                       Card(value=12, color='Copas')])
        self.compute_winner()
        self.assertEqual(self.state.winner.number, 1)

    def test_tipia_both_4(self):
        self.game.players[self.christophe].cards = sorted([Card(value=4, color='Oros'),
                                                           Card(value=7, color='Oros'),
                                                           Card(value=10, color='Bastos'),
                                                           Card(value=12, color='Copas')])
        self.game.players[self.gerard].cards = sorted([Card(value=4, color='Oros'),
                                                       Card(value=10, color='Oros'),
                                                       Card(value=11, color='Bastos'),
                                                       Card(value=12, color='Copas')])
        self.compute_winner()
        self.assertEqual(self.state.winner.number, 0)

    def test_tipia_same(self):
        self.game.players[self.christophe].cards = sorted([Card(value=4, color='Oros'),
                                                           Card(value=7, color='Oros'),
                                                           Card(value=10, color='Bastos'),
                                                           Card(value=12, color='Copas')])
        self.game.players[self.gerard].cards = sorted([Card(value=4, color='Oros'),
                                                       Card(value=7, color='Oros'),
                                                       Card(value=10, color='Bastos'),
                                                       Card(value=12, color='Copas')])
        self.compute_winner()
        self.assertEqual(self.state.winner.number, 0)

class TestPariakComparisons(TestCardComparisons):
    game_state = "Pariak"

    def test_pariak_pairvnothing(self):
        self.game.players[self.christophe].cards = sorted([Card(value=4, color='Oros'),
                                                           Card(value=7, color='Oros'),
                                                           Card(value=10, color='Bastos'),
                                                           Card(value=12, color='Copas')])
        self.game.players[self.gerard].cards = sorted([Card(value=2, color='Oros'),
                                                       Card(value=2, color='Oros'),
                                                       Card(value=10, color='Bastos'),
                                                       Card(value=12, color='Copas')])
        self.compute_winner()
        self.assertEqual(self.state.winner.number, 1)

    def test_pariak_pairvpair(self):
        self.game.players[self.christophe].cards = sorted([Card(value=4, color='Oros'),
                                                           Card(value=7, color='Oros'),
                                                           Card(value=7, color='Bastos'),
                                                           Card(value=12, color='Copas')])
        self.game.players[self.gerard].cards = sorted([Card(value=2, color='Oros'),
                                                       Card(value=2, color='Oros'),
                                                       Card(value=10, color='Bastos'),
                                                       Card(value=12, color='Copas')])
        self.compute_winner()
        self.assertEqual(self.state.winner.number, 0)

    def test_pariak_pairvpair_same(self):
        self.game.players[self.christophe].cards = sorted([Card(value=4, color='Oros'),
                                                           Card(value=7, color='Oros'),
                                                           Card(value=7, color='Bastos'),
                                                           Card(value=12, color='Copas')])
        self.game.players[self.gerard].cards = sorted([Card(value=2, color='Oros'),
                                                       Card(value=7, color='Oros'),
                                                       Card(value=7, color='Bastos'),
                                                       Card(value=12, color='Copas')])
        self.compute_winner()
        self.assertEqual(self.state.winner.number, 0)

    def test_pariak_pairvtriple(self):
        self.game.players[self.christophe].cards = sorted([Card(value=4, color='Oros'),
                                                           Card(value=7, color='Oros'),
                                                           Card(value=7, color='Bastos'),
                                                           Card(value=12, color='Copas')])
        self.game.players[self.gerard].cards = sorted([Card(value=2, color='Oros'),
                                                       Card(value=2, color='Oros'),
                                                       Card(value=2, color='Bastos'),
                                                       Card(value=12, color='Copas')])
        self.compute_winner()
        self.assertEqual(self.state.winner.number, 1)

    def test_pariak_triplevtriple(self):
        self.game.players[self.christophe].cards = sorted([Card(value=7, color='Oros'),
                                                           Card(value=7, color='Oros'),
                                                           Card(value=7, color='Bastos'),
                                                           Card(value=12, color='Copas')])
        self.game.players[self.gerard].cards = sorted([Card(value=2, color='Oros'),
                                                       Card(value=2, color='Oros'),
                                                       Card(value=2, color='Bastos'),
                                                       Card(value=12, color='Copas')])
        self.compute_winner()
        self.assertEqual(self.state.winner.number, 0)

    def test_pariak_triplevdouble_double(self):
        self.game.players[self.christophe].cards = sorted([Card(value=7, color='Oros'),
                                                           Card(value=7, color='Oros'),
                                                           Card(value=1, color='Bastos'),
                                                           Card(value=1, color='Copas')])
        self.game.players[self.gerard].cards = sorted([Card(value=2, color='Oros'),
                                                       Card(value=2, color='Oros'),
                                                       Card(value=2, color='Bastos'),
                                                       Card(value=12, color='Copas')])
        self.compute_winner()
        self.assertEqual(self.state.winner.number, 0)

    def test_double_doublevdouble_double(self):
        self.game.players[self.christophe].cards = sorted([Card(value=7, color='Oros'),
                                                           Card(value=7, color='Oros'),
                                                           Card(value=1, color='Bastos'),
                                                           Card(value=1, color='Copas')])
        self.game.players[self.gerard].cards = sorted([Card(value=7, color='Oros'),
                                                       Card(value=7, color='Oros'),
                                                       Card(value=12, color='Bastos'),
                                                       Card(value=12, color='Copas')])
        self.compute_winner()
        self.assertEqual(self.state.winner.number, 1)


class TestJokuaComparisons(TestCardComparisons):
    game_state = "Jokua"

    def test_game_v_no_game(self):
        self.game.players[self.christophe].cards = sorted([Card(value=7, color='Oros'),
                                                           Card(value=7, color='Oros'),
                                                           Card(value=1, color='Bastos'),
                                                           Card(value=1, color='Copas')])
        self.game.players[self.gerard].cards = sorted([Card(value=7, color='Oros'),
                                                       Card(value=7, color='Oros'),
                                                       Card(value=12, color='Bastos'),
                                                       Card(value=12, color='Copas')])
        self.compute_winner()
        self.assertEqual(self.state.winner.number, 1)

    def test_no_game_v_no_game(self):
        self.game.players[self.christophe].cards = sorted([Card(value=7, color='Oros'),
                                                           Card(value=7, color='Oros'),
                                                           Card(value=1, color='Bastos'),
                                                           Card(value=1, color='Copas')])
        self.game.players[self.gerard].cards = sorted([Card(value=7, color='Oros'),
                                                       Card(value=7, color='Oros'),
                                                       Card(value=3, color='Bastos'),
                                                       Card(value=3, color='Copas')])
        self.compute_winner()
        self.assertEqual(self.state.winner.number, 1)

    def test_game_v_game1(self):
        self.game.players[self.christophe].cards = sorted([Card(value=7, color='Oros'),
                                                           Card(value=7, color='Oros'),
                                                           Card(value=10, color='Bastos'),
                                                           Card(value=10, color='Copas')])
        self.game.players[self.gerard].cards = sorted([Card(value=1, color='Oros'),
                                                       Card(value=11, color='Oros'),
                                                       Card(value=12, color='Bastos'),
                                                       Card(value=12, color='Copas')])
        self.compute_winner()
        self.assertEqual(self.state.winner.number, 1)

    def test_game_v_game2(self):
        self.game.players[self.christophe].cards = sorted([Card(value=11, color='Oros'),
                                                           Card(value=11, color='Oros'),
                                                           Card(value=10, color='Bastos'),
                                                           Card(value=10, color='Copas')])
        self.game.players[self.gerard].cards = sorted([Card(value=2, color='Oros'),
                                                       Card(value=11, color='Oros'),
                                                       Card(value=12, color='Bastos'),
                                                       Card(value=12, color='Copas')])
        self.compute_winner()
        self.assertEqual(self.state.winner.number, 1)

    def test_game_v_game3(self):
        self.game.players[self.christophe].cards = sorted([Card(value=11, color='Oros'),
                                                           Card(value=11, color='Oros'),
                                                           Card(value=10, color='Bastos'),
                                                           Card(value=10, color='Copas')])
        self.game.players[self.gerard].cards = sorted([Card(value=7, color='Oros'),
                                                       Card(value=12, color='Oros'),
                                                       Card(value=12, color='Bastos'),
                                                       Card(value=12, color='Copas')])
        self.compute_winner()
        self.assertEqual(self.state.winner.number, 0)


if __name__ == '__main__':
    unittest.main()
