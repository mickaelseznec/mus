#! /usr/bin/env python3

import pickle
import sys

import redis

import mus

import telepot
from telepot import namedtuple as tnp

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

    def response_has_changed(self, text, keyboard, game_id):
        if (self.games.get("text" + str(game_id)) is None or
                self.games.get("text" + str(game_id)).decode('utf-8') != text):
            self.games.set("text" + str(game_id), text)
            return True
        if (self.games.get("kb" + str(game_id)) is None or
                self.games.get("kb" + str(game_id)).decode('utf-8') != keyboard):
            self.games.set("text" + str(game_id), keyboard)
            return True
        return False


class HordagoTelegramHandler:

    def __init__(self, token):
        self.bot = telepot.Bot(token)
        self.database = HordagoDatabase()
        self.initial_greeting = (
            '<b>Welcome to the mus bot!</b>\n\n'
            'I will be your assistant during this game.\n'
            'Mus is a game from the <i>basque country</i>,\n'
            'if you have never heard of it, please see game rules '
            '<a href="https://en.wikipedia.org/wiki/Mus_(card_game)">here</a>.\n')

        self.initial_response = [
            tnp.InlineQueryResultArticle(
                id='play',
                title='Play mus',
                input_message_content=tnp.InputTextMessageContent(message_text=self.initial_greeting,
                                                                  parse_mode='HTML',
                                                                  disable_web_page_preview=True),
                reply_markup=tnp.InlineKeyboardMarkup(
                    inline_keyboard=[[tnp.InlineKeyboardButton(text='Join team 1',
                                                               callback_data="join_team_1"),
                                      tnp.InlineKeyboardButton(text='Join team 2',
                                                               callback_data="join_team_2")
                                     ]]
                )
            )
        ]

    def start(self):
        self.bot.message_loop({'inline_query': self.on_inline_query,
                               'chosen_inline_result': self.on_chosen_inline_result,
                               'callback_query': self.on_callback_query},
                              run_forever='Listening ...')

    def on_inline_query(self, msg):
        self.bot.answerInlineQuery(msg['id'], self.initial_response, cache_time=CACHE_TIME)

    def on_chosen_inline_result(self, msg):
        from_user, inline_message_id = msg['from'], msg['inline_message_id']

        #Automaticaly add first player
        game = self.database.new_game(inline_message_id)
        game.action("add_player", from_user['id'], from_user['first_name'], "0")
        self.database.save(game)

        self.update_text(inline_message_id, game)

    def on_callback_query(self, msg):
        query_id, from_id, query_data = telepot.glance(msg, flavor='callback_query')
        inline_message_id = msg['inline_message_id']
        print('Callback Query:', query_id, from_id, query_data, inline_message_id)

        if not self.database.has_game(inline_message_id):
            self.bot.answerCallbackQuery(query_id, text='Error while retrieving your game, sorry')
            return

        game = self.database.get(inline_message_id)

        if query_data == 'show_cards':
            cards = game.players[from_id].get_cards()
            answer = "\n".join("#" + str(i + 1) + ": " + str(card) for i, card in enumerate(cards))
            self.bot.answerCallbackQuery(query_id, text=answer, show_alert=True)
        else:
            try:
                split = query_data.split('.')
                if split[0] == 'add_player':
                    game.action(split[0], from_id, msg['from']['first_name'], *split[1:])
                else:
                    game.action(split[0], from_id, *split[1:])
            except mus.WrongPlayerException:
                self.bot.answerCallbackQuery(query_id, text="It's not your turn!")
            except mus.ForbiddenActionException:
                self.bot.answerCallbackQuery(query_id, text="You can't do that!")
            else:
                self.bot.answerCallbackQuery(query_id)


        self.database.save(game)

        self.update_text(inline_message_id, game)

    def compute_message(self, game):
        msg = ""
        if game.current == "Waiting":
            msg += self.initial_greeting
            msg += "\n<b>Team 1:</b>\n" + "\n".join(player.name for player in game.players.get_team(0))
            msg += "\n<b>Team 2:</b>\n" + "\n".join(player.name for player in game.players.get_team(1))
        elif game.current == "Trading":
            msg += "<b>Choose which cards you want to change.</b>\n"
            msg += "\n<b>Team 1:</b>\n" + "\n".join(player.name + " will change " + str(len(player.asks)) + " card(s)." for player in game.players.get_team(0))
            msg += "\n<b>Team 2:</b>\n" + "\n".join(player.name + " will change " + str(len(player.asks)) + " card(s)." for player in game.players.get_team(1))
        elif game.current == "Finished":
            if game.players.has_finished():
                msg += "Party finished!\n"
                msg += "\nTeam " + str(game.players.winner_team() + 1) + " HAS WON, CONGRATS!\n"
            else:
                msg += "Turn finished!\n"
            msg += "\n<b>Summary:</b>"
            for state_name in game.bet_states:
                state = game.states[state_name]
                msg += "\n" + state_name + ": " + str(state.bet)
                if state.bonus > 0:
                    msg += " + " + str(state.bonus) + " bonus"
                if state.bet > 0 or state.bonus > 0:
                    msg += " -> <b>Team " + str(state.winner.number + 1) + "</b>"
            msg += "\n"
            for i in range(2):
                msg += "\nTeam " + str(i + 1) + ": <b>" + str(game.players.teams[i].score) + "</b>"
                player_msg = ""
                for player in game.players.get_team(i):
                    player_msg += player.name + " had " + ", ".join(str(card) for card in player.get_cards())
                msg += "\n" + player_msg

        else:
            if game.current == "Speaking":
                msg += "<b>Mus or mintza?</b>\n"
            else:
                msg += "<b>" + game.current + "</b>\n"
                msg += "Current bet: " + str(game.states[game.current].bet) + "\n"
                if game.states[game.current].proposal > 0:
                    msg += "Proposal: " + str(game.states[game.current].proposal) + "\n"
            msg += "\nPlayers in <b>bold</b> can speak.\nRemember that you play in the name of your team!\n"
            for i in range(2):
                msg += "\nTeam " + str(i + 1) + ": <b>" + str(game.players.teams[i].score) + "</b>\n"
                player_msg = ""
                for player in game.players.get_team(i):
                    player_msg += player.name
                    if game.states[game.current].is_player_authorised(player.id):
                        player_msg = "<b>" + player_msg + "</b>"
                    if game.current == "Pariak":
                        player_msg = player_msg + ": " + ("Bai" if player.has_hand else "Ez")
                    elif game.current == "Jokua":
                        player_msg = player_msg + ": " + ("Bai" if player.has_game else "Ez")
                    player_msg += "\n"
                msg += player_msg
            if game.current in game.bet_states:
                cur = game.bet_states.index(game.current)
                for i in range(cur):
                    state = game.states[game.bet_states[i]]
                    if state.winner is not None:
                        msg += "\n" + game.bet_states[i] + ": " + str(state.bet) + " -> Team "
                        if state.deffered:
                            msg += "?"
                        else:
                            msg += str(state.winner.number + 1)
                    else:
                        msg += "\n" + game.bet_states[i] + ": no bet"

        return msg

    def compute_keyboard(self, game):
        kb = []
        if game.current == "Waiting":
            kb.append([tnp.InlineKeyboardButton(text='👍 Start Game', callback_data="start")])
            kb_join = []
            kb_join.append(tnp.InlineKeyboardButton(text='Join team 1',
                                                    callback_data="add_player.0"))
            kb_join.append(tnp.InlineKeyboardButton(text='Join team 2',
                                                    callback_data="add_player.1"))
            kb.append(kb_join)
            kb.append([tnp.InlineKeyboardButton(text='🏃 Leave', callback_data="remove_player")])
            return tnp.InlineKeyboardMarkup(inline_keyboard=kb)
        if game.current == "Finished":
            if game.players.has_finished():
                kb.append([tnp.InlineKeyboardButton(text='New Game', callback_data="ok")])
            else:
                kb.append([tnp.InlineKeyboardButton(text='OK', callback_data="ok")])
            return tnp.InlineKeyboardMarkup(inline_keyboard=kb)
        kb.append([tnp.InlineKeyboardButton(text='Show cards', callback_data="show_cards")])
        if game.current == "Speaking":
            kb.append([tnp.InlineKeyboardButton(text='Mintza', callback_data="mintza"),
                       tnp.InlineKeyboardButton(text='Mus', callback_data="mus")])
        elif game.current == "Trading":
            kb.append([tnp.InlineKeyboardButton(text='Change #1', callback_data="change.0"),
                       tnp.InlineKeyboardButton(text='Change #2', callback_data="change.1"),
                       tnp.InlineKeyboardButton(text='Change #3', callback_data="change.2"),
                       tnp.InlineKeyboardButton(text='Change #4', callback_data="change.3")])
            kb.append([tnp.InlineKeyboardButton(text='Confirm', callback_data="confirm")])
        else:
            possible_actions = game.states[game.current].actions_authorised()
            if 'ok' in possible_actions:
                kb.append([tnp.InlineKeyboardButton(text='OK', callback_data="ok")])
                return tnp.InlineKeyboardMarkup(inline_keyboard=kb)
            if 'paso' in possible_actions:
                kb.append([tnp.InlineKeyboardButton(text='Imido', callback_data="imido"),
                           tnp.InlineKeyboardButton(text='Paso', callback_data="paso")])
            if 'kanta' in possible_actions:
                kb.append([tnp.InlineKeyboardButton(text='Kanta', callback_data="kanta"),
                           tnp.InlineKeyboardButton(text='Tira', callback_data="tira")])
            if 'idoki' in possible_actions:
                kb.append([tnp.InlineKeyboardButton(text='Idoki', callback_data="idoki"),
                           tnp.InlineKeyboardButton(text='Tira', callback_data="tira")])
            if 'gehiago' in possible_actions:
                basque_numbers = [("Bat", 1), ("Bi", 2), ("Hiru", 3), ("Lau", 4), ("Bost", 5), ("Amar", 10)]
                gehiago = [tnp.InlineKeyboardButton(text=name, callback_data="gehiago." + str(i)) for name, i in basque_numbers]
                kb.append(gehiago[:3])
                kb.append(gehiago[3:])
                kb.append([tnp.InlineKeyboardButton(text='Hor dago!', callback_data="hordago")])

        return tnp.InlineKeyboardMarkup(inline_keyboard=kb)

    def update_text(self, inline_message_id, game):
        """if self.database.response_has_changed(self.compute_message(game),
                                              self.compute_keyboard(game),
                                              inline_message_id):
                                              """
        self.bot.editMessageText(inline_message_id,
                                 self.compute_message(game),
                                 reply_markup=self.compute_keyboard(game),
                                 parse_mode='HTML',
                                 disable_web_page_preview=True)
