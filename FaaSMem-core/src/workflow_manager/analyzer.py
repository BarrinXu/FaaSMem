from gevent import monkey

monkey.patch_all()
from gevent import event
import logging
import math
import numpy as np
import math
import gevent
import sys

sys.path.append('../../')
import time
import random
from config import config
from gevent.pywsgi import WSGIServer
from flask import Flask, request
import requests

worker_nums = len(config.WORKERS_IP)
app = Flask(__name__)
ANALYZER_LOG_THRESHOLD = -1


class LogRepo:
    def __init__(self, function_name, exec_memory):
        self.function_name = function_name
        self.tuning_id = 0
        self.optimized_memory = exec_memory
        self.reduce_factor = 0.7
        self.memory_logs: dict[int, list] = {}
        self.result = event.AsyncResult()
        requests.get(f'http://{config.GATEWAY_URL}/upd_configs',
                     json={'function_name': self.function_name,
                           'upd_configs': {'exec_tuning_memory': int(self.optimized_memory * self.reduce_factor)}})
        logging.info(f'set {self.function_name} exec-tuning-memory to {int(self.optimized_memory * self.reduce_factor)}')

    def make_policy(self):

        # Todo: add variance analysis, or collect kernel-level / cpu-level metrics.
        print(self.function_name)
        # for memory, logs in self.memory_logs.items():
        #     print(f'{memory}M : {len(logs)} requests total')
        memories = list(self.memory_logs.keys())
        memories.sort()
        assert len(memories) == 2
        low_memory = memories[0]
        normal_memory = memories[1]
        low_logs = self.memory_logs[low_memory]
        normal_logs = self.memory_logs[normal_memory]
        low_avg = np.average(low_logs)
        normal_avg = np.average(normal_logs)
        # low_std = np.std(low_logs)
        # normal_std = np.std(normal_logs)
        low_95 = np.percentile(low_logs, 95)
        normal_95 = np.percentile(normal_logs, 95)
        low_99 = np.percentile(low_logs, 99)
        normal_99 = np.percentile(normal_logs, 99)
        logging.info(
            f'making exec-memory policy for {self.function_name},\n'
            f'norm_mem: {normal_memory}M, '
            f'norm_avg: {format(normal_avg, ".4f")}s, norm_P95: {format(normal_95, ".4f")}, '
            f'norm_P99: {format(normal_99, ".4f")}, norm_cnt: {len(normal_logs)}\n'
            f'low_mem: {low_memory}M, '
            f'low_avg: {format(low_avg, ".4f")}s, low_P95: {format(low_95, ".4f")}, '
            f'low_P99: {format(low_99, ".4f")}, low_cnt: {len(low_logs)}')
        # Todo: Design more applicable policy
        # Todo: For latency-sensitive function, add condition for std_variance or P99.
        if low_avg / normal_avg < 1.1 and low_95 / normal_95 < 1.1:
            self.optimized_memory = low_memory
            return 'OK'
        else:
            return 'FAIL'

    def upd_config(self):
        if len(self.memory_logs) <= 1:
            return
        if len(self.memory_logs) > 2:
            raise Exception('Cannot handle more than 2 types memory configs')
        for logs in self.memory_logs.values():
            if len(logs) < ANALYZER_LOG_THRESHOLD:
                return
        status = self.make_policy()
        if status == 'FAIL' and self.reduce_factor + 0.1 > 0.99:
            self.tuning_id = -1
            self.result.set(1)
            return

        self.tuning_id += 1
        self.memory_logs.clear()
        if status == 'FAIL':
            self.reduce_factor += 0.1
        exec_tuning_memory = int(self.optimized_memory * self.reduce_factor)
        logging.info(f'set {self.function_name} exec-tuning-memory to {exec_tuning_memory}')
        gevent.spawn(requests.get, f'http://{config.GATEWAY_URL}/upd_configs',
                     json={'function_name': self.function_name,
                           'upd_configs': {'tuning_id': self.tuning_id,
                                           'exec_tuning_memory': exec_tuning_memory}})


    def add_log(self, exec_config, duration):
        if exec_config['tuning_id'] != self.tuning_id:
            return
        exec_memory = exec_config['exec_memory']
        if exec_memory not in self.memory_logs:
            self.memory_logs[exec_memory] = []
        self.memory_logs[exec_memory].append(duration)
        self.upd_config()


# functions_logs: dict[str, LogRepo] = {}
functions_logs = {}


@app.route('/test')
def test():
    data = request.get_json(force=True, silent=True)
    global ANALYZER_LOG_THRESHOLD
    ANALYZER_LOG_THRESHOLD = data['ANALYZER_LOG_THRESHOLD']
    function_name = data['function_name']
    exec_memory = data['exec_memory']
    functions_logs.clear()
    functions_logs[function_name] = LogRepo(function_name, exec_memory)
    functions_logs[function_name].result.get()
    print('optimized_memory', functions_logs[function_name].optimized_memory)
    return {'optimized_memory': functions_logs[function_name].optimized_memory}


@app.route('/post_result', methods=['POST'])
def run():
    data = request.get_json(force=True, silent=True)
    function_name = data['function_name']
    functions_logs[function_name].add_log(data['exec_config'], data['duration'])

    return 'OK', 200


if __name__ == '__main__':
    logging.basicConfig(format='%(asctime)s %(message)s', datefmt='%H:%M:%S', level='INFO')
    server = WSGIServer(('127.0.0.1', 7001), app, log=None)
    server.serve_forever()
