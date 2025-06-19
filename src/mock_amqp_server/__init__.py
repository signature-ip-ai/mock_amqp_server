import logging
from mock_amqp_server.server import run_server
from mock_amqp_server.log_wrapper import configure_logger

def main():
    configure_logger(level=logging.INFO, log_file_path="mock_amqp_server.log")
    run_server()
