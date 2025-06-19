#!/bin/env python3

import logging
import traceback
import asyncio

from mock_amqp_server.protocol import TrackerProtocol
from mock_amqp_server.state import State


def run_server(global_state = State(), host = '0.0.0.0', port = 5672, start_backend = True):
    event_loop = asyncio.get_event_loop()

    amqp_server = event_loop.create_server(
        lambda: TrackerProtocol(
            global_state,
        ),
        host=host,
        port=port
    )

    server = event_loop.run_until_complete(amqp_server)

    if start_backend:
        event_loop.create_task(coro=global_state.process_messages())

    try:
        logging.info("Started AMQP Server at 0.0.0.0:5672")
        event_loop.run_forever()

    except KeyboardInterrupt:
        logging.info("Stopping service due to Keyboard Interrupt")

    except Exception as exception: # pylint: disable=broad-exception-caught
        traceback.print_exc()
        logging.error(f"Stopping service due to {exception}")

    finally:
        logging.info("Tear-down server, closing connection")
        server.close()
        event_loop.run_until_complete(server.wait_closed())
        event_loop.close()
