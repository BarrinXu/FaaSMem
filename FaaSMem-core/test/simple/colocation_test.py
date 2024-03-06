from gevent import monkey

monkey.patch_all()
import random
import json
import os
import sys
import time
import gevent
import numpy as np
import requests
import datetime
import make_handler_context
import ops
sys.path.append('../../')

from config import config

gateway_url = 'http://' + config.GATEWAY_URL + '/{}'

graph_bfs_shape = 0.1
html_server_shape = 0.8

graph_bfs_num = 100000
html_server_num = 50

latencies = {}

request_infos = {}

input_args = ''.join(sys.argv[1:])
with open('../../trace/trace_tidy.json', 'r') as f:
    raw_trace = json.load(f)


def get_pareto_num(pareto_shape, max_num):
    while True:
        x = random.paretovariate(pareto_shape)
        if x < max_num + 1:
            return int(x - 1)


def clean_worker(addr, data):
    r = requests.get(f'http://{addr}:7999/clear', json=data)
    assert r.status_code == 200


def start_monitor(addr):
    r = requests.get(f'http://{addr}:8000/start_monitor')
    assert r.status_code == 200


def end_monitor(addr):
    r = requests.get(f'http://{addr}:8000/end_monitor')
    assert r.status_code == 200


def cal_percentile(logs):
    percents = [50, 90, 95, 99]
    for percent in percents:
        print(f'P{percent}: ', format(np.percentile(logs, percent), '.3f'))


def analysis_for_container_recall(start_timestamps, exec_duration, keep_alive=600):
    print('total request in now time window:', len(start_timestamps))
    end_timestamps = []
    container_idle_times = []
    idle_containers = []
    for time_stamp in start_timestamps:
        while len(end_timestamps) > 0 and end_timestamps[0] < time_stamp:
            idle_containers.append(end_timestamps.pop(0))
        if len(idle_containers) > 0 and idle_containers[-1] + keep_alive > time_stamp:
            container_idle_times.append(time_stamp - idle_containers.pop(-1))
        # else:
        #     container_idle_times.append(keep_alive)
        end_timestamps.append(time_stamp + exec_duration)
    container_idle_times.sort()
    # print(len(container_idle_times))
    # print(container_idle_times)
    return ops.cal_percentile(container_idle_times, percentile_number=99)


# def random_drop():
#     return random.random() < 1 / 3


def post_request(request_id, function_name):
    request_info = {'request_id': request_id,
                    'function_name': function_name,
                    'runtime_configs': {},
                    'handler_context': make_handler_context.make_context(function_name)}
    st = time.time()
    r = requests.get(gateway_url.format('run'), json=request_info)
    ed = time.time()

    latencies[function_name].append(r.json()['latency'])

    # print(request_id, ed - st, r.json())


def test_to_one(function_name, trace_id, start_idx, exp_duration, upd_configs):

    latencies[function_name] = []


    print(f'firing {function_name} with_trace_id {trace_id} with {exp_duration} s and {upd_configs}')
    incoming_timestamps = raw_trace['per_function_invocations'][trace_id]['incoming_timestamps'][start_idx:]
    print(f'total request in trace {function_name} {trace_id}: {len(incoming_timestamps)}')

    # for i in range(len(incoming_timestamps) - exp_cnt - 10):
    #     if incoming_timestamps[i + exp_cnt - 1] - incoming_timestamps[i] < 20000:
    #         incoming_timestamps = incoming_timestamps[i:]
    #         break

    start_timestamp = incoming_timestamps[0] - 1
    last_timestamp = incoming_timestamps[0] + exp_duration

    exec_duration = upd_configs['exec_duration'] * 1.2
    for i, time_stamp in enumerate(incoming_timestamps):
        if time_stamp > last_timestamp:
            incoming_timestamps = incoming_timestamps[:i]
            break

    print('---analysis for container reuse interval start---')
    semiwarm_delay = analysis_for_container_recall(incoming_timestamps, exec_duration=exec_duration)
    print('semiwarm_delay_ideal:', semiwarm_delay)
    semiwarm_delay = max(semiwarm_delay, 59)
    print('semiwarm_delay_real:', semiwarm_delay)
    upd_configs['semiwarm_delay'] = int(semiwarm_delay + 1)

    print('---analysis for container reuse interval end---')
    # print(f'testing duration: {last_timestamp - start_timestamp} s')
    requests.get(f'http://{config.GATEWAY_URL}/upd_configs', json={function_name: upd_configs})
    gevent.sleep(1)
    start_local_time = time.time()
    request_idx = 0
    for time_stamp in incoming_timestamps:
        if time_stamp > last_timestamp:
            break
        gevent.sleep(max(0, time_stamp - (start_timestamp + time.time() - start_local_time)))
        gevent.spawn(post_request, f'request_{function_name}' + str(request_idx).rjust(5, '0'), function_name)
        request_idx += 1
        # if request_idx == exp_cnt:
        #     break
    gevent.sleep(max(0, last_timestamp - (start_timestamp + time.time() - start_local_time)))
    gevent.sleep(15)




