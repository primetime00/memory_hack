import falcon

from app.helpers.data_store import DataStore
from app.helpers.process_utils import get_process_names
from app.services.aob import AOB
from app.services.process import Process
from app.services.script import Script
from app.services.searcher import Search


def initialize():
    data_store = DataStore()
    data_store.set_service('process', Process())
    data_store.set_service('search', Search())
    data_store.set_service('aob', AOB())
    data_store.set_service('script', Script())



class MainResource:
    pattern = r'\s*<ons-tab.*page="/(\w+)"(.*)>'
    def on_get(self, req, resp):
        script_instance = DataStore().get_service('script')
        search_instance = DataStore().get_service('search')
        aob_instance = DataStore().get_service('aob')
        resp.content_type = falcon.MEDIA_HTML
        with open('resources/index.html', 'rt') as ac:
            resp.text = ac.read().replace('#search_active#', '').replace('#aob_active#', '').replace('#script_active#', '')

class SearchResource:
    def on_get(self, req, resp):
        search_instance = DataStore().get_service('search')
        resp.content_type = falcon.MEDIA_HTML
        resp.text = search_instance.html_main()

    def on_post(self, req: falcon.Request, resp: falcon.Response):
        search_instance = DataStore().get_service('search')
        search_instance.process(req, resp)
        if resp.status == 200:
            resp.media['process'] = search_instance.get_process_name()
class ScriptResource:
    def on_get(self, req, resp):
        script_instance = DataStore().get_service('script')
        resp.content_type = falcon.MEDIA_HTML
        resp.text = script_instance.html_main()

    def on_post(self, req: falcon.Request, resp: falcon.Response):
        script_instance = DataStore().get_service('script')
        resp.content_type = falcon.MEDIA_JSON
        script_instance.process(req, resp)

class AOBResource:

    def on_get(self, req, resp):
        aob_instance = DataStore().get_service('aob')
        if 'name' in req.params:
            aob_instance.handle_download(req, resp)
            pass
        else:
            resp.content_type = falcon.MEDIA_HTML
            resp.text = aob_instance.html_main()

    def on_post(self, req: falcon.Request, resp: falcon.Response):
        aob_instance = DataStore().get_service('aob')
        aob_instance.process(req, resp)
        if resp.status == 200:
            resp.media['process'] = aob_instance.get_process_name()


class InfoResource:
    data_store = DataStore()
    def on_post(self, req: falcon.Request, resp: falcon.Response):
        process_instance = DataStore().get_service('process')
        process_instance.process(req, resp)

    def get_process_and_crc(self, iteration=-1):
        current_proc = self.data_store.get_process()
        # if we are attached to a process already, then we will not update the process list
        if not current_proc:
            procs, crc = get_process_names()
        elif iteration == 0:
            procs, crc = get_process_names()
            if current_proc not in procs:
                procs.insert(0, current_proc)
            else:
                procs.insert(0, procs.pop(procs.index(current_proc)))
            crc = -1
        else:
            procs, crc = [], 0
        return procs, crc


