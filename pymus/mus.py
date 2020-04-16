from abc import ABC
from collections import UserList

from cards import Card, Packet, Hand, HaundiaHand, TipiaHand, PariakHand, JokuaHand

class ForbiddenActionException(Exception):
    pass


class WrongPlayerException(ForbiddenActionException):
    pass


class TeamWonException(Exception):
    pass


class Player:
    def __init__(self, player_id, player_name):
        self.id = player_id
        self.name = player_name

        self.team = None
        self.index = None
        self.is_authorised = False
        self.said = ""
        self.cards = []
        self.asks = set()
        self.has_game = False
        self.has_hand = False

    def get_cards(self):
        return self.cards

    def __str__(self):
        return self.name

    def __eq__(self, other):
        return self.id == other.id

    def __hash__(self):
        return hash(id(self))


class PlayerManager:
    def __init__(self):
        self.teams = (Team(0), Team(1))
        self.echku = 0
        self.authorised_team = None
        self.authorised_player = None
        self.id_counter = 0

    def has_finished(self):
        return any(team.score >= Game.score_max for team in self.teams)

    def winner_team(self):
        for i, team in enumerate(self.teams):
            if team.score >= Game.score_max:
                return i

    def generate_new_id(self):
        result = self.id_counter
        self.id_counter += 1
        return result

    def add(self, player_id, team_id):
        if self.get_team_id(player_id) == team_id:
            return player_id

        if len(self.teams[team_id]) >= 2:
            raise ForbiddenActionException("Team %d already full" % team_id)

        if player_id is None:
            player_id = self.generate_new_id()
        else:
            self.detach_player(player_id)
        self.teams[team_id].append(player_id)

        return player_id

    def remove(self, player_id):
        if player_id in self:
            player = self[player_id]
            player.team.remove_player(player)

    def get_all(self):
        return [player for team in self.teams for player in team.players]

    def get_all_echku_sorted(self):
        return sorted(self.get_all(), key=lambda player: player.index)

    def get_team_id(self, player_id):
        result = None
        if player_id in self.teams[0]:
            result = 0
        elif player_id in self.teams[1]:
            result = 1
        return result

    def detach_player(self, player_id):
        team_id = self.get_team_id(player_id)
        self.teams[team_id].remove(player_id)

    def get_team(self, team_id):
        return self.teams[team_id]

    def authorise_echku_player(self):
        players = self.get_all_echku_sorted()
        self.authorised_player = players[0]
        for player in players:
            player.is_authorised = player == self.authorised_player

    def authorise_next_player(self):
        players = self.get_all_echku_sorted()
        self.authorised_player = players[(self.authorised_player.index + 1) % len(players)]
        for player in players:
            player.is_authorised = player == self.authorised_player

    def other_team(self, team):
        if team.number == 0:
            return self.teams[1]
        return self.teams[0]

    def authorise_team(self, team):
        self.authorised_team = team
        team.authorise(True)
        self.other_team(team).authorise(False)

    def authorise_echku_team(self):
        team = self.get_all_echku_sorted()[0].team
        team.authorise(True)
        self.other_team(team).authorise(False)

    def record_scores(self):
        for team in self.teams:
            team.record_score()

    def can_start(self):
        team_0_size = len(self.get_team(0))
        return team_0_size == len(self.get_team(1)) and (team_0_size == 1 or team_0_size == 2)

    def set_initial_echku(self):
        index = 0
        for i in range(len(self.teams[0])):
            for team in self.teams:
                team.players[i].index = index
                index = index + 1
        self.echku = self.get_all_echku_sorted()[0]

    def set_echku(self):
        players = self.get_all_echku_sorted()
        for player in players:
            player.index = (player.index - 1) % len(players)
        self.echku = self.get_all_echku_sorted()[0]

    def __iter__(self):
        return iter(self.get_all())

    def __contains__(self, player_id):
        return player_id in [player.id for player in self.get_all()]

    def __getitem__(self, player_id):
        for other in self.get_all():
            if player_id == other.id:
                return other
        raise IndexError

class Team(UserList):
    def __init__(self, number):
        self.data = []
        self.number = number
        self.begin_score = 0
        self.score = 0
        self.said = ""
        self.is_authorised = False

    def record_score(self):
        self.begin_score = self.score

    def add_score(self, score):
        self.score += score
        if self.score >= Game.score_max:
            self.score = Game.score_max
            raise TeamWonException

    def add_player(self, player):
        if player not in self.data:
            player.team = self
            self.data.append(player)

    def remove_player(self, player):
        if player in self.data:
            player.team = None
            self.data.remove(player)

    def authorise(self, yes_or_no):
        for player in self.data:
            player.is_authorised = yes_or_no

    def toggle_authorisation(self):
        for player in self.data:
            player.is_authorised = not player.is_authorised


