import sys
sys.path.append("pymus")

import unittest
import itertools as it

from cards import Card, HaundiaHand, TipiaHand, PariakHand, JokuaHand, Packet

class PacketTestCase(unittest.TestCase):
    def setUp(self):
        self.packet = Packet()

    def test_all_cards_present(self):
        self.assertEqual(len(self.packet.drawable), 40)

    def test_take_one_card(self):
        _ = self.packet.draw()
        self.assertEqual(len(self.packet.drawable), 39)

    def test_take_and_discard_one_card(self):
        card = self.packet.draw()
        self.assertEqual(len(self.packet.drawable), 39)
        self.assertEqual(len(self.packet.discarded), 0)

        self.packet.discard(card)
        self.assertEqual(len(self.packet.drawable), 39)
        self.assertEqual(len(self.packet.discarded), 1)

    def test_refill_drawable(self):
        for i in range(40):
            card = self.packet.draw()
            if i % 2 == 0:
                self.packet.discard(card)

        self.assertEqual(len(self.packet.drawable), 0)
        self.assertEqual(len(self.packet.discarded), 20)

        discarded_copy = self.packet.discarded.copy()

        card = self.packet.draw()
        self.assertEqual(len(self.packet.drawable), 19)
        self.assertEqual(len(self.packet.discarded), 0)

        self.assertTrue(any(card.is_same(other) for other in discarded_copy))


class TestCardsOrdering(unittest.TestCase):
    def test_order(self):
        card_1 = Card(4, 'Oros')
        card_2 = Card(7, 'Bastos')

        self.assertLess(card_1, card_2)
        self.assertGreater(card_2, card_1)
        self.assertNotEqual(card_1, card_2)

    def test_value_equality(self):
        card_1 = Card(4, 'Oros')
        card_2 = Card(4, 'Bastos')

        self.assertEqual(card_1, card_2)
        self.assertFalse(card_1.is_same(card_2))

    def test_value_identical(self):
        card_1 = Card(4, 'Oros')
        card_2 = Card(4, 'Oros')

        self.assertEqual(card_1, card_2)
        self.assertTrue(card_1.is_same(card_2))

class TestHaundiaComparisons(unittest.TestCase):
    def test_haundia_no_commons(self):
        hand_1 = ((4, 'Oros'), (7, 'Oros'), (7, 'Bastos'), (10, 'Oros'))
        hand_2 = ((2, 'Copas'), (6, 'Copas'), (7, 'Espadas'), (12, 'Copas'))

        haundiahand_1 = HaundiaHand([Card(*values) for values in hand_1])
        haundiahand_2 = HaundiaHand([Card(*values) for values in hand_2])

        self.assertLess(haundiahand_1, haundiahand_2)
        self.assertGreater(haundiahand_2, haundiahand_1)

    def test_haundia_one_common(self):
        hand_1 = ((4, 'Oros'), (7, 'Oros'), (10, 'Oros'), (12, 'Oros'))
        hand_2 = ((2, 'Copas'), (6, 'Copas'), (11, 'Copas'), (12, 'Copas'))

        haundiahand_1 = HaundiaHand([Card(*values) for values in hand_1])
        haundiahand_2 = HaundiaHand([Card(*values) for values in hand_2])

        self.assertLess(haundiahand_1, haundiahand_2)
        self.assertGreater(haundiahand_2, haundiahand_1)

    def test_haundia_two_commons(self):
        hand_1 = ((5, 'Oros'), (7, 'Oros'), (12, 'Oros'), (12, 'Bastos'))
        hand_2 = ((4, 'Copas'), (6, 'Copas'), (12, 'Copas'), (12, 'Espadas'))

        haundiahand_1 = HaundiaHand([Card(*values) for values in hand_1])
        haundiahand_2 = HaundiaHand([Card(*values) for values in hand_2])

        self.assertGreater(haundiahand_1, haundiahand_2)
        self.assertLess(haundiahand_2, haundiahand_1)

    def test_haundia_three_commons(self):
        hand_1 = ((5, 'Oros'), (7, 'Oros'), (11, 'Oros'), (12, 'Bastos'))
        hand_2 = ((4, 'Copas'), (7, 'Copas'), (11, 'Copas'), (12, 'Espadas'))

        haundiahand_1 = HaundiaHand([Card(*values) for values in hand_1])
        haundiahand_2 = HaundiaHand([Card(*values) for values in hand_2])

        self.assertGreater(haundiahand_1, haundiahand_2)
        self.assertLess(haundiahand_2, haundiahand_1)

    def test_haundia_egality(self):
        hand_1 = ((5, 'Oros'), (7, 'Oros'), (11, 'Oros'), (12, 'Bastos'))
        hand_2 = ((5, 'Copas'), (7, 'Copas'), (11, 'Copas'), (12, 'Espadas'))

        haundiahand_1 = HaundiaHand([Card(*values) for values in hand_1])
        haundiahand_2 = HaundiaHand([Card(*values) for values in hand_2])

        self.assertEqual(haundiahand_1, haundiahand_2)

