from flask import current_app
from gevent.queue import Empty, Queue

clients = set()


def broadcast(event, data=None):
    for q in clients:
        q.put((event, data))


def handle_sse_request():
    return current_app.response_class(_gen(), mimetype='text/event-stream')


def _gen():
    yield _sse('connected')
    q = Queue()
    clients.add(q)
    while True:
        try:
            msg = q.get(timeout=60)
        except Empty:
            yield _sse('ping')
            continue
        try:
            yield _sse(*msg)
        except GeneratorExit:
            clients.remove(q)
            raise


def _sse(event, data=None):
    parts = [f'event: {event}', f'data: {data or ""}']
    return ('\r\n'.join(parts) + '\r\n\r\n').encode()
