import random
import itertools as it

from collections import deque, Counter
from dataclasses import dataclass
from typing import Sequence

@dataclass(order=True, unsafe_hash=True)
class Card:
    value: int
    color: str


class Hand:
    def __init__(self, cards):
        self.hand = cards


class HaundiaHand(Hand):
    def sorted_hand(self):
        return sorted(self.hand, key=lambda card: card.value, reverse=True)

    def __lt__(self, other):
        return self.sorted_hand() < other.sorted_hand()


class TipiaHand(Hand):
    def sorted_hand(self):
        return sorted(self.hand, key=lambda card: card.value)

    def __lt__(self, other):
        return self.sorted_hand() > other.sorted_hand()


class PariakHand(Hand):
    def get_counts(self):
        return Counter(card.value for card in self.hand)

    def is_special(self):
        counts = self.get_counts()
        return any(count >= 2 for count in counts.values())

    def pairs_in_order(self):
        value_counts = [(value, count) for (value, count) in self.get_counts().items() if count >= 2]
        # Split four-of-a-kind into two pairs
        for value, count in value_counts:
            if count == 4:
                value_counts = [(key, 2), (key, 2)]
        return sorted((value for (value, _) in value_counts), reverse=True)

    def bonus(self):
        counts = self.get_counts()
        bonus = 0
        if (all(count == 4 for count in counts.values()) or
                all(count == 2 for count in counts.values())):
            bonus = 3
        elif any(count == 3 for count in counts.values()):
            bonus = 2
        elif any(count == 2 for count in counts.values()):
            bonus = 1
        return bonus

    def __lt__(self, other):
        self_bonus, other_bonus = self.bonus(), other.bonus()
        if self_bonus != other_bonus:
            return self_bonus < other_bonus

        return self.pairs_in_order() < other.pairs_in_order()


class JokuaHand(Hand):
    jokua_index = [31, 32, 40, 37, 36, 35, 34, 33]

    def sum_cards(self):
        return sum(min(card.value, 10) for card in self.hand)

    def is_special(self):
        return self.sum_cards() >= 31

    def bonus(self):
        bonus = 1
        card_sum = self.sum_cards()

        if card_sum == 31:
            bonus = 3
        elif card_sum > 31:
            bonus = 2
        return bonus

    def __lt__(self, other):
        if self.is_special():
            if not other.is_special():
                return False
            return self.jokua_index.index(self.sum_cards()) > self.jokua_index.index(other.sum_cards())

        return self.sum_cards() < other.sum_cards()


class Packet:
    basque_colors = ("Copas", "Espadas", "Bastos", "Oros")
    basque_values = (1, 2, 3, 4, 5, 6, 7, 10, 11, 12)

    def __init__(self):
        self.discarded = deque()
        self.drawable = deque(Card(*attr) for
                              attr in it.product(self.basque_values, self.basque_colors))

    def draw(self) -> Card:
        if len(self.drawable) == 0:
            self.refill_drawable()
        return self.drawable.pop()

    def refill_drawable(self) -> None:
        self.drawable = deque(self.discarded)
        self.discarded = deque()

    def discard(self, card: Card) -> None:
        self.discarded.append(card)
