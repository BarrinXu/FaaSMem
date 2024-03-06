import gevent
from src.function_manager.function_manager import FunctionManager
import docker
from src.workflow_manager.request_info import RequestInfo
from gevent.queue import Queue

dispatch_interval = 0.001

class WorkerSP:
    def __init__(self, host_addr, gateway_addr, min_port, max_port, functions_info_path):
        self.host_addr = host_addr
        self.gateway_addr = gateway_addr
        self.function_manager = FunctionManager(docker.from_env(), min_port, max_port, functions_info_path)
        self.requests_queue = []
        gevent.spawn_later(dispatch_interval, self.dispatch_request)

    def dispatch_request(self):
        gevent.spawn_later(dispatch_interval, self.dispatch_request)
        if len(self.requests_queue) == 0:
            return
        request_info: RequestInfo = self.requests_queue.pop(0)
        self.function_manager.trigger(request_info)

    def run(self, request_id, function_name, runtime_configs, handler_context):
        request_info = RequestInfo(request_id, function_name, runtime_configs, handler_context)
        self.requests_queue.append(request_info)
        request_info.result.get()
        return {'exec_duration': request_info.duration, 'pgmjfault': request_info.pgmjfault,
                'return_infos': request_info.return_infos}

    def upd_configs(self, function_name, upd_configs):
        self.function_manager.upd_configs(function_name, upd_configs)
