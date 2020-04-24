import itertools as it
import json
import random

from abc import ABC, abstractmethod
from collections import deque, Counter
from dataclasses import dataclass, field
from functools import total_ordering
from typing import Sequence

@dataclass(order=True)
class Card:
    value: int = field(hash=True)
    color: str = field(compare=False, hash=True)

    def is_same(self, other) -> bool:
        return self.value == other.value and self.color == other.color

class JSONCardEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Card):
            return {"Card": {"value": obj.value, "color": obj.color}}
        return json.JSONEncoder.default(self, obj)

class Packet:
    basque_colors = ("Copas", "Espadas", "Bastos", "Oros")
    basque_values = (1, 2, 3, 4, 5, 6, 7, 10, 11, 12)

    def __init__(self):
        all_cards = list(Card(*attr) for attr in it.product(self.basque_values, self.basque_colors))
        random.shuffle(all_cards)
        self.drawable = deque(all_cards)

        self.discarded = deque()

    def draw(self) -> Card:
        if len(self.drawable) == 0:
            self.refill_drawable()
        return self.drawable.pop()

    def refill_drawable(self) -> None:
        self.drawable = self.discarded
        random.shuffle(self.drawable)
        self.discarded = deque()

    def discard(self, card: Card) -> None:
        self.discarded.append(card)

    def exchange(self, card:Card) -> Card:
        self.discard(card)
        return self.draw()


@total_ordering
@dataclass
class Hand(ABC):
    hand: Sequence[Card]

    @abstractmethod
    def __lt__(self, other):
        pass

    @abstractmethod
    def __eq__(self, other):
        pass


@total_ordering
class HaundiaHand(Hand):
    def _sorted_hand(self):
        return sorted(self.hand, key=lambda card: card.value, reverse=True)

    def __lt__(self, other):
        return self._sorted_hand() < other._sorted_hand()

    def __eq__(self, other):
        return not (self < other or other < self)


@total_ordering
class TipiaHand(Hand):
    def _sorted_hand(self):
        return sorted(self.hand, key=lambda card: card.value)

    def __lt__(self, other):
        return self._sorted_hand() > other._sorted_hand()

    def __eq__(self, other):
        return not (self < other or other < self)


@total_ordering
class PariakHand(Hand):
    @property
    def is_special(self) -> bool:
        counts = self._get_counts()
        return any(count >= 2 for count in counts.values())

    @property
    def bonus(self):
        counts = self._get_counts()
        bonus = 0
        if (all(count == 4 for count in counts.values()) or
                all(count == 2 for count in counts.values())):
            bonus = 3
        elif any(count == 3 for count in counts.values()):
            bonus = 2
        elif any(count == 2 for count in counts.values()):
            bonus = 1
        return bonus

    def _get_counts(self):
        return Counter(card.value for card in self.hand)

    def _pairs_in_order(self):
        value_counts = [(value, count) for (value, count) in self._get_counts().items() if count >= 2]
        # Split four-of-a-kind into two pairs
        for value, count in value_counts:
            if count == 4:
                value_counts = [(value, 2), (value, 2)]
        return sorted((value for (value, _) in value_counts), reverse=True)

    def __lt__(self, other):
        self_bonus, other_bonus = self.bonus, other.bonus
        if self_bonus != other_bonus:
            return self_bonus < other_bonus

        return self._pairs_in_order() < other._pairs_in_order()

    def __eq__(self, other):
        return not (self < other or other < self)


@total_ordering
class JokuaHand(Hand):
    jokua_index = [31, 32, 40, 37, 36, 35, 34, 33]

    @property
    def is_special(self):
        return self._sum_cards() >= 31

    @property
    def bonus(self):
        bonus = 1
        card_sum = self._sum_cards()

        if card_sum == 31:
            bonus = 3
        elif card_sum > 31:
            bonus = 2
        return bonus

    def _sum_cards(self):
        return sum(min(card.value, 10) for card in self.hand)

    def __lt__(self, other):
        if self.is_special:
            if not other.is_special:
                return False
            return self.jokua_index.index(self._sum_cards()) > self.jokua_index.index(other._sum_cards())

        return self._sum_cards() < other._sum_cards()

    def __eq__(self, other):
        return not (self < other or other < self)
