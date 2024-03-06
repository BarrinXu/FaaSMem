from gevent import monkey

monkey.patch_all()
import random
from copy import deepcopy
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
latencies = []
request_infos = {}
ids = {}
flag = 0
request_interval = 0

test_end = False
optimized_memory = None

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
    r = requests.get(gateway_url.format('run'), json=request_info, timeout=60)
    ed = time.time()


def end_loop(idx, function_name, parallel):
    while not test_end:
        post_request('request_' + str(idx).rjust(5, '0'), function_name)
        if request_interval > 0:
            gevent.sleep(request_interval)
        idx += parallel


input_args = ''.join(sys.argv[1:])


def cal_percentile(data):
    percents = [50, 90, 95, 99]
    for percent in percents:
        print(f'P{percent}: ', format(np.percentile(data, percent), '.3f'))


def clean_worker(addr, data):
    r = requests.get(f'http://{addr}:7999/clear', json=data)
    assert r.status_code == 200


def finish_worker(addr):
    r = requests.post(f'http://{addr}:8000/finish')
    assert r.status_code == 200


def init_analyzer(function_name, ANALYZER_LOG_THRESHOLD, exec_memory):
    r = requests.get(f'http://{config.ANALYZER_URL}/test', json={'function_name': function_name,
                                                                 'ANALYZER_LOG_THRESHOLD': ANALYZER_LOG_THRESHOLD,
                                                                 'exec_memory': exec_memory})
    global test_end, optimized_memory
    test_end = True
    optimized_memory = r.json()['optimized_memory']


def test_to_one(function_name, loop_cnt, ANALYZER_LOG_THRESHOLD, AB_TEST_FACTOR, upd_configs):
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
                                                                   'upd_configs': {'AB_TEST_FACTOR': AB_TEST_FACTOR}})
    global ids, latencies, test_end
    ids = {}
    latencies = []
    test_end = False
    gevent.spawn(init_analyzer, function_name, ANALYZER_LOG_THRESHOLD, upd_configs['exec_memory'])
    gevent.sleep(5)

    # print(f'firing {function_name} with loop {loop_cnt} for {duration} s with {memory}M memory')
    # print(f'firing {function_name} with_loop {loop_cnt} with A/B test upd threshold {ANALYZER_LOG_THRESHOLD}')
    # print(f'request_interval {request_interval} s {upd_configs}')

    st = time.time()
    events = []
    for i in range(loop_cnt):
        events.append(gevent.spawn_later(i * 1, end_loop, i, function_name, loop_cnt))
    for e in events:
        e.join()
    ed = time.time()
    print(f'optimized_memory: {optimized_memory}', f'elapsed_time: {ed - st}')
    return optimized_memory, ed - st


def test_to_one_repeat(function_name, loop_cnt, ANALYZER_LOG_THRESHOLD, AB_TEST_FACTOR, upd_configs):
    res = []
    elapsed_time = []
    print(f'firing {function_name} with_loop {loop_cnt} with '
          f'threshold {ANALYZER_LOG_THRESHOLD} factor{AB_TEST_FACTOR}')
    print(f'request_interval {request_interval} s {upd_configs}')
    for i in range(20):
        now_memory_res, now_elapsed_time = test_to_one(function_name, loop_cnt, ANALYZER_LOG_THRESHOLD, AB_TEST_FACTOR,
                                                       upd_configs)
        res.append(now_memory_res)
        elapsed_time.append(now_elapsed_time)
    cal_percentile(res)
    nowtime = str(datetime.datetime.now())
    suffix = 'ABtest_' + function_name + '_' + str(loop_cnt) + '_' + str(ANALYZER_LOG_THRESHOLD) + '_' + str(
        AB_TEST_FACTOR) + '_' + str(upd_configs['exec_memory']) + f'_({input_args})'
    if not os.path.exists('result'):
        os.mkdir('result')
    filepath = os.path.join('result', nowtime + '_' + suffix + '.json')
    save_logs = {'configs': upd_configs, 'function_name': function_name, 'loop_cnt': loop_cnt,
                 'ANALYZER_LOG_THRESHOLD': ANALYZER_LOG_THRESHOLD, 'AB_TEST_FACTOR': AB_TEST_FACTOR,
                 'args': input_args, 'res': res, 'elapsed_time': elapsed_time}
    with open(filepath, 'w') as f:
        json.dump(save_logs, f)


