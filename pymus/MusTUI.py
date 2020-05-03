#! /usr/bin/env python3
import json
import pika
import threading
import time
import urwid
import uuid

def handle_answer(ch, method, properties, body):
    action, kwargs = json.loads(body)
    print(" [x] Received '{}' with args: {}".format(action, kwargs))


def receiver(result_queue_name):
    print("Start receiver thread")
    connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
    channel = connection.channel()
    channel.queue_declare(queue='welcome')

    channel.basic_consume(queue=result_queue_name,
                          on_message_callback=handle_answer,
                          auto_ack=True)
    channel.start_consuming()

def sender(channel, result_queue_name):

    while True:
        time.sleep(2)

        channel.basic_publish(exchange='', routing_key='welcome',
                              properties=pika.BasicProperties(reply_to=result_queue_name),
                              body=json.dumps(("prout", {"game_id": "lemusdesbgs"})))
        print("Sending a prout...")

def exit_on_q(key):
    if key in ('q', 'Q'):
        raise urwid.ExitMainLoop()

class QuestionBox(urwid.Filler):
    def keypress(self, size, key):
        if key != 'enter':
            return super(QuestionBox, self).keypress(size, key)
        self.original_widget = urwid.Text(
            u"Nice to meet you, %s.\n\nPress Q to exit." %
            self.original_widget.edit_text)

def main():
    connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
    channel = connection.channel()
    channel.queue_declare(queue='welcome')

    receive_channel = channel.queue_declare(queue='')
    result_queue_name = receive_channel.method.queue

    channel.basic_publish(exchange='',
                          properties=pika.BasicProperties(reply_to=result_queue_name),
                          routing_key='welcome',
                          body=json.dumps(("register", {"game_id": "lemusdesbgs"})))

    rec_thread = threading.Thread(target=receiver, args=(result_queue_name, ))
    rec_thread.start()

    edit = urwid.Edit(u"What is your name?\n")
    fill = QuestionBox(edit)
    loop = urwid.MainLoop(fill, unhandled_input=exit_on_q)
    loop.run()

    sender(channel, result_queue_name)

    rec_thread.join()


    # channel.basic_publish(exchange='',
    #                       routing_key='welcome',
    #                       properties=pika.BasicProperties(reply_to=result_queue_name),
    #                       body=json.dumps(("join", {"game_id": "lemusdesbgs"})))


if __name__ == "__main__":
    main()
