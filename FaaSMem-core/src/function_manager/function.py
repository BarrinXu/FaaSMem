import random
import time

import gevent
import requests

from src.function_manager.port_manager import PortManager
from src.function_manager.function_info import FunctionInfo
from src.workflow_manager.global_monitor import GlobalMonitor
from src.function_manager.container import ContainerWrapper
from config import config
from src.workflow_manager.request_info import RequestInfo
import logging


class Function:
    def __init__(self, function_info: FunctionInfo, docker_client, port_manager: PortManager):
        self.function_info = function_info
        self.docker_client = docker_client
        self.port_manager = port_manager
        self.global_monitor = None
        self.idle_containers: list[ContainerWrapper] = []
        self.idle_tuning_containers: list[ContainerWrapper] = []
        self.num_exec = 0
        self.requests_queue: list[RequestInfo] = []

    def set_global_monitor(self, global_monitor):
        self.global_monitor = global_monitor

    def upd_configs(self, upd_configs):
        self.function_info.upd_configs(upd_configs)
        # For running containers, update configs after finish.
        # if 'idle_memory' in upd_configs:
        #     target_memory = upd_configs['idle_memory']
        #     for container in self.idle_containers:
        #         if container.configs['now_memory'] != target_memory:
        #             container.upd_memory_limit(target_memory)

    def create_container(self):
        if self.num_exec > self.function_info.max_containers:
            return None
        self.num_exec += 1
        container = ContainerWrapper.create(self.docker_client,
                                            self.function_info.image_name,
                                            self.function_info.function_name,
                                            self.port_manager.allocate(),
                                            self.function_info.configs,
                                            self.global_monitor)
        if container is None:
            self.num_exec -= 1
        return container

    def shrink_idle_containers(self, expect_mem):
        for container in self.idle_containers:
            now_memory = container.configs['now_memory']
            std_idle_memory = self.function_info.configs['idle_memory']
            target_idle_memory = max(int(std_idle_memory * config.IDLE_CONTAINER_ELASTICITY),
                                     std_idle_memory - expect_mem)
            if now_memory > target_idle_memory:
                container.upd_memory_limit(target_idle_memory)
                expect_mem -= now_memory - target_idle_memory
            if expect_mem == 0:
                break
        return expect_mem

    def get_idle_container(self, exec_type):
        if exec_type == 'normal':
            idle_containers = self.idle_containers
        elif exec_type == 'tuning':
            idle_containers = self.idle_tuning_containers
        else:
            raise Exception

        res = None
        if len(idle_containers) > 0:
            res = idle_containers.pop()
            # res.upd_memory_limit(self.function_info.configs['exec_memory'])
            res.last_time = time.time()
            res.global_monitor.allocate_cpu(self.function_info.function_name, self.function_info.configs['cpu'])
        return res

    def put_container(self, container: ContainerWrapper, exec_type):
        # container.upd_memory_limit(0.9, delay=1)
        # Todo: During tuning for exec-memory, do not limit idle-memory
        if (self.function_info.configs['system'] == 'baseline' and
                self.function_info.configs['test_type'] == 'idle_offload'):
            container.upd_memory_limit(self.function_info.configs['idle_memory'], direct=True)
            container.upd_memory_limit(self.function_info.configs['raw_memory'], direct=True)
        if self.function_info.configs['system'] == 'FaaSMem':
            if self.function_info.configs['MGLRU']:
                if container.configs['exec_cnt'] == 1:
                    container.reclaim_runtime()
                if self.function_info.configs['init_offload']:
                    container.try_reclaim_init()
            if self.function_info.configs['semiwarm']:
                container.start_semiwarm_routine(delay_time=self.function_info.configs['semiwarm_delay'],
                                                 reclaim_amount_per_second=int(container.mglru.get_cur_memory() / 100))
        # container.upd_memory_limit(self.function_info.configs['idle_memory'])
        # if self.function_info.configs['exec_tuning'] is False:
        #     container.gradual_offload(end_memory=self.function_info.configs['idle_memory'],
        #                               keep_alive_time=config.CONTAINER_IDLE_LIFETIME, delay_time=60)
        if exec_type == 'normal':
            idle_containers = self.idle_containers
        elif exec_type == 'tuning':
            idle_containers = self.idle_tuning_containers
        else:
            raise Exception
        idle_containers.append(container)
        container.global_monitor.free_cpu(self.function_info.configs['cpu'])

    def trigger(self, request_info):
        self.requests_queue.append(request_info)

    def dispatch_request(self):
        if len(self.requests_queue) == 0:
            return
        request_info = self.requests_queue.pop(0)
        if self.function_info.configs['exec_tuning'] and random.randint(0, 1):
            request_info.set_tuning()
        container = self.get_idle_container(request_info.exec_type)
        if container is None:
            container = self.create_container()
        if container is None:
            # logging.error('dispatch_request_failed')
            self.requests_queue.append(request_info)
            return
        container.configs['cgroup_event_id'] += 1
        container.configs['exec_cnt'] += 1
        # Random choose
        # exec_config = self.function_info.get_exec_config(container.configs['exec_cnt'], request_info.exec_type)
        # container.upd_memory_limit(exec_config['exec_memory'])
        # request_info.runtime_configs.update(exec_config)
        self.run(container, request_info)

        # Check container memory config is updated or not

        self.put_container(container, request_info.exec_type)

    def run(self, container: ContainerWrapper, request_info: RequestInfo):
        container.run(request_info)
        request_info.result.set(1)
        # if request_info.runtime_configs['container_exec_cnt'] > config.CONTAINER_AB_TEST_THRESHOLD and \
        #         self.function_info.configs['exec_tuning']:
        #     gevent.spawn(self.report_result, request_info)

    def report_result(self, request_info: RequestInfo):
        r = requests.post(f'http://{config.ANALYZER_URL}/post_result', json=request_info.gen_analyzer_log())

    def remove_container(self, container: ContainerWrapper):
        self.num_exec -= 1
        container.destroy()
        self.port_manager.put(container.port)

    def recycle(self):
        now_time = time.time()
        removed_containers = []

        pos = len(self.idle_containers)
        for i, container in enumerate(self.idle_containers):
            if container.last_time + config.CONTAINER_IDLE_LIFETIME > now_time:
                pos = i
                break
        removed_containers.extend(self.idle_containers[:pos])
        self.idle_containers = self.idle_containers[pos:]

        pos = len(self.idle_tuning_containers)
        for i, container in enumerate(self.idle_tuning_containers):
            if container.last_time + config.CONTAINER_IDLE_LIFETIME > now_time:
                pos = i
                break
        removed_containers.extend(self.idle_tuning_containers[:pos])
        self.idle_tuning_containers = self.idle_tuning_containers[pos:]

        for container in removed_containers:
            self.remove_container(container)
