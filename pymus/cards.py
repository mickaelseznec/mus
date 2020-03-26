import random

class Card:
    COLORS = ["Copas", "Espadas", "Bastos", "Oros"]
    VALUES = [1, 2, 3, 4, 5, 6, 7, 10, 11, 12]

    def __init__(self, index=None, value=None, color=None):
        if index is not None:
            self.value = Card.VALUES[int(index / len(Card.COLORS))]
            self.color = Card.COLORS[index % len(Card.COLORS)]
        else:
            if value not in Card.VALUES or color not in Card.COLORS:
                raise ForbiddenActionException
            self.value = value
            self.color = color

    def index(self):
        return Card.COLORS.index(self.color) + len(Card.COLORS) * Card.VALUES.index(self.value)

    def __str__(self):
        return str(self.value) + ' - ' + self.color

    def __eq__(self, card):
        return self.index() == card.index()

    def __lt__(self, card):
        return self.index() < card.index()


class Hand:
    def __init__(self, cards):
        self.hand = cards


class HaundiaHand(Hand):
    def __lt__(self, other):
        return (sorted([c.value for c in self.hand], reverse=True)
                < sorted([c.value for c in other.hand], reverse=True))


class TipiaHand(Hand):
    def __lt__(self, other):
        return sorted([c.value for c in self.hand]) > sorted([c.value for c in other.hand])


class PariakHand(Hand):
    def has_hand(self):
        values = [card.value for card in self.hand]
        counter = [values.count(value) for value in set(values)]
        return any(count >= 2 for count in counter)

    def group_pairs(self):
        values = [card.value for card in self.hand]
        return sorted(((values.count(value), value) for value in sorted(list(set(values)), reverse=True)), reverse=True)

    def has_double_pair(self):
        return all(pair[0] == 2 for pair in self.group_pairs()) or self.group_pairs()[0][0] == 4

    def has_triple(self):
        return any(pair[0] == 3 for pair in self.group_pairs())

    def has_double_only(self):
        return not self.has_double_pair() and any(pair[0] == 2 for pair in self.group_pairs())

    def bonus(self):
        if self.has_double_pair():
            return 3
        if self.has_triple():
            return 2
        if self.has_double_only():
            return 1
        return 0

    def __lt__(self, other):
        self_bonus, other_bonus = self.bonus(), other.bonus()
        if self_bonus != other_bonus:
            return self_bonus < other_bonus

        own_group, other_group = self.group_pairs(), other.group_pairs()
        return own_group < other_group


class JokuaHand(Hand):
    jokua_index = {(33 + i): i for i in range(8)}
    jokua_index.update({32: 8, 31: 9})

    def sum_cards(self):
        return sum(min(card.value, 10) for card in self.hand)

    def has_game(self):
        return self.sum_cards() > 30

    def bonus(self):
        card_sum = self.sum_cards()
        if card_sum > 31:
            return 2
        if card_sum == 31:
            return 3
        return 0

    def __lt__(self, other):
        if self.has_game():
            if not other.has_game():
                return False
            return JokuaHand.jokua_index[self.sum_cards()] < JokuaHand.jokua_index[other.sum_cards()]

        return self.sum_cards() < other.sum_cards()


class Packet:
    CARDS = [Card(i) for i in range(len(Card.COLORS) * len(Card.VALUES))]

    def __init__(self):
        self.used_cards = []
        self.unused_cards = []
        self.restore()

    def restore(self):
        self.unused_cards = []
        self.used_cards = list(range(len(Packet.CARDS)))
        self.new_packet()

    def new_packet(self):
        self.unused_cards = self.used_cards
        random.shuffle(self.unused_cards)
        self.used_cards = []

    def take(self, n):
        delta = len(self.unused_cards) - n
        if delta > 0:
            taken = self.unused_cards[0: n]
            self.unused_cards = self.unused_cards[n:]
            return [Card(index) for index in taken]
        else:
            taken = self.unused_cards
            self.new_packet()
            taken += self.unused_cards[0:-delta]
            self.unused_cards = self.unused_cards[-delta:]
            return [Card(index) for index in taken]

    def trade(self, card):
        self.used_cards.append(card.index())
        return self.take(1)



