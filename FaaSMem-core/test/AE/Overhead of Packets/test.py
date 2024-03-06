from gevent import monkey

monkey.patch_all()
import random
import json
import os
import sys
import time
import gevent
from tqdm import tqdm
import numpy as np
import requests
import datetime

sys.path.append('../../')
sys.path.append('../../../')

from common_lib import make_handler_context
from common_lib import ops



from config import config

gateway_url = 'http://' + config.GATEWAY_URL + '/{}'

graph_bfs_shape = 0.1
html_server_shape = 0.8

graph_bfs_num = 100000
html_server_num = 50

latencies = []
firing_timestamps = []
request_infos = {}
mglru_durations = []
ids = {}
input_args = ''.join(sys.argv[1:])
this_round_end = False

def post_request(request_id, function_name):
    request_info = {'request_id': request_id,
                    'function_name': function_name,
                    'runtime_configs': {},
                    'handler_context': make_handler_context.make_context(function_name)}
    st = time.time()
    r = requests.get(gateway_url.format('run'), json=request_info)
    ed = time.time()
    ids[request_id] = {'time': ed - st, 'st': st, 'ed': ed, 'latency': r.json()['latency']}
    latencies.append(r.json()['latency'])
    firing_timestamps.append(st)
    res = r.json()['return_infos']
    if 'mglru_durations' in res:
        mglru_durations.append(res['mglru_durations'])
        global this_round_end
        this_round_end = True
    # print(request_id, ed - st, r.json())


def test_to_one(function_name, upd_configs):
    global ids, latencies, firing_timestamps, this_round_end
    ids = {}

    print(f'firing {function_name}')

    global mglru_durations
    mglru_durations = []

    for i in range(10):
        for worker_ip in config.WORKERS_IP:
            ops.clean_worker(worker_ip, {'upd_configs': {function_name: upd_configs}})
        request_idx = 0
        this_round_end = False
        while not this_round_end:
            post_request('request_' + str(request_idx).rjust(5, '0'), function_name)
            gevent.sleep(0.1)

    # get_use_container_log(function_name, loop_cnt, duration)

    print('avg:', format(sum(latencies) / len(latencies), '.3f'))
    ops.cal_percentile(latencies)

    nowtime = str(datetime.datetime.now())
    system_tag = ''
    suffix = (f'MglruDuration_'
              f'{function_name}_'
              f'({upd_configs["system"]}{system_tag})')
    if not os.path.exists('result'):
        os.mkdir('result')
    filepath = os.path.join('result', nowtime + '_' + suffix + '.json')
    save_logs = {'configs': upd_configs,
                 'function_name': function_name,
                 'mglru_durations': mglru_durations,
                 'args': input_args}
    with open(filepath, 'w') as f:
        json.dump(save_logs, f)


def test_to_all():
    general_tests = {
        0: {'trace_id': 0, 'start_idx': 25011, 'exp_duration': 3600},
        # '0-ablation': {'trace_id': 0, 'start_idx': 8967, 'exp_duration': 3600 * 8},
        '0-ablation': {'trace_id': 3, 'start_idx': 52391, 'exp_duration': 3600 * 8},
        2: {'trace_id': 2, 'start_idx': 502, 'exp_duration': 3600},

        3: {'trace_id': 3, 'start_idx': 27267, 'exp_duration': 3600},
        4: {'trace_id': 4, 'start_idx': 0, 'exp_duration': 3600},
        5: {'trace_id': 5, 'start_idx': 6168, 'exp_duration': 3600},
        6: {'trace_id': 6, 'start_idx': 35316, 'exp_duration': 3600},
        7: {'trace_id': 7, 'start_idx': 42167, 'exp_duration': 3600},

        60: {'trace_id': 60, 'start_idx': 0, 'exp_duration': 3600},

    }
    target_functions = {

        'graph_bfs': {'configs': {'raw_memory': 885, 'cpu': 0.5, 'exec_duration': 0.3}, 'tests': [
            {'test_id': 2, 'configs': {'system': 'FaaSMem'}},
        ]},
        'bert': {'configs': {'raw_memory': 1770, 'cpu': 1, 'exec_duration': 0.15}, 'tests': [
            {'test_id': 2, 'configs': {'system': 'FaaSMem'}},
        ]},
        'html_server': {'configs': {'raw_memory': 354, 'cpu': 0.2, 'exec_duration': 0.15}, 'tests': [
            {'test_id': 2, 'configs': {'system': 'FaaSMem'}},
        ]},

        'float_operation': {'configs': {'raw_memory': 177, 'cpu': 0.1, 'exec_duration': 0.3}, 'tests': [
            {'test_id': 2, 'configs': {'system': 'FaaSMem'}},
        ]},
        'matmul': {'configs': {'raw_memory': 177, 'cpu': 0.1, 'exec_duration': 1.1}, 'tests': [
            {'test_id': 2, 'configs': {'system': 'FaaSMem'}},
        ]},
        'linpack': {'configs': {'raw_memory': 177, 'cpu': 0.1, 'exec_duration': 0.65}, 'tests': [
            {'test_id': 2, 'configs': {'system': 'FaaSMem'}},
        ]},
        'image_processing': {'configs': {'raw_memory': 177, 'cpu': 0.1, 'exec_duration': 1.3}, 'tests': [
            {'test_id': 2, 'configs': {'system': 'FaaSMem'}},
        ]},
        'chameleon': {'configs': {'raw_memory': 177, 'cpu': 0.1, 'exec_duration': 0.5}, 'tests': [
            {'test_id': 2, 'configs': {'system': 'FaaSMem'}},
        ]},
        'pyaes': {'configs': {'raw_memory': 177, 'cpu': 0.1, 'exec_duration': 0.9}, 'tests': [
            {'test_id': 2, 'configs': {'system': 'FaaSMem'}},
        ]},
        'gzip_compression': {'configs': {'raw_memory': 177, 'cpu': 0.1, 'exec_duration': 0.4}, 'tests': [
            {'test_id': 2, 'configs': {'system': 'FaaSMem'}},
        ]},
        'json_dumps_loads': {'configs': {'raw_memory': 177, 'cpu': 0.1, 'exec_duration': 1}, 'tests': [
            {'test_id': 2, 'configs': {'system': 'FaaSMem'}},
        ]},

    }

    for function_name, entry in target_functions.items():
        common_configs = entry['configs']
        for test in entry['tests']:
            now_configs = {}
            now_configs.update(common_configs)
            now_configs.update(test['configs'])
            test_to_one(function_name, now_configs)


test_to_all()
