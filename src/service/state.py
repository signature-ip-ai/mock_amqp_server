import os
import json
import asyncio
import logging

from collections import deque
from random import randint

from service.exchange import Exchange
from service.queue import Queue
from service.consumer import Consumer
from service.message import Message


DEFAULT_USER = os.environ.get('DEFAULT_USER', 'user')
DEFAULT_PASSWORD = os.environ.get('DEFAULT_PASSWORD', 'password')


class WaitTimeout(Exception):
    pass


class State:
    def __init__(self):
        self.reset()


    def reset(self):
        self._users = {
            DEFAULT_USER: DEFAULT_PASSWORD,
        }

        self._exchanges = {
            # the anonymous default exchange is defined by AMQP 0.9.1
            '': Exchange(exchange_type='direct', messages=deque())
        }

        self._queues: dict[str, Queue] = {}
        self._queues_bound_exchanges = {}
        self._authentication_tried_on = {}
        self._message_acknowledged = set()
        self._message_not_acknowledged = set()
        self._message_requeued = set()


    def to_json(self):
        exchanges_dict = {
            key: {
                'type': value.exchange_type,
                'messages': list(value.messages),
            }
            for key, value in self._exchanges.items()
        }

        return json.dumps({
            'users': self._users,
            'exchanges': exchanges_dict,
            'queues': self._queues,
            'queues_bound_exchanges': self._queues_bound_exchanges,
            'authentication_tried_on': self._authentication_tried_on,
            'messages_acknowledged': list(self._message_acknowledged),
            'messages_not_acknowledged': list(self._message_not_acknowledged),
            'messages_requeued': list(self._message_requeued),
        })


    def check_credentials(self, username, password):
        is_authenticated = self._users.get(username, None) == password

        # we "log" it for instrumentation purpose
        self._authentication_tried_on[username] = is_authenticated
        return is_authenticated


    def declare_exchange(self, exchange_name, exchange_type):
        if exchange_name not in self._exchanges:
            logging.info(f"[state] declared exchange: {exchange_name}, type: {exchange_type}")

            self._exchanges[exchange_name] = Exchange(exchange_type=exchange_type, messages=deque())
            return True

        # if redeclared with a different type => error
        return self._exchanges[exchange_name].exchange_type == exchange_type


    def declare_queue(self, queue_name):
        if queue_name not in self._queues:
            logging.info(f"[state] new queue: {queue_name}")
            self._queues[queue_name] = Queue(messages=deque(), consumers={})

            # AMQP 0.9.1 defines that by default all queues are bound to the default
            # exchange
            self.bind_queue(queue_name, with_exchange='', routing_key='')

        return (
            True,  # ok
            0,  # message count
            0,  # consumer count
        )


    def bind_queue(self, queue_name, with_exchange, routing_key):
        exchange = self._exchanges.get(with_exchange, None)
        if None is exchange:
            return False

        queue = self._queues.get(queue_name, None)
        if None is queue:
            return False

        logging.info(f"Bound Queue: {queue_name}, to exchange: {with_exchange}, with routing key: {routing_key}")

        exchange.bind_queue(routing_key=routing_key, queue=queue)
        return True


    def register_consumer(self, consumer_protocol, consumer_tag, queue_name, channel_number):
        queue = self._queues.get(queue_name, None)
        if None is queue:
            return False

        logging.info(f"Consumer registered on queue: {queue_name}")
        queue.consumers[consumer_tag] = Consumer(protocol=consumer_protocol, channel_number=channel_number)
        return True


    def pop_messages_from_queue(self, queue_name, num_of_messages = 1):
        queue = self._queues.get(queue_name, None)
        if queue is None:
            raise ValueError(f"Attempting to read message from a non-existent queue {queue_name}")

        popped_messages = []

        try:
            for _ in range(num_of_messages):
                popped_messages.append(queue.messages.popleft())

        except IndexError:
            pass

        return popped_messages


    def store_message(self, exchange_name, routing_key, headers, message_data):
        """ Store message for as queued by publisher """

        exchange = self._exchanges.get(exchange_name, None)
        if None is exchange:
            return False

        logging.info(f"Store message in exchange: {exchange_name}")
        logging.info(f"With routing key: {routing_key}")
        logging.info(f"Message Header: {headers}")
        logging.info(f"Message Data: {message_data}")

        queue = exchange.get_queue(routing_key)
        if None is queue:
            return False

        queue.messages.append(Message(headers=headers, body=message_data))
        return True


    def publish_message(self, exchange_name, headers, message_data, is_binary: bool = False):
        """Publish message to a worker without storing it."""

        if exchange_name not in self._exchanges:
            return None

        logging.info(f"[state] publish message exchange_name: {exchange_name}")

        message = Message(headers=headers, body=message_data)
        self._exchanges[exchange_name].messages.append(message)

        queues = self._queues_bound_exchanges.get(exchange_name, set())

        for queue_name in queues:
            consumers = self._queues[queue_name].consumers

            dead_consumers = []
            delivery_tag = None

            for consumer_tag, consumer in consumers.items():
                delivery_tag = randint(1, 2**31)

                # we clean dead connections, otherwise they will
                # accumulate, and you will see some
                # "socket.send() raised exception" in the logs see:
                # https://github.com/allan-simon/mock-amqp-server/issues/5
                if consumer.protocol.transport.is_closing():
                    # we can't delete them directly as we're iterating
                    # over the dictionary
                    dead_consumers.append(consumer_tag)
                    continue

                consumer.protocol.push_message(
                    headers,
                    message_data.encode('utf8') if not is_binary else message_data,
                    consumer.channel_number,
                    consumer_tag,
                    delivery_tag,
                    exchange_name,
                )
                # a message is only sent to one consumer per queue
                break

            # we clean dead consumers' connection
            for consumer_tag in dead_consumers:
                logging.info("dead consumer cleaned")
                del consumers[consumer_tag]

            # Need to support several delivery_tag
            # if exchange is plugged to several queues
            return delivery_tag


    def publish_message_in_queue(self, queue_name, headers, message_data, is_binary: bool = False):
        """Publish message to a worker without storing it."""

        if queue_name not in self._queues:
            return None

        logging.info(f"[state] publish message directly in queue: {queue_name}")

        message = Message(headers=headers, body=message_data)
        self._queues[queue_name].messages.append(message)

        consumers = self._queues[queue_name].consumers

        dead_consumers = []
        delivery_tag = None
        for consumer_tag, consumer in consumers.items():
            delivery_tag = randint(1, 2**31)

            # we clean dead connections, otherwise they will
            # accumulate, and you will see some
            # "socket.send() raised exception" in the logs see:
            # https://github.com/allan-simon/mock-amqp-server/issues/5
            if consumer.protocol.transport.is_closing():
                # we can't delete them directly as we're iterating
                # over the dictionary
                dead_consumers.append(consumer_tag)
                continue

            consumer.protocol.push_message(
                headers,
                message_data.encode('utf8') if not is_binary else message_data,
                consumer.channel_number,
                consumer_tag,
                delivery_tag,
                'dummy-exchange',
            )
            # a message is only sent to one consumer per queue
            break

        # we clean dead consumers' connection
        for consumer_tag in dead_consumers:
            logging.info("dead consumer cleaned")
            del consumers[consumer_tag]

        return delivery_tag


    def message_ack(self, delivery_tag):
        self._message_acknowledged.add(delivery_tag)


    def message_nack(self, delivery_tag, requeue: bool = False):
        if requeue:
            self._message_requeued.add(delivery_tag)
        else:
            self._message_not_acknowledged.add(delivery_tag)


    def process_messages_in_queues(self):
        for _, queue in self._queues.items():
            for consumer_tag, consumer in queue.consumers.items():
                delivery_tag = 1

                if consumer.protocol.transport.is_closing():
                    continue

                for message in queue.messages:
                    consumer.protocol.push_message(
                        message.headers,
                        message.body,
                        consumer.channel_number,
                        consumer_tag,
                        delivery_tag,
                        'dummy-exchange')

                    delivery_tag = delivery_tag + 1

            queue.messages = deque()


    async def process_messages(self):
        while True:
            self.process_messages_in_queues()
            await asyncio.sleep(1)
