#!/bin/env python3

from collections import deque
from service.message import Message


class Exchange(object):
    def __init__(self, exchange_type, messages):
        self.exchange_type = exchange_type
        self.messages: deque[Message] = messages
