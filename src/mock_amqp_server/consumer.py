#!/bin/env python3

from mock_amqp_server.protocol import TrackerProtocol


class Consumer(object):
    def __init__(self, protocol, channel_number):
        self.protocol: TrackerProtocol = protocol
        self.channel_number: int = channel_number