class GameState(ABC):
    def __init__(self, game):
        self.game = game
        self.player_manager = game.player_manager
        self.packet = game.packet
        self.history = []
        self.actions = []

    def actions_authorised(self):
        return self.actions

    def players_authorised(self):
        return [p.id for p in self.player_manager.get_all() if p.is_authorised]

    def is_player_authorised(self, player_id):
        return player_id in self.player_manager_authorised()

    def authorise_next_player(self):
        self.player_manager.authorise_next_player()

    def authorise_opposite_team(self, player_id):
        self.player_manager.authorise_team(self.player_manager.other_team(self.player_manager[player_id].team))

    def handle(self, action, player_id, *args):
        raise NotImplementedError

    def run(self, action, **kwargs):
        player_id = kwargs.get("player_id", None)

        if action not in self.actions_authorised():
            raise ForbiddenActionException
        if not self.is_player_authorised(player_id):
            raise WrongPlayerException
        try:
            ret = self.handle(action, player_id, **kwargs)
        except:
            raise
        else:
            self.record(action, player_id, **kwargs)
            return ret

    def on_entry(self):
        pass

    def on_exit(self):
        pass

    def record(self, action, player_id, *args):
        self.history.append((player_id, action, *args))

    def reset_history(self):
        self.history = []


class WaitingRoom(GameState):
    def __init__(self, game):
        super().__init__(game)
        self.actions = ["add_player", "remove_player", "start"]
        self.handle_map = {
            "add_player": self.handle_add_player,
        }

    def actions_authorised(self):
        actions = ["add_player", "remove_player"]
        if self.player_manager.can_start():
            actions.append("start")
        return actions

    def is_player_authorised(self, player_id):
        return True

    def handle_add_player(self, player_id, **kwargs):
        team_id = kwargs["team_id"]
        if team_id != 1 and team_id != 2:
            raise ForbiddenActionException("Invalid team number %d" % int(args[0]))

        # 0-indexing FTW
        team_id -= 1

        return self.player_manager.add(player_id, team_id)

    def handle(self, action, player_id, **kwargs):
        import ipdb; ipdb.set_trace()
        self.handle_map[action](player_id, **kwargs)

        if action == "add_player":
            if (len(args) != 2 and
                    not 0 <= int(args[1]) <= 1):
                raise ForbiddenActionException
            self.player_manager.add(player_id, args[0], int(args[1]))
            return "waiting_room"
        elif action == "remove_player":
            self.player_manager.remove(player_id)
            return "waiting_room"
        elif action == "start":
            if not self.player_manager.can_start:
                raise ForbiddenActionException
            return "Speaking"

    def on_exit(self):
        for player in self.player_manager:
            player.cards = sorted(self.packet.draw() for _ in range(4))
        self.player_manager.set_initial_echku()


class Speaking(GameState):
    def __init__(self, game):
        super().__init__(game)
        self.actions = ["mus", "mintza"]

    def handle(self, action, player_id, *args):
        if action == "mus":
            self.player_manager[player_id].team.said = "mus"
            if all(team.said == "mus" for team in self.player_manager.teams):
                return "Trading"
            self.authorise_opposite_team(player_id)
            return "Speaking"
        elif action == "mintza":
            return "Haundia"

    def on_entry(self):
        self.player_manager.record_scores()
        self.reset_history()
        self.player_manager.authorise_echku_team()

    def on_exit(self):
        for team in self.player_manager.teams:
            team.said = ""


class Trading(GameState):
    def __init__(self, game):
        super().__init__(game)
        self.actions = ["change", "confirm"]

    def is_player_authorised(self, player_id):
        return True

    def handle(self, action, player_id, *args):
        if action == "confirm":
            if len(self.player_manager[player_id].asks) == 0:
                raise ForbiddenActionException
            self.player_manager[player_id].said = "confirm"
            if all(player.said == "confirm" for player in self.player_manager):
                for player in self.player_manager:
                    for i in list(player.asks):
                        self.packet.discard(player.cards[i])
                        player.cards[i] = self.packet.draw()
                return "Speaking"
            return "Trading"
        elif action == "change":
            index = int(args[0]) - 1
            if len(args) != 1 or not 0 <= index <= 3:
                raise ForbiddenActionException
            if index in self.player_manager[player_id].asks:
                self.player_manager[player_id].asks.remove(index)
            else:
                self.player_manager[player_id].asks.add(index)
            return "Trading"

    def on_entry(self):
        self.reset_history()
        for player in self.player_manager:
            player.said = ""
            player.asks = set()

    def on_exit(self):
        for player in self.player_manager:
            player.cards.sort()


