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

sys.path.append('../../')
import requests
from config import config

gateway_url = 'http://' + config.GATEWAY_URL + '/{}'
pre_time = 1 * 60
latencies = []
request_infos = {}
ids = {}
flag = 0
request_interval = 0

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
    # global flag
    # flag += 1
    handler_context = {}
    if function_name == 'graph_bfs':
        handler_context['id'] = get_pareto_num(graph_bfs_shape, graph_bfs_num)
    elif function_name == 'html_server':
        handler_context['id'] = get_pareto_num(html_server_shape, html_server_num)
    request_info = {'request_id': request_id,
                    'function_name': function_name,
                    'runtime_configs': {},
                    'handler_context': handler_context}
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


def cal_percentile():
    percents = [50, 90, 95, 99]
    for percent in percents:
        print(f'P{percent}: ', format(np.percentile(latencies, percent), '.3f'))


def clean_worker(addr, data):
    r = requests.get(f'http://{addr}:7999/clear', json=data)
    assert r.status_code == 200


def finish_worker(addr):
    r = requests.post(f'http://{addr}:8000/finish')
    assert r.status_code == 200


def test_to_one(function_name, loop_cnt, duration, upd_configs, swappniess):
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
        clean_worker(worker_ip, {'upd_configs': {function_name: upd_configs}})
    gevent.sleep(5)
    requests.get(f'http://{config.GATEWAY_URL}/upd_configs', json={'function_name': function_name,
                                                                   'upd_configs': {'swappniess': swappniess}})
    gevent.sleep(5)
    global ids, latencies
    ids = {}
    latencies = []
    # print(f'firing {function_name} with loop {loop_cnt} for {duration} s with {memory}M memory')
    print(f'firing {function_name} with '
          f'swappniess {swappniess} and memory {upd_configs["exec_memory"]} for {duration} s')
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
        cal_percentile()
    nowtime = str(datetime.datetime.now())
    suffix = 'swappniess_' + function_name + '_' + str(swappniess) + '_' + str(loop_cnt) + '_' + str(
        duration) + '_' + str(upd_configs['exec_memory']) + f'_({input_args})'
    if not os.path.exists('result'):
        os.mkdir('result')
    filepath = os.path.join('result', nowtime + '_' + suffix + '.json')
    save_logs = {'configs': upd_configs, 'function_name': function_name, 'loop_cnt': loop_cnt, 'duration': duration,
                 'args': input_args, 'latencies': latencies, 'swappniess': swappniess}
    with open(filepath, 'w') as f:
        json.dump(save_logs, f)