def test_to_all():
    print(input_args)
    wordcount_general_configs = {'exec_memory': 512, 'idle_memory': 512, 'exec_tuning': True, 'cpu': 0.5}
    matrix_operation_general_configs = {'exec_memory': 512, 'idle_memory': 512, 'exec_tuning': True, 'cpu': 0.2}
    target_functions = {
        # 'html_server': [
            # {'loop': 8, 'ANALYZER_LOG_THRESHOLD': 32,
            #  'configs': {'raw_memory': 354, 'exec_memory': 354, 'idle_memory': 354, 'exec_tuning': True, 'cpu': 0.2}},
            # {'loop': 8, 'ANALYZER_LOG_THRESHOLD': 64,
            #  'configs': {'raw_memory': 354, 'exec_memory': 354, 'idle_memory': 354, 'exec_tuning': True, 'cpu': 0.2}},
            # {'loop': 8, 'ANALYZER_LOG_THRESHOLD': 128,
            #  'configs': {'raw_memory': 354, 'exec_memory': 354, 'idle_memory': 354, 'exec_tuning': True, 'cpu': 0.2}},
            # {'loop': 8, 'ANALYZER_LOG_THRESHOLD': 256,
            #  'configs': {'raw_memory': 354, 'exec_memory': 354, 'idle_memory': 354, 'exec_tuning': True, 'cpu': 0.2}},
            # {'loop': 8, 'ANALYZER_LOG_THRESHOLD': 512,
            #  'configs': {'raw_memory': 354, 'exec_memory': 354, 'idle_memory': 354, 'exec_tuning': True, 'cpu': 0.2}},
        # ],
        # 'graph_bfs': [
        #     {'loop': 8, 'ANALYZER_LOG_THRESHOLD': 32,
        #      'configs': {'raw_memory': 354, 'exec_memory': 354, 'idle_memory': 354, 'exec_tuning': True, 'cpu': 0.2}},
        #     {'loop': 8, 'ANALYZER_LOG_THRESHOLD': 64,
        #      'configs': {'raw_memory': 354, 'exec_memory': 354, 'idle_memory': 354, 'exec_tuning': True, 'cpu': 0.2}},
        #     {'loop': 8, 'ANALYZER_LOG_THRESHOLD': 128,
        #      'configs': {'raw_memory': 354, 'exec_memory': 354, 'idle_memory': 354, 'exec_tuning': True, 'cpu': 0.2}},
        #     {'loop': 8, 'ANALYZER_LOG_THRESHOLD': 256,
        #      'configs': {'raw_memory': 354, 'exec_memory': 354, 'idle_memory': 354, 'exec_tuning': True, 'cpu': 0.2}},
        #     {'loop': 8, 'ANALYZER_LOG_THRESHOLD': 512,
        #      'configs': {'raw_memory': 354, 'exec_memory': 354, 'idle_memory': 354, 'exec_tuning': True, 'cpu': 0.2}},
        # ],
        'recognizer_adult': [
            {'loop': 8, 'ANALYZER_LOG_THRESHOLD': 32,
             'configs': {'raw_memory': 885, 'exec_memory': 885, 'idle_memory': 885, 'exec_tuning': True, 'cpu': 0.5}},
            {'loop': 8, 'ANALYZER_LOG_THRESHOLD': 64,
             'configs': {'raw_memory': 885, 'exec_memory': 885, 'idle_memory': 885, 'exec_tuning': True, 'cpu': 0.5}},
            {'loop': 8, 'ANALYZER_LOG_THRESHOLD': 128,
             'configs': {'raw_memory': 885, 'exec_memory': 885, 'idle_memory': 885, 'exec_tuning': True, 'cpu': 0.5}},
            {'loop': 8, 'ANALYZER_LOG_THRESHOLD': 256,
             'configs': {'raw_memory': 885, 'exec_memory': 885, 'idle_memory': 885, 'exec_tuning': True, 'cpu': 0.5}},
            {'loop': 8, 'ANALYZER_LOG_THRESHOLD': 512,
             'configs': {'raw_memory': 885, 'exec_memory': 885, 'idle_memory': 885, 'exec_tuning': True, 'cpu': 0.5}},
        ],
    }
    for function_name in target_functions:
        entry = deepcopy(target_functions[function_name][0])
        # for ANALYZER_LOG_THRESHOLD in [32, 64, 128, 256, 512]:
        for ANALYZER_LOG_THRESHOLD in [32, 64, 128, 128, 256, 512]:
            for AB_TEST_FACTOR in [0.7]:
                entry.update({'ANALYZER_LOG_THRESHOLD': ANALYZER_LOG_THRESHOLD, 'AB_TEST_FACTOR': AB_TEST_FACTOR})
                test_to_one_repeat(function_name, entry['loop'], entry['ANALYZER_LOG_THRESHOLD'],
                                   entry['AB_TEST_FACTOR'], entry['configs'])

        # for entry in target_functions[fuction_name]:
        #         test_to_one_repeat(function_name, entry['loop'], entry['ANALYZER_LOG_THRESHOLD'], entry['configs'])


test_to_all()
