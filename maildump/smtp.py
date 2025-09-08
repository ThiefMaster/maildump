from email.parser import BytesParser

from logbook import Logger

from maildump.db import add_message
from aiosmtpd.controller import Controller

log = Logger(__name__)



# aiosmtpd handler class
class SMTPHandler:
    def __init__(self, handler_func):
        self._handler = handler_func

    async def handle_DATA(self, server, session, envelope):
        # envelope.content is bytes
        result = self._handler(
            sender=envelope.mail_from,
            recipients=envelope.rcpt_tos,
            body=envelope.content
        )
        return '250 Message accepted for delivery'


def start_smtp_server(host, port, handler_func):
    handler = SMTPHandler(handler_func)
    controller = Controller(handler, hostname=host, port=port)
    controller.start()
    return controller


def smtp_handler(sender, recipients, body):
    message = BytesParser().parsebytes(body)
    log.info("Received message from '{}' ({} bytes)".format(message['from'] or sender, len(body)))
    add_message(sender, recipients, body, message)
