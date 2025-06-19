#!/bin/env python3

from collections import deque

from mock_amqp_server.consumer import Consumer
from mock_amqp_server.message import Message


class Queue(object):
    def __init__(self, messages, consumers):
        self.messages: deque[Message] = messages
        self.consumers: dict[str, Consumer] = consumers
