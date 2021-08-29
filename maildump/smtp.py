import base64
import smtpd
from email.parser import BytesParser

from logbook import Logger

from maildump.db import add_message

log = Logger(__name__)


class SMTPChannel(smtpd.SMTPChannel):
    def __init__(self, server, conn, addr, smtp_auth, data_size_limit=smtpd.DATA_SIZE_DEFAULT,
        map=None, enable_SMTPUTF8=False, decode_data=False):
        super(SMTPChannel, self).__init__(server, conn, addr, data_size_limit, map, enable_SMTPUTF8, decode_data)
        self._smtp_auth = smtp_auth
        self._authorized = False

    def is_valid_user(self, auth_data):
        auth_data_parts = auth_data.split(b'\x00')
        if len(auth_data_parts) != 3:
            return False

        if not auth_data.startswith(b'\x00') and auth_data_parts[0] != auth_data_parts[1]:
            return False

        return self._smtp_auth.check_password(auth_data_parts[1], auth_data_parts[2])

    def smtp_EHLO(self, arg):
        if not arg:
            self.push('501 Syntax: EHLO hostname')
            return
        # See issue #21783 for a discussion of this behavior.
        if self.seen_greeting:
            self.push('503 Duplicate HELO/EHLO')
            return
        self._set_rset_state()
        self.seen_greeting = arg
        self.extended_smtp = True
        self.push('250-%s' % self.fqdn)
        if self._smtp_auth:
            self.push('250-AUTH PLAIN')
        if self.data_size_limit:
            self.push('250-SIZE %s' % self.data_size_limit)
            self.command_size_limits['MAIL'] += 26
        if not self._decode_data:
            self.push('250-8BITMIME')
        if self.enable_SMTPUTF8:
            self.push('250-SMTPUTF8')
            self.command_size_limits['MAIL'] += 10
        self.push('250 HELP')

    def smtp_AUTH(self, arg):
        print('auth:', arg, file=smtpd.DEBUGSTREAM)
        if not self._smtp_auth:
            self.push('501 Syntax: AUTH not enabled')
            return

        if not arg:
            self.push('501 Syntax: AUTH TYPE base64(username:password)')
            return

        if not arg.lower().startswith('plain '):
            self.push('501 Syntax: only PLAIN auth possible')
            return

        auth_type, auth_data = arg.split(None, 1)
        try:
            auth_data = base64.b64decode(auth_data.strip())
        except TypeError:
            self.push('535 5.7.8 Authentication credentials invalid')
            return

        if self.is_valid_user(auth_data):
            self.push('235 Authentication successful')
            self._authorized = True
            return

        self._authorized = False
        self.push('535 5.7.8 Authentication credentials invalid')

    def smtp_MAIL(self, arg):
        if self._smtp_auth and not self._authorized:
            self.push('530 5.7.0  Authentication required')
            return
        super(SMTPChannel, self).smtp_MAIL(arg)

    def smtp_RCPT(self, arg):
        if self._smtp_auth and not self._authorized:
            self.push('530 5.7.0  Authentication required')
            return
        super(SMTPChannel, self).smtp_RCPT(arg)

    def smtp_DATA(self, arg):
        if self._smtp_auth and not self._authorized:
            self.push('530 5.7.0  Authentication required')
            return
        super(SMTPChannel, self).smtp_DATA(arg)


class SMTPServer(smtpd.SMTPServer):
    def __init__(self, listener, handler, smtp_auth):
        super(SMTPServer, self).__init__(listener, None)
        self._handler = handler
        self._smtp_auth = smtp_auth

    def handle_accepted(self, conn, addr):
        if self._smtp_auth:
            channel = SMTPChannel(self,
                conn,
                addr,
                self._smtp_auth,
                self.data_size_limit,
                self._map,
                self.enable_SMTPUTF8,
                self._decode_data)
        else:
            super(SMTPServer, self).handle_accepted(conn, addr)

    def process_message(self, peer, mailfrom, rcpttos, data, **kwargs):
        return self._handler(sender=mailfrom, recipients=rcpttos, body=data)


def smtp_handler(sender, recipients, body):
    message = BytesParser().parsebytes(body)
    log.info("Received message from '{0}' ({1} bytes)".format(message['from'] or sender, len(body)))
    add_message(sender, recipients, body, message)
