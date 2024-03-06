import logging
import subprocess
import time
import random
from docker import DockerClient
from docker.models.containers import Container
import requests
from config import config
from src.workflow_manager.request_info import RequestInfo
from src.workflow_manager.global_monitor import GlobalMonitor
from src.function_manager.MGLRU import MglruWrapper
import gevent
from gevent.lock import BoundedSemaphore

container_url = 'http://127.0.0.1:{}/{}'
cgroup_event_interval = 2
# cpuset_cpus = ['0, 1, 2, 3, 4, 5, 6, 7, 16, 17, 18, 19, 20, 21, 22, 23',
#                '8, 9, 10, 11, 12, 13, 14, 15, 24, 25, 26, 27, 28, 29, 30, 31']
cpuset_cpus = ['0-7,16-23',
               '8-15,24-31']
cpuset_mems = ['0', '1']


class ContainerWrapper:
    def __init__(self, container: Container, function_name, port, configs, global_monitor: GlobalMonitor, numa_id=None):
        self.container = container
        self.port = port
        self.function_name = function_name
        self.last_time = time.time()
        self.configs = configs
        self.global_monitor = global_monitor
        self.mglru = MglruWrapper(self.container.id, numa_id)
        self.configs['cgroup_event_id'] = 0
        self.configs['exec_cnt'] = 0
        self.configs['last_reclaim_time'] = 0
        self.pgpgin = 0
        self.pgpgout = 0
        self.pgmajfault = 0
        self.lock = BoundedSemaphore()
        self.is_die = False
        gevent.spawn(self.memory_report_routine)
        if configs['system'] == 'TMO':
            gevent.spawn(self.tmo_routine)

    @classmethod
    def create(cls, docker_client: DockerClient, image_name, function_name, port, configs,
               global_monitor: GlobalMonitor):
        flag = global_monitor.allocate_memory(function_name, configs["raw_memory"])
        assert flag is True
        global_monitor.allocate_cpu(function_name, configs["cpu"])
        global_monitor.add_container()
        logging.info(f'cold start container for {function_name} with memory {configs["raw_memory"]}M')
        try:
            st = time.time()
            numa_id = random.randint(1, 1)
            container = docker_client.containers.run(image_name,
                                                     detach=True,
                                                     ports={'5000/tcp': str(port)},
                                                     labels=['FaaSMem'],
                                                     cpu_quota=int(100000 * 1),
                                                     mem_limit=f'{configs["raw_memory"]}M',
                                                     cpuset_cpus=cpuset_cpus[numa_id],
                                                     cpuset_mems=cpuset_mems[numa_id]
                                                     )
            res = cls(container, function_name, port,
                      {'now_memory': configs['raw_memory'],
                       'system': configs['system'],
                       'lru_gen_interval': configs['lru_gen_interval'],
                       'reclaim_time_interval': configs['reclaim_time_interval']},
                      global_monitor, numa_id)
            res.wait_start()
            ed = time.time()
            logging.info(
                f'cold start complete for {function_name} with ID {container.short_id} {format(ed - st, ".3f")}s')
            if res.configs['system'] != 'DAMON':
                res.add_lru_gen()
            if res.configs['system'] == 'DAMON':
                p = subprocess.run("docker inspect -f '{{ .State.Pid }}' " + container.short_id,
                                   shell=True, stdout=subprocess.PIPE)
                pid = int(p.stdout.decode())
                logging.info(f'container {container.short_id} with pid {pid}')
                subprocess.Popen(f'damo start '
                                 f'--damos_access_rate 0 0 --damos_sz_region 4K max --damos_age 60s max '
                                 f'--damos_action pageout {pid}', shell=True)

            st = time.time()
            res.init_func()
            ed = time.time()
            logging.info(
                f'func init complete for {function_name} with ID {container.short_id} {format(ed - st, ".3f")}s')

            if res.configs['system'] == 'DAMON-debug':
                p = subprocess.run("docker inspect -f '{{ .State.Pid }}' " + container.short_id,
                                   shell=True, stdout=subprocess.PIPE)
                pid = int(p.stdout.decode())
                logging.info(f'container {container.short_id} with pid {pid}')
                subprocess.Popen(f'timeout 30 '
                                 f'damo record '
                                 f'-o damon.data -n 1000 -m 2000 '
                                 f'--target_pid {pid}', shell=True)
                time.sleep(3)

            if res.configs['system'] != 'DAMON':
                res.add_lru_gen()

            # res.upd_memory_limit(configs["exec_memory"])
            res.upd_cpu_limit(int(100000 * configs['cpu']))
            return res
        except Exception as e:
            print('------------', e, '-----------------')
            global_monitor.free_cpu(configs['cpu'])
            global_monitor.del_container()
            return None

    def wait_start(self):
        while True:
            try:
                r = requests.get(container_url.format(self.port, 'status'))
                if r.status_code == 200:
                    break
            except Exception:
                pass
            gevent.sleep(0.005)

    def init_func(self):
        r = requests.get(container_url.format(self.port, 'init'))
        assert r.status_code == 200

    def will_die(self):
        return time.time() - self.last_time > config.CONTAINER_IDLE_LIFETIME - 10

    def get_page_in_out_info(self):
        return 0, 0
        cgroup_path = f'/sys/fs/cgroup/memory/docker/{self.container.id}/memory.stat'
        old_pgpgin = self.pgpgin
        old_pgpgout = self.pgpgout
        with open(cgroup_path, 'r') as f:
            for line in f:
                if line.startswith('pgpgin'):
                    self.pgpgin = int(line.split()[1])
                elif line.startswith('pgpgout'):
                    self.pgpgout = int(line.split()[1])
                    break
        return self.pgpgin - old_pgpgin, self.pgpgout - old_pgpgout

    def get_page_mjfault_info(self):
        cgroup_path = f'/sys/fs/cgroup/system.slice/docker-{self.container.id}.scope/memory.stat'
        old_pgmajfault = self.pgmajfault
        with open(cgroup_path, 'r') as f:
            for line in f:
                if line.startswith('pgmajfault'):
                    self.pgmajfault = int(line.split()[1])
                    break
        return self.pgmajfault - old_pgmajfault

    def set_cgroup_memory_limit(self, event_id, target_memory):
        if event_id != self.configs['cgroup_event_id'] or self.configs['now_memory'] == target_memory:
            return
        if target_memory < 16:
            raise Exception
        if target_memory <= self.configs['now_memory']:
            self.global_monitor.free_memory(self.configs['now_memory'] - target_memory)
        else:
            flag = self.global_monitor.allocate_memory(self.function_name, target_memory - self.configs['now_memory'])
            assert flag is True

        self.configs['now_memory'] = target_memory
        # Cgroup v1
        # cgroup_path = f'/sys/fs/cgroup/memory/docker/{self.container.id}/memory.limit_in_bytes'
        # Cgroup v2

        st = time.time()
        self.container.update(mem_limit=f'{target_memory}M', memswap_limit='64G')
        # cgroup_path = f'/sys/fs/cgroup/system.slice/docker-{self.container.id}.scope/memory.max'
        # self.lock.acquire()
        #
        # try:
        #     with open(cgroup_path, 'w') as f:
        #         f.write(f'{target_memory}M')
        # except Exception as e:
        #     logging.warning(e)
        #
        # self.lock.release()
        ed = time.time()
        logging.info(
            f'set container {self.container.short_id} memory limit to {target_memory}M, time: {format(ed - st, ".4f")}s')

    def upd_cpu_limit(self, cpu_quota):
        gevent.spawn(self.container.update, cpu_quota=cpu_quota)

    def add_lru_gen(self):
        self.mglru.add_gen(request_seq_id=self.configs['exec_cnt'])

    def reclaim_runtime(self):
        self.mglru.do_reclaim()

    def try_reclaim_init(self):
        if time.time() - self.configs['last_reclaim_time'] < self.configs['reclaim_time_interval']:
            return False
        if self.configs['exec_cnt'] - self.mglru.get_request_seq_of_last_gen() < self.configs['lru_gen_interval']:
            return False
        self.configs['last_reclaim_time'] = time.time()
        self.mglru.add_gen(request_seq_id=self.configs['exec_cnt'])
        self.mglru.do_reclaim()
        return True

    def start_semiwarm_routine(self, delay_time, reclaim_amount_per_second):
        gevent.spawn(self.semiwarm_routine, self.configs['exec_cnt'], delay_time, reclaim_amount_per_second)

    def semiwarm_routine(self, event_id, delay_time, reclaim_amount_per_second):
        if delay_time > config.CONTAINER_IDLE_LIFETIME - 5:
            return
        start_time = time.time()
        gevent.sleep(delay_time)
        if event_id != self.configs['exec_cnt']:
            return
        self.mglru.add_gen(request_seq_id=self.configs['exec_cnt'])
        self.mglru.add_gen(request_seq_id=self.configs['exec_cnt'])
        reclaim_interval = 10
        wake_up_time = start_time + delay_time + reclaim_interval
        while True:
            gevent.sleep(wake_up_time - time.time())
            if event_id != self.configs['exec_cnt']:
                return
            past_time = time.time() - start_time
            if past_time > config.CONTAINER_IDLE_LIFETIME - reclaim_interval - 5:
                return
            left_memory = self.mglru.get_cur_memory()
            reclaim_amount = min(reclaim_amount_per_second * reclaim_interval, left_memory - config.MINIMAL_MEMORY)
            if reclaim_amount > 0:
                self.mglru.do_semiwarm_reclaim(reclaim_amount)
            if left_memory - reclaim_amount <= config.MINIMAL_MEMORY or reclaim_amount < 4096:
                return
            wake_up_time += reclaim_interval

    def tmo_routine(self):
        wakeup_time = time.time() + config.TMO_RECLAIM_INTERVAL
        while True:
            gevent.sleep(wakeup_time - time.time())
            if self.is_die:
                return
            if not self.will_die():
                self.mglru.do_tmo_psi_reclaim()
            wakeup_time += config.TMO_RECLAIM_INTERVAL

    def memory_report_routine(self):
        pre_mem = 0
        now_mem = 0
        while not self.is_die:
            if not self.will_die():
                pre_mem = now_mem
                now_mem = self.mglru.get_cur_memory()
                self.global_monitor.upd_memory(now_mem - pre_mem)
            gevent.sleep(config.MEMORY_REPORT_INTERVAL)
        pre_mem = now_mem
        now_mem = 0
        self.global_monitor.upd_memory(now_mem - pre_mem)

    def upd_memory_limit(self, target_memory, direct=False):
        if direct:
            logging.info(f'update memory to {target_memory}M')
            if target_memory > 0:
                self.container.update(mem_limit=f'{target_memory}M', memswap_limit='64G')
            else:
                self.mglru.force_offload(amount=1073741824)
            return
        self.configs['cgroup_event_id'] += 1
        gevent.spawn(self.set_cgroup_memory_limit, self.configs['cgroup_event_id'], target_memory)

    def gradual_offload(self, end_memory, keep_alive_time, delay_time):
        self.configs['cgroup_event_id'] += 1
        gevent.spawn(self.gradual_offload_event, self.configs['cgroup_event_id'], self.configs['now_memory'],
                     end_memory, keep_alive_time, delay_time)

    def gradual_offload_event(self, event_id, begin_memory, end_memory, keep_alive_time, delay_time):
        start_time = time.time()
        gevent.sleep(delay_time)
        while True:
            gevent.sleep(10)
            if self.configs['cgroup_event_id'] != event_id:
                return
            past_time = time.time() - start_time
            if past_time > keep_alive_time - 11:
                return
            if past_time <= delay_time:
                continue
            target_memory = begin_memory - (begin_memory - end_memory) * (past_time - delay_time) / (
                        keep_alive_time - delay_time)
            self.set_cgroup_memory_limit(event_id, int(target_memory))

    def run(self, request_info: RequestInfo):
        logging.info(f'function {self.function_name} exec start '
                     f'with {self.container.short_id} {request_info.handler_context}')
        self.get_page_mjfault_info()
        r = requests.get(container_url.format(self.port, 'run'), json={'handler_context': request_info.handler_context})
        assert r.status_code == 200
        duration = r.json()['duration']
        request_info.duration = duration
        # request_pg_in, request_pg_out = self.get_page_in_out_info()
        request_pgmjfault = self.get_page_mjfault_info()
        request_info.pgmjfault = request_pgmjfault
        if len(self.mglru.durations) == 8:
            request_info.return_infos['mglru_durations'] = self.mglru.durations
        logging.info(f'func {self.function_name} complete by {self.container.short_id}, '
                     f'duration: {format(duration, ".3f")}s, pg_mgfault: {request_pgmjfault}')
        self.last_time = time.time()

    def destroy(self):
        self.is_die = True
        self.global_monitor.free_memory(self.configs['now_memory'])
        self.global_monitor.del_container()
        self.container.remove(force=True)

