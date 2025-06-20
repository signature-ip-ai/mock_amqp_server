#!/bin/env python3

import waiting
from mock_amqp_server.ServiceController import ServiceController


class TestInterface(object):
    def __init__(self, host = '0.0.0.0', port = 5672):
        self._controller = ServiceController(host=host, port=port)
        self._state = self._controller.get_state()
        self._event_loop = self._controller.get_event_loop()


    def initialize_server(self):
        self._controller.start_server()


    def teardown_server(self):
        self._controller.stop_server()


    def pop_message_from_queue(self, queue_name):
        message_future = self._event_loop.create_task(coro=self._state.pop_message_from_queue(queue_name=queue_name))
        waiting.wait(message_future.done)
        return message_future.result()


    def insert_message_to_exchange(self, exchange_name, routing_key, message_data):
        self._event_loop.create_task(
            coro=self._state.insert_message_to_exchange(
                exchange_name=exchange_name,
                routing_key=routing_key,
                message_data=message_data))
