import os
from pathlib import Path
from wsgiref.simple_server import make_server

import falcon
from falcon_multipart.middleware import MultipartMiddleware

from app.services import AOB, Search, Script
from helpers.data_store import DataStore

script_instance = Script()
search_instance = Search()
aob_instance = AOB()

class MainResource:
    pattern = r'\s*<ons-tab.*page="/(\w+)"(.*)>'
    def on_get(self, req, resp):
        resp.content_type = falcon.MEDIA_HTML
        with open('resources/index.html', 'rt') as ac:
            if script_instance.is_running():
                resp.text = ac.read().replace('#search_active#', '').replace('#aob_active#', '').replace('#script_active#', 'active')
            elif search_instance.is_running():
                resp.text = ac.read().replace('#search_active#', 'active').replace('#aob_active#', '').replace('#script_active#', '')
            elif aob_instance.is_running():
                resp.text = ac.read().replace('#search_active#', '').replace('#aob_active#', 'active').replace('#script_active#', '')
            else:
                resp.text = ac.read().replace('#search_active#', '').replace('#aob_active#', '').replace('#script_active#', '')

class SearchResource:
    def on_get(self, req, resp):
        resp.content_type = falcon.MEDIA_HTML
        resp.text = search_instance.html_main()

    def on_post(self, req: falcon.Request, resp: falcon.Response):
        search_instance.search(req.media, resp)
        if resp.status == 200:
            resp.media['process'] = DataStore().get_process()
class ScriptResource:
    def on_get(self, req, resp):
        resp.content_type = falcon.MEDIA_HTML
        resp.text = script_instance.html_main()

    def on_post(self, req: falcon.Request, resp: falcon.Response):
        resp.content_type = falcon.MEDIA_JSON
        script_instance.process(req, resp)

class AOBResource:
    def on_get(self, req, resp):
        resp.content_type = falcon.MEDIA_HTML
        resp.text = aob_instance.html_main()

    def on_post(self, req: falcon.Request, resp: falcon.Response):
        aob_instance.process(req, resp)
        if resp.status == 200:
            resp.media['process'] = DataStore().get_process()


class InfoResource:
    def on_post(self, req: falcon.Request, resp: falcon.Response):
        resp.content_type = falcon.MEDIA_JSON
        resp.status = 200
        try:
            if req.media['type'] == 'GET_INFO':
                resp.media = {'status': 'INFO_GET_SUCCESS', 'process': DataStore().get_process(), 'processes': []}
            if req.media['type'] == 'SET_PROCESS':
                DataStore().set_process(req.media['process'])
                resp.media = {'status': 'INFO_SET_SUCCESS', 'process': DataStore().get_process(), 'processes': []}
        except Exception as e:
            resp.media = {'status': 'INFO_ERROR', 'process': req.media['process'], 'error': 'Could not open process.  Is a script running already?'}

if __name__ == '__main__':
    pt = Path(__file__).parent
    os.chdir(pt)
    app = falcon.App(middleware=[MultipartMiddleware()])
    app.add_route('/', MainResource())
    app.add_route('/search', SearchResource())
    app.add_route('/script', ScriptResource())
    app.add_route('/aob', AOBResource())
    app.add_route('/info', InfoResource())
    app.add_static_route('/resources/static', pt.joinpath("resources/static/").absolute())

    with make_server('', 5000, app) as httpd:
        print('Serving on port 5000...')
        httpd.serve_forever()


