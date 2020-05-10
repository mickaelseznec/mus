#! /usr/bin/env python3
import json
import multiprocessing as mp
import os
import pika
import urwid
import uuid

from collections import deque


class ReceptionProcess(mp.Process):
    def __init__(self, incoming_channel_name, signal_pipe, callback_queue):
        super().__init__(name="reception_process")
        self.incoming_channel_name = incoming_channel_name
        self.signal_pipe = signal_pipe
        self.callback_queue = callback_queue

    def run(self):
        with PikaConnection() as (con, chan):
            chan.basic_consume(queue=self.incoming_channel_name,
                                on_message_callback=self.handle_answer,
                                auto_ack=True)
            chan.start_consuming()

    def handle_answer(self, ch, method, properties, body):
        answer = json.loads(body)
        self.callback_queue.put((answer, properties.correlation_id))

        os.write(self.signal_pipe, b"1")


class QuestionBox(urwid.Edit):
    def __init__(self, *args, on_user_validation, **kwargs):
        super().__init__(*args, **kwargs)
        self.on_user_validation = on_user_validation

    def keypress(self, size, key):
        if key != 'enter':
            return super().keypress(size, key)

        self.on_user_validation(self.edit_text)
        self.edit_text = ""


class PikaConnection:
    def __init__(self):
        self.connection = None

    def __enter__(self):
        connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
        channel = connection.channel()

        return connection, channel

    def __exit__(self,  exc_type, exc_value, traceback):
        if self.connection:
            self.connection.close()


