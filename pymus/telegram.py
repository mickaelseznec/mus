#! /usr/bin/env python3

import pickle
import redis
import sys
import yaml
import telepot

from telepot import namedtuple as tnp
from telepot.loop import MessageLoop

import mus


class HordagoDatabase():
    def __init__(self):
        self.games = redis.StrictRedis('localhost')

    def has_game(self, game_id):
        return self.games.get(game_id) is not None

    def new_game(self, game_id):
        game = mus.Game(game_id)
        self.games.set(game_id, pickle.dumps(game))
        return game

    def get(self, game_id):
        game = self.games.get(game_id)
        return pickle.loads(game) if game is not None else None

    def save(self, game):
        self.games.set(game.game_id, pickle.dumps(game))

    def response_has_changed(self, game_id, text, keyboard):
        old_text = self.games.get("{}_{}".format(game_id, "text"))
        old_keyboard = self.games.get("{}_{}".format(game_id, "keyboard"))

        text_changed = old_text is None or old_text.decode("utf-8") != text
        keyboard_changed = old_keyboard is None or old_keyboard.decode("utf-8") != str(keyboard)

        self.games.set("{}_{}".format(game_id, "text"), text)
        self.games.set("{}_{}".format(game_id, "keyboard"), str(keyboard))

        return text_changed or keyboard_changed


