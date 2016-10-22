#! /usr/bin/env python3

import logging
import pickle
import redis
import sys

import mus

import telepot
from telepot import namedtuple as tnp

DEBUG_LOG = False
CACHE_TIME = 0

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


class HordagoTelegramHandler():
    INITIAL_GREETING = """<b>Welcome to the mus bot!</b>
    I will be your assistant during this game.
    Mus is a game from the <i>basque country</i>,
    if you have never heard of it, please see game rules\
    <a href="https://en.wikipedia.org/wiki/Mus_(card_game)">here</a>."""

    INIT_KB = tnp.InlineKeyboardMarkup(inline_keyboard=[
        [
            tnp.InlineKeyboardButton(text='Join team 1', callback_data="join_team_1"),
            tnp.InlineKeyboardButton(text='Join team 2', callback_data="join_team_2"),
            ],
        ])

    def __init__(self, token):
        self.bot = telepot.Bot(token)
        self.database = HordagoDatabase()

    def update_text(self, inline_message_id, query_id, game):
        if self.database.response_has_changed(self.compute_message(game),
                                              self.compute_keyboard(game),
                                              inline_message_id):
            self.bot.editMessageText(inline_message_id,
                                     self.compute_message(game),
                                     reply_markup=self.compute_keyboard(game),
                                     parse_mode='HTML',
                                     disable_web_page_preview=True)
        elif query_id is not None:
            self.bot.answerCallbackQuery(query_id)

    def compute_message(self, game):
        msg = ""
        if not game.is_started:
            msg = self.INITIAL_GREETING
            msg += "\n<b>Team 1:</b>\n" + "\n".join(player.name for player in game.teams[0].players)
            msg += "\n<b>Team 2:</b>\n" + "\n".join(player.name for player in game.teams[1].players)
        else:
            msg = "Game started!"
            if game.turn.sub_current == mus.Turn.SUBTURNS[1]:
                msg += "\n<b>Team 1:</b>\n" + "\n".join(player.name + " will change " + str(len(player.asks)) + " card(s)." for player in game.teams[0].players)
                msg += "\n<b>Team 2:</b>\n" + "\n".join(player.name + " will change " + str(len(player.asks)) + " card(s)." for player in game.teams[1].players)
            else:
                msg += "\n<b>Team 1:</b>\n" + "\n".join(player.name for player in game.teams[0].players)
                msg += "\n<b>Team 2:</b>\n" + "\n".join(player.name for player in game.teams[1].players)
        return msg

    def compute_keyboard(self, game):
        kb = []
        if not game.is_started:
            if game.can_start():
                kb.append([tnp.InlineKeyboardButton(text='Start Game', callback_data="start_game")])
            kb_join = []
            if game.can_join_team(0):
                kb_join.append(tnp.InlineKeyboardButton(text='Join team 1',
                                                        callback_data="join_team_1"))
            if game.can_join_team(1):
                kb_join.append(tnp.InlineKeyboardButton(text='Join team 2',
                                                        callback_data="join_team_2"))
            if len(kb_join) > 0:
                kb.append(kb_join)
            kb.append([tnp.InlineKeyboardButton(text='Leave', callback_data="leave")])
        else:
            kb.append([tnp.InlineKeyboardButton(text='Show cards', callback_data="show_cards")])
            if game.turn.current == mus.Turn.TURNS[0]:
                if game.turn.sub_current == mus.Turn.SUBTURNS[0]:
                    kb.append([tnp.InlineKeyboardButton(text='Minsa', callback_data="play_Minsa"),
                               tnp.InlineKeyboardButton(text='Mus', callback_data="play_Mus")])
                elif game.turn.sub_current == mus.Turn.SUBTURNS[1]:
                    kb.append([tnp.InlineKeyboardButton(text='Change #1', callback_data="play_0"),
                               tnp.InlineKeyboardButton(text='Change #2', callback_data="play_1"),
                               tnp.InlineKeyboardButton(text='Change #3', callback_data="play_2"),
                               tnp.InlineKeyboardButton(text='Change #4', callback_data="play_3")])
                    kb.append([tnp.InlineKeyboardButton(text='Confirm', callback_data="play_Ready")])

        return tnp.InlineKeyboardMarkup(inline_keyboard=kb)

    def start(self):
        self.bot.message_loop({'inline_query': self.on_inline_query,
                               'chosen_inline_result': self.on_chosen_inline_result,
                               'callback_query': self.on_callback_query},
                              run_forever='Listening ...')

    def on_inline_query(self, msg):
        query_id, _, _ = telepot.glance(msg, flavor='inline_query')

        articles = [tnp.InlineQueryResultArticle(
            id='play',
            title='Play mus',
            input_message_content=tnp.InputTextMessageContent(message_text=self.INITIAL_GREETING,
                                                              parse_mode='HTML',
                                                              disable_web_page_preview=True),
            reply_markup=self.INIT_KB,
            )]

        self.bot.answerInlineQuery(query_id, articles, cache_time=CACHE_TIME)

    def on_chosen_inline_result(self, msg):
        _, from_id, _ = telepot.glance(msg, flavor='chosen_inline_result')
        inline_message_id = msg['inline_message_id']

        #Automaticaly add first player
        game = self.database.new_game(inline_message_id)
        game.add_player(mus.Player(from_id, msg['from']['first_name']), 0)
        self.database.save(game)

        self.update_text(inline_message_id, None, game)

    def on_callback_query(self, msg):
        query_id, from_id, query_data = telepot.glance(msg, flavor='callback_query')
        inline_message_id = msg['inline_message_id']
        print('Callback Query:', query_id, from_id, query_data, inline_message_id)

        if self.database.has_game(inline_message_id):
            game = self.database.get(inline_message_id)
            player_name = msg['from']['first_name']
            if query_data.startswith('join_team'):
                game.add_player(mus.Player(from_id, player_name), int(query_data[-1]) - 1)
            elif query_data == 'leave':
                game.remove_player(mus.Player(from_id, player_name))
            elif query_data == 'start_game':
                game.start()
            elif query_data == 'show_cards':
                cards = game.get_player(mus.Player(from_id, player_name)).get_cards()
                cards.sort()
                answer = "\n".join(str(i+1) + ": " + str(mus.Card(card)) for i, card in enumerate(cards))
                self.bot.answerCallbackQuery(query_id, text=answer, show_alert=True)
            elif query_data.startswith('play'):
                game.play(query_data.split('_')[-1], mus.Player(from_id, player_name))
            self.database.save(game)
        else:
            self.bot.answerCallbackQuery(query_id, text='NOPE')

        self.update_text(inline_message_id, query_id, game)

def main():
    if DEBUG_LOG:
        logging.basicConfig(level=logging.DEBUG,
                            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    telegram_handler = HordagoTelegramHandler(sys.argv[1])
    telegram_handler.start()

if __name__ == "__main__":
    main()
