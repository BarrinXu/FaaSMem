import gevent

from src.function_manager.port_manager import PortManager
import os
from src.workflow_manager.global_monitor import GlobalMonitor
from src.function_manager.function import Function
from src.function_manager.function_info import FunctionInfo
from src.workflow_manager.request_info import RequestInfo
dispatch_interval = 0.005
recycle_interval = 10


class FunctionManager:
    def __init__(self, docker_client, min_port, max_port, functions_info_path):
        self.port_manager = PortManager(min_port, max_port)
        self.docker_client = docker_client
        self.functions_info = FunctionInfo.parse(functions_info_path)
        self.functions: dict[str, Function] = {
            function_name: Function(function_info, self.docker_client, self.port_manager)
            for function_name, function_info in self.functions_info.items()}
        self.global_monitor = GlobalMonitor(self.functions)
        for func in self.functions.values():
            func.set_global_monitor(self.global_monitor)
        self.init()

    def init(self):
        print('Clearing previous containers...')
        os.system('docker rm -f $(docker ps -aq --filter label=FaaSMem)')
        gevent.spawn_later(dispatch_interval, self.regular_dispatch)
        gevent.spawn_later(recycle_interval, self.regular_recycle)

    def regular_dispatch(self):
        gevent.spawn_later(dispatch_interval, self.regular_dispatch)
        for func in self.functions.values():
            gevent.spawn(func.dispatch_request)

    def regular_recycle(self):
        gevent.spawn_later(recycle_interval, self.regular_recycle)
        for func in self.functions.values():
            gevent.spawn(func.recycle)

    def trigger(self, request_info: RequestInfo):
        self.functions[request_info.function_name].trigger(request_info)

    def upd_configs(self, function_name, upd_configs):
        self.functions[function_name].upd_configs(upd_configs)
