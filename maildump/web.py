import re
from io import BytesIO

import bs4
from flask import Flask, abort, render_template, request, send_file, url_for
from logbook import Logger

import maildump
from maildump import db
from maildump.util import bool_arg, get_version, rest
from maildump.web_realtime import handle_sse_request

RE_CID = re.compile(r'(?P<replace>cid:(?P<cid>.+))')
RE_CID_URL = re.compile(r'url\(\s*(?P<quote>["\']?)(?P<replace>cid:(?P<cid>[^\\\')]+))(?P=quote)\s*\)')

# Flask app
app = Flask(__name__, static_folder='static/dist', static_url_path='/static')
app._logger = log = Logger(__name__)
app.add_url_rule('/event-stream', view_func=handle_sse_request)


@app.before_request
def check_auth():
    htpasswd = app.config['MAILDUMP_HTPASSWD']
    if htpasswd is None:
        # Authentication disabled
        return
    auth = request.authorization
    if auth and htpasswd.check_password(auth.username, auth.password):
        log.debug('Request authenticated ({0})'.format(auth.username))
        return
    return app.response_class(
        'This MailDump instance is password-protected.', 401, {'WWW-Authenticate': 'Basic realm="MailDump"'}
    )


@app.route('/')
def home():
    return render_template('index.parcel.html', version=get_version())


@app.route('/', methods=('DELETE',))
@rest
def terminate():
    if app.config['MAILDUMP_NO_QUIT']:
        abort(403)
    log.info('Terminate request received')
    maildump.stop()


@app.route('/messages/', methods=('DELETE',))
@rest
def delete_messages():
    db.delete_messages()


@app.route('/messages/', methods=('GET',))
@rest
def get_messages():
    lightweight = not bool_arg(request.args.get('full'))
    return {'messages': db.get_messages(lightweight)}


@app.route('/messages/<int:message_id>', methods=('DELETE',))
@rest
def delete_message(message_id):
    message = db.get_message(message_id, True)
    if not message:
        return 404, 'message does not exist'
    db.delete_message(message_id)


def _part_url(part):
    return url_for('get_message_part', message_id=part['message_id'], cid=part['cid'])


def _part_response(part, body=None, charset=None):
    charset = charset or part['charset'] or 'utf-8'
    if body is None:
        body = part['body']
    if charset != 'utf-8':
        body = body.decode(charset).encode('utf-8')
    io = BytesIO(body)
    io.seek(0)
    response = send_file(io, part['type'], part['is_attachment'], part['filename'])
    response.charset = charset
    return response


@app.route('/messages/<int:message_id>.json', methods=('GET',))
@rest
def get_message_info(message_id):
    lightweight = not bool_arg(request.args.get('full'))
    message = db.get_message(message_id, lightweight)
    if not message:
        return 404, 'message does not exist'
    message['href'] = url_for('get_message_eml', message_id=message_id)
    message['formats'] = {'source': url_for('get_message_source', message_id=message_id)}
    if db.message_has_plain(message_id):
        message['formats']['plain'] = url_for('get_message_plain', message_id=message_id)
    if db.message_has_html(message_id):
        message['formats']['html'] = url_for('get_message_html', message_id=message_id)
    message['attachments'] = [dict(part, href=_part_url(part)) for part in db.get_message_attachments(message_id)]
    return message


@app.route('/messages/<int:message_id>.plain', methods=('GET',))
@rest
def get_message_plain(message_id):
    part = db.get_message_part_plain(message_id)
    if not part:
        return 404, 'part does not exist'
    return _part_response(part)


def _fix_cid_links(soup, message_id):
    def _url_from_cid_match(m):
        return m.group().replace(
            m.group('replace'), url_for('get_message_part', message_id=message_id, cid=m.group('cid'))
        )

    # Iterate over all attributes that do not contain CSS and replace cid references
    for tag in (x for x in soup.descendants if isinstance(x, bs4.Tag)):
        for name, value in tag.attrs.items():
            if isinstance(value, list):
                value = ' '.join(value)
            m = RE_CID.match(value)
            if m is not None:
                tag.attrs[name] = _url_from_cid_match(m)
    # Rewrite cid references within inline stylesheets
    for tag in soup.find_all('style'):
        tag.string = RE_CID_URL.sub(_url_from_cid_match, tag.string)


@app.route('/messages/<int:message_id>.html', methods=('GET',))
@rest
def get_message_html(message_id):
    part = db.get_message_part_html(message_id)
    if not part:
        return 404, 'part does not exist'
    charset = part['charset'] or 'utf-8'
    soup = bs4.BeautifulSoup(part['body'].decode(charset), 'html5lib')
    _fix_cid_links(soup, message_id)
    return _part_response(part, soup.encode('utf-8'), 'utf-8')


@app.route('/messages/<int:message_id>.source', methods=('GET',))
@rest
def get_message_source(message_id):
    message = db.get_message(message_id)
    if not message:
        return 404, 'message does not exist'
    io = BytesIO(message['source'])
    io.seek(0)
    return send_file(io, 'text/plain')


@app.route('/messages/<int:message_id>.eml', methods=('GET',))
@rest
def get_message_eml(message_id):
    message = db.get_message(message_id)
    if not message:
        return 404, 'message does not exist'
    io = BytesIO(message['source'])
    io.seek(0)
    return send_file(io, 'message/rfc822')


@app.route('/messages/<int:message_id>/parts/<cid>', methods=('GET',))
@rest
def get_message_part(message_id, cid):
    part = db.get_message_part_cid(message_id, cid)
    if not part:
        return 404, 'part does not exist'
    return _part_response(part)
