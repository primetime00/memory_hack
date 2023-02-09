from pathlib import Path
import os
import falcon

from falcon_multipart.middleware import MultipartMiddleware
from app import ScriptResource, SearchResource, MainResource, AOBResource, InfoResource, CodeListResource
from app.main import initialize
from app.helpers.data_store import DataStore
from wsgiref.simple_server import make_server, WSGIRequestHandler

class NoLoggingWSGIRequestHandler(WSGIRequestHandler):
    def log_message(self, format, *args):
        pass

if __name__ == '__main__':
    pt = Path(__file__).parent.joinpath('app')
    os.chdir(pt)
    app = falcon.App(middleware=[MultipartMiddleware()])
    initialize()
    app.add_route('/', MainResource())
    app.add_route('/search', SearchResource())
    app.add_route('/codelist', CodeListResource())
    app.add_route('/script', ScriptResource())
    app.add_route('/aob', AOBResource())
    app.add_route('/info', InfoResource())
    app.add_static_route('/resources/static', pt.joinpath("resources/static/").absolute())

    try:
        with make_server('', 5000, app, handler_class=NoLoggingWSGIRequestHandler) as httpd:
            print('Serving on port 5000...')
            httpd.serve_forever()
    except KeyboardInterrupt:
        DataStore().kill()
