#!/bin/env python3

from service.protocol import TrackerProtocol


class Consumer(object):
    def __init__(self, protocol, channel_number):
        self.protocol: TrackerProtocol = protocol
        self.channel_number: int = channel_number
