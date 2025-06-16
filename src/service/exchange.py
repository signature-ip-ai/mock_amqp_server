#!/bin/env python3

from collections import deque
from service.message import Message
from service.queue import Queue


class Exchange(object):
    def __init__(self, exchange_type, messages):
        self.exchange_type = exchange_type
        self.messages: deque[Message] = messages
        self._bound_queues = {}


    def bind_queue(self, routing_key, queue: Queue):
        if routing_key in self._bound_queues:
            return

        self._bound_queues[routing_key] = queue


    def get_queue(self, routing_key) -> Queue:
        return self._bound_queues.get(routing_key, None)
