import shlex
from gevent import subprocess
import logging
import time

from config import config
numa_cnt = 2
bind_numa = True


class MglruWrapper:
    def __init__(self, container_id, numa_id=None):
        self.container_id = container_id
        self.numa_id = numa_id
        self.cgroup_id = -1
        self.max_gen = 3
        self.gens_pos = [-2, -2, -2, -2]  # The request_seq_id of each gen
        self.reclaim_overdraft = 0
        self.durations = []
        with open('/sys/kernel/debug/lru_gen') as f:
            for line in f:
                if container_id in line:
                    self.cgroup_id = line.split()[1]
                    logging.info(f'{self.container_id} {self.cgroup_id}')
                    break
        assert self.cgroup_id != -1

    def get_lru_info(self):
        with open('/sys/kernel/debug/lru_gen') as f:
            lines = f.read().split('\n')
        lru_info = [[], []]
        for i, line in enumerate(lines):
            if self.container_id in line:
                now_row = i + 2
                while 'node' not in lines[now_row] and 'memcg' not in lines[now_row]:
                    entry = lines[now_row].split()
                    lru_info[0].append((int(entry[0]), int(entry[2]) + int(entry[3])))
                    now_row += 1
                now_row += 1
                while 'node' not in lines[now_row] and 'memcg' not in lines[now_row]:
                    entry = lines[now_row].split()
                    lru_info[1].append((int(entry[0]), int(entry[2]) + int(entry[3])))
                    now_row += 1
                break
        return lru_info

    def get_request_seq_of_last_gen(self):
        return self.gens_pos[-1]

    def do_reclaim(self):
        # Todo: very important change!
        lru_info = self.get_lru_info()
        reclaim_amount = sum(entry[1] for entry in lru_info[self.numa_id][:-2])
        if reclaim_amount < 64:
            return
        # Use the code above???!!!

        for node_id in range(0, numa_cnt):
            if bind_numa and node_id != self.numa_id:
                continue
            # command = (f'echo "- {self.cgroup_id} {node_id} {mem_info[node_id][0][0]} 60 {mem_info[node_id][0][1]}" > '
            #            f'/sys/kernel/debug/lru_gen')
            command = (f'echo "- {self.cgroup_id} {node_id} {self.max_gen - 2} 60 {reclaim_amount}" > '
                       f'/sys/kernel/debug/lru_gen')
            logging.info(command)
            p = subprocess.run(command, shell=True, check=True)
        return True

    def add_gen(self, request_seq_id):
        self.gens_pos.append(request_seq_id)
        if len(self.gens_pos) > 4:
            self.gens_pos.pop(0)
        for node_id in range(0, numa_cnt):
            if bind_numa and node_id != self.numa_id:
                continue
            command = f'echo "+ {self.cgroup_id} {node_id} {self.max_gen}" > /sys/kernel/debug/lru_gen'
            logging.info(command)
            st = time.time()
            p = subprocess.run(command, shell=True, check=True)
            ed = time.time()
            if len(self.durations) < 10:
                self.durations.append(ed - st)
            # logging.info(f'add gen duration: {ed - st}')
        self.max_gen += 1
        return True

    def get_cur_memory(self):
        with open(f'/sys/fs/cgroup/system.slice/docker-{self.container_id}.scope/memory.current') as f:
            now_memory = int(f.read())
        return now_memory

    def do_semiwarm_reclaim(self, amount):
        target_pages = int(amount / 4096)
        for node_id in range(0, numa_cnt):
            if bind_numa and node_id != self.numa_id:
                continue
            command = (f'echo "- {self.cgroup_id} {node_id} {self.max_gen - 2} 60 {target_pages}" > '
                       f'/sys/kernel/debug/lru_gen')
            logging.info(command)
            p = subprocess.run(command, shell=True, check=True)

    def get_psi_some(self):
        filepath = f'/sys/fs/cgroup/system.slice/docker-{self.container_id}.scope/memory.pressure'
        with open(filepath) as f:
            for line in f:
                if 'some' in line:
                    psi_number = float(line.split(' ')[1].split('=')[1])
                    break
        return psi_number

    def do_tmo_psi_reclaim(self):
        current_mem = self.get_cur_memory()
        psi_some = self.get_psi_some()
        reclaim_mem = (current_mem * config.TMO_RECLAIM_RATIO *
                       max(0, 1 - psi_some / config.TMO_PSI_THRESHOLD_IN_PERCENT))
        target_pages = int(reclaim_mem / 4096)
        if target_pages == 0:
            return
        if target_pages < 128:
            if target_pages <= self.reclaim_overdraft:
                self.reclaim_overdraft -= target_pages
                return
            else:
                target_pages -= self.reclaim_overdraft
                self.reclaim_overdraft = 0
                if target_pages < 128:
                    self.reclaim_overdraft = 128 - target_pages
                    target_pages = 128
        command = (f'echo {4*target_pages}K > '
                   f'/sys/fs/cgroup/system.slice/docker-{self.container_id}.scope/memory.reclaim')
        logging.info(command)
        p = subprocess.run(command, shell=True, check=True)
        # self.add_gen(request_seq_id=-100)
        # self.add_gen(request_seq_id=-100)
        # for node_id in range(0, numa_cnt):
        #     if bind_numa and node_id != self.numa_id:
        #         continue
        #     command = (f'echo "- {self.cgroup_id} {node_id} {self.max_gen - 2} 60 {target_pages}" > '
        #                f'/sys/kernel/debug/lru_gen')
        #     logging.info(command)
        #     p = subprocess.run(command, shell=True, check=True)

    def force_offload(self, amount):
        self.add_gen(request_seq_id=-100)
        self.add_gen(request_seq_id=-100)
        self.do_semiwarm_reclaim(amount)
