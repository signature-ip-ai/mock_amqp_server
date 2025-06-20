import logging
from mock_amqp_server.log_wrapper import configure_logger
from mock_amqp_server.ServiceController import ServiceController


def main():
    configure_logger(level=logging.INFO, log_file_path="mock_amqp_server.log")
    controller = ServiceController()
    controller.start_standalone_server()