class BetState(GameState):
    own_state = ""
    next_state = ""
    has_bonus = False
    HandType = Hand

    def __init__(self, game):
        super().__init__(game)
        self.actions = ["paso", "imido", "tira", "gehiago", "hordago", "kanta", "idoki", "ok"]
        self.bet = 0
        self.bonus = 0
        self.deffered = True
        self.engaged = False
        self.hor_daged = False
        self.proposal = 0
        self.winner = None

    def compute_winner(self):
        if not self.deffered:
            return
        echku_order = self.player_manager.get_all_echku_sorted()
        for i in range(len(echku_order)):
            for j in range(i, len(echku_order)):
                hand_1 = self.HandType(echku_order[i].cards)
                hand_2 = self.HandType(echku_order[j].cards)
                if hand_1 < hand_2:
                    echku_order[i], echku_order[j] = echku_order[j], echku_order[i]
        self.winner = echku_order[0].team

    def compute_bonus(self):
        if self.has_bonus and self.engaged:
            for player in self.player_manager:
                if player.team == self.winner:
                    self.bonus += self.HandType(player.cards).bonus()

    def actions_authorised(self):
        actions = []
        if self.hor_daged:
            actions += "kanta", "tira"
        else:
            actions += "gehiago", "hordago"
            if not self.engaged:
                actions += "paso", "imido"
            else:
                actions += "tira", "idoki"
        return actions

    def on_entry(self):
        self.reset_history()
        self.first_player = self.player_manager.echku
        self.player_manager.authorise_echku_player()
        self.winner = None
        self.bet = 1
        self.deffered = True
        self.engaged = False
        self.hor_daged = False
        self.proposal = 0
        self.bonus = 0

    def everybody_is_paso(self):
        return self.player_manager.authorised_player == self.first_player

    def handle(self, action, player_id, *args):
        if action == "paso":
            self.authorise_next_player()
            if self.everybody_is_paso():
                self.deffered = True
                return self.next_state
            return self.own_state
        elif action == "imido":
            self.proposal = 1
            self.engaged = True
            self.authorise_opposite_team(player_id)
            return self.own_state
        elif action == "gehiago":
            proposal = int(args[0])
            if not self.engaged:
                proposal -= 1
            if proposal <= 0:
                raise ForbiddenActionException
            self.bet += self.proposal
            self.proposal = proposal
            self.engaged = True
            self.authorise_opposite_team(player_id)
            return self.own_state
        elif action == "hordago":
            self.hor_daged = True
            bet = Game.score_max
            return self.handle("gehiago", player_id, str(bet))
        elif action == "tira":
            self.deffered = False
            self.winner = self.player_manager.other_team(self.player_manager[player_id].team)
            try:
                self.player_manager.other_team(self.player_manager[player_id].team).add_score(self.bet)
            except TeamWonException:
                return "Finished"
            return self.next_state
        elif action == "idoki":
            self.bet += self.proposal
            return self.next_state
        elif action == "kanta":
            self.bet += self.proposal
            return "Finished"

    def on_exit(self):
        self.compute_winner()
        self.compute_bonus()


class Haundia(BetState):
    own_state = "Haundia"
    next_state = "Tipia"
    HandType = HaundiaHand


class Tipia(BetState):
    own_state = "Tipia"
    next_state = "Pariak"
    HandType = TipiaHand


class Pariak(BetState):
    own_state = "Pariak"
    next_state = "Jokua"
    HandType = PariakHand
    has_bonus = True

    def __init__(self, game):
        super().__init__(game)
        self.no_bet = False
        self.no_winner = False

    def is_player_authorised(self, player_id):
        if self.no_bet:
            return True
        return self.player_manager[player_id].has_hand and super().is_player_authorised(player_id)

    def actions_authorised(self):
        if self.no_bet:
            return ['ok']
        return super().actions_authorised()

    def authorise_next_player(self):
        self.player_manager.authorise_next_player()
        while not self.player_manager.authorised_player.has_hand:
            self.player_manager.authorise_next_player()

    def handle(self, action, player_id, *args):
        if action == 'ok':
            if not self.player_manager[player_id].waiting_confirmation:
                raise ForbiddenActionException
            self.player_manager[player_id].waiting_confirmation = False

            if all(not player.waiting_confirmation for player in self.player_manager):
                return self.next_state
            else:
                return self.own_state

        return super().handle(action, player_id, *args)

    def compute_winner(self):
        if not self.no_winner:
            super().compute_winner()

    def on_entry(self):
        super().on_entry()
        self.no_bet = False
        self.no_winner = False
        self.bet = 1
        for player in self.player_manager:
            player.has_hand = PariakHand(player.cards).is_special
        if all(not player.has_hand for player in self.player_manager):
            self.no_winner = True
            self.no_bet = True
            self.deffered = False
            self.bet = 0

        elif not (any(player.has_hand for player in self.player_manager.get_team(0)) and
                  any(player.has_hand for player in self.player_manager.get_team(1))):
            self.compute_winner()
            self.no_bet = True
            self.bet = 0
            self.deffered = False
            self.engaged = True
        else:
            while not self.player_manager.authorised_player.has_hand:
                self.player_manager.authorise_next_player()
            self.first_player = self.player_manager.authorised_player

        if self.no_bet:
            for player in self.player_manager:
                player.waiting_confirmation = True


