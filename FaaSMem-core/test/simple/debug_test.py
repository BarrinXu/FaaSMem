from gevent import monkey

monkey.patch_all()
import make_handler_context
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
pre_time = 60
latencies = []
request_infos = {}
ids = {}
flag = 0
request_interval = 0


def post_request(request_id, function_name):
    # global flag
    # flag += 1
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
        # print(idx % parallel, 'start')
        post_request('request_' + str(idx).rjust(5, '0'), function_name)
        # print(idx % parallel, 'end')
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


def start_monitor(addr):
    r = requests.get(f'http://{addr}:8000/start_monitor')
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
        clean_worker(worker_ip, {'upd_configs': {function_name: upd_configs}})
    for worker_ip in config.WORKERS_IP:
        start_monitor(worker_ip)

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
        cal_percentile()
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
    wordcount_general_configs = {'exec_memory': 512, 'idle_memory': 512, 'exec_tuning': False, 'cpu': 0.5}
    matrix_operation_general_configs = {'exec_memory': 512, 'idle_memory': 512, 'exec_tuning': False, 'cpu': 0.2}
    target_functions = {
        'html_server': [
            # {'loop': 1, 'duration': 1,
            #  'configs': {'raw_memory': 354, 'exec_memory': 260, 'idle_memory': 260, 'exec_tuning': False, 'cpu': 0.2}},
            # {'loop': 1, 'duration': 1,
            #  'configs': {'raw_memory': 384, 'exec_memory': 64, 'idle_memory': 64, 'exec_tuning': False, 'cpu': 0.2}},
        ],
        'graph_bfs': [
            # {'loop': 8, 'duration': 1,
            #  'configs': {'raw_memory': 384, 'exec_memory': 384, 'idle_memory': 384, 'exec_tuning': False, 'cpu': 0.2}},
            # {'loop': 32, 'duration': 60,
            #  'configs': {'raw_memory': 384, 'exec_memory': 384, 'idle_memory': 384, 'exec_tuning': False, 'cpu': 0.2}},
            # {'loop': 64, 'duration': 60,
            #  'configs': {'raw_memory': 384, 'exec_memory': 128, 'idle_memory': 128, 'exec_tuning': False, 'cpu': 0.2}},
            # {'loop': 4, 'duration': 1,
            #  'configs': {'raw_memory': 384, 'exec_memory': 223, 'idle_memory': 64, 'exec_tuning': False, 'cpu': 0.2}},
            # {'loop': 16, 'duration': 1,
            #  'configs': {'raw_memory': 384, 'exec_memory': 223, 'idle_memory': 64, 'exec_tuning': False, 'cpu': 0.2}},
            # {'loop': 32, 'duration': 1,
            #  'configs': {'raw_memory': 384, 'exec_memory': 223, 'idle_memory': 64, 'exec_tuning': False, 'cpu': 0.2}},
            # {'loop': 8, 'duration': 1,
            #  'configs': {'raw_memory': 384, 'exec_memory': 160, 'idle_memory': 160, 'exec_tuning': False, 'cpu': 0.2}},
            # {'loop': 16, 'duration': 1,
            #  'configs': {'raw_memory': 384, 'exec_memory': 160, 'idle_memory': 160, 'exec_tuning': False, 'cpu': 0.2}},
            # {'loop': 32, 'duration': 1,
            #  'configs': {'raw_memory': 384, 'exec_memory': 160, 'idle_memory': 160, 'exec_tuning': False, 'cpu': 0.2}},
        ],
        'recognizer_adult': [
            # {'loop': 1, 'duration': 1,
            #  'configs': {'raw_memory': 885, 'exec_memory': 248, 'idle_memory': 248, 'exec_tuning': False, 'cpu': 0.5}},
            {'loop': 1, 'duration': 3,
             'configs': {'raw_memory': 885, 'exec_memory': 885, 'idle_memory': 885, 'exec_tuning': False, 'cpu': 0.5}},
            # {'loop': 1, 'duration': 1,
            #  'configs': {'raw_memory': 512, 'exec_memory': 160, 'idle_memory': 160, 'exec_tuning': False, 'cpu': 0.5}},
            # {'loop': 1, 'duration': 1,
            #  'configs': {'raw_memory': 512, 'exec_memory': 128, 'idle_memory': 128, 'exec_tuning': False, 'cpu': 0.5}},
        ],
        # 'float_operation': [
        #     {'loop': 1, 'duration': 1,
        #      'configs': {'raw_memory': 354, 'exec_memory': 354, 'idle_memory': 354, 'exec_tuning': False, 'cpu': 0.1}},
        #     {'loop': 1, 'duration': 1,
        #      'configs': {'raw_memory': 354, 'exec_memory': 32, 'idle_memory': 32, 'exec_tuning': False, 'cpu': 0.1}},
        #     {'loop': 1, 'duration': 1,
        #      'configs': {'raw_memory': 354, 'exec_memory': 24, 'idle_memory': 24, 'exec_tuning': False, 'cpu': 0.1}},
        #     {'loop': 1, 'duration': 1,
        #      'configs': {'raw_memory': 354, 'exec_memory': 16, 'idle_memory': 16, 'exec_tuning': False, 'cpu': 0.1}},
        # ],
        # 'matmul': [
        #     {'loop': 1, 'duration': 1,
        #      'configs': {'raw_memory': 354, 'exec_memory': 354, 'idle_memory': 354, 'exec_tuning': False, 'cpu': 0.1}},
        #     {'loop': 1, 'duration': 1,
        #      'configs': {'raw_memory': 354, 'exec_memory': 64, 'idle_memory': 64, 'exec_tuning': False, 'cpu': 0.1}},
        #     {'loop': 1, 'duration': 1,
        #      'configs': {'raw_memory': 354, 'exec_memory': 48, 'idle_memory': 48, 'exec_tuning': False, 'cpu': 0.1}},
        #     {'loop': 1, 'duration': 1,
        #      'configs': {'raw_memory': 354, 'exec_memory': 32, 'idle_memory': 32, 'exec_tuning': False, 'cpu': 0.1}},
        # ],
        # 'linpack': [
        #     {'loop': 1, 'duration': 1,
        #      'configs': {'raw_memory': 354, 'exec_memory': 354, 'idle_memory': 354, 'exec_tuning': False, 'cpu': 0.1}},
        #     {'loop': 1, 'duration': 1,
        #      'configs': {'raw_memory': 354, 'exec_memory': 64, 'idle_memory': 64, 'exec_tuning': False, 'cpu': 0.1}},
        #     {'loop': 1, 'duration': 1,
        #      'configs': {'raw_memory': 354, 'exec_memory': 48, 'idle_memory': 48, 'exec_tuning': False, 'cpu': 0.1}},
        #     {'loop': 1, 'duration': 1,
        #      'configs': {'raw_memory': 354, 'exec_memory': 32, 'idle_memory': 32, 'exec_tuning': False, 'cpu': 0.1}},
        # ],
        # 'image_processing': [
        #     {'loop': 1, 'duration': 1,
        #      'configs': {'raw_memory': 354, 'exec_memory': 354, 'idle_memory': 354, 'exec_tuning': False, 'cpu': 0.1}},
        #     {'loop': 1, 'duration': 1,
        #      'configs': {'raw_memory': 354, 'exec_memory': 96, 'idle_memory': 96, 'exec_tuning': False, 'cpu': 0.1}},
        #     {'loop': 1, 'duration': 1,
        #      'configs': {'raw_memory': 354, 'exec_memory': 80, 'idle_memory': 80, 'exec_tuning': False, 'cpu': 0.1}},
        #     {'loop': 1, 'duration': 1,
        #      'configs': {'raw_memory': 354, 'exec_memory': 64, 'idle_memory': 64, 'exec_tuning': False, 'cpu': 0.1}},
        #     {'loop': 1, 'duration': 1,
        #      'configs': {'raw_memory': 354, 'exec_memory': 48, 'idle_memory': 48, 'exec_tuning': False, 'cpu': 0.1}},
        #     {'loop': 1, 'duration': 1,
        #      'configs': {'raw_memory': 354, 'exec_memory': 32, 'idle_memory': 32, 'exec_tuning': False, 'cpu': 0.1}},
        # ],
        # 'video_processing': [
        #     {'loop': 1, 'duration': 1,
        #      'configs': {'raw_memory': 354, 'exec_memory': 354, 'idle_memory': 354, 'exec_tuning': False, 'cpu': 0.1}},
        # ],
        # 'chameleon': [
        #     {'loop': 1, 'duration': 1,
        #      'configs': {'raw_memory': 354, 'exec_memory': 354, 'idle_memory': 354, 'exec_tuning': False, 'cpu': 0.1}},
        #     {'loop': 1, 'duration': 1,
        #      'configs': {'raw_memory': 354, 'exec_memory': 32, 'idle_memory': 32, 'exec_tuning': False, 'cpu': 0.1}},
        #     {'loop': 1, 'duration': 1,
        #      'configs': {'raw_memory': 354, 'exec_memory': 24, 'idle_memory': 24, 'exec_tuning': False, 'cpu': 0.1}},
        #     {'loop': 1, 'duration': 1,
        #      'configs': {'raw_memory': 354, 'exec_memory': 16, 'idle_memory': 16, 'exec_tuning': False, 'cpu': 0.1}},
        # ],
        # 'pyaes': [
        #     {'loop': 1, 'duration': 1,
        #      'configs': {'raw_memory': 354, 'exec_memory': 354, 'idle_memory': 354, 'exec_tuning': False, 'cpu': 0.1}},
        #     {'loop': 1, 'duration': 1,
        #      'configs': {'raw_memory': 354, 'exec_memory': 32, 'idle_memory': 32, 'exec_tuning': False, 'cpu': 0.1}},
        #     {'loop': 1, 'duration': 1,
        #      'configs': {'raw_memory': 354, 'exec_memory': 24, 'idle_memory': 24, 'exec_tuning': False, 'cpu': 0.1}},
        #     {'loop': 1, 'duration': 1,
        #      'configs': {'raw_memory': 354, 'exec_memory': 16, 'idle_memory': 16, 'exec_tuning': False, 'cpu': 0.1}},
        #
        # ],
        # 'model_training': [
        #     {'loop': 1, 'duration': 1,
        #      'configs': {'raw_memory': 885, 'exec_memory': 885, 'idle_memory': 885, 'exec_tuning': False, 'cpu': 1}},
        # ],
        # 'gzip_compression': [
        #     {'loop': 1, 'duration': 1,
        #      'configs': {'raw_memory': 354, 'exec_memory': 354, 'idle_memory': 354, 'exec_tuning': False, 'cpu': 0.1}},
        #     {'loop': 1, 'duration': 1,
        #      'configs': {'raw_memory': 354, 'exec_memory': 32, 'idle_memory': 32, 'exec_tuning': False, 'cpu': 0.1}},
        #     {'loop': 1, 'duration': 1,
        #      'configs': {'raw_memory': 354, 'exec_memory': 24, 'idle_memory': 24, 'exec_tuning': False, 'cpu': 0.1}},
        #     {'loop': 1, 'duration': 1,
        #      'configs': {'raw_memory': 354, 'exec_memory': 16, 'idle_memory': 16, 'exec_tuning': False, 'cpu': 0.1}},
        # ],
        # 'json_dumps_loads': [
        #     {'loop': 1, 'duration': 1,
        #      'configs': {'raw_memory': 354, 'exec_memory': 354, 'idle_memory': 354, 'exec_tuning': False, 'cpu': 0.1}},
        #     {'loop': 1, 'duration': 1,
        #      'configs': {'raw_memory': 354, 'exec_memory': 64, 'idle_memory': 64, 'exec_tuning': False, 'cpu': 0.1}},
        #     {'loop': 1, 'duration': 1,
        #      'configs': {'raw_memory': 354, 'exec_memory': 48, 'idle_memory': 48, 'exec_tuning': False, 'cpu': 0.1}},
        #     {'loop': 1, 'duration': 1,
        #      'configs': {'raw_memory': 354, 'exec_memory': 32, 'idle_memory': 32, 'exec_tuning': False, 'cpu': 0.1}},
        #
        # ],
    }
    for function_name in target_functions:
        for entry in target_functions[function_name]:
            test_to_one(function_name, entry['loop'], 60 * entry['duration'], entry['configs'])


test_to_all()
