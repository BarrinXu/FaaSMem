from gevent import monkey

monkey.patch_all()
import random
import datetime
import json
import sys
import time
import os
import gevent
import numpy as np
import make_handler_context
import ops

sys.path.append('../../')
import requests
from config import config

gateway_url = 'http://' + config.GATEWAY_URL + '/{}'
pre_time = 1 * 60
latencies = []
request_infos = {}
ids = {}
flag = 0
request_interval = 0.8

graph_bfs_shape = 0.1
html_server_shape = 0.8

graph_bfs_num = 100000
html_server_num = 50


def get_pareto_num(pareto_shape, max_num):
    while True:
        x = random.paretovariate(pareto_shape)
        if x < max_num + 1:
            return int(x - 1)


def post_request(request_id, function_name):
    request_info = {'request_id': request_id,
                    'function_name': function_name,
                    'runtime_configs': {},
                    'handler_context': make_handler_context.make_context(function_name)}

    st = time.time()
    r = requests.get(gateway_url.format('run'), json=request_info)
    ed = time.time()
    if st > test_start + pre_time:
        ids[request_id] = {'time': ed - st, 'st': st, 'ed': ed, 'latency': r.json()['latency']}
        latencies.append(r.json()['latency'])
    # print(request_id, ed - st, r.json())


def end_loop(idx, function_name, parallel, duration):
    while time.time() - test_start < pre_time + duration:
        post_request('request_' + str(idx).rjust(5, '0'), function_name)
        if request_interval > 0:
            gevent.sleep(request_interval)
        idx += parallel


input_args = ''.join(sys.argv[1:])


def finish_worker(addr):
    r = requests.post(f'http://{addr}:8000/finish')
    assert r.status_code == 200


def test_to_one(function_name, loop_cnt, duration, upd_configs):
    # r = requests.get(f'http://{config.GATEWAY_IP}:7000/upd_configs',
    #                  json={'function_name': function_name, 'upd_configs': {'memory': memory}})
    # assert r.status_code == 200
    # threads_ = []
    # for addr in config.WORKER_ADDRS:
    #     t = threading.Thread(target=clean_worker, args=(addr, ))
    #     threads_.append(t)
    #     t.start()
    # for t in threads_:
    #     t.join()
    for worker_ip in config.WORKERS_IP:
        ops.clean_worker(worker_ip, {'upd_configs': {function_name: upd_configs}})
    for worker_ip in config.WORKERS_IP:
        ops.start_monitor(worker_ip)
    global ids, latencies
    ids = {}
    latencies = []
    # print(f'firing {function_name} with loop {loop_cnt} for {duration} s with {memory}M memory')
    print(f'firing {function_name} with_loop {loop_cnt} for {duration} s')
    print(f'request_interval {request_interval} s {upd_configs}')
    global test_start
    test_start = time.time()
    events = []
    for i in range(loop_cnt):
        events.append(gevent.spawn_later(i * 1, end_loop, i, function_name, loop_cnt, duration))
    for e in events:
        e.join()
    time.sleep(10)

    # threads_ = []
    # for addr in config.WORKER_ADDRS:
    #     t = threading.Thread(target=finish_worker, args=(addr,))
    #     threads_.append(t)
    #     t.start()
    # for t in threads_:
    #     t.join()

    print('total requests count:', len(latencies))
    # get_use_container_log(function_name, loop_cnt, duration)
    if len(latencies) > 0:
        print('avg:', format(sum(latencies) / len(latencies), '.3f'))
        ops.cal_percentile(latencies)
    # nowtime = str(datetime.datetime.now())
    # suffix = 'RDMAvsHDD_' + function_name + '_' + str(loop_cnt) + '_' + str(duration) + '_' + str(
    #     upd_configs['exec_memory']) + f'_({input_args})'
    # if not os.path.exists('result'):
    #     os.mkdir('result')
    # filepath = os.path.join('result', nowtime + '_' + suffix + '.json')
    # save_logs = {'configs': upd_configs, 'function_name': function_name, 'loop_cnt': loop_cnt, 'duration': duration,
    #              'args': input_args, 'latencies': latencies}
    # with open(filepath, 'w') as f:
    #     json.dump(save_logs, f)


def test_to_all():
    print(input_args)
    # wordcount_general_configs = {'exec_memory': 512, 'idle_memory': 512, 'exec_tuning': False, 'cpu': 0.5}
    # matrix_operation_general_configs = {'exec_memory': 512, 'idle_memory': 512, 'exec_tuning': False, 'cpu': 0.2}
    target_functions = {
        'bert': [
            # {'loop': 1, 'duration': 1,
            #  'configs': {
            #      'raw_memory': 1770, 'cpu': 1, 'system': 'DAMON-debug', }},
            # {'loop': 1, 'duration': 2,
            #  'configs': {
            #      'raw_memory': 1770, 'idle_memory': 360, 'cpu': 1, 'system': 'baseline', 'test_type': 'idle_offload'}},
            # {'loop': 1, 'duration': 2,
            #  'configs': {
            #      'raw_memory': 1770, 'idle_memory': 0, 'cpu': 1, 'system': 'baseline', 'test_type': 'idle_offload'}},

        ],

        'graph_bfs': [
            # {'loop': 1, 'duration': 2,
            #  'configs': {
            #      'raw_memory': 885, 'idle_memory': 885, 'cpu': 0.5, 'system': 'baseline', 'test_type': 'idle_offload'}},
            # {'loop': 1, 'duration': 2,
            #  'configs': {
            #      'raw_memory': 885, 'idle_memory': 164, 'cpu': 0.5, 'system': 'baseline', 'test_type': 'idle_offload'}},
            # {'loop': 1, 'duration': 2,
            #  'configs': {
            #      'raw_memory': 885, 'idle_memory': 0, 'cpu': 0.5, 'system': 'baseline', 'test_type': 'idle_offload'}},
        ],

        'html_server': [
            {'loop': 1, 'duration': 1,
             'configs': {
                 'raw_memory': 1770, 'cpu': 1, 'system': 'DAMON-debug', }},
            # {'loop': 1, 'duration': 2,
            #  'configs': {
            #      'raw_memory': 384, 'idle_memory': 384, 'cpu': 0.2, 'system': 'baseline', 'test_type': 'idle_offload'}},
            # {'loop': 1, 'duration': 2,
            #  'configs': {
            #      'raw_memory': 384, 'idle_memory': 48, 'cpu': 0.2, 'system': 'baseline', 'test_type': 'idle_offload'}},
            # {'loop': 1, 'duration': 2,
            #  'configs': {
            #      'raw_memory': 384, 'idle_memory': 0, 'cpu': 0.2, 'system': 'baseline', 'test_type': 'idle_offload'}},
        ],
    }
    for function_name in target_functions:
        for entry in target_functions[function_name]:
            test_to_one(function_name, entry['loop'], 60 * entry['duration'], entry['configs'])


test_to_all()
