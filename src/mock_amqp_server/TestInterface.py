#!/bin/env python3

from mock_amqp_server.ServiceController import ServiceController


class TestInterface(object):
    def __init__(self, host = '0.0.0.0', port = 5672):
        self._controller = ServiceController(host=host, port=port)
        self._state = self._controller.get_state()


    def initialize_server(self):
        self._controller.start_server()


    def teardown_server(self):
        self._controller.stop_server()


    def pop_message_from_queue(self, queue_name) -> list:
        messages = self._state.pop_messages_from_queue(queue_name=queue_name)
        messages = [ message.body for message in messages ]
        return messages[0]


    def pop_messages_from_queue(self, queue_name, num_of_messages) -> list:
        messages = self._state.pop_messages_from_queue(queue_name=queue_name, num_of_messages=num_of_messages)
        messages = [ message.body for message in messages ]
        return messages


    def insert_message_to_exchange(self, exchange_name, routing_key, message_data):
        self._state.store_message(
            exchange_name=exchange_name,
            routing_key=routing_key,
            headers={},
            message_data=message_data)