class HordagoTelegramHandler:
    CACHE_TIME=0 #TODO:Change me when stable

    def __init__(self, token):
        self.bot = telepot.Bot(token)
        self.database = HordagoDatabase()

        with open("static/telegram_text_interface.yaml") as f:
            data = yaml.safe_load(f)

        self.texts = data["texts"]
        self.keyboards = data["keyboards"]
        self.states = data["states"]
        self.card_colors = data["card_colors"]
        self.numbers = data["basque_numbers"]

    def start(self):
        MessageLoop(
            self.bot,
            {'inline_query': self.on_inline_query,
             'chosen_inline_result': self.on_chosen_inline_result,
             'callback_query': self.on_callback_query}
        ).run_forever()

    def on_inline_query(self, msg):
        """ Displays always the same result whatever the user input.

        Must give a mockup text an keyboard to get further interaction with the users."""

        play_mus_inline_answer = [
            tnp.InlineQueryResultArticle(
                id='start',
                title=self.texts["inline_answer"],
                input_message_content=tnp.InputTextMessageContent(
                    message_text=self.texts["loading"]),
                reply_markup=tnp.InlineKeyboardMarkup(
                    inline_keyboard=[[tnp.InlineKeyboardButton(
                        text=self.keyboards["loading"],
                        callback_data="None")]])
            )]

        self.bot.answerInlineQuery(msg['id'], play_mus_inline_answer, cache_time=self.CACHE_TIME)

    def on_chosen_inline_result(self, msg):
        """ Creates a new game and automatically adds first player"""

        from_user, inline_message_id = msg['from'], msg['inline_message_id']

        #Automaticaly add first player
        game = self.database.new_game(inline_message_id)
        game.do("add_player", from_user['id'], from_user['first_name'], "0")
        self.database.save(game)

        self.update_text(inline_message_id, game)

    def on_callback_query(self, msg):
        query_id, from_id, query_data = telepot.glance(msg, flavor='callback_query')
        inline_message_id = msg['inline_message_id']
        print('Callback Query:', query_id, from_id, query_data, inline_message_id)

        if not self.database.has_game(inline_message_id):
            self.bot.answerCallbackQuery(query_id, text=self.texts["no_data"])
            return

        game = self.database.get(inline_message_id)

        if query_data == 'show_cards':
            cards = game.players[from_id].get_cards()
            answer = "\n".join("#{}:  {} {}".format(i + 1, card.value, self.card_colors[card.color])
                               for i, card in enumerate(cards))
            self.bot.answerCallbackQuery(query_id, text=answer, show_alert=True)
        else:
            try:
                split = query_data.split('.')
                if split[0] == 'add_player':
                    game.do(split[0], from_id, msg['from']['first_name'], *split[1:])
                else:
                    game.do(split[0], from_id, *split[1:])
            except mus.WrongPlayerException:
                self.bot.answerCallbackQuery(query_id, text=self.texts["not_your_turn"])
            except mus.ForbiddenActionException:
                self.bot.answerCallbackQuery(query_id, text=self.texts["cannot_do_that"])
            else:
                self.bot.answerCallbackQuery(query_id)


        self.database.save(game)

        self.update_text(inline_message_id, game)

    def compute_message(self, game):
        msg = ""

        if game.current == "waiting_room":
            return self.texts["waiting_room"].format(
                "\n\t".join([player.name for player in game.players.get_team(0)]),
                "\n\t".join([player.name for player in game.players.get_team(1)])
            )

        if game.current == "Trading":
            exchanges_team_1 = [self.texts["exchange"].format(player.name, len(player.asks))
                                for player in game.players.get_team(0)]

            exchanges_team_2 = [self.texts["exchange"].format(player.name, len(player.asks))
                                for player in game.players.get_team(1)]

            return self.texts["trading"].format("\n".join(exchanges_team_1),
                                                "\n".join(exchanges_team_2))

        if game.current == "Finished":

            msg = (self.texts["finished"] if not game.players.has_finished() else
                   self.texts["end_game"].format(game.players.winner_team() + 1))

            msg += self.texts["summary"]

            states_summary = []
            for state_name in game.bet_states:
                state = game.states[state_name]

                state_bet = self.texts["state_bet"].format(
                    self.states[state_name],
                    state.bet
                )

                state_bonus = (self.texts["state_bonus"].format(state.bonus)
                               if state.bonus > 0 else "")
                state_team = (self.texts["state_team"].format(state.winner.number + 1)
                              if (state.bet > 0 or state.bonus > 0) else "")

                states_summary.append(state_bet + state_bonus + state_team)

            msg += "\n".join(states_summary) + "\n\n"

            team_messages = []
            for i in range(2):
                intro = self.texts["team_score"].format(i + 1, game.players.teams[i].score)

                player_cards = "\n".join([self.texts["show_cards"].format(
                    player.name,
                    ", ".join(str(card.value) for card in player.get_cards()))
                                          for player in game.players.get_team(i)])
                team_messages.append(intro + player_cards)

            msg += "\n".join(team_messages) + "\n\n"

            msg += self.format_history(game)

            return msg

        msg = self.texts["title"].format(self.states[str(game.current)])
        if not game.current == "Speaking":
            msg += self.texts["current_bet"].format(game.states[game.current].bet)

            if game.states[game.current].proposal > 0:
                msg += self.texts["proposal"].format(game.states[game.current].proposal)
        msg += "\n"

        if game.current in game.bet_states:
            current_state = game.bet_states.index(game.current)
            state_summaries = []

            for i in range(current_state):
                state = game.states[game.bet_states[i]]

                state_summary = (self.texts["state_summary"] if state.winner is not None
                                    else self.texts["state_summary_empty"]).format(
                                        self.states[game.bet_states[i]], state.bet,
                                        ("?" if state.deffered else state.winner.number + 1))
                state_summaries.append(state_summary)

            if state_summaries:
                msg += "\n ".join(state_summaries) + "\n\n"

        team_messages = []
        for i in range(2):
            intro = self.texts["team_score"].format(i + 1, game.players.teams[i].score)

            player_messages = []
            for player in game.players.get_team(i):
                player_name = (self.texts["active_player"]
                               if game.states[game.current].is_player_authorised(player.id)
                               else self.texts["inactive_player"]).format(player.name)

                player_says = ""
                if game.current == "Pariak":
                    player_says = self.texts["bai"] if player.has_hand else self.texts["ez"]
                elif game.current == "Jokua":
                    player_says = self.texts["bai"] if player.has_game else self.texts["ez"]

                player_messages.append(player_name + player_says)

            team_messages.append(intro + "\n".join(player_messages))
        msg += "\n".join(team_messages)
        msg += "\n\n"
        msg += self.format_history(game)

        return msg

    def format_history(self, game):
        message = ""

        for player_id, action, *arguments in game.state.history:
            if action == "gehiago":
                action = self.numbers[int(arguments[0])]
            message += self.texts["player_said"].format(game.state.players[player_id].name,
                                                        action)

        return message


    def compute_keyboard(self, game):
        if game.current == "waiting_room":
            join_teams = [
                tnp.InlineKeyboardButton(text=self.keyboards["join_team"][1],
                                         callback_data="add_player.0"),
                tnp.InlineKeyboardButton(text=self.keyboards["join_team"][2],
                                         callback_data="add_player.1"),
            ]

            kb = [
                [tnp.InlineKeyboardButton(text=self.keyboards["start_game"],
                                          callback_data="start")],
                join_teams,
                [tnp.InlineKeyboardButton(text=self.keyboards["leave_game"],
                                          callback_data="remove_player")]
            ]
            return tnp.InlineKeyboardMarkup(inline_keyboard=kb)

        if game.current == "Finished":
            kb = [[tnp.InlineKeyboardButton(text=self.keyboards["new_game"], callback_data="ok")
                  if game.players.has_finished() else
                  tnp.InlineKeyboardButton(text=self.keyboards["ok"], callback_data="ok")]]

            return tnp.InlineKeyboardMarkup(inline_keyboard=kb)

        kb = [[tnp.InlineKeyboardButton(text=self.keyboards["show_cards"], callback_data="show_cards")]]

        if game.current == "Speaking":
            kb.append([tnp.InlineKeyboardButton(text=self.keyboards["mintza"], callback_data="mintza"),
                       tnp.InlineKeyboardButton(text=self.keyboards["mus"], callback_data="mus")])

        elif game.current == "Trading":
            choices = [tnp.InlineKeyboardButton(text=self.keyboards["change"].format(i),
                                                callback_data="change.{}".format(i))
                       for i in range(1, 5)]
            kb += [choices[:2], choices[2:]]
            kb.append([tnp.InlineKeyboardButton(text=self.keyboards["confirm"], callback_data="confirm")])

        else:
            possible_actions = game.states[game.current].actions_authorised()
            if 'ok' in possible_actions:
                kb.append([tnp.InlineKeyboardButton(text=self.keyboards["ok"], callback_data="ok")])
                return tnp.InlineKeyboardMarkup(inline_keyboard=kb)
            if 'paso' in possible_actions:
                kb.append([tnp.InlineKeyboardButton(text=self.keyboards["imido"], callback_data="imido"),
                           tnp.InlineKeyboardButton(text=self.keyboards["paso"], callback_data="paso")])
            if 'kanta' in possible_actions:
                kb.append([tnp.InlineKeyboardButton(text=self.keyboards["kanta"], callback_data="kanta"),
                           tnp.InlineKeyboardButton(text=self.keyboards["tira"], callback_data="tira")])
            if 'idoki' in possible_actions:
                kb.append([tnp.InlineKeyboardButton(text=self.keyboards["idoki"], callback_data="idoki"),
                           tnp.InlineKeyboardButton(text=self.keyboards["tira"], callback_data="tira")])
            if 'gehiago' in possible_actions:
                gehiago = [tnp.InlineKeyboardButton(text=self.numbers[i], callback_data="gehiago.{}".format(i)) for i in [1, 2, 3, 4, 5, 10]]
                kb += [gehiago[:3], gehiago[3:]]
                kb.append([tnp.InlineKeyboardButton(text=self.keyboards["hordago"], callback_data="hordago")])

        return tnp.InlineKeyboardMarkup(inline_keyboard=kb)

    def update_text(self, inline_message_id, game):
        message_update = self.compute_message(game)
        keyboard_update = self.compute_keyboard(game)

        if self.database.response_has_changed(inline_message_id, message_update, keyboard_update):
            self.bot.editMessageText(inline_message_id,
                                    message_update,
                                    reply_markup=keyboard_update,
                                    parse_mode='HTML',
                                    disable_web_page_preview=True)
