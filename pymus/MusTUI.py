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
        connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
        channel = connection.channel()

        channel.basic_consume(queue=self.incoming_channel_name,
                              on_message_callback=self.handle_answer,
                              auto_ack=True)
        channel.start_consuming()

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


class UrwidTUI:
    programmatic_names = {
        'Waiting Room': 'waiting_room'
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
        self.intercepted_answer = {"add_player": None}
        self.player_id = None
        self.public_player_id = None

    def start(self):
        connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
        self.channel = connection.channel()
        self.channel.queue_declare(queue='welcome')
        self.callback_queue = mp.Queue()

        incoming_channel = self.channel.queue_declare(queue='')
        self.incoming_channel_name = incoming_channel.method.queue

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

        self.channel.basic_publish(
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
                        return

        state_widget = getattr(
            self, "display_" + self.programmatic_names[answer['current_state']])(answer)
        server_prompt = QuestionBox(">", on_user_validation=self._send_server)

        widget_list = urwid.ListBox((state_widget, server_prompt))

        self.frame.body = widget_list
        self.frame.footer = urwid.Text("Connected to game {}, Turn: {}".format(
            self.game_id, answer['current_state']))

    def _send_server(self, data):
        prompt = deque(data.split(" "))

        cmd = prompt.popleft()
        if not cmd:
            return

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
            kwargs[argument] = int(value)

        self.channel.basic_publish(
            exchange='',
            properties=pika.BasicProperties(**properties_args),
            routing_key='welcome',
            body=json.dumps((cmd, kwargs)))

        self.frame.header = urwid.Text("just send " + str(data))

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


def main():
    UrwidTUI().start()


if __name__ == "__main__":
    main()
