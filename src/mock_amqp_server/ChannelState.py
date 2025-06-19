#!/bin/env python3

from enum import IntEnum


class ChannelState(IntEnum):
    WAITING_OPEN = 1
    OPENED = 2
    WAITING_HEADER = 3
    WAITING_BODY = 4