class Jokua(BetState):
    own_state = "Jokua"
    next_state = "Finished"
    HandType = JokuaHand
    has_bonus = True

    def __init__(self, game):
        super().__init__(game)
        self.no_bet = False
        self.false_game = False

    def is_player_authorised(self, player_id):
        if self.no_bet:
            return True
        if not self.false_game:
            return self.player_manager[player_id].has_game and super().is_player_authorised(player_id)
        return super().is_player_authorised(player_id)

    def actions_authorised(self):
        if self.no_bet:
            return ['ok']
        return super().actions_authorised()

    def handle(self, action, player_id, *args):
        if action == 'ok':
            if not self.player_manager[player_id].waiting_confirmation:
                raise ForbiddenActionException
            self.player_manager[player_id].waiting_confirmation = False

            if all(not player.waiting_confirmation for player in self.player_manager):
                return self.next_state
            else:
                return self.own_state
        return super().handle(action, player_id, *args)

    def on_entry(self):
        super().on_entry()
        self.no_bet = False
        self.false_game = False
        for player in self.player_manager:
            player.has_game = JokuaHand(player.cards).is_special
        if any(player.has_game for player in self.player_manager):
            if not (any(player.has_game for player in self.player_manager.get_team(0)) and
                    any(player.has_game for player in self.player_manager.get_team(1))):
                self.compute_winner()
                self.no_bet = True
                self.bet = 0
                self.engaged = True
                self.deffered = False
            else:
                while not self.player_manager.authorised_player.has_game:
                    self.player_manager.authorise_next_player()
                self.first_player = self.player_manager.authorised_player
        else:
            self.false_game = True

        if self.no_bet:
            for player in self.player_manager:
                player.waiting_confirmation = True

    def compute_bonus(self):
        if self.false_game and self.engaged:
            self.bonus = 1
        else:
            super().compute_bonus()

class Finished(GameState):
    own_state = "Finished"
    next_state = "Speaking"

    def __init__(self, game):
        super().__init__(game)
        self.actions = ["ok"]

    def is_player_authorised(self, player_id):
        return True

    def on_entry(self):
        self.reset_history()
        if not self.player_manager.has_finished():
            try:
                for state in Game.bet_states:
                    if self.game.states[state].winner is not None:
                        if self.game.states[state].deffered:
                            self.player_manager.teams[self.game.states[state].winner.number].add_score(self.game.states[state].bet)
                        self.player_manager.teams[self.game.states[state].winner.number].add_score(self.game.states[state].bonus)
            except TeamWonException:
                self.game.finished = True

            for player in self.player_manager:
                player.waiting_confirmation = True

    def handle(self, action, player_id, *args):
        if not self.player_manager[player_id].waiting_confirmation:
            raise ForbiddenActionException

        self.player_manager[player_id].waiting_confirmation = False

        if all(not player.waiting_confirmation for player in self.player_manager):
            return self.next_state
        else:
            return self.own_state

    def on_exit(self):
        self.packet.restore()
        for player in self.player_manager:
            player.cards = sorted(self.packet.draw() for _ in range(4))
        self.player_manager.get_all_echku_sorted()
        if self.player_manager.has_finished():
            for team in self.player_manager.teams:
                team.score = 0
        self.player_manager.set_echku()


class Game:
    score_max = 40
    bet_states = ["Haundia", "Tipia", "Pariak", "Jokua"]

    def __init__(self):
        self.player_manager = PlayerManager()
        self.packet = Packet()
        self._current_state = "waiting_room"

        self.states = {
            "waiting_room": WaitingRoom(self),
            "Speaking": Speaking(self),
            "Trading": Trading(self),
            "Haundia": Haundia(self),
            "Tipia": Tipia(self),
            "Pariak": Pariak(self),
            "Jokua": Jokua(self),
            "Finished": Finished(self),
        }

    @property
    def current_state(self):
        return self._current_state

    @current_state.setter
    def current_state(self, value):
        self._current_state = value

    def do(self, message):
        action = message[0]
        kwargs = message[1]

        old_state = self.current_state
        answer = self.states[self.current_state].run(action, **kwargs)

        if old_state != self.current_state:
            self.states[old_state].on_exit()
            self.states[self.current_state].on_entry()

        return answer
