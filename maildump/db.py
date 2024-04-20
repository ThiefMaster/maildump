import json
import sqlite3
import uuid

from logbook import Logger

from maildump.util import decode_header, split_addresses
from maildump.web_realtime import broadcast

log = Logger(__name__)
_conn = None


def connect(db=None):
    global _conn
    db = db or ':memory:'
    log.info(f'Using database {db}')
    _conn = sqlite3.connect(db, detect_types=sqlite3.PARSE_DECLTYPES)
    _conn.row_factory = sqlite3.Row
    _conn.text_factory = str


def disconnect():
    global _conn
    if _conn:
        log.debug('Closing database')
        _conn.close()
        _conn = None


def create_tables():
    log.debug('Creating tables')
    _conn.execute(
        """
        CREATE TABLE IF NOT EXISTS message (
            id INTEGER PRIMARY KEY ASC,
            sender TEXT,
            recipients TEXT,
            subject TEXT,
            source BLOB,
            size INTEGER,
            type TEXT,
            created_at TIMESTAMP
        )
        """,
    )

    _conn.execute(
        """
        CREATE TABLE IF NOT EXISTS message_part (
            id INTEGER PRIMARY KEY ASC,
            message_id INTEGER NOT NULL,
            cid TEXT,
            type TEXT,
            is_attachment INTEGER,
            filename TEXT,
            charset TEXT,
            body BLOB,
            size INTEGER,
            created_at TIMESTAMP
        )
        """,
    )


def iter_message_parts(message):
    if message.is_multipart():
        for msg in message.get_payload():
            yield from iter_message_parts(msg)
    else:
        yield message


def add_message(sender, recipients, body, message):
    sql = """
        INSERT INTO message
            (sender, recipients, subject, source, type, size, created_at)
        VALUES
            (?, ?, ?, ?, ?, ?, datetime('now'))
    """

    to_list = [decode_header(r) for r in recipients]
    cc_list = split_addresses(decode_header(message['CC'])) if 'CC' in message else []
    bcc_list = split_addresses(decode_header(message['BCC'])) if 'BCC' in message else []
    all_recipients = {'to': to_list, 'cc': cc_list, 'bcc': bcc_list}
    cur = _conn.cursor()
    cur.execute(
        sql,
        (
            decode_header(sender),
            json.dumps(all_recipients),
            decode_header(message['Subject']),
            body,
            message.get_content_type(),
            len(body),
        ),
    )
    message_id = cur.lastrowid
    # Store parts (why do we do this for non-multipart at all?!)
    parts = 0
    for part in iter_message_parts(message):
        cid = part.get('Content-Id') or str(uuid.uuid4())
        if cid[0] == '<' and cid[-1] == '>':
            cid = cid[1:-1]
        _add_message_part(message_id, cid, part)
        parts += 1
    _conn.commit()
    cur.close()
    log.debug(f'Stored message {message_id} (parts={parts})')
    broadcast('add_message', message_id)
    return message_id


def _add_message_part(message_id, cid, part):
    sql = """
        INSERT INTO message_part
            (message_id, cid, type, is_attachment, filename, charset, body, size, created_at)
        VALUES
            (?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
    """

    body = part.get_payload(decode=True)
    body_len = len(body) if body else 0
    _conn.execute(
        sql,
        (
            message_id,
            cid,
            part.get_content_type(),
            part.get_filename() is not None,
            part.get_filename(),
            part.get_content_charset(),
            body,
            body_len,
        ),
    )


def _get_message_cols(lightweight):
    cols = ('sender', 'recipients', 'created_at', 'subject', 'id', 'size') if lightweight else ('*',)
    return ','.join(cols)


def _parse_recipients(recipients):
    recipients = json.loads(recipients)
    if isinstance(recipients, list):
        # legacy data
        return {'to': recipients, 'cc': [], 'bcc': []}
    else:
        return recipients


def get_message(message_id, lightweight=False):
    cols = _get_message_cols(lightweight)
    row = _conn.execute(f'SELECT {cols} FROM message WHERE id = ?', (message_id,)).fetchone()  # noqa: S608
    if not row:
        return None
    row = dict(row)
    row['recipients'] = _parse_recipients(row['recipients'])
    return row


def get_message_attachments(message_id):
    sql = """
        SELECT
            message_id, cid, type, filename, size
        FROM
            message_part
        WHERE
            message_id = ? AND
            is_attachment = 1
        ORDER BY
            filename ASC
    """
    return _conn.execute(sql, (message_id,)).fetchall()


def _get_message_part_types(message_id, types):
    sql = """
        SELECT
            *
        FROM
            message_part
        WHERE
            message_id = ? AND
            type IN ({}) AND
            is_attachment = 0
        LIMIT
            1
    """.format(
        ','.join('?' * len(types)),
    )
    return _conn.execute(sql, (message_id, *types)).fetchone()


def get_message_part_html(message_id):
    return _get_message_part_types(message_id, ('text/html', 'application/xhtml+xml'))


def get_message_part_plain(message_id):
    return _get_message_part_types(message_id, ('text/plain',))


def get_message_part_cid(message_id, cid):
    return _conn.execute('SELECT * FROM message_part WHERE message_id = ? AND cid = ?', (message_id, cid)).fetchone()


def _message_has_types(message_id, types):
    sql = """
        SELECT
            1
        FROM
            message_part
        WHERE
            message_id = ? AND
            is_attachment = 0 AND
            type IN ({})
        LIMIT
            1
    """.format(
        ','.join('?' * len(types)),
    )
    res = _conn.execute(sql, (message_id, *types)).fetchone()
    return res is not None


def message_has_html(message_id):
    return _message_has_types(message_id, ('application/xhtml+xml', 'text/html'))


def message_has_plain(message_id):
    return _message_has_types(message_id, ('text/plain',))


def get_messages(lightweight=False):
    cols = _get_message_cols(lightweight)
    rows = list(map(dict, _conn.execute(f'SELECT {cols} FROM message ORDER BY created_at ASC').fetchall()))  # noqa: S608
    for row in rows:
        row['recipients'] = _parse_recipients(row['recipients'])
    return rows


def delete_message(message_id):
    _conn.execute('DELETE FROM message WHERE id = ?', (message_id,))
    _conn.execute('DELETE FROM message_part WHERE message_id = ?', (message_id,))
    _conn.commit()
    log.debug(f'Deleted message {message_id}')
    broadcast('delete_message', message_id)


def delete_messages():
    _conn.execute('DELETE FROM message')
    _conn.execute('DELETE FROM message_part')
    _conn.commit()
    log.debug('Deleted all messages')
    broadcast('delete_messages')
