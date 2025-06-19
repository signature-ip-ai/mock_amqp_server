#!/bin/env python3

from mock_amqp_server.server import run_server
from mock_amqp_server.state import State

global_state = State()


def initialize_server(host, port):
    run_server(
        global_state=global_state,
        host=host,
        port=port,
        start_backend=False)


def pop_message_from_queue(queue_name) -> list:
    messages = global_state.pop_messages_from_queue(queue_name=queue_name)
    messages = [ message.body for message in messages ]
    return messages[0]


def pop_messages_from_queue(queue_name, num_of_messages) -> list:
    messages = global_state.pop_messages_from_queue(queue_name=queue_name, num_of_messages=num_of_messages)
    messages = [ message.body for message in messages ]
    return messages


def insert_message_to_exchange(exchange_name, routing_key, message_data):
    global_state.store_message(
        exchange_name=exchange_name,
        routing_key=routing_key,
        headers={},
        message_data=message_data)
