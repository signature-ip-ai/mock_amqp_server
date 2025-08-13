#!/bin/env python3

import logging
import traceback
import asyncio
import threading

from mock_amqp_server.protocol import TrackerProtocol
from mock_amqp_server.state import State


class ServiceController(object):
    def __init__(self, host = '0.0.0.0', port = 5672):
        self._event_loop = None
        self._event_loop_thread = None
        self._state = State()
        self._host = host
        self._port = port
        self._server: asyncio.Server = None
        self._backend_process: asyncio.Task = None


    def start_server(self):
        self._initialize_server()
        self._event_loop_thread = threading.Thread(target=self._run_server)
        self._event_loop_thread.start()


    def stop_server(self, timeout_seconds = 0.5):
        logging.info("Tear-down server, closing connection")
        self._event_loop.stop()
        self._event_loop_thread.join()

        self._backend_process.cancel()
        self._server.close()
        self._event_loop.run_until_complete(self._wait_server_close(timeout_seconds))
        self._event_loop.close()


    async def _wait_server_close(self, timeout_seconds):
        try:
            async with asyncio.timeout(timeout_seconds):
                await self._server.wait_closed()

        except asyncio.TimeoutError:
            logging.info("Server close operation timed out")


    def start_standalone_server(self):
        self._initialize_server()
        self._run_standalone_server()


    def get_state(self):
        return self._state


    def get_event_loop(self):
        return self._event_loop


    def _initialize_server(self):
        self._event_loop = asyncio.new_event_loop()
        amqp_server = self._event_loop.create_server(
            lambda: TrackerProtocol(
                self._state,
            ),
            host=self._host,
            port=self._port
        )

        self._server = self._event_loop.run_until_complete(amqp_server)
        self._backend_process = self._event_loop.create_task(coro=self._state.process_messages())


    def _run_standalone_server(self):
        try:
            logging.info(f"Started AMQP Server at {self._host}:{self._port}")
            self._event_loop.run_forever()

        except KeyboardInterrupt:
            logging.info("Stopping service due to Keyboard Interrupt")

        except Exception as exception: # pylint: disable=broad-exception-caught
            traceback.print_exc()
            logging.error(f"Stopping service due to {exception}")

        finally:
            self._backend_process.cancel()
            self._server.close()
            self._event_loop.run_until_complete(self._server.wait_closed())
            self._event_loop.close()


    def _run_server(self):
        try:
            logging.info(f"Started AMQP Server at {self._host}:{self._port}")
            self._event_loop.run_forever()

        except Exception as exception: # pylint: disable=broad-exception-caught
            traceback.print_exc()
            logging.error(f"Stopping service due to {exception}")