class TestTipiaComparisons(unittest.TestCase):
    def test_tipia_no_commons(self):
        hand_1 = ((3, 'Oros'), (7, 'Oros'), (10, 'Oros'), (12, 'Oros'))
        hand_2 = ((2, 'Copas'), (6, 'Copas'), (10, 'Copas'), (12, 'Copas'))

        tipiahand_1 = TipiaHand([Card(*values) for values in hand_1])
        tipiahand_2 = TipiaHand([Card(*values) for values in hand_2])

        self.assertLess(tipiahand_1, tipiahand_2)
        self.assertGreater(tipiahand_2, tipiahand_1)

    def test_tipia_one_common(self):
        hand_1 = ((2, 'Oros'), (7, 'Oros'), (10, 'Oros'), (12, 'Oros'))
        hand_2 = ((2, 'Copas'), (6, 'Copas'), (10, 'Copas'), (12, 'Copas'))

        tipiahand_1 = TipiaHand([Card(*values) for values in hand_1])
        tipiahand_2 = TipiaHand([Card(*values) for values in hand_2])

        self.assertLess(tipiahand_1, tipiahand_2)
        self.assertGreater(tipiahand_2, tipiahand_1)

    def test_tipia_two_commons(self):
        hand_1 = ((1, 'Oros'), (2, 'Oros'), (10, 'Oros'), (12, 'Oros'))
        hand_2 = ((1, 'Copas'), (2, 'Copas'), (11, 'Copas'), (12, 'Copas'))

        tipiahand_1 = TipiaHand([Card(*values) for values in hand_1])
        tipiahand_2 = TipiaHand([Card(*values) for values in hand_2])

        self.assertGreater(tipiahand_1, tipiahand_2)
        self.assertLess(tipiahand_2, tipiahand_1)

    def test_tipia_three_commons(self):
        hand_1 = ((1, 'Oros'), (2, 'Oros'), (10, 'Oros'), (12, 'Oros'))
        hand_2 = ((1, 'Copas'), (2, 'Copas'), (11, 'Copas'), (12, 'Copas'))

        tipiahand_1 = TipiaHand([Card(*values) for values in hand_1])
        tipiahand_2 = TipiaHand([Card(*values) for values in hand_2])

        self.assertGreater(tipiahand_1, tipiahand_2)
        self.assertLess(tipiahand_2, tipiahand_1)

    def test_tipia_equality(self):
        hand_1 = ((1, 'Oros'), (2, 'Oros'), (11, 'Oros'), (12, 'Oros'))
        hand_2 = ((1, 'Copas'), (2, 'Copas'), (11, 'Copas'), (12, 'Copas'))

        tipiahand_1 = TipiaHand([Card(*values) for values in hand_1])
        tipiahand_2 = TipiaHand([Card(*values) for values in hand_2])

        self.assertEqual(tipiahand_1, tipiahand_2)

