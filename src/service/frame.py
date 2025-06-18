import logging
import struct
from service.method import Method
from service.method import Header
from service.method import Body
from service.heartbeat import HeartBeat

_FRAME_HEADER_SIZE = 7
_FRAME_END_SIZE = 1

_FRAME_END = b'\xce'

_FRAME_METHOD = 1
_FRAME_HEADER = 2
_FRAME_BODY = 3
_FRAME_HEARTBEAT = 8


class InvalidFrameError(Exception):
    pass


def read_frame(frame_buffer):
    # Extracted from pika's library and slightly adapted
    logging.info("Check for new frame")

    try:
        (
            frame_type,
            channel_number,
            payload_size,
        ) = struct.unpack('>BHL', frame_buffer[0:7])

    except struct.error as error:
        logging.error("Struct unpacking error")
        raise InvalidFrameError("Invalid frame format") from error

    frame_size = _FRAME_HEADER_SIZE + payload_size + _FRAME_END_SIZE
    logging.info(f"New frame detected with size: {frame_size}")

    # We don't have all of the frame yet
    if frame_size > len(frame_buffer):
        logging.warning(f"No enough data frame_size={frame_size}, data length={len(frame_buffer)}")
        return None

    # The Frame termination chr is wrong
    if frame_buffer[frame_size - 1:frame_size] != _FRAME_END:
        raise InvalidFrameError("Invalid FRAME_END marker")

    # Get the raw frame data
    payload = frame_buffer[_FRAME_HEADER_SIZE:frame_size - 1]

    if frame_type == _FRAME_METHOD:
        # Get the Method ID from the frame data
        method_id = struct.unpack_from('>I', payload)[0]
        logging.info(f"Frame Type: _FRAME_METHOD, channel_number: {channel_number}, method_id: {hex(method_id)}")

        return Method(
            channel_number,
            frame_size,
            method_id,
            payload)

    if frame_type == _FRAME_HEARTBEAT:
        logging.info("Frame Type: _FRAME_HEARTBEAT")
        return HeartBeat(frame_size)

    if frame_type == _FRAME_HEADER:
        (
            class_id,
            _weight,  # unused
            body_size,
            property_flags,
        ) = struct.unpack('>HHQH', payload[0:14])

        logging.info(f"Frame Type: _FRAME_HEADER, channel_number: {channel_number} class_id: {hex(class_id)}")

        return Header(
            channel_number,
            frame_size,
            class_id,
            body_size,
            property_flags,
            payload)

    if frame_type == _FRAME_BODY:
        logging.info(f"Frame Type: _FRAME_BODY, channel_number: {channel_number}")

        return Body(
            channel_number,
            frame_size,
            payload)
