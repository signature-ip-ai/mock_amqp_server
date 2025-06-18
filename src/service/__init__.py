import logging
from service.server import run_server
from service.log_wrapper import configure_logger

def main():
    configure_logger(level=logging.INFO, log_file_path="mock_amqp_server.log")
    run_server()