class TestPariakComparisons(unittest.TestCase):
    def test_pariak_pairvpair_distinct(self):
        hand_1 = ((4, 'Oros'), (7, 'Oros'), (7, 'Bastos'), (12, 'Copas'))
        hand_2 = ((2, 'Oros'), (2, 'Bastos'), (10, 'Bastos'), (12, 'Copas'))

        pariakhand_1 = PariakHand([Card(*values) for values in hand_1])
        pariakhand_2 = PariakHand([Card(*values) for values in hand_2])

        self.assertGreater(pariakhand_1, pariakhand_2)
        self.assertLess(pariakhand_2, pariakhand_1)

    def test_pariak_pairvpair_equality(self):
        hand_1 = ((4, 'Oros'), (7, 'Oros'), (7, 'Bastos'), (12, 'Copas'))
        hand_2 = ((2, 'Oros'), (7, 'Copas'), (7, 'Espadas'), (12, 'Copas'))

        pariakhand_1 = PariakHand([Card(*values) for values in hand_1])
        pariakhand_2 = PariakHand([Card(*values) for values in hand_2])

        self.assertEqual(pariakhand_1, pariakhand_2)

    def test_pariak_pairvtriple(self):
        hand_1 = ((4, 'Oros'), (7, 'Oros'), (7, 'Bastos'), (12, 'Copas'))
        hand_2 = ((2, 'Oros'), (2, 'Bastos'), (2, 'Copas'), (12, 'Copas'))

        pariakhand_1 = PariakHand([Card(*values) for values in hand_1])
        pariakhand_2 = PariakHand([Card(*values) for values in hand_2])

        self.assertLess(pariakhand_1, pariakhand_2)
        self.assertGreater(pariakhand_2, pariakhand_1)

    def test_pariak_triplevtriple(self):
        hand_1 = ((7, 'Oros'), (7, 'Copas'), (7, 'Bastos'), (12, 'Copas'))
        hand_2 = ((2, 'Oros'), (2, 'Copas'), (2, 'Bastos'), (12, 'Bastos'))

        pariakhand_1 = PariakHand([Card(*values) for values in hand_1])
        pariakhand_2 = PariakHand([Card(*values) for values in hand_2])

        self.assertGreater(pariakhand_1, pariakhand_2)
        self.assertLess(pariakhand_2, pariakhand_1)

    def test_pariak_triplevdouble_double(self):
        hand_1 = ((7, 'Oros'), (7, 'Bastos'), (1, 'Bastos'), (1, 'Copas'))
        hand_2 = ((2, 'Oros'), (2, 'Copas'), (2, 'Bastos'), (12, 'Copas'))

        pariakhand_1 = PariakHand([Card(*values) for values in hand_1])
        pariakhand_2 = PariakHand([Card(*values) for values in hand_2])

        self.assertGreater(pariakhand_1, pariakhand_2)
        self.assertLess(pariakhand_2, pariakhand_1)

    def test_double_doublevdouble_double_no_commons(self):
        hand_1 = ((7, 'Oros'), (7, 'Bastos'), (1, 'Bastos'), (1, 'Copas'))
        hand_2 = ((7, 'Copas'), (7, 'Espadas'), (12, 'Bastos'), (12, 'Copas'))

        pariakhand_1 = PariakHand([Card(*values) for values in hand_1])
        pariakhand_2 = PariakHand([Card(*values) for values in hand_2])

        self.assertLess(pariakhand_1, pariakhand_2)
        self.assertGreater(pariakhand_2, pariakhand_1)

    def test_double_doublevdouble_double_one_common(self):
        hand_1 = ((7, 'Oros'), (7, 'Bastos'), (3, 'Bastos'), (3, 'Copas'))
        hand_2 = ((7, 'Copas'), (7, 'Espadas'), (2, 'Bastos'), (2, 'Copas'))

        pariakhand_1 = PariakHand([Card(*values) for values in hand_1])
        pariakhand_2 = PariakHand([Card(*values) for values in hand_2])

        self.assertGreater(pariakhand_1, pariakhand_2)
        self.assertLess(pariakhand_2, pariakhand_1)

    def test_double_doublevdouble_double_equality(self):
        hand_1 = ((7, 'Oros'), (7, 'Bastos'), (3, 'Bastos'), (3, 'Copas'))
        hand_2 = ((7, 'Copas'), (7, 'Espadas'), (3, 'Espadas'), (3, 'Oros'))

        pariakhand_1 = PariakHand([Card(*values) for values in hand_1])
        pariakhand_2 = PariakHand([Card(*values) for values in hand_2])

        self.assertEqual(pariakhand_1, pariakhand_2)

    def test_double_doublevsquare(self):
        hand_1 = ((7, 'Oros'), (7, 'Bastos'), (7, 'Espadas'), (7, 'Copas'))
        hand_2 = ((10, 'Copas'), (10, 'Espadas'), (3, 'Espadas'), (3, 'Oros'))

        pariakhand_1 = PariakHand([Card(*values) for values in hand_1])
        pariakhand_2 = PariakHand([Card(*values) for values in hand_2])

        self.assertLess(pariakhand_1, pariakhand_2)
        self.assertGreater(pariakhand_2, pariakhand_1)


