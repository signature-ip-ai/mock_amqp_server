#!/bin/env python3

from service.server import run_server
from service.state import State

global_state = State()


def initialize_server(host, port):
    run_server(
        global_state=global_state,
        host=host,
        port=port)


def pop_messages_from_queue(queue_name) -> list:
    pass
