from email.parser import BytesParser

import smtpd
from logbook import Logger

from maildump.db import add_message

log = Logger(__name__)


class SMTPServer(smtpd.SMTPServer):
    def __init__(self, listener, handler):
        super().__init__(listener, None)
        self._handler = handler

    def process_message(self, peer, mailfrom, rcpttos, data, **kwargs):
        return self._handler(sender=mailfrom, recipients=rcpttos, body=data)


def smtp_handler(sender, recipients, body):
    message = BytesParser().parsebytes(body)
    log.info("Received message from '{}' ({} bytes)".format(message['from'] or sender, len(body)))
    add_message(sender, recipients, body, message)
