#!/bin/env python3

from collections import deque

from service.consumer import Consumer
from service.message import Message


class Queue(object):
    def __init__(self, messages, consumers):
        self.messages: deque[Message] = messages
        self.consumers: dict[str, Consumer] = consumers
