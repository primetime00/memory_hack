import falcon
from pathlib import Path
import os
import ssl
import json
from falcon_auth import FalconAuthMiddleware, BasicAuthBackend
from falcon_multipart.middleware import MultipartMiddleware
from app import ScriptResource, SearchResource, MainResource, AOBResource, InfoResource, CodeListResource
from app.main import initialize
from app.helpers.data_store import DataStore
from wsgiref.simple_server import make_server, WSGIRequestHandler

def load_auth_config():
    auth_file = Path("auth.json")
    if not auth_file.exists():
        return None
    try:
        return json.loads(auth_file.read_text())
    except Exception:
        return None

def user_loader(username, password):
    creds = load_auth_config()
    if not creds:
        return None
    if username == creds.get("username") and password == creds.get("password"):
        return {"username": username}
    return None

auth_backend = BasicAuthBackend(user_loader)
auth_middleware = FalconAuthMiddleware(auth_backend)

class NoLoggingWSGIRequestHandler(WSGIRequestHandler):
    def log_message(self, format, *args):
        pass

if __name__ == '__main__':
    pt = Path(__file__).parent.joinpath('app')
    os.chdir(pt)
    app = falcon.App(middleware=[MultipartMiddleware(), auth_middleware])
    initialize()
    app.add_route('/', MainResource())
    app.add_route('/search', SearchResource())
    app.add_route('/codelist', CodeListResource())
    app.add_route('/script', ScriptResource())
    app.add_route('/aob', AOBResource())
    app.add_route('/info', InfoResource())
    app.add_static_route('/resources/static', pt.joinpath("resources/static/").absolute())
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(certfile="cert.pem", keyfile="key.pem")

    try:
        with make_server('', 5000, app, handler_class=NoLoggingWSGIRequestHandler) as httpd:
            httpd.socket = context.wrap_socket(httpd.socket, server_side=True)
            print('Serving on https://0.0.0.0:5000...')
            httpd.serve_forever()
    except KeyboardInterrupt:
        DataStore().kill()
