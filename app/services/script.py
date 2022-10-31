import importlib.util
import inspect
import logging
import shutil
import traceback
from pathlib import Path
from threading import Thread, Event

import falcon.app_helpers
import mem_edit
from falcon import Request, Response

from app.helpers import MemoryHandler
from app.helpers.data_store import DataStore
from app.helpers.exceptions import ScriptException, ProcessException
from app.script_common.base_script import BaseScript
from app.helpers.directory_utils import scripts_directory


class Script(MemoryHandler):
    directory = scripts_directory

    def __init__(self):
        super().__init__('scripts')
        self.wait_event: Event = Event()
        self.current_script = ""
        self.current_script_obj: BaseScript = None
        self.error = ""
        self.script_thread: Script.ScriptThread = None
        self.search_thread: Script.SearchThread = None
        self.mod_name = ""
        if not self.directory.exists():
            self.directory.mkdir(parents=True, exist_ok=True)
            for f in Path('./scripts').glob('*.py'):
                shutil.copy(f, self.directory.joinpath(f.name))

    def kill(self):
        self.release()
    def release(self):
        if self.script_thread and self.script_thread.is_alive():
            self.script_thread.stop()
            self.script_thread.join()
        if self.search_thread and self.search_thread.is_alive():
            self.search_thread.stop()
            self.search_thread.join()

    def process_error(self, msg: str):
        self.error = msg


    def set(self, data):
        pass

    def get_script_list(self):
        return [x.stem for x in Script.directory.glob('*.py') if not x.stem.startswith('__')]

    def html_main(self):
        with open('resources/script.html', 'rt') as ac:
            res_html = ac.read()
        return res_html

    def is_running(self):
        return self.current_script_obj is not None and self.script_thread is not None and self.script_thread.is_alive()

    def process(self, req: Request, resp: Response):
        resp.status = 200
        script_type = req.media['type']
        try:
            if script_type == "SCRIPT_STATUS":
                self.handle_script_status(req, resp)
            elif script_type == "SCRIPT_LOAD":
                self.handle_load_script(req, resp)
            elif script_type == "SCRIPT_IS_READY":
                self.handle_is_ready_script(req, resp)
            elif script_type == "SCRIPT_UI_GET":
                self.handle_script_ui_get(req, resp)
            elif script_type == "SCRIPT_INTERACT":
                resp.content_type = falcon.app_helpers.MEDIA_JSON
                self.handle_script_interact(req, resp)
            elif script_type == "SCRIPT_UPLOAD_FILE":
                self.handle_script_upload(req, resp)
        except ScriptException as e:
            self.unload_script()
            resp.media = self.send_error(e)
            self.error = ""
            if e.is_from_thread():
                self.script_thread = None

    def handle_script_status(self, req: Request, resp: Response):
        resp.media = {'status': 'SCRIPT_STATUS', 'scripts': self.get_script_list(), 'current': self.current_script}
        if self.script_thread:
            if self.error:
                self.release()
                self.script_thread = None
                self.search_thread = None
                raise ScriptException(self.error, from_thread=False)
            if self.script_thread.error:
                self.release()
                self.script_thread = None
                self.search_thread = None
                raise ScriptException(self.script_thread.error, from_thread=True)
            if self.script_thread.is_alive():
                resp.media['controls'] = self.current_script_obj.get_ui_status()
                resp.media['repeat'] = 1000

    def handle_script_interact(self, req: Request, resp: Response):
        id = req.media['id']
        data = req.media['data']
        if not self.current_script_obj:
            raise ScriptException("No script is currently running.")
        self.current_script_obj.handle_interaction(id, data)
        resp.media = {'status': 'SUCCESS'}

    def handle_is_ready_script(self, req: Request, resp: Response):
        if not self.script_thread:
            raise ScriptException('Script was not loaded properly.')
        if not self.script_thread.is_alive():
            if not self.script_thread.error:
                raise ScriptException('Script has crashed.')
            else:
                raise ScriptException(self.script_thread.error, from_thread=True)
        if not self.current_script_obj:
            raise ScriptException('Script has been corrupted.')
        if self.script_thread.error:
            raise ScriptException(self.error, from_thread=True)
        if not self.script_thread.running:
            resp.media = {'status': 'SCRIPT_NOT_READY'}
        else:
            resp.media = {'status': 'SCRIPT_IS_READY'}
        resp.media['current'] = self.current_script

    def handle_script_ui_get(self, req: Request, resp: Response):
        resp.media = {'status': 'SCRIPT_UI_GET', 'scripts': self.get_script_list(), 'current': self.current_script}
        if req.media['name'] != self.current_script:
            logging.error("Requested UI for {}, but running {}".format(req.media['name'], self.current_script))
            raise ScriptException('Requested UI from script that is not running')
        if not self.current_script_obj:
            logging.error("Requested UI for {}, but no script running.")
            raise ScriptException('Requested UI from script that is not running')
        html = self.current_script_obj.get_ui()
        resp.media['ui'] = html



    def handle_load_script(self, req: Request, resp: Response):
        resp.media = {'scripts': self.get_script_list()}
        name = req.media['name']
        load = req.media['unload'] == 'false'
        self.release()
        if load:
            self.unload_script()
            self.current_script_obj = self.load_script(name)
        else:
            self.unload_script()
        if self.current_script_obj:
            proc_service = DataStore().get_service('process')
            for req_proc in self.current_script_obj.get_app():
                try:
                    proc_service.request_process('scripts', req_proc)
                    self.current_script_obj.set_process(req_proc)
                    break
                except ProcessException:
                    continue
            if not self.has_mem():
                raise ScriptException('Could not find requested process for this script.')
            self.current_script_obj.set_memory(self.mem())
            self.wait_event = Event()
            self.script_thread = Script.ScriptThread(self.current_script_obj, self.current_script, self.mem(), self.wait_event)
            self.search_thread = Script.SearchThread(self.current_script_obj, self.current_script, self.mem(), self.wait_event)
            self.search_thread.start()
            self.script_thread.start()
        resp.media['status'] = 'SCRIPT_LOADED' if load else 'SCRIPT_UNLOADED'
        resp.media['current'] = self.current_script

    def handle_script_upload(self, req: Request, resp: Response):
        name: str = req.media['name'].strip()
        if name.startswith('_'):
            resp.media = {'status': 'SCRIPT_ERROR', 'error': 'Script filename must not begin with "_".'}
            return
        data: str = req.media['data']
        if 'BaseScript' not in data:
            resp.media = {'status': 'SCRIPT_ERROR', 'error': 'Not a valid script file.'}
            return
        pt = Path(name)
        filename: str = pt.stem
        name_list = [item.casefold() for item in self.get_script_list()]
        index = 0
        proposed_filename = filename
        while proposed_filename.casefold() in name_list:
            index += 1
            proposed_filename = "{}-{:03d}".format(filename, index)
        dest = self.directory.joinpath("{}{}".format(proposed_filename, pt.suffix))
        with open(dest, "wt") as fp:
            fp.write(data)
        resp.media = {'status': 'SCRIPT_UPLOAD_COMPLETE', 'name': proposed_filename, 'scripts': self.get_script_list()}


    def unload_script(self):
        if self.current_script_obj:
            self.current_script_obj.on_unload()
        self.release()
        self.current_script_obj = None
        self.current_script = ""
        if self.mod_name:
            #del sys.modules[self.mod_name]
            self.mod_name = ""

    def load_script(self, name):
        self.mod_name = 'app.user_scripts.{}'.format(name)
        try:
            spec = importlib.util.spec_from_file_location(self.mod_name, self.directory.joinpath(name + '.py'))
            mod = importlib.util.module_from_spec(spec)  #import_module(self.mod_name)
            spec.loader.exec_module(mod)
            for cls, obj in inspect.getmembers(mod):
                if inspect.isclass(obj) and obj.__module__ == self.mod_name:
                    logging.info('Starting {}'.format(name))
                    bs: BaseScript = getattr(mod, cls)()
                    bs.on_load()
                    self.current_script = name
                    return bs
        except BaseException as e:
            raise ScriptException("Script Error: {}".format(Script.parse_error(name, traceback.format_exc(limit=-1))))
        logging.error("Could not properly load script")
        raise ScriptException("Could not properly load script.")

    def send_error(self, e: ScriptException) -> dict:
        return {'status': 'SCRIPT_ERROR', 'error': e.get_message()}

    @staticmethod
    def parse_error(name: str, error: str):
        lines = error.splitlines()
        msg = name+': '
        for line in reversed(lines):
            pos = line.rfind(", line ")
            if pos < 0:
                continue
            msg += '{}\n'.format(line[pos+2: ])
            break
        msg += lines[-1]
        return msg



    class ScriptThread(Thread):
        def __init__(self, script: BaseScript, filename, memory: mem_edit.Process, wait_event: Event):
            super().__init__(target=self.loop)
            self.running = False
            self.wait_event = wait_event
            self.script: BaseScript = script
            self.filename = filename
            self.error = ""
            self.memory = memory

        def get_name(self):
            return self.filename

        def stop(self):
            self.running = False
            self.wait_event.set()

        def loop(self):
            try:
                self.running = True
                while self.running:
                    self.script.process()
                    self.wait_event.wait(self.script.get_speed())
            except IOError as io_error:
                logging.error(str(io_error))
                self.error = 'Could not open process {}. Is it opened in scanners?'.format(self.script.get_app())
            except Exception as e:
                logging.error(str(e))
                self.error = Script.parse_error(self.filename, traceback.format_exc(limit=-1))

    class SearchThread(Thread):
        def __init__(self, script: BaseScript, filename, memory: mem_edit.Process, wait_event: Event):
            super().__init__(target=self.loop)
            self.running = False
            self.wait_event = wait_event
            self.script: BaseScript = script
            self.filename = filename
            self.error = ""
            self.memory = memory

        def stop(self):
            self.running = False
            self.wait_event.set()

        def loop(self):
            try:
                self.running = True
                while self.running:
                    self.script.search()
                    self.wait_event.wait(1)
            except IOError as io_error:
                logging.error(str(io_error))
                self.error = 'Could not open process {}. Is it opened in scanners?'.format(self.script.get_app())
            except Exception as e:
                logging.error(str(e))
                self.error = Script.parse_error(self.filename, traceback.format_exc(limit=-1))



