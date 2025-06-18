#!/bin/env python3

from enum import IntEnum


class ConnectionState(IntEnum):
    """State of the parsing state machine."""

    WAITING_PROTOCOL_HEADER = 1
    WAITING_START_OK = 2
    WAITING_TUNE_OK = 3
    WAITING_OPEN = 4
    OPENED = 5

    WAITING_OTHER = 999
