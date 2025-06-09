#!/bin/env python3

import logging
import traceback
import asyncio

from .protocol import TrackerProtocol
from .state import State


def _exception_handler(loop, context):
    exception = context['exception']
    # see https://stackoverflow.com/questions/9555133
    traceback_list = traceback.format_exception(
        None,  # <- type(e) by docs, but ignored
        exception,
        exception.__traceback__,
    )

    for line in traceback_list:
        logging.debug(line)


def run_server(global_state = State(), host = '0.0.0.0', port = 5672):
    loop = asyncio.get_event_loop()
    loop.set_exception_handler(_exception_handler)

    coroutine = loop.create_server(
        lambda: TrackerProtocol(
            global_state,
        ),
        host=host,
        port=port
    )

    server = loop.run_until_complete(coroutine)

    try:
        logging.info("Started AMQP Server at 0.0.0.0:5672")
        loop.run_forever()

    except KeyboardInterrupt:
        pass

    logging.info("Tear-down server, closing connection")
    server.close()
    loop.run_until_complete(server.wait_closed())
    loop.close()
