#!/bin/env python3

import waiting
from mock_amqp_server.ServiceController import ServiceController


class TestInterface(object):
    def __init__(self, host = '0.0.0.0', port = 5672):
        self._controller = ServiceController(host=host, port=port)
        self._state = self._controller.get_state()
        self._event_loop = None


    def initialize_server(self):
        self._controller.start_server()
        self._event_loop = self._controller.get_event_loop()


    def teardown_server(self, timeout_seconds = 0.5):
        self._controller.stop_server(timeout_seconds)


    def pop_message_from_queue(self, queue_name, timeout_seconds: int | None = None):
        waiting.wait(lambda: None is not self._event_loop)

        message_future = self._event_loop.create_task(
            coro=self._state.pop_message_from_queue(queue_name=queue_name))

        waiting.wait(message_future.done, timeout_seconds=timeout_seconds)
        result_message = message_future.result()
        return result_message.get_body()


    def insert_message_to_exchange(self, exchange_name, routing_key, message_data: bytes):
        waiting.wait(lambda: None is not self._event_loop)

        result = self._event_loop.create_task(
            coro=self._state.insert_message_to_exchange(
                exchange_name=exchange_name,
                routing_key=routing_key,
                message_data=message_data))

        waiting.wait(result.done)
