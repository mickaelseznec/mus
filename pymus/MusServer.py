#! /usr/bin/env python3
import pickle
import pika
import redis
import json
import time

from PyMus import Game

def get_game(game_id):
    redis_db = redis.StrictRedis('localhost')
    game = redis_db.get(game_id)

    if game is None:
        game = Game()
    else:
        game = pickle.loads(game)

    return game

def save_game(game_id, game):
    redis_db = redis.StrictRedis('localhost')
    redis_db.set(game_id, pickle.dumps(game))

class MessageQueueServer:
    def __init__(self):
        self.connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
        self.channel = self.connection.channel()
        self.channel.queue_declare(queue='welcome')

        self.channel.basic_consume(queue='welcome',
                                   on_message_callback=self.handle_message,
                                   auto_ack=True)

    def run(self):
        print(' [*] Waiting for messages. To exit press CTRL+C')
        self.channel.start_consuming()

    def handle_message(self, ch, method, properties, body):
        action, kwargs = json.loads(body)
        print(" [x] Received '{}' with args: {}".format(action, kwargs))

        game_id = kwargs.pop("game_id")

        if action == "register":
            game = get_game(game_id)
            game_status = game.status()

            print("Registering {} to exchange {}".format(properties.reply_to, game_id))
            self.channel.exchange_declare(exchange=game_id, exchange_type='fanout')
            self.channel.queue_bind(exchange=game_id, queue=properties.reply_to)

            self.channel.basic_publish(exchange='',
                                       routing_key=properties.reply_to,
                                       body=json.dumps(game_status))
        else:
            game = get_game(game_id)
            game_answer = game.do((action, kwargs))
            save_game(game_id, game)

            cmd_status = game_answer["status"]
            if cmd_status != "OK":
                print("Die with", cmd_status)
            else:
                result, game_status = game_answer["result"], game_answer["state"]
                print("Result: ", result)

                if result is not None:
                    self.channel.basic_publish(exchange='',
                                               properties=pika.BasicProperties(
                                                   correlation_id=properties.correlation_id),
                                               routing_key=properties.reply_to,
                                               body=json.dumps(result))

                print("Status: ", game_status)
                self.channel.basic_publish(exchange=game_id, routing_key='', body=json.dumps(game_status))


def main():
    queue_server = MessageQueueServer()
    queue_server.run()


if __name__ == "__main__":
    main()


