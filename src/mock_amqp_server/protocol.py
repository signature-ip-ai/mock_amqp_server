import logging
import traceback
import asyncio

from mock_amqp_server.message_buffer import MessageBuffer
from mock_amqp_server.ChannelState import ChannelState
from mock_amqp_server.ConnectionState import ConnectionState
from mock_amqp_server.Channel import Channel
from mock_amqp_server.serialization import loads
from mock_amqp_server.frame import read_frame
from mock_amqp_server.heartbeat import HeartBeat
from mock_amqp_server.method import MethodIDs
from mock_amqp_server.sender import (
    send_connection_start,
    send_connection_tune,
    send_connection_ok,
    send_connection_close_ok,
    send_heartbeat,
    send_content_header,
    send_content_body,
    send_channel_open_ok,
    send_channel_close_ok,
    send_exchange_declare_ok,
    send_queue_declare_ok,
    send_queue_bind_ok,
    send_basic_qos_ok,
    send_confirm_select_ok,
    send_basic_consume_ok,
    send_basic_deliver,
    send_basic_cancel_ok
)


PROTOCOL_HEADER = b'AMQP\x00\x00\x09\x01'
CE_END_FRAME = b'\xce'

class TrackerProtocol(asyncio.protocols.Protocol):
    """Handle connection and bytes parsing."""

    def __init__(
        self,
        global_state,
    ) -> None:
        """Create a new instance.
        """
        self.transport = None  # type: asyncio.transports.Transport
        self._global_state = global_state

        self._buffer = b''
        self._parser_state = ConnectionState.WAITING_PROTOCOL_HEADER
        self._channels: dict[int, Channel] = {}


    def connection_made(self, transport):
        """Handle new connection """

        logging.info(f"connection_made: {transport}")
        self.transport = transport


    def connection_lost(self, exception):
        if exception is None:
            return

        # see https://stackoverflow.com/questions/9555133
        traceback_list = traceback.format_exception(
            None,  # <- type(e) by docs, but ignored
            exception,
            exception.__traceback__,
        )

        logging.error(traceback_list)


    def data_received(self, data):
        """Treat incoming bytes and handle the state machine.

        State transitions in normal case:

        """

        logging.info("New data_received")

        self._buffer += data

        if self._parser_state == ConnectionState.WAITING_PROTOCOL_HEADER:
            protocol_ok = self._check_protocol_header()
            if not protocol_ok:
                logging.info("protocol_nok")
                return

            logging.info("protocol_ok")
            send_connection_start(self.transport)
            self._parser_state = ConnectionState.WAITING_START_OK
            logging.info("Parser State: ConnectionState.WAITING_START_OK")
            return

        while len(self._buffer) > 0:
            frame_value = read_frame(self._buffer)
            if not frame_value:
                logging.debug("No more complete frame available, wait for next data")
                return

            self._buffer = self._buffer[frame_value.size:]

            if isinstance(frame_value, HeartBeat):
                send_heartbeat(self.transport)
                logging.info("send hearbeat")
                continue

            if frame_value.channel_number != 0:
                self._upsert_channel(frame_value.channel_number)
                self._treat_channel_frame(frame_value)
                continue

            if frame_value.method_id == MethodIDs.CLOSE:
                # TODO: clean the global state
                send_connection_close_ok(self.transport)
                self.transport.close()
                return

            if self._parser_state == ConnectionState.WAITING_START_OK:
                # correct_credentials = self._check_start_ok(frame_value)
                correct_credentials = True

                if not correct_credentials:
                    # TODO: we're supposed to send a connection.close method
                    # https://www.rabbitmq.com/auth-notification.html
                    self.transport.close()
                    return

                logging.info("Credentials accepted")
                send_connection_tune(self.transport)
                self._parser_state = ConnectionState.WAITING_TUNE_OK
                logging.info("Parser State: ConnectionState.WAITING_TUNE_OK")
                return

            if self._parser_state == ConnectionState.WAITING_TUNE_OK:
                if frame_value.method_id != MethodIDs.TUNE_OK:
                    self.transport.close()
                    return
                self._parser_state = ConnectionState.WAITING_OPEN
                continue

            if self._parser_state == ConnectionState.WAITING_OPEN:
                if frame_value.method_id != MethodIDs.OPEN:
                    self.transport.close()
                    return

                open_is_ok = self._check_open(frame_value)
                if not open_is_ok:
                    self.transport.close()
                    return

                send_connection_ok(self.transport)
                self._parser_state = ConnectionState.OPENED
                continue

    def _check_protocol_header(self):
        if len(self._buffer) < len(PROTOCOL_HEADER):
            logging.error("Buffer underflow")
            return False

        if self._buffer != PROTOCOL_HEADER:
            self.transport.close()
            self._buffer = b''
            return False

        self._buffer = b''
        return True


    # TODO: Need to update implementation for crendential validation
    def _check_start_ok(self, method):
        if method.properties['mechanism'] not in ["PLAIN", "AMQPLAIN"]:
            return False

        username = None
        password = None

        if method.properties['mechanism'] == "PLAIN":
            _, username, password = method.properties['response'].split('\x00', 3)

        if method.properties['mechanism'] == "AMQPLAIN":
            _, _, username, _, _, password = loads(
                'soSsoS',
                method.properties['response'].encode('utf-8')
            )[0]  # [0] decoded values, [1] => length decoded

        accepted = self._global_state.check_credentials(
            username,
            password
        )

        return accepted


    def _check_open(self, method):
        # TODO: use callback to check user has access to vhost etc.
        return True


    def _check_channel_open(self, method):
        return True


    def _upsert_channel(self, channel_number):
        if channel_number not in self._channels:
            logging.info(f"new channel: {channel_number}")

            self._channels[channel_number] = Channel(
                state=ChannelState.WAITING_OPEN,
                number=channel_number)


    def _treat_channel_frame(self, frame_value):
        channel = self._channels[frame_value.channel_number]
        channel_number = frame_value.channel_number

        if channel.state == ChannelState.WAITING_OPEN:
            if frame_value.method_id != MethodIDs.CHANNEL_OPEN:
                self.transport.close()
                return

            open_is_ok = self._check_channel_open(frame_value)
            if not open_is_ok:
                self.transport.close()
                return

            send_channel_open_ok(
                self.transport,
                channel_id='42',
                channel_number=channel.number,
            )
            logging.info("send_channel open ok")
            channel.state = ChannelState.OPENED
            return

        if frame_value.method_id == MethodIDs.CHANNEL_CLOSE:
            del self._channels[channel_number]
            send_channel_close_ok(self.transport, channel_number)
            logging.info("closed")
            self.transport.close()
            return

        if channel.state == ChannelState.OPENED:
            if frame_value.method_id == MethodIDs.EXCHANGE_DECLARE:
                # TODO add exchange declare callback

                ok = self._global_state.declare_exchange(
                    frame_value.properties['exchange-name'],
                    frame_value.properties['type'],
                )

                if not ok:
                    self.transport.close()

                send_exchange_declare_ok(
                    self.transport,
                    channel_number,
                )

                logging.info("exchange ok")
                return

            if frame_value.method_id == MethodIDs.QUEUE_DECLARE:
                ok, message_count, consumer_count = self._global_state.declare_queue(
                    frame_value.properties['queue-name'],
                )
                if not ok:
                    self.transport.close()

                send_queue_declare_ok(
                    self.transport,
                    channel_number,
                    frame_value.properties['queue-name'],
                    message_count=message_count,
                    consumer_count=consumer_count,
                )
                logging.info("queue ok")
                return

            if frame_value.method_id == MethodIDs.QUEUE_BIND:
                # TODO add queue bind callback
                ok = self._global_state.bind_queue(
                    queue_name=frame_value.properties['queue-name'],
                    with_exchange=frame_value.properties['exchange-name'],
                    routing_key=frame_value.properties['routing-key']
                )

                if not ok:
                    self.transport.close()
                    return

                send_queue_bind_ok(
                    self.transport,
                    channel_number)

                logging.info("queue bind")
                return

            if frame_value.method_id == MethodIDs.BASIC_QOS:
                # TODO add basic qos callback
                send_basic_qos_ok(
                    self.transport,
                    channel_number,
                )
                logging.info("basic qos")
                return

            if frame_value.method_id == MethodIDs.CONFIRM_SELECT:
                send_confirm_select_ok(
                    self.transport,
                    channel_number,
                )
                logging.info("confirm delivery")
                return

            if frame_value.method_id == MethodIDs.BASIC_PUBLISH:
                logging.info("message published started")
                channel.state = ChannelState.WAITING_HEADER
                channel.exchange = frame_value.properties['exchange-name']
                channel.routing_key = frame_value.properties['routing-key']
                return

            if frame_value.method_id == MethodIDs.BASIC_CONSUME:
                self._global_state.register_consumer(
                    consumer_protocol=self,
                    consumer_tag=frame_value.properties['consumer-tag'],
                    queue_name=frame_value.properties['queue-name'],
                    channel_number=channel_number,
                )

                send_basic_consume_ok(
                    self.transport,
                    channel_number,
                    frame_value.properties['consumer-tag']
                )
                logging.info("basic consume")
                return

            if frame_value.method_id == MethodIDs.BASIC_ACK:
                self._global_state.message_ack(
                    frame_value.properties['delivery-tag']
                )
                return

            if frame_value.method_id == MethodIDs.BASIC_NACK:
                self._global_state.message_nack(
                    frame_value.properties['delivery-tag'],
                    frame_value.properties['requeue'],
                )
                return

            if frame_value.method_id == MethodIDs.BASIC_CANCEL:
                send_basic_cancel_ok(
                    self.transport,
                    channel_number,
                    frame_value.properties['consumer-tag']
                )
                return

        if channel.state == ChannelState.WAITING_HEADER:
            if not frame_value.is_header:
                return

            channel.on_going_message = MessageBuffer(headers=frame_value)
            channel.state = ChannelState.WAITING_BODY

        if channel.state == ChannelState.WAITING_BODY:
            if not frame_value.is_body:
                return

            message_buffer = channel.on_going_message
            message_buffer.add_content(frame_value.content)
            if not message_buffer.is_complete():
                return

            ok = self._global_state.store_message(
                exchange_name=channel.exchange,
                routing_key=channel.routing_key,
                headers=message_buffer.headers.properties,
                message_data=message_buffer.content)

            if not ok:
                self.transport.close()
                return

            channel.on_going_message = None
            channel.state = ChannelState.OPENED


    def push_message(self, headers, message, channel_number, consumer_tag, delivery_tag, exchange_name):
        send_basic_deliver(
            self.transport,
            channel_number,
            consumer_tag,
            delivery_tag,
            False,
            exchange_name,
            '')

        send_content_header(
            self.transport,
            channel_number,
            headers,
            body_size=len(message))

        send_content_body(
            self.transport,
            channel_number,
            message)

        logging.info("sent")