def test_to_all():
    general_tests = {
        0: {'trace_id': 0, 'start_idx': 25011, 'exp_duration': 3600},
        '0-sp1': {'trace_id': 0, 'start_idx': 13958, 'exp_duration': 3600},
        '0-sp2': {'trace_id': 0, 'start_idx': 29277, 'exp_duration': 3600},
        '0-sp3': {'trace_id': 0, 'start_idx': 39348, 'exp_duration': 3600},
        '0-debug': {'trace_id': 0, 'start_idx': 25011, 'exp_duration': 60},
        # '0-ablation': {'trace_id': 0, 'start_idx': 8967, 'exp_duration': 3600 * 8},
        '3-ablation': {'trace_id': 3, 'start_idx': 52391, 'exp_duration': 3600 * 8},
        '2-ablation': {'trace_id': 2, 'start_idx': 18320, 'exp_duration': 3600 * 8},
        2: {'trace_id': 2, 'start_idx': 502, 'exp_duration': 3600},

        3: {'trace_id': 3, 'start_idx': 27267, 'exp_duration': 3600},
        '3-sp1': {'trace_id': 3, 'start_idx': 0, 'exp_duration': 3600},
        4: {'trace_id': 4, 'start_idx': 0, 'exp_duration': 3600},
        5: {'trace_id': 5, 'start_idx': 6168, 'exp_duration': 3600},
        6: {'trace_id': 6, 'start_idx': 35316, 'exp_duration': 3600},
        7: {'trace_id': 7, 'start_idx': 42167, 'exp_duration': 3600},
        8: {'trace_id': 8, 'start_idx': 52, 'exp_duration': 3600},
        9: {'trace_id': 9, 'start_idx': 0, 'exp_duration': 3600},
        10: {'trace_id': 10, 'start_idx': 0, 'exp_duration': 3600},
        11: {'trace_id': 11, 'start_idx': 16, 'exp_duration': 3600},
        12: {'trace_id': 12, 'start_idx': 0, 'exp_duration': 3600},
        17: {'trace_id': 17, 'start_idx': 0, 'exp_duration': 3600},

        14: {'trace_id': 14, 'start_idx': 2009, 'exp_duration': 3600},
        '14-sp1': {'trace_id': 14, 'start_idx': 2370, 'exp_duration': 3600},
        15: {'trace_id': 15, 'start_idx': 4003, 'exp_duration': 3600},
        16: {'trace_id': 16, 'start_idx': 3000, 'exp_duration': 3600},
        '16-sp1': {'trace_id': 16, 'start_idx': 3100, 'exp_duration': 3600},
        25: {'trace_id': 25, 'start_idx': 5017, 'exp_duration': 3600},

        60: {'trace_id': 60, 'start_idx': 0, 'exp_duration': 3600},

        86: {'trace_id': 86, 'start_idx': 0, 'exp_duration': 3600},  # Especially for DAMON

    }
    target_functions = {
        'graph_bfs': {'configs': {'raw_memory': 885, 'cpu': 0.5, 'exec_duration': 0.3}, 'tests': [
            {'test_id': 60, 'configs': {'system': 'FaaSMem'}},
        ]},
        'bert': {'configs': {'raw_memory': 1770, 'cpu': 1, 'exec_duration': 0.15}, 'tests': [
            {'test_id': 60, 'configs': {'system': 'FaaSMem'}},
        ]},
        'html_server': {'configs': {'raw_memory': 354, 'cpu': 0.2, 'exec_duration': 0.15}, 'tests': [

            {'test_id': 60, 'configs': {'system': 'FaaSMem'}},

        ]},

        'float_operation': {'configs': {'raw_memory': 177, 'cpu': 0.5, 'exec_duration': 0.3}, 'tests': [
            {'test_id': 60, 'configs': {'system': 'FaaSMem'}},
        ]},
        'matmul': {'configs': {'raw_memory': 177, 'cpu': 0.5, 'exec_duration': 1.1}, 'tests': [

            {'test_id': 60, 'configs': {'system': 'FaaSMem'}},

        ]},
        'linpack': {'configs': {'raw_memory': 177, 'cpu': 0.5, 'exec_duration': 0.65}, 'tests': [

            {'test_id': 60, 'configs': {'system': 'FaaSMem'}},
        ]},
        'image_processing': {'configs': {'raw_memory': 177, 'cpu': 0.5, 'exec_duration': 1.3}, 'tests': [
            {'test_id': 60, 'configs': {'system': 'FaaSMem'}},

        ]},
        'chameleon': {'configs': {'raw_memory': 177, 'cpu': 0.5, 'exec_duration': 0.5}, 'tests': [

            {'test_id': 60, 'configs': {'system': 'FaaSMem'}},

        ]},
        'pyaes': {'configs': {'raw_memory': 177, 'cpu': 0.5, 'exec_duration': 0.9}, 'tests': [
            {'test_id': 60, 'configs': {'system': 'FaaSMem'}},
        ]},
        'gzip_compression': {'configs': {'raw_memory': 177, 'cpu': 0.5, 'exec_duration': 0.4}, 'tests': [

            {'test_id': 60, 'configs': {'system': 'FaaSMem'}},

        ]},
        'json_dumps_loads': {'configs': {'raw_memory': 177, 'cpu': 0.5, 'exec_duration': 1}, 'tests': [

            {'test_id': 60, 'configs': {'system': 'FaaSMem'}},

        ]},
    }
    latencies.clear()
    for worker_ip in config.WORKERS_IP:
        clean_worker(worker_ip, {})
    for worker_ip in config.WORKERS_IP:
        start_monitor(worker_ip)
    events = []

    for function_name, entry in target_functions.items():
        common_configs = entry['configs']
        for test in entry['tests']:
            test_info = general_tests[test['test_id']]
            now_configs = {}
            now_configs.update(common_configs)
            now_configs.update(test['configs'])
            events.append(gevent.spawn(test_to_one,
                                       function_name,
                                       test_info['trace_id'], test_info['start_idx'], test_info['exp_duration'],
                                       now_configs))


    gevent.joinall(events)
    for worker_ip in config.WORKERS_IP:
        end_monitor(worker_ip)
    time.sleep(5)

    for function_name, logs in latencies.items():
        print(function_name)
        print('total requests count:', len(logs))
        print('avg:', format(sum(logs) / len(logs), '.3f'))
        cal_percentile(logs)

    nowtime = str(datetime.datetime.now())
    suffix = 'AzureTraceLatency_Colocation_' + f'_({input_args})'
    if not os.path.exists('result'):
        os.mkdir('result')
    filepath = os.path.join('result', nowtime + '_' + suffix + '.json')
    save_logs = {'target_functions': target_functions, 'args': input_args,
                 'latencies': latencies}
    with open(filepath, 'w') as f:
        json.dump(save_logs, f)


test_to_all()
