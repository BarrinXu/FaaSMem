import time
import json
import gevent

# from src.function_manager.function import Function
import logging
import datetime
import os


class GlobalMonitor:
    def __init__(self, functions):
        self.global_memory = 0
        self.global_cpu = 0
        self.global_containers = 0
        self.rcv_data = 0
        self.xmit_data = 0

        self.max_rcv_speed = 0
        self.max_xmit_speed = 0

        self.monitor_end = False
        self.save_logs = None
        self.memory_limit = 1024 * 64
        # self.memory_limit = 1024 * 32
        self.cpu_limit = 32
        self.functions = functions
        self.functions_priority_list = list(self.functions.keys())
        self.functions_priority_list.sort(key=lambda x: self.functions[x].function_info.configs['priority'])

    def start_collect(self):
        gevent.spawn(self.regular_report)

    def end_collect(self):
        self.monitor_end = True
        while self.save_logs is None:
            gevent.sleep(2)
        return self.save_logs

    def collect_swap_memory(self):
        with open('/proc/meminfo', 'r') as f:
            for line in f:
                if line.startswith('SwapTotal'):
                    swap_total = int(line.split()[1])
                elif line.startswith('SwapFree'):
                    swap_free = int(line.split()[1])
        return (swap_total - swap_free) / 1024

    def collect_rdma_bandwidth(self):
        old_rcv_data = self.rcv_data
        old_xmit_data = self.xmit_data
        # device_name = 'mlx4_0'
        device_name = 'ibp130s0'
        # device_name = 'ibp8s0'
        with open(f'/sys/class/infiniband/{device_name}/ports/1/counters/port_rcv_data', 'r') as f:
            self.rcv_data = int(f.read()) * 4
        with open(f'/sys/class/infiniband/{device_name}/ports/1/counters/port_xmit_data', 'r') as f:
            self.xmit_data = int(f.read()) * 4
        if old_rcv_data == 0 or old_xmit_data == 0:
            return 0, 0
        else:
            return self.rcv_data - old_rcv_data, self.xmit_data - old_xmit_data

    def regular_report(self):
        memory_logs = []
        swap_logs = []
        rdma_rcv = []
        rdma_xmit = []
        container_nums = []
        monitor_interval = 1
        next_wake_up_time = time.time()
        while True:
            if self.monitor_end:
                break
            now_swap = self.collect_swap_memory()
            logging.info(f'now_memory: {format(self.global_memory / 1048576, ".3f")}, now_cpu: {self.global_cpu}, now_swap:{now_swap}')
            rdma_rcv_speed, rdma_xmit_speed = self.collect_rdma_bandwidth()
            rdma_rcv_speed /= monitor_interval
            rdma_xmit_speed /= monitor_interval
            self.max_rcv_speed = max(self.max_rcv_speed, rdma_rcv_speed)
            self.max_xmit_speed = max(self.max_xmit_speed, rdma_xmit_speed)
            logging.warning(f'rdma_rcv: {format(rdma_rcv_speed / 1048576, ".3f")} MB/s, '
                         f'rdma_xmit: {format(rdma_xmit_speed / 1048576, ".3f")} MB/s, '
                         f'max_rcv: {format(self.max_rcv_speed / 1048576, ".3f")} MB/s, '
                         f'max_xmit: {format(self.max_xmit_speed / 1048576, ".3f")} MB/s')

            memory_logs.append(self.global_memory)
            swap_logs.append(now_swap)
            rdma_rcv.append(format(rdma_rcv_speed / 1048576, ".3f"))
            rdma_xmit.append(format(rdma_xmit_speed / 1048576, ".3f"))
            container_nums.append(self.global_containers)
            next_wake_up_time += monitor_interval
            gevent.sleep(next_wake_up_time - time.time())
        nowtime = str(datetime.datetime.now())
        suffix = 'AzureTraceGlobalmonitor'
        if not os.path.exists('result'):
            os.mkdir('result')
        filepath = os.path.join('result', nowtime + '_' + suffix + '.json')
        self.save_logs = {'memory_logs': memory_logs, 'monitor_interval': monitor_interval, 'swap_logs': swap_logs,
                          'rdma_rcv': rdma_rcv, 'rdma_xmit': rdma_xmit, 'container_nums': container_nums}
        # with open(filepath, 'w') as f:
        #     json.dump(self.save_logs, f)

    def allocate_cpu(self, target_function, add_cpu):
        self.global_cpu += add_cpu

    def free_cpu(self, amount):
        self.global_cpu -= amount

    def add_container(self):
        self.global_containers += 1

    def del_container(self):
        self.global_containers -= 1

    def allocate_memory(self, target_function, add_memory):
        # Always return True for testing.
        return True
        self.global_memory += add_memory
        return True

        delta = self.global_memory + add_memory - self.memory_limit
        if delta <= 0:
            self.global_memory += add_memory
            return True
        target_priority = self.functions[target_function].function_info.configs['priority']
        for function_name in self.functions_priority_list:
            now_priority = self.functions[function_name].function_info.configs['priority']
            if now_priority >= target_priority:
                break
            delta = self.functions[function_name].shrink_idle_containers(delta)
            if delta == 0:
                self.global_memory += add_memory
                return True
        return False

    def free_memory(self, amount):
        return True
        self.global_memory -= amount

    def upd_memory(self, delta):
        self.global_memory += delta