class UrwidTUI:
    programmatic_names = {
        'Waiting Room': 'waiting_room',
        'Speaking': 'speaking',
        'Haundia': 'haundia',
        'Tipia': 'tipia',
    }

    def __init__(self):
        header = urwid.Text("pymus client")
        footer = urwid.Divider()

        self.game_id = None
        self.body = urwid.ListBox(
            [QuestionBox("Pleaser enter the room name\n", on_user_validation=self._join_room)])

        self.frame = urwid.Frame(self.body, header, footer)

        self.loop = urwid.MainLoop(self.frame, unhandled_input=self._exit_on_q)
        self.callback_pipe = self.loop.watch_pipe(self.handle_new_data_from_server)
        self.intercepted_answer = {"add_player": None, "get_cards": None}
        self.player_id = None
        self.public_player_id = None
        self.old_state = None
        self.cards = None

    def start(self):
        with PikaConnection() as (conn, chan):
            chan.queue_declare(queue='welcome')
            incoming_channel = chan.queue_declare(queue='')
        self.incoming_channel_name = incoming_channel.method.queue

        self.callback_queue = mp.Queue()
        self.reception_process = ReceptionProcess(self.incoming_channel_name, self.callback_pipe,
                                                  self.callback_queue)
        self.reception_process.start()

        self.loop.run()

        self.reception_process.kill()
        self.reception_process.join()

    def _exit_on_q(self, key):
        if key in ('q', 'Q'):
            raise urwid.ExitMainLoop()

    def _join_room(self, game_id):
        self.game_id = game_id

        with PikaConnection() as (con, chan):
            chan.basic_publish(
                exchange='',
                properties=pika.BasicProperties(reply_to=self.incoming_channel_name),
                routing_key='welcome',
                body=json.dumps(("register", {"game_id": self.game_id})))

    def handle_new_data_from_server(self, pipe_data):
        answer, correlation_id = self.callback_queue.get()

        if correlation_id is not None:
            for key, value in self.intercepted_answer.items():
                if value == correlation_id:
                    if key == "add_player":
                        self.player_id, self.public_player_id = answer
                    if key == "get_cards":
                        self.cards = answer
                    return

        current_state = answer['current_state']
        if current_state == "Speaking" and self.old_state != current_state:
            self._send_server("get_cards")
        self.old_state = current_state

        state_widget = self.get_main_display(answer)
        history_widget = self.get_history(answer)

        state_and_history = urwid.Columns((state_widget, history_widget))

        server_prompt = QuestionBox(">", on_user_validation=self._send_server)

        widget_list = urwid.ListBox((state_and_history, server_prompt))

        self.frame.body = widget_list
        self.frame.footer = urwid.Text("Connected to game {}, Turn: {}".format(
            self.game_id, answer['current_state']))

    def get_history(self, answer):
        history = [urwid.Text("Historique :\n")]
        if "Trading" in answer:
            state = urwid.Text("Échange :\n")
            history.append(state)
        if "Speaking" in answer:
            state = urwid.Text("Début :\n")
            history.append(state)

        fancy_states = {
            "Haundia": "Le grand",
            "Tipia": "Le petit",
            "Pariak": "Les paires",
            "Jokua": "Le jeu",
        }

        for state in ("Haundia", "Tipia", "Pariak", "Jokua"):
            if state in answer:
                text = fancy_states[state] + " :\n"
                if answer[state]["IsSkipped"]:
                    text += "Pas de paris\n"
                elif answer[state]["Winner"]:
                    text += "Paris à {} points\n".format(answer[state]["Bid"])
                if answer[state]["Winner"]:
                    text += "Remporté par l'équipe {}\n".format(answer[state]["Winner"])

                history.append(urwid.Text(text))

        return urwid.Pile(history)

    def get_main_display(self, answer):
        state = answer["current_state"]

        if state == "Waiting Room":
            return display_waiting_room(answer)

        team_text = []
        for index, team in enumerate(answer["teams"]):
            team_text.append("Équipe {}: {}. {} points".format(
                index, " ".join(team["players"]), team["score"]))
        team_text = "\n".join(team_text)

        player_text = []
        for player in answer["echku_order"]:
            if answer["players"][player]["can_speak"]:
                player_text.append(("blink", "!" + player + "\n"))
            else:
                player_text.append(player + "\n")

        team_text = urwid.Text(team_text)
        player_text = urwid.Text(player_text)

        rows = (team_text, player_text)

        if self.cards is not None:
            card_text = []
            for card in self.cards:
                card_text.append("{}-{}".format(*card))

            card_text = urwid.Text("Mes cartes : " + " ".join(card_text))
            rows += (card_text, )

        if state in ("Haundia", "Tipia", "Pariak", "Jokua"):
            state_status = answer[state]
            state_text = ""

            if state_status["IsSkipped"]:
                state_text = "Pas de paris pour cette manche, veuillez confirmer"
            elif state_status["UnderHordago"]:
                state_text = "Hord'ago !"
            else:
                state_text = "Paris en cours : {}\n".format(state_status["Bid"])
                if state_status["Offer"]:
                    state_text += "Proposition : {}".format(state_status["Bid"] + state_status["Offer"])

            state_text = urwid.Text(state_text)
            rows += (state_text, )

        return urwid.Pile(rows)

    def display_waiting_room(self, answer):
        columns = [0, 0]
        for team in answer['teams']:
            team_id = team['team_id']

            text = "Team #{}:\n".format(team_id + 1)
            for player in team['players']:
                text += str(player) + '\n'

            columns[team_id] = urwid.Text(text)

        team_columns = urwid.Columns(columns)
        return team_columns

    def _send_server(self, data):
        prompt = deque(data.split(" "))

        cmd = prompt.popleft()
        if not cmd:
            return
        if cmd == "_register":
            self.player_id = prompt.popleft()
            if self.old_state != "waiting_room":
                return self._send_server("get_cards")

        kwargs = {"game_id": self.game_id}
        if self.player_id is not None:
            kwargs["player_id"] = self.player_id

        properties_args = {"reply_to": self.incoming_channel_name}


        if cmd in self.intercepted_answer:
            correlation_id = str(uuid.uuid4())
            self.intercepted_answer[cmd] = correlation_id
            properties_args["correlation_id"] = correlation_id

        while len(prompt):
            argument, value = prompt.popleft().split("=")
            kwargs[argument] = json.loads(value)

        with PikaConnection() as (conn, chan):
            chan.basic_publish(
                exchange='',
                properties=pika.BasicProperties(**properties_args),
                routing_key='welcome',
                body=json.dumps((cmd, kwargs)))

        self.frame.header = urwid.Text("just send " + str(data))


def main():
    UrwidTUI().start()


if __name__ == "__main__":
    main()
