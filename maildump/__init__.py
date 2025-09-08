from gevent.pywsgi import WSGIServer
from logbook import Logger

from maildump.db import connect, create_tables, disconnect
from maildump.smtp import start_smtp_server, smtp_handler
from maildump.web import app

log = Logger(__name__)
stopper = None
smtp_controller = None


def start(http_host, http_port, smtp_host, smtp_port, db_path=None):
    global stopper, smtp_controller
    # Webserver
    log.notice(f'Starting web server on http://{http_host}:{http_port}')
    http_server = WSGIServer((http_host, http_port), app)
    stopper = http_server.close
    # SMTP server
    log.notice(f'Starting smtp server on {smtp_host}:{smtp_port}')
    smtp_controller = start_smtp_server(smtp_host, smtp_port, smtp_handler)
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
