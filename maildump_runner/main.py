import argparse
import os
import signal
import sys
from pathlib import Path

import lockfile
import logbook
from daemon.pidfile import TimeoutPIDLockFile
from logbook import NullHandler
from logbook.more import ColorizedStderrHandler

from .geventdaemon import GeventDaemonContext


def read_pidfile(path):
    try:
        return int(Path(path).read_text())
    except Exception as e:
        raise ValueError(e.message)


def terminate_server(sig, frame):
    from maildump import stop

    if sig == signal.SIGINT and os.isatty(sys.stdout.fileno()):
        # Terminate the line containing ^C
        print()
    stop()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--smtp-ip', default='127.0.0.1', metavar='IP', help='SMTP ip (default: 127.0.0.1)')
    parser.add_argument('--smtp-port', default=1025, type=int, metavar='PORT', help='SMTP port (default: 1025)')
    parser.add_argument('--http-ip', default='127.0.0.1', metavar='IP', help='HTTP ip (default: 127.0.0.1)')
    parser.add_argument('--http-port', default=1080, type=int, metavar='PORT', help='HTTP port (default: 1080)')
    parser.add_argument('--db', metavar='PATH', help='SQLite database - in-memory if missing')
    parser.add_argument('--htpasswd', metavar='HTPASSWD', help='Apache-style htpasswd file')
    parser.add_argument('-v', '--version', help='Display the version and exit', action='store_true')
    parser.add_argument(
        '-f',
        '--foreground',
        help='Run in the foreground (default if no pid file is specified)',
        action='store_true',
    )
    parser.add_argument('-d', '--debug', help='Run the web app in debug mode', action='store_true')
    parser.add_argument(
        '-n',
        '--no-quit',
        help='Do not allow clients to terminate the application',
        action='store_true',
    )
    parser.add_argument('-p', '--pidfile', help='Use a PID file')
    parser.add_argument('--stop', help='Sends SIGTERM to the running daemon (needs --pidfile)', action='store_true')
    args = parser.parse_args()

    if args.version:
        from maildump.util import get_version

        print(f'MailDump {get_version()}')
        sys.exit(0)

    # Do we just want to stop a running daemon?
    if args.stop:
        if not args.pidfile or not os.path.exists(args.pidfile):
            print('PID file not specified or not found')
            sys.exit(1)
        try:
            pid = read_pidfile(args.pidfile)
        except ValueError as e:
            print(f'Could not read PID file: {e}')
            sys.exit(1)
        try:
            os.kill(pid, signal.SIGTERM)
        except OSError as e:
            print(f'Could not send SIGTERM: {e}')
            sys.exit(1)
        sys.exit(0)

    # Default to foreground mode if no pid file is specified
    if not args.pidfile and not args.foreground:
        print('No PID file specified; runnning in foreground')
        args.foreground = True

    # Warn about relative paths and absolutize them
    if args.db and not os.path.isabs(args.db):
        args.db = os.path.abspath(args.db)
        print(f'Database path is relative, using {args.db}')
    if args.htpasswd and not os.path.isabs(args.htpasswd):
        args.htpasswd = os.path.abspath(args.htpasswd)
        print(f'Htpasswd path is relative, using {args.htpasswd}')

    # Check if the password file is valid
    if args.htpasswd and not os.path.isfile(args.htpasswd):
        print('Htpasswd file does not exist')
        sys.exit(1)

    daemon_kw = {
        'monkey_greenlet_report': False,
        'signal_map': {signal.SIGTERM: terminate_server, signal.SIGINT: terminate_server},
    }

    if args.foreground:
        # Do not detach and keep std streams open
        daemon_kw.update({'detach_process': False, 'stdin': sys.stdin, 'stdout': sys.stdout, 'stderr': sys.stderr})

    pidfile = None
    if args.pidfile:
        pidfile = os.path.abspath(args.pidfile) if not os.path.isabs(args.pidfile) else args.pidfile
        if os.path.exists(pidfile):
            pid = read_pidfile(pidfile)
            if not os.path.exists(os.path.join('/proc', str(pid))):
                print(f'Deleting obsolete PID file (process {pid} does not exist)')
                os.unlink(pidfile)
        daemon_kw['pidfile'] = TimeoutPIDLockFile(pidfile, 5)

    # Unload threading module to avoid error on exit (it's loaded by lockfile)
    if 'threading' in sys.modules:
        del sys.modules['threading']

    context = GeventDaemonContext(**daemon_kw)
    try:
        context.open()
    except lockfile.LockTimeout:
        print(f'Could not acquire lock on pid file {pidfile}')
        print('Check if the daemon is already running.')
        sys.exit(1)
    except KeyboardInterrupt:
        print()
        sys.exit(1)

    with context:
        # Imports are here to avoid importing anything before monkeypatching
        from maildump import start
        from maildump.web import app

        app.debug = args.debug
        app.config['MAILDUMP_HTPASSWD'] = None
        if args.htpasswd:
            # passlib is broken on py39, hence the local import
            # https://foss.heptapod.net/python-libs/passlib/-/issues/115
            try:
                from passlib.apache import HtpasswdFile
            except OSError:
                print('Are you using Python 3.9? If yes, authentication is currently not available due to a bug.\n\n')
                raise
            app.config['MAILDUMP_HTPASSWD'] = HtpasswdFile(args.htpasswd)
        app.config['MAILDUMP_NO_QUIT'] = args.no_quit

        level = logbook.DEBUG if args.debug else logbook.INFO
        format_string = '[{record.time:%Y-%m-%d %H:%M:%S}]  {record.level_name:<8}  {record.channel}: {record.message}'
        stderr_handler = ColorizedStderrHandler(level=level, format_string=format_string)
        with NullHandler().applicationbound():
            with stderr_handler.applicationbound():
                start(args.http_ip, args.http_port, args.smtp_ip, args.smtp_port, args.db)


if __name__ == '__main__':
    main()
