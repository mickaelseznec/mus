#! /usr/bin/env python3
import json
import multiprocessing
import os
import pika
import urwid


class ReceptionProcess(multiprocessing.Process):
    def __init__(self, incoming_channel_name, signal_pipe):
        super().__init__(name="reception_process")
        self.incoming_channel_name = incoming_channel_name
        self.signal_pipe = signal_pipe

    def run(self):
        connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
        channel = connection.channel()

        channel.basic_consume(queue=self.incoming_channel_name,
                              on_message_callback=self.handle_answer,
                              auto_ack=True)
        channel.start_consuming()

    def handle_answer(self, ch, method, properties, body):
        answer = json.loads(body)
        print(" [x] Received {}".format(answer))
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
    def __init__(self):
        header = urwid.Text("pymus client")
        footer = urwid.Divider()

        self.body = urwid.ListBox(
            [QuestionBox("Pleaser enter the room name\n", on_user_validation=self._join_room)])

        self.frame = urwid.Frame(self.body, header, footer)

        self.loop = urwid.MainLoop(self.frame, unhandled_input=self._exit_on_q)
        self.callback_pipe = self.loop.watch_pipe(handle_new_data_from_server)

    def start(self):
        connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
        self.channel = connection.channel()
        self.channel.queue_declare(queue='welcome')

        incoming_channel = self.channel.queue_declare(queue='')
        self.incoming_channel_name = incoming_channel.method.queue

        self.reception_process = ReceptionProcess(self.incoming_channel_name, self.callback_pipe)
        self.reception_process.start()

        self.loop.run()

        self.reception_process.kill()
        self.reception_process.join()

    def _exit_on_q(self, key):
        if key in ('q', 'Q'):
            raise urwid.ExitMainLoop()

    def _join_room(self, text):
        self.channel.basic_publish(
            exchange='',
            properties=pika.BasicProperties(reply_to=self.incoming_channel_name),
            routing_key='welcome',
            body=json.dumps(("register", {"game_id": text})))

    def handle_new_data_from_server(self):
        print("Triggered!")


def main():
    UrwidTUI().start()


if __name__ == "__main__":
    main()
