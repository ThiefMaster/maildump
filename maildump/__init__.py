import asyncore

import gevent
from gevent.pywsgi import WSGIServer
from logbook import Logger

from maildump.db import connect, create_tables, disconnect
from maildump.smtp import SMTPServer, smtp_handler
from maildump.web import app

log = Logger(__name__)
stopper = None


def start(http_host, http_port, smtp_host, smtp_port, db_path=None):
    global stopper
    # Webserver
    log.notice('Starting web server on http://{0}:{1}'.format(http_host, http_port))
    http_server = WSGIServer((http_host, http_port), app)
    stopper = http_server.close
    # SMTP server
    log.notice('Starting smtp server on {0}:{1}'.format(smtp_host, smtp_port))
    SMTPServer((smtp_host, smtp_port), smtp_handler)
    gevent.spawn(asyncore.loop)
    # Database
    connect(db_path)
    create_tables()
    http_server.serve_forever()  # runs until stopper is triggered
    log.debug('Received stop signal')
    # Clean up
    disconnect()
    log.notice('Terminating')


def stop():
    stopper()
