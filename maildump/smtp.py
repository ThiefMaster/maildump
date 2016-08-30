import smtpd
from email.parser import Parser

from logbook import Logger

from maildump.db import add_message


log = Logger(__name__)


class SMTPChannel(smtpd.SMTPChannel):
    def smtp_EHLO(self, arg):
        if not arg:
            self.push('501 Syntax: EHLO hostname')
        elif self.__greeting:
            self.push('503 Duplicate HELO/EHLO')
        else:
            self.push('250 %s' % self.__fqdn)


class SMTPServer(smtpd.SMTPServer, object):
    def __init__(self, listener, handler):
        super(SMTPServer, self).__init__(listener, None)
        self._handler = handler

    def process_message(self, peer, mailfrom, rcpttos, data):
        return self._handler(sender=mailfrom, recipients=rcpttos, body=data)

    def handle_accept(self):
        conn, addr = self.accept()
        channel = SMTPChannel(self, conn, addr)


def smtp_handler(sender, recipients, body):
    message = Parser().parsestr(body)
    log.info("Received message from '{0}' ({1} bytes)".format(message['from'] or sender, len(body)))
    add_message(sender, recipients, body, message)