class TestJokuaComparisons(unittest.TestCase):
    def test_no_game_v_no_game_distinct(self):
        hand_1 = ((7, 'Oros'), (6, 'Oros'), (2, 'Bastos'), (1, 'Copas'))
        hand_2 = ((11, 'Oros'), (10, 'Oros'), (4, 'Bastos'), (3, 'Copas'))

        jokuahand_1 = JokuaHand([Card(*values) for values in hand_1])
        jokuahand_2 = JokuaHand([Card(*values) for values in hand_2])

        self.assertLess(jokuahand_1, jokuahand_2)
        self.assertGreater(jokuahand_2, jokuahand_1)

    def test_no_game_v_no_game_equal(self):
        hand_1 = ((12, 'Oros'), (7, 'Oros'), (7, 'Bastos'), (3, 'Copas'))
        hand_2 = ((11, 'Oros'), (10, 'Oros'), (4, 'Bastos'), (3, 'Bastos'))

        jokuahand_1 = JokuaHand([Card(*values) for values in hand_1])
        jokuahand_2 = JokuaHand([Card(*values) for values in hand_2])

        self.assertEqual(jokuahand_1, jokuahand_2)

    def test_game_v_game1(self):
        hand_1 = ((7, 'Oros'), (7, 'Copas'), (10, 'Bastos'), (10, 'Copas'))
        hand_2 = ((1, 'Oros'), (11, 'Oros'), (12, 'Bastos'), (12, 'Copas'))

        jokuahand_1 = JokuaHand([Card(*values) for values in hand_1])
        jokuahand_2 = JokuaHand([Card(*values) for values in hand_2])

        self.assertLess(jokuahand_1, jokuahand_2)
        self.assertGreater(jokuahand_2, jokuahand_1)

    def test_game_v_game2(self):
        hand_1 = ((11, 'Oros'), (11, 'Copas'), (10, 'Bastos'), (10, 'Copas'))
        hand_2 = ((2, 'Oros'), (11, 'Bastos'), (12, 'Bastos'), (12, 'Copas'))

        jokuahand_1 = JokuaHand([Card(*values) for values in hand_1])
        jokuahand_2 = JokuaHand([Card(*values) for values in hand_2])

        self.assertLess(jokuahand_1, jokuahand_2)
        self.assertGreater(jokuahand_2, jokuahand_1)

    def test_game_v_game3(self):
        hand_1 = ((11, 'Oros'), (11, 'Oros'), (10, 'Bastos'), (10, 'Copas'))
        hand_2 = ((7, 'Oros'), (12, 'Oros'), (12, 'Bastos'), (12, 'Copas'))

        jokuahand_1 = JokuaHand([Card(*values) for values in hand_1])
        jokuahand_2 = JokuaHand([Card(*values) for values in hand_2])

        self.assertGreater(jokuahand_1, jokuahand_2)
        self.assertLess(jokuahand_2, jokuahand_1)

    def test_game_v_game_equal(self):
        hand_1 = ((3, 'Oros'), (11, 'Oros'), (10, 'Bastos'), (10, 'Copas'))
        hand_2 = ((3, 'Copas'), (12, 'Oros'), (12, 'Bastos'), (12, 'Copas'))

        jokuahand_1 = JokuaHand([Card(*values) for values in hand_1])
        jokuahand_2 = JokuaHand([Card(*values) for values in hand_2])

        self.assertEqual(jokuahand_1, jokuahand_2)


if __name__ == '__main__':
    unittest.main()
