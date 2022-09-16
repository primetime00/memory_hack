import falcon
import mem_edit

from app.helpers.data_store import DataStore
from app.helpers.process_utils import get_process_names
from app.services import AOB, Search, Script

script_instance: Script = None
search_instance: Search = None
aob_instance: AOB = None

def initialize():
    global script_instance, search_instance, aob_instance
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
        search_instance.process(req, resp)
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
        if 'name' in req.params:
            aob_instance.handle_download(req, resp)
            pass
        else:
            resp.content_type = falcon.MEDIA_HTML
            resp.text = aob_instance.html_main()

    def on_post(self, req: falcon.Request, resp: falcon.Response):
        aob_instance.process(req, resp)
        if resp.status == 200:
            resp.media['process'] = DataStore().get_process()


class InfoResource:
    data_store = DataStore()
    def on_post(self, req: falcon.Request, resp: falcon.Response):
        resp.content_type = falcon.MEDIA_JSON
        resp.status = 200
        try:
            if req.media['type'] == 'GET_INFO':
                iteration = int(req.media['iteration'])
                current_proc = self.data_store.get_process()
                procs, crc = self.get_process_and_crc(iteration)
                resp.media = {'status': 'INFO_GET_SUCCESS', 'process': current_proc, 'processes': procs, 'crc': crc}
            if req.media['type'] == 'IS_ALIVE':
                if self.data_store.pid == 0:
                    resp.media = {'alive': False}
                else:
                    resp.media = {'alive': True}
            if req.media['type'] == 'SET_PROCESS':
                self.data_store.set_process(req.media['process'])
                procs, crc = self.get_process_and_crc()
                resp.media = {'status': 'INFO_SET_SUCCESS', 'process': self.data_store.get_process(), 'processes': procs, 'crc': crc}
        except mem_edit.MemEditError as e:
            resp.media = {'status': 'INFO_ERROR', 'process': req.media['process'], 'error': 'Could not open process.  Is a script running already?'}

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


