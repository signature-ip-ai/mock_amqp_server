#!/bin/env python3

from mock_amqp_server.ChannelState import ChannelState
from mock_amqp_server.message_buffer import MessageBuffer


class Channel(object):
    def __init__(self, state, number):
        self.state: ChannelState = state
        self.number: int = number
        self.exchnage = None
        self.routing_key = None
        self.on_going_message:MessageBuffer = None
