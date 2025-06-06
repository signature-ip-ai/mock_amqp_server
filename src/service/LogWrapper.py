#!/bin/env python3

import sys
import logging
import threading

__console_log_format='%(asctime)s [TID %(thread_id)d][%(levelname)s][%(filename)s] %(message)s'
__file_log_format='%(asctime)s [TID %(thread_id)d][%(levelname)s][%(filename)s:%(lineno)s - %(funcName)s()] %(message)s'
__log_datetime_format = '%m/%d/%Y %I:%M:%S %p'


def configure_logger(level, stream = sys.stderr, log_file_path = None) -> None:
    handlers = [
        __enable_console_handler(level=level, stream=stream),
    ]

    if log_file_path:
        handlers.append(__enable_file_handler(level=level, log_file_path=log_file_path))

    logging.basicConfig(level=level, handlers=handlers, force=True)


def __thread_id_filter(record):
    record.thread_id = threading.get_native_id()
    return record


def __enable_console_handler(level, stream = sys.stderr):
    console_handler = logging.StreamHandler(stream=stream)
    console_handler.setFormatter(logging.Formatter(fmt=__console_log_format, datefmt=__log_datetime_format))
    console_handler.setLevel(level)
    console_handler.addFilter(__thread_id_filter)
    return console_handler


def __enable_file_handler(level, log_file_path):
    file_handler = logging.FileHandler(filename=log_file_path)
    file_handler.setFormatter(logging.Formatter(fmt=__file_log_format, datefmt=__log_datetime_format))
    file_handler.setLevel(level)
    file_handler.addFilter(__thread_id_filter)
    return file_handler