def test_to_all():
    print(input_args)
    # wordcount_general_configs = {'exec_memory': 512, 'idle_memory': 512, 'exec_tuning': False, 'cpu': 0.5}
    # matrix_operation_general_configs = {'exec_memory': 512, 'idle_memory': 512, 'exec_tuning': False, 'cpu': 0.2}
    target_functions = {
        # 'html_server': [
        #     {'loop': 8, 'duration': 2,
        #      'configs': {'raw_memory': 384, 'exec_memory': 384, 'idle_memory': 384, 'exec_tuning': False, 'cpu': 0.2}},
        #     {'loop': 8, 'duration': 2,
        #      'configs': {'raw_memory': 256, 'exec_memory': 256, 'idle_memory': 256, 'exec_tuning': False, 'cpu': 0.2}},
        #     {'loop': 8, 'duration': 2,
        #      'configs': {'raw_memory': 192, 'exec_memory': 192, 'idle_memory': 192, 'exec_tuning': False, 'cpu': 0.2}},
        #     {'loop': 8, 'duration': 2,
        #      'configs': {'raw_memory': 128, 'exec_memory': 128, 'idle_memory': 128, 'exec_tuning': False, 'cpu': 0.2}},
        #     {'loop': 8, 'duration': 2,
        #      'configs': {'raw_memory': 96, 'exec_memory': 96, 'idle_memory': 96, 'exec_tuning': False, 'cpu': 0.2}},
        #     {'loop': 8, 'duration': 2,
        #      'configs': {'raw_memory': 64, 'exec_memory': 64, 'idle_memory': 64, 'exec_tuning': False, 'cpu': 0.2}},
        # ],
        'graph_bfs': [
            {'loop': 8, 'duration': 3, 'swappniess': 10,
             'configs': {'raw_memory': 512, 'exec_memory': 150, 'idle_memory': 150, 'exec_tuning': False, 'cpu': 1}},
            # {'loop': 8, 'duration': 3, 'swappniess': 40,
            #  'configs': {'raw_memory': 512, 'exec_memory': 160, 'idle_memory': 160, 'exec_tuning': False, 'cpu': 0.5}},
            {'loop': 8, 'duration': 3, 'swappniess': 60,
             'configs': {'raw_memory': 512, 'exec_memory': 150, 'idle_memory': 150, 'exec_tuning': False, 'cpu': 1}},
            # {'loop': 8, 'duration': 3, 'swappniess': 80,
            #  'configs': {'raw_memory': 512, 'exec_memory': 160, 'idle_memory': 160, 'exec_tuning': False, 'cpu': 0.5}},
            {'loop': 8, 'duration': 3, 'swappniess': 90,
             'configs': {'raw_memory': 512, 'exec_memory': 150, 'idle_memory': 150, 'exec_tuning': False, 'cpu': 1}},
        ],
        # 'recognizer_adult': [
        #     {'loop': 8, 'duration': 3, 'swappniess': 10,
        #      'configs': {'raw_memory': 512, 'exec_memory': 160, 'idle_memory': 160, 'exec_tuning': False, 'cpu': 0.5}},
        #     {'loop': 8, 'duration': 3, 'swappniess': 40,
        #      'configs': {'raw_memory': 512, 'exec_memory': 160, 'idle_memory': 160, 'exec_tuning': False, 'cpu': 0.5}},
        #     {'loop': 8, 'duration': 3, 'swappniess': 60,
        #      'configs': {'raw_memory': 512, 'exec_memory': 160, 'idle_memory': 160, 'exec_tuning': False, 'cpu': 0.5}},
        #     {'loop': 8, 'duration': 3, 'swappniess': 80,
        #      'configs': {'raw_memory': 512, 'exec_memory': 160, 'idle_memory': 160, 'exec_tuning': False, 'cpu': 0.5}},
        #     {'loop': 8, 'duration': 3, 'swappniess': 90,
        #      'configs': {'raw_memory': 512, 'exec_memory': 160, 'idle_memory': 160, 'exec_tuning': False, 'cpu': 0.5}},
            # {'loop': 8, 'duration': 3, 'swappniess': 10,
            #  'configs': {'raw_memory': 512, 'exec_memory': 170, 'idle_memory': 170, 'exec_tuning': False, 'cpu': 0.5}},
            # {'loop': 8, 'duration': 3, 'swappniess': 40,
            #  'configs': {'raw_memory': 512, 'exec_memory': 170, 'idle_memory': 170, 'exec_tuning': False, 'cpu': 0.5}},
            # {'loop': 8, 'duration': 3, 'swappniess': 60,
            #  'configs': {'raw_memory': 512, 'exec_memory': 170, 'idle_memory': 170, 'exec_tuning': False, 'cpu': 0.5}},
            # {'loop': 8, 'duration': 3, 'swappniess': 70,
            #  'configs': {'raw_memory': 512, 'exec_memory': 170, 'idle_memory': 170, 'exec_tuning': False, 'cpu': 0.5}},
            # {'loop': 8, 'duration': 3, 'swappniess': 90,
            #  'configs': {'raw_memory': 512, 'exec_memory': 170, 'idle_memory': 170, 'exec_tuning': False, 'cpu': 0.5}},
        # ],
    }
    for function_name in target_functions:
        for entry in target_functions[function_name]:
            test_to_one(function_name, entry['loop'], 60 * entry['duration'], entry['configs'], entry['swappniess'])


test_to_all()
